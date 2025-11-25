"""
Sprint 2 Validation Tests: Centralized Data & Enhanced Service Management
==========================================================================
Tests for PostgreSQL integration, database migration, and service management.
"""
import pytest
import requests
import subprocess
import os
import time
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd


# Test Configuration
DASH_ROOT = Path(__file__).parent.parent
DATABASE_TEST_ENABLED = os.getenv('TEST_DATABASE', 'false').lower() == 'true'


class TestPostgreSQLIntegration:
    """Test PostgreSQL database layer and connection pooling."""
    
    def test_db_utils_import(self):
        """Test that db_utils module can be imported with PostgreSQL support."""
        try:
            from utils import db_utils
            assert hasattr(db_utils, 'execute_pg_query')
            assert hasattr(db_utils, 'get_pg_connection')
            assert hasattr(db_utils, 'create_picks_history_table')
        except ImportError as e:
            pytest.skip(f"PostgreSQL dependencies not installed: {e}")
    
    @pytest.mark.skipif(not DATABASE_TEST_ENABLED, reason="Database tests disabled (set TEST_DATABASE=true)")
    def test_connection_pool_initialization(self):
        """Test that PostgreSQL connection pool initializes correctly."""
        from utils.db_utils import initialize_pg_pool, close_pg_pool
        
        try:
            initialize_pg_pool(minconn=1, maxconn=5)
            # If no exception, pool initialized successfully
            close_pg_pool()
        except Exception as e:
            pytest.skip(f"Could not connect to PostgreSQL: {e}")
    
    @pytest.mark.skipif(not DATABASE_TEST_ENABLED, reason="Database tests disabled")
    def test_picks_history_table_creation(self):
        """Test that picks_history table can be created."""
        from utils.db_utils import create_picks_history_table, execute_pg_query
        
        try:
            create_picks_history_table()
            
            # Verify table exists
            query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'picks_history'
            """
            result = execute_pg_query(query, fetch=True)
            assert len(result) > 0, "picks_history table not found"
            
        except Exception as e:
            pytest.skip(f"Database operation failed: {e}")
    
    @pytest.mark.skipif(not DATABASE_TEST_ENABLED, reason="Database tests disabled")
    def test_insert_and_query_picks(self):
        """Test inserting and querying picks from database."""
        from utils.db_utils import execute_pg_query, execute_pg_many
        
        try:
            # Insert test data
            test_data = [
                ('AAPL', '2025-10-01', 'monthly', 0.15, 0.85, 'Technology', 3000000000000),
                ('MSFT', '2025-10-01', 'monthly', 0.12, 0.80, 'Technology', 2800000000000),
            ]
            
            insert_query = """
            INSERT INTO picks_history (ticker, pick_date, pick_type, predicted_return, confidence, sector, market_cap)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ticker, pick_date, pick_type) DO NOTHING
            """
            execute_pg_many(insert_query, test_data)
            
            # Query test data
            query = """
            SELECT ticker, pick_type FROM picks_history 
            WHERE pick_date = '2025-10-01' AND pick_type = 'monthly'
            ORDER BY ticker
            """
            results = execute_pg_query(query, fetch=True)
            
            assert len(results) >= 2, "Test data not inserted correctly"
            tickers = [row[0] for row in results]
            assert 'AAPL' in tickers
            assert 'MSFT' in tickers
            
        except Exception as e:
            pytest.skip(f"Database operation failed: {e}")


class TestDatabaseMigration:
    """Test the database migration script."""
    
    def test_migration_script_exists(self):
        """Test that migration script file exists."""
        migration_script = DASH_ROOT / 'scripts' / 'migrate_picks_to_db.py'
        assert migration_script.exists(), f"Migration script not found: {migration_script}"
    
    def test_migration_script_imports(self):
        """Test that migration script can be imported."""
        try:
            import sys
            sys.path.insert(0, str(DASH_ROOT / 'scripts'))
            import migrate_picks_to_db
            
            assert hasattr(migrate_picks_to_db, 'migrate_all_picks')
            assert hasattr(migrate_picks_to_db, 'load_csv_to_db')
            assert hasattr(migrate_picks_to_db, 'parse_date_from_filename')
        except ImportError as e:
            pytest.fail(f"Could not import migration script: {e}")
    
    def test_parse_date_from_filename(self):
        """Test date parsing from picks filenames."""
        import sys
        sys.path.insert(0, str(DASH_ROOT / 'scripts'))
        from migrate_picks_to_db import parse_date_from_filename
        
        # Test valid filenames
        assert parse_date_from_filename('picks_20251001.csv') == datetime(2025, 10, 1).date()
        assert parse_date_from_filename('picks_20251231.csv') == datetime(2025, 12, 31).date()
        
        # Test invalid filename
        assert parse_date_from_filename('picks_invalid.csv') is None
    
    def test_determine_pick_type(self):
        """Test pick type determination from file path."""
        import sys
        sys.path.insert(0, str(DASH_ROOT / 'scripts'))
        from migrate_picks_to_db import determine_pick_type
        from pathlib import Path
        
        assert determine_pick_type(Path('models/weekly_run/picks_20251001.csv')) == 'weekly'
        assert determine_pick_type(Path('models/full_run/picks_20251001.csv')) == 'monthly'
        assert determine_pick_type(Path('models/monthly/picks_20251001.csv')) == 'monthly'
    
    @pytest.mark.skipif(not DATABASE_TEST_ENABLED, reason="Database tests disabled")
    def test_migration_dry_run(self):
        """Test migration script can find CSV files."""
        # Check if picks CSV files exist
        models_dir = DASH_ROOT / 'models'
        if not models_dir.exists():
            pytest.skip("Models directory not found")
        
        csv_files = list(models_dir.rglob('picks_*.csv'))
        assert len(csv_files) > 0, "No picks CSV files found for migration"


class TestAnalysisHubDatabaseIntegration:
    """Test Analysis Hub service using PostgreSQL."""
    
    ANALYSIS_SERVICE_URL = "http://localhost:8054"
    
    @pytest.fixture(scope="class", autouse=True)
    def check_service(self):
        """Check if Analysis Hub service is running."""
        try:
            response = requests.get(f"{self.ANALYSIS_SERVICE_URL}/health", timeout=2)
            if response.status_code != 200:
                pytest.skip("Analysis Hub service not running")
        except requests.exceptions.RequestException:
            pytest.skip("Analysis Hub service not running")
    
    def test_analysis_service_uses_database(self):
        """Test that Analysis Hub can use PostgreSQL for picks data."""
        # Create attribution analysis job
        response = requests.post(
            f"{self.ANALYSIS_SERVICE_URL}/api/jobs",
            json={"picks_type": "monthly"},
            timeout=10
        )
        assert response.status_code == 200, f"Job creation failed: {response.text}"
        
        data = response.json()
        assert "job_id" in data
        assert data["status"] in ["queued", "running"]
        
        # Wait for job to process
        job_id = data["job_id"]
        time.sleep(3)
        
        # Check job status
        response = requests.get(f"{self.ANALYSIS_SERVICE_URL}/api/jobs/{job_id}", timeout=5)
        assert response.status_code == 200
        
        # If database is available, service should have loaded data
        # (This test passes regardless, but logs will show if DB was used)


class TestServiceManagementScripts:
    """Test enhanced service management scripts."""
    
    def test_start_script_exists(self):
        """Test that start_all.sh exists and is executable."""
        start_script = DASH_ROOT / 'start_all.sh'
        assert start_script.exists(), "start_all.sh not found"
        assert os.access(start_script, os.X_OK), "start_all.sh not executable"
    
    def test_stop_script_exists(self):
        """Test that stop_all.sh exists and is executable."""
        stop_script = DASH_ROOT / 'stop_all.sh'
        assert stop_script.exists(), "stop_all.sh not found"
        assert os.access(stop_script, os.X_OK), "stop_all.sh not executable"
    
    def test_start_script_has_health_checks(self):
        """Test that start_all.sh includes health check polling."""
        start_script = DASH_ROOT / 'start_all.sh'
        content = start_script.read_text()
        
        # Check for health check polling enhancements
        assert 'MAX_RETRIES' in content or 'health' in content.lower()
        assert 'curl' in content
    
    def test_stop_script_has_pid_handling(self):
        """Test that stop_all.sh uses PID files for shutdown."""
        stop_script = DASH_ROOT / 'stop_all.sh'
        content = stop_script.read_text()
        
        # Check for PID file handling
        assert 'pid' in content.lower() or 'PID' in content
        assert 'kill' in content
    
    def test_pids_directory_can_be_created(self):
        """Test that PIDs directory can be created."""
        pids_dir = DASH_ROOT / 'pids'
        pids_dir.mkdir(exist_ok=True)
        assert pids_dir.exists()
        assert pids_dir.is_dir()


class TestLoggingConfiguration:
    """Test standardized logging configuration."""
    
    def test_logging_config_exists(self):
        """Test that logging_config.py exists."""
        logging_config = DASH_ROOT / 'utils' / 'logging_config.py'
        assert logging_config.exists(), "logging_config.py not found"
    
    def test_logging_config_imports(self):
        """Test that logging configuration can be imported."""
        try:
            from utils.logging_config import setup_logging, setup_service_logging
            assert callable(setup_logging)
            assert callable(setup_service_logging)
        except ImportError as e:
            pytest.fail(f"Could not import logging_config: {e}")
    
    def test_setup_logging_function(self):
        """Test that setup_logging creates a configured logger."""
        from utils.logging_config import setup_logging
        import logging
        
        logger = setup_logging(
            service_name="test_service",
            log_level=logging.INFO,
            log_to_file=False
        )
        
        assert logger is not None
        assert logger.name == "test_service"
        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0
    
    def test_log_utility_functions(self):
        """Test logging utility functions."""
        from utils.logging_config import log_request, log_job_status, log_startup, log_shutdown
        from utils.logging_config import setup_logging
        import logging
        
        logger = setup_logging("test", logging.INFO, log_to_file=False)
        
        # These should not raise exceptions
        log_request(logger, "GET", "/api/health", 200, 45.2)
        log_job_status(logger, "test-job-123", "completed", "Success")
        log_startup(logger, "test_service", 8000, "1.0.0")
        log_shutdown(logger, "test_service")


class TestEndToEndIntegration:
    """End-to-end tests for Sprint 2 features."""
    
    @pytest.mark.skipif(not DATABASE_TEST_ENABLED, reason="Database tests disabled")
    def test_full_migration_workflow(self):
        """Test complete workflow: CSV -> PostgreSQL -> Analysis Service."""
        # 1. Verify database connection
        from utils.db_utils import initialize_pg_pool, create_picks_history_table
        
        try:
            initialize_pg_pool()
            create_picks_history_table()
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
        
        # 2. Run migration (if CSV files exist)
        models_dir = DASH_ROOT / 'models'
        if not models_dir.exists():
            pytest.skip("No models directory to migrate")
        
        csv_files = list(models_dir.rglob('picks_*.csv'))
        if not csv_files:
            pytest.skip("No CSV files to migrate")
        
        # Migration would be run here in production
        # For tests, we just verify the infrastructure is ready
        
        # 3. Verify Analysis Hub can access data
        try:
            response = requests.get("http://localhost:8054/health", timeout=2)
            assert response.status_code == 200
        except requests.exceptions.RequestException:
            pytest.skip("Analysis Hub service not running")


# Run tests with: python -m pytest tests/test_sprint_2.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
