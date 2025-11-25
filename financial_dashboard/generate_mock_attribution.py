#!/usr/bin/env python3
"""
Generate Mock Attribution Data for Testing

Creates realistic attribution analysis results to populate the Analysis Hub.
"""
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

# Setup paths
BASE_DIR = Path(__file__).parent
ATTRIBUTION_DIR = BASE_DIR / 'attribution'
ATTRIBUTION_DIR.mkdir(exist_ok=True)

def generate_mock_attribution():
    """Generate mock attribution analysis results."""
    print("📊 Generating mock attribution data...")
    
    # Sample tickers from recent picks
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA', 'META', 'AMZN', 'AMD', 'NFLX', 'CRM']
    
    # Generate per-pick attribution data
    attribution_data = []
    
    for ticker in tickers:
        # Random but realistic returns
        realized_return = np.random.normal(0.08, 0.15)  # 8% mean, 15% std
        beta = np.random.uniform(0.8, 1.5)
        benchmark_return = np.random.normal(0.05, 0.10)  # SPY returns
        
        beta_contrib = beta * benchmark_return
        alpha = realized_return - beta_contrib
        
        # Factor contributions (SHAP-based)
        factors = {
            'momentum': np.random.uniform(-0.02, 0.10),
            'sentiment': np.random.uniform(-0.03, 0.08),
            'value': np.random.uniform(-0.01, 0.05),
            'size': np.random.uniform(-0.02, 0.03),
            'quality': np.random.uniform(0.00, 0.06),
            'volatility': np.random.uniform(-0.05, 0.02),
        }
        
        attribution_data.append({
            'ticker': ticker,
            'realized_return': realized_return,
            'beta': beta,
            'beta_contrib': beta_contrib,
            'alpha': alpha,
            'factors': factors
        })
    
    # Save per-pick data
    date_str = datetime.now().strftime('%Y%m%d')
    per_pick_file = ATTRIBUTION_DIR / f'{date_str}_per_pick.parquet'
    
    df = pd.DataFrame([{
        'ticker': item['ticker'],
        'realized_return': item['realized_return'],
        'beta': item['beta'],
        'beta_contrib': item['beta_contrib'],
        'alpha': item['alpha'],
        **{f'factor_{k}': v for k, v in item['factors'].items()}
    } for item in attribution_data])
    
    df.to_parquet(per_pick_file, index=False)
    print(f"  ✓ Saved per-pick data: {per_pick_file}")
    
    # Generate portfolio-level aggregation
    portfolio_data = {
        'date': date_str,
        'total_return': df['realized_return'].mean(),
        'total_alpha': df['alpha'].mean(),
        'avg_beta': df['beta'].mean(),
        'beta_contrib': df['beta_contrib'].mean(),
        'num_picks': len(df),
        'factor_contributions': {
            'momentum': df['factor_momentum'].sum(),
            'sentiment': df['factor_sentiment'].sum(),
            'value': df['factor_value'].sum(),
            'size': df['factor_size'].sum(),
            'quality': df['factor_quality'].sum(),
            'volatility': df['factor_volatility'].sum(),
        },
        'top_performers': df.nlargest(3, 'realized_return')[['ticker', 'realized_return', 'alpha']].to_dict('records'),
        'worst_performers': df.nsmallest(3, 'realized_return')[['ticker', 'realized_return', 'alpha']].to_dict('records')
    }
    
    portfolio_file = ATTRIBUTION_DIR / f'{date_str}_portfolio.json'
    with open(portfolio_file, 'w') as f:
        json.dump(portfolio_data, f, indent=2, default=str)
    
    print(f"  ✓ Saved portfolio data: {portfolio_file}")
    
    # Also save as "latest" for easy access
    latest_per_pick = ATTRIBUTION_DIR / 'latest_per_pick.parquet'
    latest_portfolio = ATTRIBUTION_DIR / 'latest_portfolio.json'
    
    df.to_parquet(latest_per_pick, index=False)
    with open(latest_portfolio, 'w') as f:
        json.dump(portfolio_data, f, indent=2, default=str)
    
    print(f"  ✓ Saved latest files for quick access")
    
    # Print summary
    print(f"\n📈 Attribution Summary:")
    print(f"  Total Return: {portfolio_data['total_return']:.2%}")
    print(f"  Total Alpha: {portfolio_data['total_alpha']:.2%}")
    print(f"  Avg Beta: {portfolio_data['avg_beta']:.2f}")
    print(f"  Number of Picks: {portfolio_data['num_picks']}")
    print(f"\n  Top Factor Contributions:")
    for factor, contrib in sorted(portfolio_data['factor_contributions'].items(), key=lambda x: abs(x[1]), reverse=True):
        print(f"    {factor:12s}: {contrib:+.2%}")
    
    return True

if __name__ == "__main__":
    print("="*60)
    print("🔧 Mock Attribution Data Generator")
    print("="*60)
    
    try:
        generate_mock_attribution()
        print("\n✅ Mock attribution data generated successfully!")
        print("="*60)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
