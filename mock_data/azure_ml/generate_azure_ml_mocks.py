"""
Mock Data Generator for Azure ML Lab

Generates safe mock datasets for testing Azure ML integration:
- Portfolio mock CSVs
- Market factor mock JSON
- Time series mock data

All data is read-only and isolated from live dashboard data.

Usage:
    python generate_azure_ml_mocks.py
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from pathlib import Path

# Output directory
OUTPUT_DIR = Path(__file__).parent

def generate_portfolio_mock_csv():
    """Generate mock portfolio CSV matching weekly picks format."""
    
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'META', 'TSLA', 'AMD', 'AMZN', 'NFLX', 'CRM']
    
    data = []
    for ticker in tickers:
        base_price = np.random.uniform(100, 500)
        
        data.append({
            'ticker': ticker,
            'last_price': round(base_price, 2),
            'position_size_dollars': round(np.random.uniform(5000, 20000), 2),
            'ret_5d': round(np.random.normal(0.01, 0.05), 4),
            'pred_mean': round(np.random.normal(0.02, 0.03), 4),
            'sector': np.random.choice(['Technology', 'Communication', 'Consumer', 'Financial']),
            'market_cap': round(np.random.uniform(50e9, 3000e9), 0),
            'volume': int(np.random.uniform(1e6, 100e6))
        })
    
    df = pd.DataFrame(data)
    output_path = OUTPUT_DIR / 'mock_portfolio.csv'
    df.to_csv(output_path, index=False)
    
    print(f"✅ Generated mock portfolio CSV: {output_path}")
    print(f"   Tickers: {len(df)}")
    print(f"   Total Value: ${df['position_size_dollars'].sum():,.2f}")
    
    return output_path


def generate_market_factors_json():
    """Generate mock Fama-French factor data."""
    
    dates = pd.date_range(end=datetime.now(), periods=252, freq='D')
    
    factors = {
        'metadata': {
            'source': 'mock_data',
            'generated': datetime.now().isoformat(),
            'description': 'Mock Fama-French 5-factor data for testing',
            'frequency': 'daily',
            'periods': 252
        },
        'factors': []
    }
    
    for date in dates:
        factors['factors'].append({
            'date': date.strftime('%Y-%m-%d'),
            'mkt_rf': round(np.random.normal(0.0004, 0.01), 6),
            'smb': round(np.random.normal(0.0001, 0.005), 6),
            'hml': round(np.random.normal(0.0001, 0.005), 6),
            'rmw': round(np.random.normal(0.0001, 0.004), 6),
            'cma': round(np.random.normal(0.0001, 0.004), 6),
            'rf': round(np.random.uniform(0.00001, 0.00015), 6)
        })
    
    output_path = OUTPUT_DIR / 'mock_market_factors.json'
    with open(output_path, 'w') as f:
        json.dump(factors, f, indent=2)
    
    print(f"✅ Generated mock market factors JSON: {output_path}")
    print(f"   Periods: {len(factors['factors'])}")
    print(f"   Factors: mkt_rf, smb, hml, rmw, cma, rf")
    
    return output_path


def generate_time_series_data():
    """Generate mock historical time series for multiple tickers."""
    
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'META']
    dates = pd.date_range(end=datetime.now(), periods=252, freq='D')
    
    all_data = []
    
    for ticker in tickers:
        base_price = np.random.uniform(100, 500)
        
        # Random walk with drift
        returns = np.random.normal(0.0005, 0.02, len(dates))
        prices = base_price * np.exp(np.cumsum(returns))
        
        for i, date in enumerate(dates):
            all_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'ticker': ticker,
                'open': round(prices[i] * np.random.uniform(0.99, 1.01), 2),
                'high': round(prices[i] * np.random.uniform(1.00, 1.03), 2),
                'low': round(prices[i] * np.random.uniform(0.97, 1.00), 2),
                'close': round(prices[i], 2),
                'volume': int(np.random.uniform(1e6, 50e6)),
                'returns': round(returns[i], 6)
            })
    
    df = pd.DataFrame(all_data)
    output_path = OUTPUT_DIR / 'mock_time_series.csv'
    df.to_csv(output_path, index=False)
    
    print(f"✅ Generated mock time series CSV: {output_path}")
    print(f"   Tickers: {len(tickers)}")
    print(f"   Periods: {len(dates)} days")
    print(f"   Total rows: {len(df)}")
    
    return output_path


def generate_volatility_forecast():
    """Generate mock volatility forecast data."""
    
    dates = pd.date_range(start=datetime.now(), periods=21, freq='D')
    
    volatility_data = {
        'metadata': {
            'model': 'GARCH(1,1)',
            'generated': datetime.now().isoformat(),
            'forecast_horizon': 21,
            'description': 'Mock volatility forecast for testing'
        },
        'forecasts': []
    }
    
    base_vol = 0.20
    for i, date in enumerate(dates):
        vol = base_vol * (1 + np.random.normal(0, 0.05))
        
        volatility_data['forecasts'].append({
            'date': date.strftime('%Y-%m-%d'),
            'forecast_vol': round(vol, 4),
            'lower_bound': round(vol * 0.8, 4),
            'upper_bound': round(vol * 1.2, 4),
            'confidence': round(1.0 - (i / 21) * 0.3, 2)  # Decreasing confidence
        })
    
    output_path = OUTPUT_DIR / 'mock_volatility_forecast.json'
    with open(output_path, 'w') as f:
        json.dump(volatility_data, f, indent=2)
    
    print(f"✅ Generated mock volatility forecast JSON: {output_path}")
    print(f"   Forecast periods: {len(volatility_data['forecasts'])}")
    
    return output_path


def generate_all_mocks():
    """Generate all mock data files."""
    
    print("\n" + "=" * 70)
    print("GENERATING MOCK DATA FOR AZURE ML LAB")
    print("=" * 70 + "\n")
    
    files = [
        generate_portfolio_mock_csv(),
        generate_market_factors_json(),
        generate_time_series_data(),
        generate_volatility_forecast()
    ]
    
    print("\n" + "=" * 70)
    print("MOCK DATA GENERATION COMPLETE")
    print("=" * 70)
    print(f"\nGenerated {len(files)} files in: {OUTPUT_DIR}")
    print("\nFiles:")
    for f in files:
        print(f"  - {f.name}")
    print("\n")
    
    return files


if __name__ == "__main__":
    generate_all_mocks()
