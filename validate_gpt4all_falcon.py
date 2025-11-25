#!/usr/bin/env python3
"""
Phase 10: GPT4All Falcon Local Model Validation
Validates local GPT4All Falcon model with deterministic prompts and telemetry logging
"""

import os
import sys
import time
import json
import sqlite3
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from pathlib import Path

# ============================================================
# Data Models
# ============================================================

@dataclass
class GPT4AllTestResult:
    """Result of a single GPT4All test prompt"""
    prompt: str
    response: str
    inference_time_ms: float
    tokens_generated: int
    temperature: float
    max_tokens: int
    success: bool
    error_message: str = ""
    timestamp: str = ""


@dataclass
class DeterministicValidationResult:
    """Result of deterministic validation (3 identical runs)"""
    prompt: str
    run1_response: str
    run2_response: str
    run3_response: str
    all_identical: bool
    inference_times_ms: List[float]
    avg_inference_time_ms: float


@dataclass
class GPT4AllValidationReport:
    """Complete GPT4All validation report"""
    model_path: str
    model_exists: bool
    model_size_mb: float
    total_prompts_tested: int
    successful_prompts: int
    failed_prompts: int
    deterministic_validation_passed: bool
    test_results: List[Dict[str, Any]]
    deterministic_results: List[Dict[str, Any]]
    avg_inference_time_ms: float
    validation_success: bool
    timestamp: str
    error_message: str = ""


# ============================================================
# GPT4All Falcon Validator
# ============================================================

class GPT4AllValidator:
    """Validates GPT4All Falcon local model"""
    
    def __init__(self, model_path: str = "models/gpt4all-falcon-newbpe-q4_0.gguf",
                 telemetry_db: str = "telemetry.db"):
        self.model_path = model_path
        self.telemetry_db = telemetry_db
        self.gpt4all_model = None
        self.db_conn = None
        
    def check_model_exists(self) -> bool:
        """Check if model file exists"""
        return os.path.exists(self.model_path)
    
    def get_model_size(self) -> float:
        """Get model file size in MB"""
        if not self.check_model_exists():
            return 0.0
        return os.path.getsize(self.model_path) / (1024 * 1024)
    
    def load_model(self) -> bool:
        """Load GPT4All Falcon model"""
        try:
            print(f"📦 Loading GPT4All Falcon model from: {self.model_path}")
            
            # Import GPT4All library
            try:
                from gpt4all import GPT4All
            except ImportError:
                print("❌ GPT4All library not installed. Installing...")
                import subprocess
                subprocess.check_call([sys.executable, "-m", "pip", "install", "gpt4all"])
                from gpt4all import GPT4All
            
            # Load model
            start_time = time.time()
            self.gpt4all_model = GPT4All(
                model_name=os.path.basename(self.model_path),
                model_path=os.path.dirname(self.model_path)
            )
            load_time = (time.time() - start_time) * 1000
            
            print(f"✅ Model loaded successfully in {load_time:.0f}ms")
            
            # Log to telemetry
            self.log_event(
                "gpt4all_model_load",
                f"GPT4All Falcon model loaded in {load_time:.0f}ms",
                "validation"
            )
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            self.log_event(
                "gpt4all_model_load_error",
                f"Failed to load model: {str(e)}",
                "validation"
            )
            return False
    
    def test_prompt(self, prompt: str, temperature: float = 0.0, 
                   max_tokens: int = 100) -> GPT4AllTestResult:
        """Test a single prompt with GPT4All"""
        try:
            print(f"\n🔍 Testing prompt: '{prompt[:60]}...'")
            
            start_time = time.time()
            
            # Generate response
            response = self.gpt4all_model.generate(
                prompt=prompt,
                temp=temperature,
                max_tokens=max_tokens
            )
            
            inference_time = (time.time() - start_time) * 1000
            
            # Count tokens (approximate)
            tokens_generated = len(response.split())
            
            print(f"   ✅ Response: '{response[:80]}...'")
            print(f"   ⏱️  Inference time: {inference_time:.0f}ms")
            print(f"   📊 Tokens: ~{tokens_generated}")
            
            # Log to telemetry
            self.log_event(
                "gpt4all_inference",
                f"Prompt: {prompt[:100]}, Response: {response[:100]}, Time: {inference_time:.0f}ms",
                "validation"
            )
            
            return GPT4AllTestResult(
                prompt=prompt,
                response=response.strip(),
                inference_time_ms=inference_time,
                tokens_generated=tokens_generated,
                temperature=temperature,
                max_tokens=max_tokens,
                success=True,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            
            self.log_event(
                "gpt4all_inference_error",
                f"Prompt failed: {prompt[:100]}, Error: {str(e)}",
                "validation"
            )
            
            return GPT4AllTestResult(
                prompt=prompt,
                response="",
                inference_time_ms=0.0,
                tokens_generated=0,
                temperature=temperature,
                max_tokens=max_tokens,
                success=False,
                error_message=str(e),
                timestamp=datetime.now(timezone.utc).isoformat()
            )
    
    def validate_deterministic(self, prompt: str, runs: int = 3) -> DeterministicValidationResult:
        """Validate deterministic behavior by running same prompt multiple times"""
        print(f"\n🔄 Running deterministic validation ({runs} runs)...")
        print(f"   Prompt: '{prompt}'")
        
        responses = []
        inference_times = []
        
        for i in range(runs):
            print(f"\n   Run {i+1}/{runs}:")
            result = self.test_prompt(prompt, temperature=0.0, max_tokens=50)
            
            if result.success:
                responses.append(result.response)
                inference_times.append(result.inference_time_ms)
            else:
                print(f"   ❌ Run {i+1} failed: {result.error_message}")
                responses.append("")
                inference_times.append(0.0)
        
        # Check if all responses are identical
        all_identical = len(set(responses)) == 1 and responses[0] != ""
        
        avg_time = sum(inference_times) / len(inference_times) if inference_times else 0.0
        
        print(f"\n   🎯 Deterministic Check: {'✅ PASSED' if all_identical else '❌ FAILED'}")
        print(f"   ⏱️  Avg inference time: {avg_time:.0f}ms")
        
        if not all_identical:
            print(f"   ⚠️  Responses differ:")
            for i, resp in enumerate(responses, 1):
                print(f"      Run {i}: '{resp[:60]}...'")
        
        # Log to telemetry
        self.log_event(
            "gpt4all_deterministic_validation",
            f"Deterministic check: {'PASSED' if all_identical else 'FAILED'}, Avg time: {avg_time:.0f}ms",
            "validation"
        )
        
        return DeterministicValidationResult(
            prompt=prompt,
            run1_response=responses[0] if len(responses) > 0 else "",
            run2_response=responses[1] if len(responses) > 1 else "",
            run3_response=responses[2] if len(responses) > 2 else "",
            all_identical=all_identical,
            inference_times_ms=inference_times,
            avg_inference_time_ms=avg_time
        )
    
    def connect_telemetry(self) -> bool:
        """Connect to telemetry database"""
        try:
            self.db_conn = sqlite3.connect(self.telemetry_db)
            
            # Ensure telemetry_events table exists
            cursor = self.db_conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS telemetry_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    details TEXT,
                    module TEXT DEFAULT 'unknown'
                )
            """)
            self.db_conn.commit()
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to telemetry database: {e}")
            return False
    
    def log_event(self, event_type: str, details: str, module: str = "gpt4all_validation"):
        """Log event to telemetry database"""
        if not self.db_conn:
            if not self.connect_telemetry():
                return
        
        try:
            cursor = self.db_conn.cursor()
            cursor.execute(
                "INSERT INTO telemetry_events (timestamp, event_type, details, module) VALUES (?, ?, ?, ?)",
                (datetime.now(timezone.utc).isoformat(), event_type, details, module)
            )
            self.db_conn.commit()
        except Exception as e:
            print(f"⚠️  Failed to log event: {e}")
    
    def run_validation(self) -> GPT4AllValidationReport:
        """Run complete GPT4All validation"""
        print("=" * 60)
        print("GPT4All Falcon Local Model Validation")
        print("=" * 60)
        
        # Check model exists
        model_exists = self.check_model_exists()
        model_size = self.get_model_size()
        
        if not model_exists:
            print(f"❌ Model file not found: {self.model_path}")
            return GPT4AllValidationReport(
                model_path=self.model_path,
                model_exists=False,
                model_size_mb=0.0,
                total_prompts_tested=0,
                successful_prompts=0,
                failed_prompts=0,
                deterministic_validation_passed=False,
                test_results=[],
                deterministic_results=[],
                avg_inference_time_ms=0.0,
                validation_success=False,
                timestamp=datetime.now(timezone.utc).isoformat(),
                error_message="Model file not found"
            )
        
        print(f"✅ Model file found: {self.model_path}")
        print(f"📊 Model size: {model_size:.2f} MB")
        
        # Connect to telemetry
        if not self.connect_telemetry():
            print("⚠️  Telemetry connection failed, continuing without logging")
        
        # Load model
        if not self.load_model():
            return GPT4AllValidationReport(
                model_path=self.model_path,
                model_exists=True,
                model_size_mb=model_size,
                total_prompts_tested=0,
                successful_prompts=0,
                failed_prompts=0,
                deterministic_validation_passed=False,
                test_results=[],
                deterministic_results=[],
                avg_inference_time_ms=0.0,
                validation_success=False,
                timestamp=datetime.now(timezone.utc).isoformat(),
                error_message="Model failed to load"
            )
        
        # Test prompts
        test_prompts = [
            "What is 2 + 2? Answer with just the number.",
            "Name the capital of France in one word.",
            "Is the sky blue? Answer yes or no."
        ]
        
        test_results = []
        successful = 0
        failed = 0
        total_inference_time = 0.0
        
        print("\n" + "=" * 60)
        print("Running Test Prompts")
        print("=" * 60)
        
        for prompt in test_prompts:
            result = self.test_prompt(prompt, temperature=0.0, max_tokens=50)
            test_results.append(result)
            
            if result.success:
                successful += 1
                total_inference_time += result.inference_time_ms
            else:
                failed += 1
        
        avg_inference_time = total_inference_time / successful if successful > 0 else 0.0
        
        # Deterministic validation
        print("\n" + "=" * 60)
        print("Deterministic Validation (3 Runs)")
        print("=" * 60)
        
        deterministic_prompts = [
            "What is 2 + 2? Answer with just the number.",
            "Name the capital of France in one word.",
            "Is the sky blue? Answer yes or no."
        ]
        
        deterministic_results = []
        all_deterministic_passed = True
        
        for prompt in deterministic_prompts:
            det_result = self.validate_deterministic(prompt, runs=3)
            deterministic_results.append(det_result)
            
            if not det_result.all_identical:
                all_deterministic_passed = False
        
        # Generate report
        validation_success = (
            model_exists and 
            successful > 0 and 
            all_deterministic_passed and
            avg_inference_time < 5000  # SLA: <5s per prompt
        )
        
        report = GPT4AllValidationReport(
            model_path=self.model_path,
            model_exists=model_exists,
            model_size_mb=model_size,
            total_prompts_tested=len(test_prompts),
            successful_prompts=successful,
            failed_prompts=failed,
            deterministic_validation_passed=all_deterministic_passed,
            test_results=[asdict(r) for r in test_results],
            deterministic_results=[asdict(r) for r in deterministic_results],
            avg_inference_time_ms=avg_inference_time,
            validation_success=validation_success,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # Print summary
        self.print_summary(report)
        
        # Save report
        self.save_report(report)
        
        # Close telemetry connection
        if self.db_conn:
            self.db_conn.close()
        
        return report
    
    def print_summary(self, report: GPT4AllValidationReport):
        """Print validation summary"""
        print("\n" + "=" * 60)
        print("GPT4ALL VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Model Path: {report.model_path}")
        print(f"Model Exists: {'✅ Yes' if report.model_exists else '❌ No'}")
        print(f"Model Size: {report.model_size_mb:.2f} MB")
        print(f"Total Prompts Tested: {report.total_prompts_tested}")
        print(f"✅ Successful: {report.successful_prompts}")
        print(f"❌ Failed: {report.failed_prompts}")
        print(f"🔄 Deterministic Validation: {'✅ PASSED' if report.deterministic_validation_passed else '❌ FAILED'}")
        print(f"⏱️  Avg Inference Time: {report.avg_inference_time_ms:.0f}ms")
        print(f"🎯 SLA Check (<5000ms): {'✅ PASSED' if report.avg_inference_time_ms < 5000 else '❌ FAILED'}")
        print(f"Validation: {'✅ PASSED' if report.validation_success else '❌ FAILED'}")
        print("=" * 60)
    
    def save_report(self, report: GPT4AllValidationReport):
        """Save validation report to JSON"""
        report_path = "gpt4all_validation.json"
        
        try:
            with open(report_path, 'w') as f:
                json.dump(asdict(report), f, indent=2)
            
            print(f"\n📄 Report saved: {report_path}")
            
        except Exception as e:
            print(f"❌ Failed to save report: {e}")


# ============================================================
# Main Execution
# ============================================================

def main():
    """Main execution"""
    validator = GPT4AllValidator()
    report = validator.run_validation()
    
    # Exit code based on validation success
    if report.validation_success:
        print("\n✅ GPT4All validation PASSED")
        sys.exit(0)
    else:
        print("\n❌ GPT4All validation FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
