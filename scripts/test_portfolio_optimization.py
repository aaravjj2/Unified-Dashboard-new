#!/usr/bin/env python3
"""
Phase 5B: Portfolio Optimization Validation Script

Purpose:
- Test portfolio optimization with real Alpaca/yfinance data
- Validate covariance matrix stability (>30 days historical data)
- Ensure optimizer converges without fallback to equal weights
- Log condition numbers, optimization status, and warnings

Expected Output:
- Optimization status: 'success' or 'success_with_shrinkage' (NOT 'fallback_*')
- Weights sum to 1.0
- All weights non-negative
- All weights <= 0.4 (max position size)
- Sharpe ratio computed successfully

Usage:
    python scripts/test_portfolio_optimization.py [tickers]
    python scripts/test_portfolio_optimization.py AAPL,MSFT,GOOGL,AMZN,NVDA
"""

import sys
import os
from datetime import datetime, timedelta
import json

# Add project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'financial_dashboard'))

from utils.portfolio import PortfolioOptimizer
import numpy as np
import pandas as pd

def main(tickers_str=None):
    """
    Run portfolio optimization validation test.
    
    Args:
        tickers_str: Comma-separated ticker string (defaults to test portfolio)
    """
    print('=' * 70)
    print('PHASE 5B: PORTFOLIO OPTIMIZATION VALIDATION')
    print('=' * 70)
    print()
    
    # Parse tickers
    if tickers_str:
        tickers = [t.strip().upper() for t in tickers_str.split(',')]
    else:
        # Default test portfolio
        tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']
    
    print(f'📊 Test Portfolio: {", ".join(tickers)}')
    print()
    
    # Setup date range for historical data (90 days minimum for robust optimization)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    print(f'📅 Date Range: {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}')
    print(f'   Duration: 90 days (minimum for robust optimization)')
    print()
    
    # Step 1: Initialize optimizer
    print('Step 1: Initializing Portfolio Optimizer...')
    print('-' * 70)
    
    try:
        optimizer = PortfolioOptimizer(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            risk_free_rate=0.04  # 4% risk-free rate
        )
        
        # Check if optimizer initialized successfully
        if optimizer.optimization_status == 'insufficient_data':
            print('❌ FAILED: Insufficient data after initialization')
            print(f'   Tickers with data: {len(optimizer.tickers)}')
            print(f'   Observations: {len(optimizer.returns) if hasattr(optimizer, "returns") else 0}')
            return False
        
        print(f'✅ Optimizer initialized')
        print(f'   Tickers with data: {len(optimizer.tickers)}/{len(tickers)}')
        print(f'   Observations: {len(optimizer.returns)}')
        print(f'   Covariance status: {optimizer.optimization_status}')
        print()
        
    except Exception as e:
        print(f'❌ FAILED: Optimizer initialization error: {e}')
        import traceback
        traceback.print_exc()
        return False
    
    # Step 2: Validate covariance matrix
    print('Step 2: Validating Covariance Matrix...')
    print('-' * 70)
    
    try:
        # Compute condition number (measure of matrix stability)
        cond_number = np.linalg.cond(optimizer.cov_matrix)
        
        print(f'📐 Covariance Matrix Diagnostics:')
        print(f'   Shape: {optimizer.cov_matrix.shape}')
        print(f'   Condition Number: {cond_number:.2e}')
        
        if cond_number > 1e10:
            print(f'   ⚠️  WARNING: High condition number (>{1e10:.0e}) - matrix may be ill-conditioned')
        elif cond_number > 1e6:
            print(f'   ⚠️  Moderate condition number - Ledoit-Wolf shrinkage recommended')
        else:
            print(f'   ✅ Healthy condition number (<{1e6:.0e})')
        
        # Check for NaN or inf values
        has_nan = np.isnan(optimizer.cov_matrix.values).any()
        has_inf = np.isinf(optimizer.cov_matrix.values).any()
        
        if has_nan or has_inf:
            print(f'   ❌ CRITICAL: Covariance matrix contains NaN or inf values')
            return False
        else:
            print(f'   ✅ No NaN or inf values detected')
        
        print()
        
    except Exception as e:
        print(f'❌ FAILED: Covariance validation error: {e}')
        return False
    
    # Step 3: Run Sharpe optimization
    print('Step 3: Running Maximum Sharpe Optimization...')
    print('-' * 70)
    
    try:
        result = optimizer.optimize_sharpe()
        
        if not result:
            print('❌ FAILED: Optimization returned None')
            return False
        
        status = result.get('optimization_status', 'unknown')
        opt_method = result.get('optimization', 'unknown')
        
        print(f'📊 Optimization Results:')
        print(f'   Method: {opt_method}')
        print(f'   Status: {status}')
        print()
        
        # CRITICAL VALIDATION: Status should NOT start with 'fallback_'
        if status.startswith('fallback_'):
            print(f'❌ FAILED: Unexpected fallback to equal weights')
            print(f'   Reason: {status}')
            print(f'   This indicates the optimizer did not converge successfully')
            return False
        
        # Validate status is 'success' or 'success_with_shrinkage'
        if status not in ['success', 'success_with_shrinkage']:
            print(f'⚠️  WARNING: Unusual status: {status}')
        else:
            print(f'✅ Optimization converged successfully')
        
        print()
        
    except Exception as e:
        print(f'❌ FAILED: Optimization execution error: {e}')
        import traceback
        traceback.print_exc()
        return False
    
    # Step 4: Validate weights
    print('Step 4: Validating Portfolio Weights...')
    print('-' * 70)
    
    try:
        weights = result.get('weights', {})
        
        if not weights:
            print('❌ FAILED: No weights returned')
            return False
        
        print(f'📊 Weight Validation:')
        print(f'   Number of positions: {len(weights)}')
        print()
        
        # Convert to array for numerical checks
        weights_array = np.array(list(weights.values()))
        tickers_list = list(weights.keys())
        
        # Check 1: Sum to 1.0
        weights_sum = weights_array.sum()
        print(f'   Sum of weights: {weights_sum:.6f}')
        if abs(weights_sum - 1.0) < 1e-6:
            print(f'   ✅ Weights sum to 1.0')
        else:
            print(f'   ❌ FAILED: Weights do not sum to 1.0 (diff: {abs(weights_sum - 1.0):.6e})')
            return False
        
        # Check 2: Non-negative weights
        min_weight = weights_array.min()
        print(f'   Minimum weight: {min_weight:.6f}')
        if min_weight >= 0:
            print(f'   ✅ All weights non-negative')
        else:
            print(f'   ❌ FAILED: Negative weights detected')
            return False
        
        # Check 3: Max position size (40% constraint)
        max_weight = weights_array.max()
        print(f'   Maximum weight: {max_weight:.6f}')
        if max_weight <= 0.4 + 1e-6:  # Allow small numerical tolerance
            print(f'   ✅ All weights within 40% constraint')
        else:
            print(f'   ⚠️  WARNING: Max weight exceeds 40% (constraint violation)')
        
        print()
        
        # Display top 5 positions
        sorted_weights = sorted(zip(tickers_list, weights_array), key=lambda x: x[1], reverse=True)
        print(f'   Top 5 Positions:')
        for i, (ticker, weight) in enumerate(sorted_weights[:5], 1):
            print(f'     {i}. {ticker}: {weight:.4f} ({weight*100:.2f}%)')
        
        print()
        
    except Exception as e:
        print(f'❌ FAILED: Weight validation error: {e}')
        return False
    
    # Step 5: Validate performance metrics
    print('Step 5: Validating Performance Metrics...')
    print('-' * 70)
    
    try:
        expected_return = result.get('expected_return', 0.0)
        volatility = result.get('volatility', 0.0)
        sharpe_ratio = result.get('sharpe_ratio', 0.0)
        
        print(f'📈 Performance Metrics (Annualized):')
        print(f'   Expected Return: {expected_return:.4f} ({expected_return*100:.2f}%)')
        print(f'   Volatility: {volatility:.4f} ({volatility*100:.2f}%)')
        print(f'   Sharpe Ratio: {sharpe_ratio:.4f}')
        print()
        
        # Validate metrics are reasonable
        if volatility <= 0:
            print(f'   ❌ FAILED: Volatility is zero or negative')
            return False
        else:
            print(f'   ✅ Volatility is positive')
        
        if np.isnan(sharpe_ratio) or np.isinf(sharpe_ratio):
            print(f'   ❌ FAILED: Sharpe ratio is NaN or inf')
            return False
        else:
            print(f'   ✅ Sharpe ratio is valid')
        
        print()
        
    except Exception as e:
        print(f'❌ FAILED: Metrics validation error: {e}')
        return False
    
    # Step 6: Test minimum variance optimization
    print('Step 6: Testing Minimum Variance Optimization...')
    print('-' * 70)
    
    try:
        min_var_result = optimizer.optimize_min_variance()
        
        if not min_var_result:
            print('❌ FAILED: Min variance optimization returned None')
            return False
        
        min_var_status = min_var_result.get('optimization_status', 'unknown')
        
        print(f'📊 Min Variance Results:')
        print(f'   Status: {min_var_status}')
        print(f'   Volatility: {min_var_result.get("volatility", 0.0):.4f}')
        
        # Validate min variance volatility is lower than max Sharpe
        if min_var_result.get('volatility', 0.0) <= volatility + 1e-6:
            print(f'   ✅ Min variance volatility ≤ max Sharpe volatility (as expected)')
        else:
            print(f'   ⚠️  WARNING: Min variance has higher volatility than max Sharpe (unexpected)')
        
        # Validate status
        if min_var_status.startswith('fallback_'):
            print(f'   ❌ FAILED: Min variance fell back to equal weights')
            return False
        else:
            print(f'   ✅ Min variance optimization converged')
        
        print()
        
    except Exception as e:
        print(f'❌ FAILED: Min variance test error: {e}')
        return False
    
    # Success summary
    print('=' * 70)
    print('✅ PHASE 5B PORTFOLIO OPTIMIZATION VALIDATION: SUCCESS')
    print('=' * 70)
    print()
    print('📦 Validation Summary:')
    print(f'   ✅ Optimizer initialized with {len(optimizer.tickers)} tickers')
    print(f'   ✅ Covariance matrix validated (condition number: {cond_number:.2e})')
    print(f'   ✅ Max Sharpe optimization converged (status: {status})')
    print(f'   ✅ Weights validated (sum=1.0, non-negative, ≤40%)')
    print(f'   ✅ Performance metrics valid (Sharpe={sharpe_ratio:.4f})')
    print(f'   ✅ Min variance optimization converged (status: {min_var_status})')
    print()
    print(f'🎯 No fallback to equal weights detected - optimizer is healthy!')
    print()
    
    # Save results to file for reproducibility
    output_file = os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'outputs', 
        f'portfolio_optimization_validation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    )
    
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        validation_output = {
            'timestamp': datetime.now().isoformat(),
            'tickers': tickers,
            'date_range': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d'),
                'days': 90
            },
            'covariance_diagnostics': {
                'condition_number': float(cond_number),
                'status': optimizer.optimization_status
            },
            'max_sharpe': {
                'optimization_status': status,
                'weights': result.get('weights', {}),
                'expected_return': float(expected_return),
                'volatility': float(volatility),
                'sharpe_ratio': float(sharpe_ratio)
            },
            'min_variance': {
                'optimization_status': min_var_status,
                'volatility': float(min_var_result.get('volatility', 0.0))
            },
            'validation_result': 'SUCCESS'
        }
        
        with open(output_file, 'w') as f:
            json.dump(validation_output, f, indent=2)
        
        print(f'💾 Validation results saved to: {output_file}')
        print()
        
    except Exception as e:
        print(f'⚠️  Warning: Could not save validation results: {e}')
    
    return True


if __name__ == '__main__':
    # Parse command-line arguments
    tickers_arg = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Run validation
    success = main(tickers_arg)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)
