#!/usr/bin/env python3
"""
Phase 13 - ML Endpoint Validation
Tests all 3 ML models via Flask /ml/predict endpoint
"""

import requests
import json
import time
from typing import Dict, Any, List

BASE_URL = "http://localhost:8050"

def test_ml_endpoint(model_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Test ML prediction endpoint"""
    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/ml/predict",
            json={'model': model_name, 'input': input_data},
            timeout=5
        )
        elapsed = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            result = response.json()
            return {
                'success': True,
                'model': model_name,
                'status_code': response.status_code,
                'elapsed_ms': round(elapsed, 2),
                'result': result
            }
        else:
            return {
                'success': False,
                'model': model_name,
                'status_code': response.status_code,
                'elapsed_ms': round(elapsed, 2),
                'error': response.text
            }
    except Exception as e:
        return {
            'success': False,
            'model': model_name,
            'error': str(e)
        }

def main():
    print("=" * 70)
    print("🧪 PHASE 13 - ML ENDPOINT VALIDATION")
    print("=" * 70)
    
    # Test data for each model
    test_cases = [
        {
            'model': 'forecast',
            'input': {
                'ticker': 'AAPL',
                'prices': [150.0, 152.0, 151.5, 153.0, 154.5, 153.8, 155.0],
                'horizon': 1
            }
        },
        {
            'model': 'clustering',
            'input': {
                'returns': [0.01, 0.02, -0.01, 0.03, 0.015],
                'volatility': 0.15,
                'sharpe_ratio': 1.5,
                'beta': 1.1,
                'alpha': 0.02
            }
        },
        {
            'model': 'strategy',
            'input': {
                'rsi': 65.0,
                'macd': 0.5,
                'ma_20': 150.0,
                'ma_50': 148.0,
                'ma_200': 145.0,
                'volume_ratio': 1.2
            }
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        model_name = test_case['model']
        print(f"\n{i}. Testing {model_name.upper()} Model...")
        
        result = test_ml_endpoint(model_name, test_case['input'])
        results.append(result)
        
        if result['success']:
            print(f"   ✅ Success (HTTP {result['status_code']})")
            print(f"   ⏱️  Response Time: {result['elapsed_ms']}ms")
            
            # Extract key prediction info
            pred = result['result']['result']
            if model_name == 'forecast':
                print(f"   📈 Predicted Price: ${pred['predicted_price']}")
                print(f"   📊 Change: {pred['price_change_pct']:+.2f}%")
            elif model_name == 'clustering':
                print(f"   🎯 Cluster: {pred['cluster_name']} (ID: {pred['cluster_id']})")
            elif model_name == 'strategy':
                print(f"   🎲 Signal: {pred['signal']} (Strength: {pred['signal_strength']})")
        else:
            print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 VALIDATION SUMMARY")
    print("=" * 70)
    
    successful = sum(1 for r in results if r['success'])
    total = len(results)
    success_rate = (successful / total) * 100
    
    print(f"Total Tests: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    if successful > 0:
        avg_time = sum(r.get('elapsed_ms', 0) for r in results if r['success']) / successful
        max_time = max(r.get('elapsed_ms', 0) for r in results if r['success'])
        print(f"Avg Response Time: {avg_time:.2f}ms")
        print(f"Max Response Time: {max_time:.2f}ms")
        print(f"Target Met (<2500ms): {'✅ YES' if max_time < 2500 else '❌ NO'}")
    
    print("\n" + "=" * 70)
    
    # Save results
    with open('phase13_ml_endpoint_test.json', 'w') as f:
        json.dump({
            'timestamp': time.time(),
            'test_cases': test_cases,
            'results': results,
            'summary': {
                'total_tests': total,
                'successful': successful,
                'failed': total - successful,
                'success_rate': success_rate
            }
        }, f, indent=2)
    
    print(f"✅ Results saved to phase13_ml_endpoint_test.json")
    
    return success_rate == 100.0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
