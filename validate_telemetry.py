#!/usr/bin/env python3
"""
Telemetry Validation Script
===========================

Purpose: Validate local SQLite telemetry logging functionality

Features:
- Check if telemetry.db exists (create if missing)
- Test logging functionality (write test events)
- Read back last N entries
- Verify event recording accuracy
- Optional: Generate telemetry visualization

Success Criteria:
- SQLite database operational
- Events logged with correct timestamp/details
- Read operations functional
"""

import json
import os
import sqlite3
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class TelemetryEvent:
    """Single telemetry event"""
    id: Optional[int]
    timestamp: str
    event_type: str
    details: str
    module: str = "validation"
    
    
@dataclass
class TelemetryValidationReport:
    """Telemetry validation report"""
    timestamp: str
    database_exists: bool
    database_path: str
    database_created: bool
    test_events_written: int
    test_events_read: int
    validation_success: bool
    recent_events: List[TelemetryEvent]
    error_message: str = ""


class TelemetryValidator:
    """Validate local SQLite telemetry logging"""
    
    def __init__(self, db_path: str = "telemetry.db"):
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None
        self.database_created = False
        
    def check_database_exists(self) -> bool:
        """Check if telemetry database exists"""
        exists = self.db_path.exists()
        print(f"{'✅' if exists else '⚠️ '} Database {'exists' if exists else 'does not exist'}: {self.db_path}")
        return exists
        
    def create_database(self):
        """Create telemetry database with schema"""
        print(f"\n📊 Creating telemetry database: {self.db_path}")
        
        self.conn = sqlite3.connect(str(self.db_path))
        cursor = self.conn.cursor()
        
        # Create telemetry events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                details TEXT,
                module TEXT DEFAULT 'unknown'
            )
        """)
        
        # Create index on timestamp for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON telemetry_events(timestamp DESC)
        """)
        
        self.conn.commit()
        self.database_created = True
        print("✅ Database schema created")
        
    def connect(self):
        """Connect to existing database"""
        if not self.conn:
            self.conn = sqlite3.connect(str(self.db_path))
            print(f"✅ Connected to database: {self.db_path}")
            
    def log_event(self, event_type: str, details: str, module: str = "validation") -> bool:
        """Log a telemetry event"""
        try:
            if not self.conn:
                self.connect()
                
            cursor = self.conn.cursor()
            timestamp = datetime.utcnow().isoformat() + "Z"
            
            cursor.execute("""
                INSERT INTO telemetry_events (timestamp, event_type, details, module)
                VALUES (?, ?, ?, ?)
            """, (timestamp, event_type, details, module))
            
            self.conn.commit()
            print(f"  ✅ Logged: {event_type} - {details[:50]}...")
            return True
            
        except Exception as e:
            print(f"  ❌ Failed to log event: {e}")
            return False
            
    def read_recent_events(self, limit: int = 5) -> List[TelemetryEvent]:
        """Read recent telemetry events"""
        try:
            if not self.conn:
                self.connect()
                
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, timestamp, event_type, details, module
                FROM telemetry_events
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            events = []
            for row in cursor.fetchall():
                event = TelemetryEvent(
                    id=row[0],
                    timestamp=row[1],
                    event_type=row[2],
                    details=row[3],
                    module=row[4]
                )
                events.append(event)
                
            print(f"\n📖 Read {len(events)} recent events:")
            for event in events:
                print(f"  [{event.id}] {event.timestamp} | {event.event_type} | {event.module}")
                print(f"      {event.details[:80]}...")
                
            return events
            
        except Exception as e:
            print(f"❌ Failed to read events: {e}")
            return []
            
    def get_event_count(self) -> int:
        """Get total count of events in database"""
        try:
            if not self.conn:
                self.connect()
                
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM telemetry_events")
            count = cursor.fetchone()[0]
            print(f"📊 Total events in database: {count}")
            return count
            
        except Exception as e:
            print(f"❌ Failed to count events: {e}")
            return 0
            
    def validate(self) -> TelemetryValidationReport:
        """Run complete telemetry validation"""
        print(f"\n{'='*60}")
        print(f"Telemetry Validation")
        print(f"{'='*60}\n")
        
        # Step 1: Check if database exists
        db_exists = self.check_database_exists()
        
        # Step 2: Create or connect to database
        if not db_exists:
            self.create_database()
        else:
            self.connect()
            
        # Step 3: Write test events
        print(f"\n🔍 Writing test events...")
        test_events = [
            ("test_startup", "Telemetry validation started"),
            ("test_openai_call", "OpenAI key rotation validated"),
            ("test_data_write", "Test data written to database"),
            ("test_query_performance", "Database query performance tested"),
            ("test_completion", "Telemetry validation completed")
        ]
        
        written_count = 0
        for event_type, details in test_events:
            if self.log_event(event_type, details):
                written_count += 1
                
        # Step 4: Read back events
        print(f"\n📖 Reading back events...")
        recent_events = self.read_recent_events(limit=10)
        read_count = len(recent_events)
        
        # Step 5: Get total count
        total_count = self.get_event_count()
        
        # Step 6: Validate
        validation_success = (written_count == len(test_events) and read_count > 0)
        
        # Generate report
        report = TelemetryValidationReport(
            timestamp=datetime.utcnow().isoformat() + "Z",
            database_exists=db_exists,
            database_path=str(self.db_path),
            database_created=self.database_created,
            test_events_written=written_count,
            test_events_read=read_count,
            validation_success=validation_success,
            recent_events=recent_events
        )
        
        self.print_summary(report)
        self.save_report(report)
        
        return report
        
    def print_summary(self, report: TelemetryValidationReport):
        """Print validation summary"""
        print(f"\n{'='*60}")
        print(f"TELEMETRY VALIDATION SUMMARY")
        print(f"{'='*60}")
        print(f"Database Path: {report.database_path}")
        print(f"Database Exists: {'✅ Yes' if report.database_exists else '⚠️  No (created)'}")
        print(f"Database Created: {'Yes' if report.database_created else 'No'}")
        print(f"Test Events Written: {report.test_events_written}/5")
        print(f"Test Events Read: {report.test_events_read}")
        print(f"Validation: {'✅ PASSED' if report.validation_success else '❌ FAILED'}")
        print(f"{'='*60}\n")
        
    def save_report(self, report: TelemetryValidationReport):
        """Save JSON report"""
        report_path = "telemetry_validation.json"
        
        # Convert to dict
        report_dict = {
            "timestamp": report.timestamp,
            "database_exists": report.database_exists,
            "database_path": report.database_path,
            "database_created": report.database_created,
            "test_events_written": report.test_events_written,
            "test_events_read": report.test_events_read,
            "validation_success": report.validation_success,
            "recent_events": [asdict(e) for e in report.recent_events],
            "error_message": report.error_message
        }
        
        with open(report_path, "w") as f:
            json.dump(report_dict, f, indent=2)
            
        print(f"📄 Report saved: {report_path}")
        
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print(f"✅ Database connection closed")


def main():
    """Main entry point"""
    try:
        validator = TelemetryValidator()
        report = validator.validate()
        validator.close()
        
        # Exit code
        if report.validation_success:
            print("\n✅ Telemetry validation PASSED")
            sys.exit(0)
        else:
            print("\n❌ Telemetry validation FAILED")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Validation crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
