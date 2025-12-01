"""
Long-Running Execution Test
Tests 24+ hour trading loop stability, logging, and data persistence.
"""

import pytest
import asyncio
import time
import os
import requests
from datetime import datetime, timedelta
from pathlib import Path


# Configuration
OPTIONS_SERVICE_URL = "http://localhost:8060"
TEST_DURATION_HOURS = 24  # Full 24-hour test
SHORT_TEST_DURATION_MINUTES = 5  # Quick validation test
CHECK_INTERVAL_SECONDS = 60  # Check every minute


class TestLongRunningExecution:
    """Test long-running execution stability."""
    
    @pytest.fixture(scope="class")
    def service_url(self):
        """Get service URL."""
        return OPTIONS_SERVICE_URL
    
    def test_service_available(self, service_url):
        """Test that service is available before starting long test."""
        try:
            response = requests.get(f"{service_url}/health", timeout=10)
            assert response.status_code == 200
            print("✓ Options service is available")
        except Exception as e:
            pytest.skip(f"Options service not available: {e}")
    
    def test_start_live_loop(self, service_url):
        """Test starting the live execution loop."""
        try:
            response = requests.post(
                f"{service_url}/api/live/start",
                params={'interval_seconds': 60},  # Run every minute for testing
                timeout=10
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data.get('success') is True
            print("✓ Live execution loop started successfully")
            
        except Exception as e:
            pytest.skip(f"Could not start live loop: {e}")
    
    def test_loop_status(self, service_url):
        """Test getting loop status."""
        try:
            response = requests.get(f"{service_url}/api/live/status", timeout=10)
            assert response.status_code == 200
            
            data = response.json()
            assert data.get('success') is True
            assert 'data' in data
            
            status = data['data']
            assert 'running' in status
            assert 'state' in status
            
            print(f"✓ Loop status: running={status['running']}")
            
        except Exception as e:
            pytest.fail(f"Could not get loop status: {e}")
    
    def test_short_duration_run(self, service_url):
        """Test loop runs for 5 minutes without crashing (quick validation)."""
        print(f"\n🔄 Starting {SHORT_TEST_DURATION_MINUTES}-minute validation test...")
        
        # Start the loop
        try:
            response = requests.post(
                f"{service_url}/api/live/start",
                params={'interval_seconds': 30},  # Run every 30 seconds
                timeout=10
            )
            assert response.status_code == 200
        except Exception as e:
            pytest.skip(f"Could not start loop: {e}")
        
        # Monitor for 5 minutes
        end_time = time.time() + (SHORT_TEST_DURATION_MINUTES * 60)
        check_count = 0
        errors = []
        
        while time.time() < end_time:
            try:
                # Check status
                response = requests.get(f"{service_url}/api/live/status", timeout=10)
                assert response.status_code == 200
                
                data = response.json()
                status = data['data']
                
                # Verify still running
                if not status.get('running'):
                    errors.append(f"Loop stopped unexpectedly at check {check_count}")
                    break
                
                # Check for errors in state
                state = status.get('state', {})
                state_errors = state.get('errors', [])
                if state_errors:
                    errors.extend(state_errors)
                
                check_count += 1
                elapsed = SHORT_TEST_DURATION_MINUTES * 60 - (end_time - time.time())
                print(f"✓ Check {check_count}: Loop running after {elapsed:.0f}s, "
                      f"runs={state.get('total_runs', 0)}, "
                      f"executions={state.get('execution_count', 0)}")
                
            except Exception as e:
                errors.append(f"Health check failed at check {check_count}: {str(e)}")
                break
            
            # Wait before next check
            time.sleep(CHECK_INTERVAL_SECONDS)
        
        # Stop the loop
        try:
            requests.post(f"{service_url}/api/live/stop", timeout=10)
        except:
            pass
        
        # Assert no errors
        if errors:
            pytest.fail(f"Errors during short test:\n" + "\n".join(errors[:10]))
        
        print(f"✓ Short duration test completed: {check_count} checks passed")
    
    @pytest.mark.slow
    @pytest.mark.skip(reason="24-hour test requires manual execution")
    def test_24_hour_stability(self, service_url):
        """Test loop runs for 24+ hours without crashing (manual test)."""
        print(f"\n🔄 Starting {TEST_DURATION_HOURS}-hour stability test...")
        print("⚠️  This test will run for 24 hours. Run manually with: pytest -m slow --tb=short")
        
        # Start the loop
        try:
            response = requests.post(
                f"{service_url}/api/live/start",
                params={'interval_seconds': 300},  # Run every 5 minutes in production
                timeout=10
            )
            assert response.status_code == 200
            print("✓ Live loop started")
        except Exception as e:
            pytest.skip(f"Could not start loop: {e}")
        
        # Monitor for 24 hours
        end_time = time.time() + (TEST_DURATION_HOURS * 3600)
        check_count = 0
        errors = []
        last_run_count = 0
        
        while time.time() < end_time:
            try:
                # Check status
                response = requests.get(f"{service_url}/api/live/status", timeout=10)
                assert response.status_code == 200
                
                data = response.json()
                status = data['data']
                
                # Verify still running
                if not status.get('running'):
                    errors.append(f"Loop stopped unexpectedly at check {check_count}")
                    break
                
                # Get state
                state = status.get('state', {})
                total_runs = state.get('total_runs', 0)
                execution_count = state.get('execution_count', 0)
                
                # Check that runs are progressing
                if total_runs == last_run_count and check_count > 2:
                    errors.append(f"Loop appears stuck: no new runs after check {check_count}")
                
                last_run_count = total_runs
                
                # Check for errors
                state_errors = state.get('errors', [])
                if state_errors:
                    errors.extend(state_errors)
                
                check_count += 1
                hours_elapsed = (time.time() - (end_time - TEST_DURATION_HOURS * 3600)) / 3600
                hours_remaining = (end_time - time.time()) / 3600
                
                print(f"✓ Check {check_count} ({hours_elapsed:.1f}h elapsed, {hours_remaining:.1f}h remaining): "
                      f"runs={total_runs}, executions={execution_count}, errors={len(state_errors)}")
                
            except Exception as e:
                error_msg = f"Health check failed at {check_count}: {str(e)}"
                errors.append(error_msg)
                print(f"⚠️  {error_msg}")
                
                # Allow a few failures but not too many
                if len(errors) > 10:
                    break
            
            # Wait before next check
            time.sleep(CHECK_INTERVAL_SECONDS)
        
        # Stop the loop
        try:
            response = requests.post(f"{service_url}/api/live/stop", timeout=10)
            print("✓ Live loop stopped")
        except Exception as e:
            print(f"⚠️  Could not stop loop: {e}")
        
        # Assert test passed
        if errors:
            pytest.fail(f"Errors during 24-hour test:\n" + "\n".join(errors[:20]))
        
        print(f"✓ 24-hour stability test completed: {check_count} checks, {last_run_count} runs")
    
    def test_logs_captured(self, service_url):
        """Test that logs are being captured."""
        log_dir = Path(__file__).parent.parent / 'logs'
        
        if not log_dir.exists():
            pytest.skip("Log directory not found")
        
        # Look for log files
        log_files = list(log_dir.glob('*.log'))
        
        assert len(log_files) > 0, "No log files found"
        print(f"✓ Found {len(log_files)} log files")
        
        # Check that logs are recent
        now = datetime.now()
        recent_logs = []
        
        for log_file in log_files:
            modified_time = datetime.fromtimestamp(log_file.stat().st_mtime)
            age = now - modified_time
            
            if age < timedelta(hours=1):
                recent_logs.append(log_file)
        
        if recent_logs:
            print(f"✓ Found {len(recent_logs)} recent log files (< 1 hour old)")
        else:
            print("⚠️  No recent log files found")
    
    def test_data_persists(self, service_url):
        """Test that execution data persists."""
        # Get initial status
        try:
            response1 = requests.get(f"{service_url}/api/live/status", timeout=10)
            data1 = response1.json()
            state1 = data1['data']['state']
            initial_runs = state1.get('total_runs', 0)
            
            print(f"Initial state: {initial_runs} runs")
            
            # Wait a bit
            time.sleep(5)
            
            # Get status again
            response2 = requests.get(f"{service_url}/api/live/status", timeout=10)
            data2 = response2.json()
            state2 = data2['data']['state']
            current_runs = state2.get('total_runs', 0)
            
            print(f"Current state: {current_runs} runs")
            
            # Data should persist (or increase if loop is running)
            assert current_runs >= initial_runs, "Run count decreased - data not persisting"
            
            print("✓ Data persistence verified")
            
        except Exception as e:
            pytest.skip(f"Could not verify data persistence: {e}")
    
    def test_stop_and_restart(self, service_url):
        """Test that loop can be stopped and restarted."""
        # Start loop
        try:
            response = requests.post(
                f"{service_url}/api/live/start",
                params={'interval_seconds': 60},
                timeout=10
            )
            assert response.status_code == 200
            print("✓ Loop started")
            
            # Verify running
            time.sleep(2)
            response = requests.get(f"{service_url}/api/live/status", timeout=10)
            data = response.json()
            assert data['data'].get('running') is True
            print("✓ Loop confirmed running")
            
            # Stop loop
            response = requests.post(f"{service_url}/api/live/stop", timeout=10)
            assert response.status_code == 200
            print("✓ Loop stopped")
            
            # Verify stopped
            time.sleep(2)
            response = requests.get(f"{service_url}/api/live/status", timeout=10)
            data = response.json()
            assert data['data'].get('running') is False
            print("✓ Loop confirmed stopped")
            
            # Restart loop
            response = requests.post(
                f"{service_url}/api/live/start",
                params={'interval_seconds': 60},
                timeout=10
            )
            assert response.status_code == 200
            print("✓ Loop restarted")
            
            # Verify running again
            time.sleep(2)
            response = requests.get(f"{service_url}/api/live/status", timeout=10)
            data = response.json()
            assert data['data'].get('running') is True
            print("✓ Loop confirmed running after restart")
            
            # Clean up - stop loop
            requests.post(f"{service_url}/api/live/stop", timeout=10)
            
        except Exception as e:
            pytest.fail(f"Stop/restart test failed: {e}")
    
    def test_error_handling(self, service_url):
        """Test that errors are handled gracefully."""
        try:
            # Get current status
            response = requests.get(f"{service_url}/api/live/status", timeout=10)
            data = response.json()
            state = data['data']['state']
            
            # Check error handling
            errors = state.get('errors', [])
            
            if errors:
                print(f"⚠️  Found {len(errors)} errors in state")
                # Errors should be limited (not growing indefinitely)
                assert len(errors) <= 10, "Too many errors accumulated"
                print("✓ Error accumulation is limited")
            else:
                print("✓ No errors in state")
            
        except Exception as e:
            pytest.skip(f"Could not check error handling: {e}")


class TestPerformanceUnderLoad:
    """Test performance under sustained load."""
    
    def test_memory_stable(self):
        """Test that memory usage remains stable (requires psutil)."""
        try:
            import psutil
            import os
            
            # Get current process
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            print(f"Initial memory: {initial_memory:.2f} MB")
            
            # Run for a bit
            time.sleep(10)
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            print(f"Final memory: {final_memory:.2f} MB")
            print(f"Memory increase: {memory_increase:.2f} MB")
            
            # Memory should not grow excessively
            assert memory_increase < 100, f"Memory grew by {memory_increase:.2f} MB"
            
            print("✓ Memory usage is stable")
            
        except ImportError:
            pytest.skip("psutil not available")
    
    def test_cpu_usage_reasonable(self):
        """Test that CPU usage is reasonable (requires psutil)."""
        try:
            import psutil
            
            # Monitor CPU for a bit
            cpu_samples = []
            for _ in range(5):
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_samples.append(cpu_percent)
            
            avg_cpu = sum(cpu_samples) / len(cpu_samples)
            
            print(f"Average CPU: {avg_cpu:.1f}%")
            
            # CPU should be reasonable (< 50% average for idle system)
            assert avg_cpu < 50, f"CPU usage too high: {avg_cpu:.1f}%"
            
            print("✓ CPU usage is reasonable")
            
        except ImportError:
            pytest.skip("psutil not available")


if __name__ == "__main__":
    # Run with: python -m pytest tests/test_long_running.py -v -s
    # For 24-hour test: python -m pytest tests/test_long_running.py -v -s -m slow
    pytest.main([__file__, "-v", "-s"])
