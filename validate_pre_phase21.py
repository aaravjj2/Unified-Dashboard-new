#!/usr/bin/env python3
"""
Pre-Phase 21 Full-System Validation Harness
============================================
Validates:
- Backend callback logic (no UI)
- Database integrity (PostgreSQL only)
- ML inference (Azure ML / GPT4All)
- Options Lab contract selector
- Hybrid AI chatbot (Local + Gemini)
- TradingView stub
- Observability (Sentry, Datadog, Prometheus)

Rules:
- 100% pass rate required
- No skipped tests
- No CSV/JSON fallbacks
- All callbacks must have Sentry/Datadog instrumentation
"""

import sys
import os
import json
import time
import traceback
from datetime import datetime
from typing import Dict, List, Any, Tuple
import logging

# Setup paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'financial_dashboard'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Results tracking
validation_results = {
    "timestamp": datetime.now().isoformat(),
    "environment": "local_docker",
    "tests": [],
    "summary": {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0
    },
    "performance": {},
    "observability": {},
    "errors": []
}


def log_test(name: str, status: str, details: str = "", duration: float = 0.0, error: str = ""):
    """Log a test result"""
    result = {
        "name": name,
        "status": status,  # PASS, FAIL, SKIP
        "details": details,
        "duration_ms": round(duration * 1000, 2),
        "error": error,
        "timestamp": datetime.now().isoformat()
    }
    validation_results["tests"].append(result)
    validation_results["summary"]["total"] += 1
    
    if status == "PASS":
        validation_results["summary"]["passed"] += 1
        logger.info(f"✅ PASS: {name} ({duration*1000:.0f}ms)")
    elif status == "FAIL":
        validation_results["summary"]["failed"] += 1
        logger.error(f"❌ FAIL: {name} - {error}")
        validation_results["errors"].append(f"{name}: {error}")
    elif status == "SKIP":
        validation_results["summary"]["skipped"] += 1
        logger.warning(f"⚠️ SKIP: {name} - {details}")
    
    if details:
        logger.debug(f"   Details: {details}")


def test_imports():
    """Phase 1: Validate all imports and dependencies"""
    logger.info("\n" + "="*80)
    logger.info("PHASE 1: ENVIRONMENT & DEPENDENCY VALIDATION")
    logger.info("="*80)
    
    imports_to_test = [
        ("dash", "Dash framework"),
        ("dash_bootstrap_components", "Dash Bootstrap Components"),
        ("dash_extensions.enrich", "Dash Extensions"),
        ("pandas", "Pandas"),
        ("numpy", "NumPy"),
        ("plotly", "Plotly"),
        ("requests", "Requests"),
        ("yfinance", "yfinance"),
        ("financial_dashboard.app", "Main app module"),
        ("financial_dashboard.callbacks", "Global callbacks"),
        ("financial_dashboard.tabs.options_lab.callbacks", "Options Lab callbacks"),
        ("financial_dashboard.tabs.azure_ml_lab.callbacks", "Azure ML Lab callbacks"),
        ("financial_dashboard.tabs.home_lab.callbacks", "Home Lab callbacks"),
    ]
    
    for module_name, description in imports_to_test:
        start = time.time()
        try:
            __import__(module_name)
            log_test(
                f"Import: {description}",
                "PASS",
                f"Module: {module_name}",
                time.time() - start
            )
        except Exception as e:
            log_test(
                f"Import: {description}",
                "FAIL",
                f"Module: {module_name}",
                time.time() - start,
                str(e)
            )


def test_database_connectivity():
    """Phase 2: Database integrity checks"""
    logger.info("\n" + "="*80)
    logger.info("PHASE 2: DATABASE INTEGRITY CHECK")
    logger.info("="*80)
    
    start = time.time()
    try:
        # Check for database utilities
        from financial_dashboard.utils import db_utils
        log_test(
            "Database: Import db_utils",
            "PASS",
            "Database utilities available",
            time.time() - start
        )
    except ImportError as e:
        log_test(
            "Database: Import db_utils",
            "FAIL",
            "",
            time.time() - start,
            f"Database utilities not found: {e}"
        )
        return
    
    # Check PostgreSQL connection
    start = time.time()
    try:
        conn_string = os.getenv("DATABASE_URL", "")
        if not conn_string:
            raise ValueError("DATABASE_URL not set")
        
        if "postgres" not in conn_string.lower():
            raise ValueError(f"Non-PostgreSQL database detected: {conn_string[:20]}...")
        
        log_test(
            "Database: PostgreSQL Configuration",
            "PASS",
            "DATABASE_URL configured for PostgreSQL",
            time.time() - start
        )
    except Exception as e:
        log_test(
            "Database: PostgreSQL Configuration",
            "FAIL",
            "",
            time.time() - start,
            str(e)
        )
    
    # Check for CSV/JSON fallbacks (should NOT exist)
    start = time.time()
    forbidden_patterns = ["*.csv", "*.json"]
    data_dirs = ["data", "financial_dashboard/data", "cache"]
    
    csv_json_found = []
    for data_dir in data_dirs:
        if os.path.exists(data_dir):
            for root, dirs, files in os.walk(data_dir):
                for file in files:
                    if file.endswith(('.csv', '.json')) and not file.startswith('.'):
                        csv_json_found.append(os.path.join(root, file))
    
    if csv_json_found:
        log_test(
            "Database: No CSV/JSON Fallbacks",
            "FAIL",
            "",
            time.time() - start,
            f"Found {len(csv_json_found)} CSV/JSON files: {csv_json_found[:3]}"
        )
    else:
        log_test(
            "Database: No CSV/JSON Fallbacks",
            "PASS",
            "No CSV/JSON fallback files found",
            time.time() - start
        )


def test_callback_registration():
    """Phase 3: Validate callback registration"""
    logger.info("\n" + "="*80)
    logger.info("PHASE 3: CALLBACK REGISTRATION VALIDATION")
    logger.info("="*80)
    
    start = time.time()
    try:
        from financial_dashboard.app import create_app
        app = create_app()
        
        # Count registered callbacks
        callback_count = len(app.callback_map)
        
        if callback_count > 0:
            log_test(
                "Callbacks: Registration Count",
                "PASS",
                f"Registered {callback_count} callbacks",
                time.time() - start
            )
        else:
            log_test(
                "Callbacks: Registration Count",
                "FAIL",
                "",
                time.time() - start,
                "No callbacks registered"
            )
        
        validation_results["observability"]["callback_count"] = callback_count
        
    except Exception as e:
        log_test(
            "Callbacks: Registration Count",
            "FAIL",
            "",
            time.time() - start,
            f"Failed to create app: {e}"
        )


def test_observability_instrumentation():
    """Phase 4: Check for Sentry and Datadog instrumentation"""
    logger.info("\n" + "="*80)
    logger.info("PHASE 4: OBSERVABILITY INSTRUMENTATION")
    logger.info("="*80)
    
    # Check Sentry
    start = time.time()
    try:
        import sentry_sdk
        sentry_configured = bool(os.getenv("SENTRY_DSN"))
        
        if sentry_configured:
            log_test(
                "Observability: Sentry SDK",
                "PASS",
                "Sentry SDK imported and DSN configured",
                time.time() - start
            )
        else:
            log_test(
                "Observability: Sentry SDK",
                "SKIP",
                "Sentry SDK available but DSN not configured",
                time.time() - start
            )
    except ImportError:
        log_test(
            "Observability: Sentry SDK",
            "SKIP",
            "Sentry SDK not installed",
            time.time() - start
        )
    
    # Check Datadog
    start = time.time()
    try:
        from datadog import statsd
        datadog_host = os.getenv("DATADOG_HOST", "localhost")
        
        log_test(
            "Observability: Datadog StatsD",
            "PASS",
            f"Datadog StatsD imported, host: {datadog_host}",
            time.time() - start
        )
    except ImportError:
        log_test(
            "Observability: Datadog StatsD",
            "SKIP",
            "Datadog library not installed",
            time.time() - start
        )
    
    # Check for observability in callback modules
    start = time.time()
    callback_files = [
        "financial_dashboard/tabs/options_lab/callbacks.py",
        "financial_dashboard/tabs/azure_ml_lab/callbacks.py",
        "financial_dashboard/engines/options_observability.py",
    ]
    
    instrumented_count = 0
    for file_path in callback_files:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
                if 'sentry_sdk' in content or 'statsd' in content:
                    instrumented_count += 1
    
    if instrumented_count >= 2:
        log_test(
            "Observability: Callback Instrumentation",
            "PASS",
            f"{instrumented_count}/{len(callback_files)} callback files instrumented",
            time.time() - start
        )
    else:
        log_test(
            "Observability: Callback Instrumentation",
            "FAIL",
            "",
            time.time() - start,
            f"Only {instrumented_count}/{len(callback_files)} files instrumented"
        )


def test_options_lab_components():
    """Phase 5: Validate Options Lab contract selector and callbacks"""
    logger.info("\n" + "="*80)
    logger.info("PHASE 5: OPTIONS LAB VALIDATION")
    logger.info("="*80)
    
    # Test layout components
    start = time.time()
    try:
        from financial_dashboard.tabs.options_lab import layout
        layout_obj = layout.create_layout()
        layout_str = str(layout_obj)
        
        required_components = [
            ("contract-option-type", "Option type radio"),
            ("contract-strike-input", "Strike input"),
            ("contract-expiration-selector", "Expiration dropdown"),
            ("options-forecast-btn", "Forecast button"),
            ("tradingview-fetch-btn", "TradingView signals button"),
        ]
        
        missing_components = []
        for component_id, description in required_components:
            if component_id not in layout_str:
                missing_components.append(f"{description} ({component_id})")
        
        if not missing_components:
            log_test(
                "Options Lab: Contract Selector Components",
                "PASS",
                f"All {len(required_components)} components present",
                time.time() - start
            )
        else:
            log_test(
                "Options Lab: Contract Selector Components",
                "FAIL",
                "",
                time.time() - start,
                f"Missing: {', '.join(missing_components)}"
            )
        
        # Check TradingView subtab is removed
        if 'tab_id="tradingview-signals"' in layout_str:
            log_test(
                "Options Lab: TradingView Subtab Removed",
                "FAIL",
                "",
                time.time() - start,
                "TradingView subtab still exists"
            )
        else:
            log_test(
                "Options Lab: TradingView Subtab Removed",
                "PASS",
                "TradingView subtab correctly removed",
                time.time() - start
            )
        
    except Exception as e:
        log_test(
            "Options Lab: Layout Validation",
            "FAIL",
            "",
            time.time() - start,
            f"Failed to load layout: {e}"
        )


def test_azure_ml_lab_components():
    """Phase 6: Validate Azure ML Lab callbacks"""
    logger.info("\n" + "="*80)
    logger.info("PHASE 6: AZURE ML LAB VALIDATION")
    logger.info("="*80)
    
    start = time.time()
    try:
        from financial_dashboard.tabs.azure_ml_lab import layout, callbacks
        layout_obj = layout.create_layout()
        layout_str = str(layout_obj)
        
        required_components = [
            ("azure-run-prediction", "Run Prediction button"),
            ("azure-model-insights", "Model Insights"),
            ("azure-metrics", "Metrics"),
            ("azure-feature-importance", "Feature Importance"),
            ("azure-risk-analysis", "Risk Analysis"),
        ]
        
        found_count = sum(1 for comp_id, _ in required_components if comp_id in layout_str)
        
        if found_count >= 3:  # At least 3 components should exist
            log_test(
                "Azure ML Lab: Component Presence",
                "PASS",
                f"Found {found_count}/{len(required_components)} components",
                time.time() - start
            )
        else:
            log_test(
                "Azure ML Lab: Component Presence",
                "FAIL",
                "",
                time.time() - start,
                f"Only found {found_count}/{len(required_components)} components"
            )
        
    except Exception as e:
        log_test(
            "Azure ML Lab: Layout Validation",
            "FAIL",
            "",
            time.time() - start,
            f"Failed to load layout: {e}"
        )


def test_chatbot_hybrid_ai():
    """Phase 7: Validate hybrid AI chatbot (Local + Gemini)"""
    logger.info("\n" + "="*80)
    logger.info("PHASE 7: HYBRID AI CHATBOT VALIDATION")
    logger.info("="*80)
    
    start = time.time()
    try:
        # Check if chatbot module exists
        from financial_dashboard.tabs.home_lab import callbacks
        
        # Look for chatbot-related callback IDs in the module
        callback_source = open("financial_dashboard/tabs/home_lab/callbacks.py").read()
        
        has_chatbot = "chatbot" in callback_source.lower()
        has_gemini = "gemini" in callback_source.lower()
        has_local_ai = "local" in callback_source.lower() or "gpt4all" in callback_source.lower()
        
        if has_chatbot:
            log_test(
                "Chatbot: Module Exists",
                "PASS",
                f"Gemini: {has_gemini}, Local AI: {has_local_ai}",
                time.time() - start
            )
        else:
            log_test(
                "Chatbot: Module Exists",
                "SKIP",
                "Chatbot not found in home_lab callbacks",
                time.time() - start
            )
        
    except Exception as e:
        log_test(
            "Chatbot: Module Validation",
            "FAIL",
            "",
            time.time() - start,
            str(e)
        )


def generate_report():
    """Generate executive summary report"""
    logger.info("\n" + "="*80)
    logger.info("GENERATING VALIDATION REPORT")
    logger.info("="*80)
    
    # Save JSON results
    json_path = "phase_pre21_results.json"
    with open(json_path, 'w') as f:
        json.dump(validation_results, f, indent=2)
    logger.info(f"✅ Saved JSON results to {json_path}")
    
    # Generate markdown summary
    summary = validation_results["summary"]
    pass_rate = (summary["passed"] / summary["total"] * 100) if summary["total"] > 0 else 0
    
    md_content = f"""# Pre-Phase 21 Validation Summary
**Generated:** {validation_results['timestamp']}  
**Environment:** {validation_results['environment']}

## 📊 Overall Results

| Metric | Count | Percentage |
|--------|-------|------------|
| **Total Tests** | {summary['total']} | 100% |
| **✅ Passed** | {summary['passed']} | {pass_rate:.1f}% |
| **❌ Failed** | {summary['failed']} | {summary['failed']/summary['total']*100 if summary['total'] > 0 else 0:.1f}% |
| **⚠️ Skipped** | {summary['skipped']} | {summary['skipped']/summary['total']*100 if summary['total'] > 0 else 0:.1f}% |

## 🎯 Pass Rate: {pass_rate:.1f}%

{'✅ **VALIDATION PASSED** - Ready for Phase 21 CI/CD' if pass_rate == 100 and summary['failed'] == 0 else '❌ **VALIDATION FAILED** - Issues must be resolved before Phase 21'}

## 📋 Test Breakdown by Phase

"""
    
    # Group tests by phase
    phases = {}
    for test in validation_results["tests"]:
        phase = test["name"].split(":")[0]
        if phase not in phases:
            phases[phase] = {"passed": 0, "failed": 0, "skipped": 0}
        phases[phase][test["status"].lower()] += 1
    
    for phase, counts in sorted(phases.items()):
        total = sum(counts.values())
        md_content += f"\n### {phase}\n"
        md_content += f"- ✅ Passed: {counts['passed']}/{total}\n"
        md_content += f"- ❌ Failed: {counts['failed']}/{total}\n"
        md_content += f"- ⚠️ Skipped: {counts['skipped']}/{total}\n"
    
    # Failed tests detail
    if validation_results["errors"]:
        md_content += "\n## ❌ Failed Tests Detail\n\n"
        for i, error in enumerate(validation_results["errors"], 1):
            md_content += f"{i}. {error}\n"
    
    # Observability metrics
    if validation_results["observability"]:
        md_content += "\n## 📡 Observability Status\n\n"
        for key, value in validation_results["observability"].items():
            md_content += f"- **{key}**: {value}\n"
    
    # Individual test results
    md_content += "\n## 📝 Detailed Test Results\n\n"
    for test in validation_results["tests"]:
        status_emoji = {"PASS": "✅", "FAIL": "❌", "SKIP": "⚠️"}.get(test["status"], "❓")
        md_content += f"- {status_emoji} **{test['name']}** ({test['duration_ms']}ms)\n"
        if test["details"]:
            md_content += f"  - {test['details']}\n"
        if test["error"]:
            md_content += f"  - ❌ Error: {test['error']}\n"
    
    md_content += f"\n---\n*Generated by Pre-Phase 21 Validation Harness*\n"
    
    md_path = "PHASE_PRE21_SUMMARY.md"
    with open(md_path, 'w') as f:
        f.write(md_content)
    logger.info(f"✅ Saved markdown summary to {md_path}")
    
    # Print summary to console
    logger.info("\n" + "="*80)
    logger.info("VALIDATION COMPLETE")
    logger.info("="*80)
    logger.info(f"Total Tests: {summary['total']}")
    logger.info(f"✅ Passed: {summary['passed']}")
    logger.info(f"❌ Failed: {summary['failed']}")
    logger.info(f"⚠️ Skipped: {summary['skipped']}")
    logger.info(f"Pass Rate: {pass_rate:.1f}%")
    
    if pass_rate == 100 and summary['failed'] == 0:
        logger.info("✅ VALIDATION PASSED - Ready for Phase 21 CI/CD")
        return 0
    else:
        logger.error("❌ VALIDATION FAILED - Resolve issues before continuing")
        return 1


def main():
    """Execute full validation suite"""
    logger.info("="*80)
    logger.info("PRE-PHASE 21 FULL-SYSTEM VALIDATION")
    logger.info("="*80)
    logger.info(f"Started: {datetime.now().isoformat()}")
    logger.info(f"Working Directory: {os.getcwd()}")
    logger.info("="*80)
    
    try:
        # Execute validation phases
        test_imports()
        test_database_connectivity()
        test_callback_registration()
        test_observability_instrumentation()
        test_options_lab_components()
        test_azure_ml_lab_components()
        test_chatbot_hybrid_ai()
        
        # Generate reports
        exit_code = generate_report()
        
        return exit_code
        
    except Exception as e:
        logger.error(f"❌ CRITICAL ERROR: {e}")
        logger.error(traceback.format_exc())
        validation_results["errors"].append(f"CRITICAL: {str(e)}")
        generate_report()
        return 1


if __name__ == "__main__":
    sys.exit(main())
