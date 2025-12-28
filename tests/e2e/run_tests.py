#!/usr/bin/env python3
"""
Test Runner - Orchestrates UI tests and AI evaluation
======================================================
Usage:
    python run_tests.py check:command_center
    python run_tests.py check:portfolio
    python run_tests.py check:all
"""
import sys
import subprocess
from pathlib import Path

# Add tests/e2e to path
sys.path.insert(0, str(Path(__file__).parent))

from config import TEST_AREAS


def run_command(cmd: list, description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n🔧 {description}")
    print(f"   Command: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent.parent)
    
    if result.returncode == 0:
        print(f"   ✅ Success")
        return True
    else:
        print(f"   ❌ Failed (exit code: {result.returncode})")
        return False


def check_area(area: str) -> bool:
    """Run UI test + AI evaluation for an area."""
    print(f"\n{'='*70}")
    print(f"🧪 TESTING: {area.upper()}")
    print(f"{'='*70}")
    
    # Step 1: Run UI test
    ui_test_script = Path(__file__).parent / f"test_{area}.py"
    if not ui_test_script.exists():
        print(f"❌ Test script not found: {ui_test_script}")
        return False
    
    ui_success = run_command(
        ["python", str(ui_test_script)],
        f"Running UI test for {area}"
    )
    
    if not ui_success:
        print(f"❌ UI test failed for {area}")
        return False
    
    # Step 2: Run AI evaluation
    ai_eval_script = Path(__file__).parent / "ai_test_evaluator.py"
    ai_success = run_command(
        ["python", str(ai_eval_script), area],
        f"Running AI evaluation for {area}"
    )
    
    return ai_success


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_tests.py <command>")
        print("\nCommands:")
        for area in TEST_AREAS.keys():
            print(f"  check:{area}")
        print(f"  check:all")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "check:all":
        results = {}
        for area in TEST_AREAS.keys():
            results[area] = check_area(area)
        
        # Summary
        print(f"\n{'='*70}")
        print("📊 FINAL RESULTS")
        print(f"{'='*70}")
        for area, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {area}")
        
        all_passed = all(results.values())
        print(f"\n{'='*70}")
        if all_passed:
            print("🎉 ALL TESTS PASSED!")
        else:
            print("❌ SOME TESTS FAILED")
        print(f"{'='*70}")
        
        sys.exit(0 if all_passed else 1)
    
    elif command.startswith("check:"):
        area = command.split(":", 1)[1]
        if area in TEST_AREAS:
            success = check_area(area)
            sys.exit(0 if success else 1)
        else:
            print(f"❌ Unknown area: {area}")
            sys.exit(1)
    
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
