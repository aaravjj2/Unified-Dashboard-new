#!/usr/bin/env python3
"""
Manual E2E Test - Validate All Enhancements
Tests server logs and callback behavior
"""

import time
import requests
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SERVER_URL = "http://localhost:8053"

def test_server_health():
    """Test 1: Server is running and healthy."""
    logger.info("\n=== TEST 1: Server Health ===")
    try:
        resp = requests.get(SERVER_URL, timeout=5)
        if resp.status_code == 200:
            logger.info("✅ Server responding on port 8053")
            return True
        else:
            logger.error(f"❌ Server returned status {resp.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Server not responding: {e}")
        return False

def test_keys_loaded():
    """Test 2: Verify 42 keys loaded from logs."""
    logger.info("\n=== TEST 2: Keys Loading ===")
    try:
        with open('/home/aarav/Unified-Dashboard/server_enhanced.log', 'r') as f:
            logs = f.read()
            if '🔑 Loaded 42 API keys' in logs:
                logger.info("✅ 42 API keys loaded from keys.env")
                return True
            else:
                logger.error("❌ Keys not loaded properly")
                return False
    except Exception as e:
        logger.error(f"❌ Error reading logs: {e}")
        return False

def test_async_components():
    """Test 3: Check async-dropdown.js loads (no ERR_CONNECTION_REFUSED)."""
    logger.info("\n=== TEST 3: Async Components ===")
    try:
        with open('/home/aarav/Unified-Dashboard/server_enhanced.log', 'r') as f:
            logs = f.read()
            # Look for successful async-dropdown.js load
            if 'async-dropdown.v3_3_0' in logs and '200 -' in logs:
                logger.info("✅ async-dropdown.js loading successfully (eager_loading=True worked)")
                return True
            else:
                logger.warning("⚠️ Could not confirm async-dropdown.js status")
                return False
    except Exception as e:
        logger.error(f"❌ Error checking async components: {e}")
        return False

def test_greeks_calculator():
    """Test 4: Test greeks_calculator.py directly."""
    logger.info("\n=== TEST 4: Greeks Calculator ===")
    try:
        from financial_dashboard.tabs.options_lab.greeks_calculator import calculate_all_greeks
        
        # Test with sample option
        greeks = calculate_all_greeks(
            S=150.0,  # spot price
            K=155.0,  # strike
            T=30/365,  # time to expiry (30 days)
            sigma=0.25,  # volatility
            r=0.05,  # risk-free rate
            option_type='call'
        )
        
        if greeks and greeks['delta'] > 0:
            logger.info(f"✅ Greeks calculator working:")
            logger.info(f"   Delta: {greeks['delta']:.4f}, Gamma: {greeks['gamma']:.4f}")
            logger.info(f"   Theta: {greeks['theta']:.4f}, Vega: {greeks['vega']:.4f}")
            return True
        else:
            logger.error("❌ Greeks calculator returned invalid values")
            return False
    except Exception as e:
        logger.error(f"❌ Greeks calculator error: {e}")
        return False

def test_groq_recommendations():
    """Test 5: Test GROQ API integration."""
    logger.info("\n=== TEST 5: GROQ API Integration ===")
    try:
        from financial_dashboard.tabs.options_lab.ml_recommendations import get_groq_recommendation
        from financial_dashboard.utils.load_keys_env import load_keys_env
        
        # Load keys
        load_keys_env()
        
        # Test recommendation
        recommendation = get_groq_recommendation(
            ticker="AAPL",
            spot_price=150.0,
            options_data={'test': 'data'}
        )
        
        # Check if dict or string
        if isinstance(recommendation, dict):
            strategy = recommendation.get('strategy', '')
            rationale = recommendation.get('rationale', '')
            if strategy and len(rationale) > 50:
                logger.info(f"✅ GROQ recommendations working")
                logger.info(f"   Strategy: {strategy}")
                logger.info(f"   Rationale: {rationale[:100]}...")
                return True
        elif isinstance(recommendation, str) and len(recommendation) > 50:
            logger.info(f"✅ GROQ recommendations working ({len(recommendation)} chars)")
            logger.info(f"   Preview: {recommendation[:100]}...")
            return True
        
        logger.warning(f"⚠️ GROQ returned unexpected format: {type(recommendation)}")
        return False
    except Exception as e:
        logger.error(f"❌ GROQ API error: {e}")
        return False

def test_flow_analysis():
    """Test 6: Test flow analysis functions."""
    logger.info("\n=== TEST 6: Flow Analysis ===")
    try:
        from financial_dashboard.tabs.options_lab.analytics import calculate_put_call_ratio, calculate_max_pain
        
        # Sample chain data
        chain_data = {
            'chains': {
                '2025-01-17': {
                    'calls': [
                        {'strike': 150, 'volume': 1000, 'openInterest': 5000},
                        {'strike': 155, 'volume': 800, 'openInterest': 4000}
                    ],
                    'puts': [
                        {'strike': 145, 'volume': 1200, 'openInterest': 6000},
                        {'strike': 140, 'volume': 900, 'openInterest': 4500}
                    ]
                }
            }
        }
        
        # Test P/C ratio
        pcr = calculate_put_call_ratio(chain_data)
        
        # Test max pain
        max_pain_strike, _ = calculate_max_pain(chain_data, '2025-01-17')
        
        if pcr['volume_ratio'] > 0 and max_pain_strike > 0:
            logger.info(f"✅ Flow analysis working:")
            logger.info(f"   P/C Volume: {pcr['volume_ratio']}, P/C OI: {pcr['oi_ratio']}")
            logger.info(f"   Max Pain: ${max_pain_strike}, Sentiment: {pcr['volume_sentiment']}")
            return True
        else:
            logger.error("❌ Flow analysis returned invalid values")
            return False
    except Exception as e:
        logger.error(f"❌ Flow analysis error: {e}")
        return False

def test_callback_errors():
    """Test 7: Check for callback errors in logs."""
    logger.info("\n=== TEST 7: Callback Errors ===")
    try:
        with open('/home/aarav/Unified-Dashboard/server_enhanced.log', 'r') as f:
            logs = f.read()
            
            # Check for recent errors
            error_keywords = [
                'ML recommendations error:',
                'Flow analysis error:',
                'Greeks calculation error:',
                'OptionsMLEngine.__init__'
            ]
            
            recent_errors = []
            for keyword in error_keywords:
                if keyword in logs:
                    # Get last occurrence
                    idx = logs.rfind(keyword)
                    error_line = logs[idx:idx+200]
                    recent_errors.append(error_line.split('\n')[0])
            
            if not recent_errors:
                logger.info("✅ No callback errors found in logs")
                return True
            else:
                logger.warning(f"⚠️ Found {len(recent_errors)} callback errors:")
                for error in recent_errors[:3]:
                    logger.warning(f"   {error}")
                return False
    except Exception as e:
        logger.error(f"❌ Error checking logs: {e}")
        return False

def run_all_tests():
    """Run all manual E2E tests."""
    logger.info("=" * 60)
    logger.info("MANUAL E2E TEST - All Enhancements")
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    results = {}
    
    results['Server Health'] = test_server_health()
    results['Keys Loading'] = test_keys_loaded()
    results['Async Components'] = test_async_components()
    results['Greeks Calculator'] = test_greeks_calculator()
    results['GROQ API'] = test_groq_recommendations()
    results['Flow Analysis'] = test_flow_analysis()
    results['Callback Errors'] = test_callback_errors()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {test_name}")
    
    logger.info("-" * 60)
    logger.info(f"TOTAL: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    logger.info(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
