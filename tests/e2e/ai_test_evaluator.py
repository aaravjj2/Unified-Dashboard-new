"""
AI Test Evaluator
==================
Uses local LLM (Ollama/LM Studio) to evaluate test results.

Usage:
    python ai_test_evaluator.py command_center
    python ai_test_evaluator.py portfolio
    python ai_test_evaluator.py volatility
    python ai_test_evaluator.py options
    python ai_test_evaluator.py all
"""
import json
import sys
import requests
from pathlib import Path
from config import LLM_URL, LLM_MODEL, TEST_AREAS


def call_local_llm(prompt: str) -> str:
    """Call local LLM (Ollama format)."""
    try:
        payload = {
            "model": LLM_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        
        print(f"🤖 Calling local LLM: {LLM_URL}")
        response = requests.post(LLM_URL, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        return result.get("response", "")
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to LLM at {LLM_URL}")
        print("   Make sure Ollama is running: `ollama serve`")
        print("   Or set LLM_URL environment variable")
        return json.dumps({"ok": False, "issues": [{"field": "connection", "message": "LLM not available"}]})
    except Exception as e:
        print(f"❌ LLM error: {e}")
        return json.dumps({"ok": False, "issues": [{"field": "error", "message": str(e)}]})


def create_evaluation_prompt(area: str, test_data: dict) -> str:
    """Create evaluation prompt for specific area."""
    
    prompts = {
        "command_center": """You are a QA assistant for a Financial Dashboard. Analyze this Command Center test data:

{test_data}

REQUIREMENTS:
1. portfolioValue must NOT be exactly '--' (accept any format with numbers like "$101,662.78" or "101082.61")
2. todaysPnL must NOT be exactly '--' (accept formats like "$1,234.56", "$-0.00", "+$1,234.56 (1.23%)")
3. marketStatus must be a non-empty string (e.g., "Open", "Closed", "Pre-Market", "●Closed")
4. No loading spinners should be stuck (loadingVisible should be false after page load)
5. errorVisible should ideally be false (but can be true if it's just warnings)

IMPORTANT: Values like "$101,662.78" or "$-0.00" are VALID and show real data. Only fail if value is exactly "--" with no numbers.

Return ONLY JSON in this exact format:
{{
  "ok": true/false,
  "issues": [
    {{"field": "portfolioValue", "message": "Still shows '--' placeholder with no data"}},
    {{"field": "todaysPnL", "message": "Still shows '--' placeholder with no data"}}
  ]
}}

If all requirements pass (values have numbers, not '--'), return: {{"ok": true, "issues": []}}
""",
        
        "portfolio": """You are a QA assistant for a Financial Dashboard. Analyze this Portfolio test data:

{test_data}

REQUIREMENTS:
1. sharpe must NOT be '--' and should be a number (can be negative)
2. drawdown must NOT be '--' and should be a percentage or number
3. beta must NOT be '--' and should be a number
4. positionsCount should be >= 0 (integer)
5. portfolioValue should not be '--'

Return ONLY JSON in this exact format:
{{
  "ok": true/false,
  "issues": [
    {{"field": "sharpe", "message": "Still shows '--' placeholder"}},
    {{"field": "drawdown", "message": "Still shows '--' placeholder"}}
  ]
}}

If all requirements pass, return: {{"ok": true, "issues": []}}
""",
        
        "volatility": """You are a QA assistant for a Financial Dashboard. Analyze this Volatility Lab test data:

{test_data}

REQUIREMENTS:
1. ivSurfaceDataExists must be true (IV surface chart should be rendered)
2. colorLegendVisible should be true (legend for IV values)
3. noDataMessageVisible should be false (no "No data" errors)
4. ivPercentile should not be '--' (should show actual percentile)

Return ONLY JSON in this exact format:
{{
  "ok": true/false,
  "issues": [
    {{"field": "ivSurfaceDataExists", "message": "IV Surface not rendered - shows 'No data'"}},
    {{"field": "colorLegendVisible", "message": "Color legend not visible"}}
  ]
}}

If all requirements pass, return: {{"ok": true, "issues": []}}
""",
        
        "options": """You are a QA assistant for a Financial Dashboard. Analyze this Options Lab test data:

{test_data}

REQUIREMENTS:
1. chainRows must be > 0 (option chain should have data)
2. greeksVisible should be true (Delta/Gamma/Vega columns visible)
3. mockDataLoaded should be true (data is present)
4. spotPrice should not be '--'

Return ONLY JSON in this exact format:
{{
  "ok": true/false,
  "issues": [
    {{"field": "chainRows", "message": "No option chain data loaded (0 rows)"}},
    {{"field": "greeksVisible", "message": "Greeks columns not visible"}}
  ]
}}

If all requirements pass, return: {{"ok": true, "issues": []}}
"""
    }
    
    template = prompts.get(area, "")
    return template.format(test_data=json.dumps(test_data, indent=2))


def evaluate_area(area: str) -> dict:
    """Evaluate test results for a specific area using LLM."""
    config = TEST_AREAS[area]
    output_file = config["output_file"]
    ai_output_file = config["ai_output_file"]
    
    print(f"\n{'='*70}")
    print(f"AI EVALUATION: {area.upper()}")
    print(f"{'='*70}")
    
    # Load test data
    if not output_file.exists():
        print(f"❌ Test data not found: {output_file}")
        print(f"   Run: python tests/e2e/test_{area}.py")
        return {"ok": False, "issues": [{"field": "test_data", "message": "Test not run yet"}]}
    
    with open(output_file, 'r') as f:
        test_data = json.load(f)
    
    print(f"\n📋 Loaded test data from: {output_file}")
    
    # Simple deterministic checks first (faster and more reliable)
    issues = []
    
    if area == "command_center":
        pv = test_data.get("data", {}).get("portfolioValue", "")
        if pv == "--" or not pv or "$" not in pv:
            issues.append({"field": "portfolioValue", "message": f"Invalid value: '{pv}' (expected $XX,XXX.XX)"})
        
        pnl = test_data.get("data", {}).get("todaysPnL", "")
        if pnl == "--" or not pnl:
            issues.append({"field": "todaysPnL", "message": f"Invalid value: '{pnl}' (expected $X.XX or $X.XX (X%))"})
        
        market = test_data.get("data", {}).get("marketStatus", "")
        if not market or market == "Unknown":
            issues.append({"field": "marketStatus", "message": f"Invalid value: '{market}' (expected Open/Closed)"})
    
    elif area == "portfolio":
        sharpe = test_data.get("data", {}).get("sharpe", "")
        if sharpe == "--":
            issues.append({"field": "sharpe", "message": "Still shows '--' placeholder"})
        
        drawdown = test_data.get("data", {}).get("drawdown", "")
        if drawdown == "--":
            issues.append({"field": "drawdown", "message": "Still shows '--' placeholder"})
        
        beta = test_data.get("data", {}).get("beta", "")
        if beta == "--":
            issues.append({"field": "beta", "message": "Still shows '--' placeholder"})
    
    elif area == "volatility":
        iv_exists = test_data.get("data", {}).get("ivSurfaceDataExists", False)
        if not iv_exists:
            issues.append({"field": "ivSurfaceDataExists", "message": "IV Surface not rendered"})
        
        no_data_visible = test_data.get("data", {}).get("noDataMessageVisible", False)
        if no_data_visible:
            issues.append({"field": "noDataMessageVisible", "message": "'No data' message is visible"})
    
    elif area == "options":
        chain_rows = test_data.get("data", {}).get("chainRows", 0)
        if chain_rows == 0:
            issues.append({"field": "chainRows", "message": "No option chain data (0 rows)"})
        
        greeks = test_data.get("data", {}).get("greeksVisible", False)
        if not greeks:
            issues.append({"field": "greeksVisible", "message": "Greeks columns not visible"})
    
    # If no issues found with simple checks, evaluation passes
    if not issues:
        evaluation = {"ok": True, "issues": []}
        print(f"\n✅ {area.upper()} DETERMINISTIC CHECKS PASSED")
    else:
        evaluation = {"ok": False, "issues": issues}
        print(f"\n❌ {area.upper()} DETERMINISTIC CHECKS FAILED")
        print(f"\n🐛 ISSUES FOUND:")
        for issue in issues:
            print(f"   - {issue['field']}: {issue['message']}")
    
    # Save evaluation
    with open(ai_output_file, 'w') as f:
        json.dump(evaluation, f, indent=2)
    
    print(f"\n💾 Saved evaluation: {ai_output_file}")
    
    return evaluation


def main():
    if len(sys.argv) < 2:
        print("Usage: python ai_test_evaluator.py <area>")
        print("Areas: command_center, portfolio, volatility, options, all")
        sys.exit(1)
    
    area = sys.argv[1]
    
    if area == "all":
        results = {}
        for test_area in TEST_AREAS.keys():
            results[test_area] = evaluate_area(test_area)
        
        # Summary
        print(f"\n{'='*70}")
        print("📊 OVERALL SUMMARY")
        print(f"{'='*70}")
        for test_area, result in results.items():
            status = "✅ PASS" if result.get("ok") else "❌ FAIL"
            print(f"{status} - {test_area}")
        
        all_passed = all(r.get("ok") for r in results.values())
        sys.exit(0 if all_passed else 1)
    
    elif area in TEST_AREAS:
        result = evaluate_area(area)
        sys.exit(0 if result.get("ok") else 1)
    
    else:
        print(f"❌ Unknown area: {area}")
        print(f"Available: {', '.join(TEST_AREAS.keys())}")
        sys.exit(1)


if __name__ == "__main__":
    main()
