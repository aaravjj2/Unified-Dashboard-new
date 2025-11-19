"""
Phase 1 Local Explainability - Diagnostic Script

Validates the explainability engine with mock data and generates performance reports.

Execution:
    python tests/phase1_local_explainability/phase1_diagnostic.py

Output:
    - outputs/phase1_reports/phase1_diagnostic_report.md
    - outputs/phase1_reports/phase1_diagnostic_summary.json
    - outputs/phase1_reports/explainability_plots/ (PNG files)
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from financial_dashboard.tabs.azure_ml_lab.explainability_engine import (
    generate_explanation,
    generate_batch_explanations,
    MockSHAPEngine
)

# ============================================================================
# CONFIGURATION
# ============================================================================

OUTPUT_DIR = project_root / "outputs" / "phase1_reports"
PLOT_DIR = OUTPUT_DIR / "explainability_plots"
MOCK_DATA_DIR = project_root / "mock_data" / "explainability_samples"

# Test cases
TEST_PREDICTIONS = [
    {'ticker': 'AAPL', 'value': 0.0523, 'target': 'return', 'top_n': 10},
    {'ticker': 'TSLA', 'value': 0.0832, 'target': 'return', 'top_n': 10},
    {'ticker': 'NVDA', 'value': 0.0234, 'target': 'volatility', 'top_n': 10},
    {'ticker': 'MSFT', 'value': -0.0145, 'target': 'return', 'top_n': 8},
    {'ticker': 'GOOGL', 'value': 0.0389, 'target': 'return', 'top_n': 12},
]

# Performance targets
TARGET_INFERENCE_TIME = 3.0  # seconds per explanation


# ============================================================================
# DIAGNOSTIC FUNCTIONS
# ============================================================================

def run_single_explanation_test(pred: Dict) -> Dict:
    """Test single explanation generation and measure performance."""
    print(f"\n🔍 Testing {pred['ticker']} ({pred['target']})...")
    
    start_time = time.time()
    
    try:
        result = generate_explanation(
            ticker=pred['ticker'],
            prediction_value=pred['value'],
            prediction_target=pred['target'],
            top_n_features=pred['top_n'],
            output_dir=PLOT_DIR
        )
        
        elapsed = time.time() - start_time
        
        # Extract top features
        top_features = [f['feature'] for f in result['feature_importance'][:5]]
        
        print(f"  ✅ Success in {elapsed:.3f}s")
        print(f"  📊 Top 5 features: {', '.join(top_features)}")
        
        return {
            'ticker': pred['ticker'],
            'target': pred['target'],
            'status': 'success',
            'elapsed_time': elapsed,
            'top_5_features': top_features,
            'plot_generated': result['plot_path'] is not None,
            'rationale_length': len(result['textual_rationale'])
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"  ❌ Failed in {elapsed:.3f}s: {e}")
        
        return {
            'ticker': pred['ticker'],
            'target': pred['target'],
            'status': 'failed',
            'elapsed_time': elapsed,
            'error': str(e)
        }


def run_batch_test() -> Dict:
    """Test batch explanation generation."""
    print("\n🔄 Running batch explanation test...")
    
    start_time = time.time()
    
    try:
        results = generate_batch_explanations(
            predictions=TEST_PREDICTIONS,
            output_dir=PLOT_DIR
        )
        
        elapsed = time.time() - start_time
        
        success_count = sum(1 for r in results if 'error' not in r)
        
        print(f"  ✅ Batch complete in {elapsed:.3f}s")
        print(f"  📊 {success_count}/{len(results)} successful")
        
        return {
            'status': 'success',
            'total_predictions': len(TEST_PREDICTIONS),
            'successful': success_count,
            'failed': len(results) - success_count,
            'total_time': elapsed,
            'avg_time_per_prediction': elapsed / len(TEST_PREDICTIONS)
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"  ❌ Batch failed in {elapsed:.3f}s: {e}")
        
        return {
            'status': 'failed',
            'error': str(e),
            'total_time': elapsed
        }


def validate_determinism() -> Dict:
    """Verify that explanations are deterministic (same ticker = same output)."""
    print("\n🔁 Validating determinism...")
    
    ticker = 'AAPL'
    
    # Generate explanation twice
    result1 = generate_explanation(ticker, 0.05, 'return', top_n_features=10)
    result2 = generate_explanation(ticker, 0.05, 'return', top_n_features=10)
    
    # Compare feature importance
    features1 = [f['feature'] for f in result1['feature_importance']]
    features2 = [f['feature'] for f in result2['feature_importance']]
    
    shaps1 = [f['shap_value'] for f in result1['feature_importance']]
    shaps2 = [f['shap_value'] for f in result2['feature_importance']]
    
    features_match = features1 == features2
    shaps_match = shaps1 == shaps2
    
    if features_match and shaps_match:
        print("  ✅ Deterministic: Identical outputs for same input")
        status = 'pass'
    else:
        print("  ❌ Non-deterministic: Outputs differ for same input")
        status = 'fail'
    
    return {
        'status': status,
        'features_match': features_match,
        'shaps_match': shaps_match,
        'ticker_tested': ticker
    }


def validate_mock_data_samples() -> Dict:
    """Verify that mock JSON samples are present and valid."""
    print("\n📂 Validating mock data samples...")
    
    expected_files = [
        'sample_explanation_AAPL.json',
        'sample_explanation_TSLA.json',
        'sample_explanation_NVDA_volatility.json'
    ]
    
    results = []
    for filename in expected_files:
        filepath = MOCK_DATA_DIR / filename
        
        if not filepath.exists():
            print(f"  ❌ Missing: {filename}")
            results.append({'file': filename, 'status': 'missing'})
            continue
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Validate structure
            required_keys = ['ticker', 'prediction_value', 'feature_importance', 'textual_rationale']
            missing_keys = [k for k in required_keys if k not in data]
            
            if missing_keys:
                print(f"  ⚠️  Invalid: {filename} (missing keys: {missing_keys})")
                results.append({'file': filename, 'status': 'invalid', 'missing_keys': missing_keys})
            else:
                print(f"  ✅ Valid: {filename}")
                results.append({'file': filename, 'status': 'valid'})
        
        except json.JSONDecodeError as e:
            print(f"  ❌ Corrupt: {filename} ({e})")
            results.append({'file': filename, 'status': 'corrupt', 'error': str(e)})
    
    valid_count = sum(1 for r in results if r['status'] == 'valid')
    
    return {
        'total_files': len(expected_files),
        'valid': valid_count,
        'invalid': len(results) - valid_count,
        'details': results
    }


# ============================================================================
# REPORT GENERATION
# ============================================================================

def generate_markdown_report(diagnostic_results: Dict) -> str:
    """Generate markdown diagnostic report."""
    
    report_lines = [
        "# Phase 1 Local Explainability - Diagnostic Report",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Test Suite:** Phase 1 Local Intelligence",
        "",
        "---",
        "",
        "## 📋 Executive Summary",
        ""
    ]
    
    # Summary stats
    single_tests = diagnostic_results['single_tests']
    batch_test = diagnostic_results['batch_test']
    determinism = diagnostic_results['determinism_test']
    mock_validation = diagnostic_results['mock_data_validation']
    
    total_tests = len(single_tests)
    passed_tests = sum(1 for t in single_tests if t['status'] == 'success')
    
    report_lines.extend([
        f"- **Total Explanations Generated:** {total_tests}",
        f"- **Successful:** {passed_tests}/{total_tests}",
        f"- **Batch Processing:** {'✅ Pass' if batch_test['status'] == 'success' else '❌ Fail'}",
        f"- **Determinism Check:** {'✅ Pass' if determinism['status'] == 'pass' else '❌ Fail'}",
        f"- **Mock Data Samples:** {mock_validation['valid']}/{mock_validation['total_files']} valid",
        "",
        "---",
        "",
        "## 🧪 Individual Explanation Tests",
        ""
    ])
    
    # Table header
    report_lines.extend([
        "| Ticker | Target | Status | Time (s) | Top 5 Features |",
        "|--------|--------|--------|----------|----------------|"
    ])
    
    for test in single_tests:
        status_icon = "✅" if test['status'] == 'success' else "❌"
        features = ", ".join(test.get('top_5_features', [])[:3]) + "..." if test.get('top_5_features') else "N/A"
        
        report_lines.append(
            f"| {test['ticker']} | {test['target']} | {status_icon} | "
            f"{test['elapsed_time']:.3f} | {features} |"
        )
    
    report_lines.extend([
        "",
        "---",
        "",
        "## ⚡ Performance Metrics",
        ""
    ])
    
    # Calculate avg inference time
    avg_time = sum(t['elapsed_time'] for t in single_tests if t['status'] == 'success') / passed_tests
    max_time = max(t['elapsed_time'] for t in single_tests if t['status'] == 'success')
    min_time = min(t['elapsed_time'] for t in single_tests if t['status'] == 'success')
    
    report_lines.extend([
        f"- **Average Inference Time:** {avg_time:.3f}s",
        f"- **Min/Max Time:** {min_time:.3f}s / {max_time:.3f}s",
        f"- **Target (< {TARGET_INFERENCE_TIME}s):** {'✅ Pass' if avg_time < TARGET_INFERENCE_TIME else '❌ Fail'}",
        f"- **Batch Processing Time:** {batch_test.get('total_time', 0):.3f}s for {batch_test.get('total_predictions', 0)} predictions",
        f"- **Avg Time per Prediction (Batch):** {batch_test.get('avg_time_per_prediction', 0):.3f}s",
        "",
        "---",
        "",
        "## 🔁 Determinism Validation",
        ""
    ])
    
    if determinism['status'] == 'pass':
        report_lines.append("✅ **PASS**: Explanations are deterministic (same ticker → same output)")
    else:
        report_lines.append("❌ **FAIL**: Explanations are non-deterministic")
    
    report_lines.extend([
        "",
        f"- Ticker tested: `{determinism['ticker_tested']}`",
        f"- Features match: {determinism['features_match']}",
        f"- SHAP values match: {determinism['shaps_match']}",
        "",
        "---",
        "",
        "## 📂 Mock Data Validation",
        ""
    ])
    
    report_lines.extend([
        f"- **Valid Samples:** {mock_validation['valid']}/{mock_validation['total_files']}",
        ""
    ])
    
    for detail in mock_validation['details']:
        status_icon = {'valid': '✅', 'missing': '❌', 'invalid': '⚠️', 'corrupt': '❌'}.get(detail['status'], '❓')
        report_lines.append(f"  {status_icon} `{detail['file']}` - {detail['status']}")
    
    report_lines.extend([
        "",
        "---",
        "",
        "## 📊 Output Artifacts",
        "",
        f"- **Plots Generated:** {sum(1 for t in single_tests if t.get('plot_generated', False))} PNG files",
        f"- **Plot Directory:** `{PLOT_DIR.relative_to(project_root)}`",
        f"- **JSON Summary:** `{(OUTPUT_DIR / 'phase1_diagnostic_summary.json').relative_to(project_root)}`",
        "",
        "---",
        "",
        "## ✅ Completion Checklist",
        "",
        f"- [{'x' if passed_tests == total_tests else ' '}] All single explanations generated successfully",
        f"- [{'x' if batch_test['status'] == 'success' else ' '}] Batch processing functional",
        f"- [{'x' if avg_time < TARGET_INFERENCE_TIME else ' '}] Performance target met (< {TARGET_INFERENCE_TIME}s avg)",
        f"- [{'x' if determinism['status'] == 'pass' else ' '}] Determinism validated",
        f"- [{'x' if mock_validation['valid'] == mock_validation['total_files'] else ' '}] All mock samples valid",
        "",
        "---",
        "",
        f"**Report Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Phase 1 Status:** {'✅ COMPLETE' if all([passed_tests == total_tests, batch_test['status'] == 'success', determinism['status'] == 'pass']) else '⚠️ ISSUES DETECTED'}"
    ])
    
    return "\n".join(report_lines)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Run all diagnostic tests and generate reports."""
    
    print("="*80)
    print("Phase 1 Local Explainability - Diagnostic Suite")
    print("="*80)
    
    # Ensure output directories exist
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    
    diagnostic_results = {
        'timestamp': datetime.now().isoformat(),
        'single_tests': [],
        'batch_test': {},
        'determinism_test': {},
        'mock_data_validation': {}
    }
    
    # Run individual tests
    print("\n" + "="*80)
    print("SECTION 1: Individual Explanation Tests")
    print("="*80)
    
    for pred in TEST_PREDICTIONS:
        result = run_single_explanation_test(pred)
        diagnostic_results['single_tests'].append(result)
    
    # Run batch test
    print("\n" + "="*80)
    print("SECTION 2: Batch Processing Test")
    print("="*80)
    
    diagnostic_results['batch_test'] = run_batch_test()
    
    # Validate determinism
    print("\n" + "="*80)
    print("SECTION 3: Determinism Validation")
    print("="*80)
    
    diagnostic_results['determinism_test'] = validate_determinism()
    
    # Validate mock data
    print("\n" + "="*80)
    print("SECTION 4: Mock Data Validation")
    print("="*80)
    
    diagnostic_results['mock_data_validation'] = validate_mock_data_samples()
    
    # Generate reports
    print("\n" + "="*80)
    print("SECTION 5: Report Generation")
    print("="*80)
    
    # JSON summary
    json_path = OUTPUT_DIR / 'phase1_diagnostic_summary.json'
    with open(json_path, 'w') as f:
        json.dump(diagnostic_results, f, indent=2)
    print(f"\n📄 JSON summary saved: {json_path.relative_to(project_root)}")
    
    # Markdown report
    markdown_report = generate_markdown_report(diagnostic_results)
    md_path = OUTPUT_DIR / 'phase1_diagnostic_report.md'
    with open(md_path, 'w') as f:
        f.write(markdown_report)
    print(f"📄 Markdown report saved: {md_path.relative_to(project_root)}")
    
    # Final summary
    print("\n" + "="*80)
    print("DIAGNOSTIC COMPLETE")
    print("="*80)
    
    passed = sum(1 for t in diagnostic_results['single_tests'] if t['status'] == 'success')
    total = len(diagnostic_results['single_tests'])
    
    print(f"\n✅ {passed}/{total} tests passed")
    print(f"📊 Reports available in: {OUTPUT_DIR.relative_to(project_root)}")
    
    if passed == total:
        print("\n🎉 Phase 1 Diagnostic: ALL TESTS PASSED")
        return 0
    else:
        print("\n⚠️  Phase 1 Diagnostic: SOME TESTS FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(main())
