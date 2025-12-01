"""
Create synthetic test data for picks pipeline validation.
Generates 20 weekly and 20 monthly picks with diverse sectors.
"""

import json
import csv
from pathlib import Path
import random

SECTORS = ['Technology', 'Healthcare', 'Finance', 'Consumer', 'Energy', 'Industrial']
TICKERS_BY_SECTOR = {
    'Technology': ['NVDA', 'AAPL', 'MSFT', 'GOOGL', 'META', 'TSLA', 'AMD', 'INTC', 'ORCL', 'CRM'],
    'Healthcare': ['UNH', 'JNJ', 'PFE', 'ABBV', 'TMO', 'MRK', 'ABT', 'DHR', 'LLY', 'BMY'],
    'Finance': ['JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'AXP', 'SCHW', 'USB'],
    'Consumer': ['AMZN', 'WMT', 'HD', 'NKE', 'MCD', 'SBUX', 'TGT', 'LOW', 'COST', 'DIS'],
    'Energy': ['XOM', 'CVX', 'COP', 'SLB', 'EOG', 'PXD', 'MPC', 'PSX', 'VLO', 'OXY'],
    'Industrial': ['BA', 'CAT', 'GE', 'HON', 'UNP', 'UPS', 'LMT', 'RTX', 'DE', 'MMM']
}

def generate_picks(count=20):
    """Generate synthetic picks with realistic values."""
    picks = []
    used_tickers = set()
    
    # Distribute across sectors
    per_sector = count // len(SECTORS)
    
    for sector, tickers in TICKERS_BY_SECTOR.items():
        for i, ticker in enumerate(tickers[:per_sector]):
            if len(picks) >= count:
                break
                
            picks.append({
                'ticker': ticker,
                'sector': sector,
                'current_price': round(random.uniform(50, 500), 2),
                'daily_change': round(random.uniform(-5, 5), 2),
                'week_start_price': round(random.uniform(50, 500), 2),
                'month_start_price': round(random.uniform(50, 500), 2),
                'return_pct': round(random.uniform(-20, 30), 2),
                'volatility': round(random.uniform(10, 60), 2),
                'profit_loss': round(random.uniform(-100, 150), 2),
                'data_source': 'synthetic',
                'analyzed_at': '2025-11-23T18:30:00',
                'combined_score': round(random.uniform(0.5, 0.95), 4),
                'momentum_score': round(random.uniform(0.4, 1.0), 4),
                'fundamental_score': round(random.uniform(0.3, 0.9), 4),
                'sentiment_score': round(random.uniform(0.2, 0.8), 4)
            })
    
    # Fill remaining if needed
    while len(picks) < count:
        sector = random.choice(list(TICKERS_BY_SECTOR.keys()))
        ticker = random.choice(TICKERS_BY_SECTOR[sector])
        if ticker not in used_tickers:
            picks.append({
                'ticker': ticker,
                'sector': sector,
                'current_price': round(random.uniform(50, 500), 2),
                'daily_change': round(random.uniform(-5, 5), 2),
                'week_start_price': round(random.uniform(50, 500), 2),
                'month_start_price': round(random.uniform(50, 500), 2),
                'return_pct': round(random.uniform(-20, 30), 2),
                'volatility': round(random.uniform(10, 60), 2),
                'profit_loss': round(random.uniform(-100, 150), 2),
                'data_source': 'synthetic',
                'analyzed_at': '2025-11-23T18:30:00',
                'combined_score': round(random.uniform(0.5, 0.95), 4),
                'momentum_score': round(random.uniform(0.4, 1.0), 4),
                'fundamental_score': round(random.uniform(0.3, 0.9), 4),
                'sentiment_score': round(random.uniform(0.2, 0.8), 4)
            })
            used_tickers.add(ticker)
    
    return picks[:count]

# Generate data
weekly_picks = generate_picks(20)
monthly_picks = generate_picks(20)

# Save as CSV to canonical input directory
data_dir = Path('data/picks_input')
data_dir.mkdir(parents=True, exist_ok=True)

weekly_csv = data_dir / 'weekly_source.csv'
monthly_csv = data_dir / 'monthly_source.csv'

# Write weekly CSV
with open(weekly_csv, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=weekly_picks[0].keys())
    writer.writeheader()
    writer.writerows(weekly_picks)

# Write monthly CSV
with open(monthly_csv, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=monthly_picks[0].keys())
    writer.writeheader()
    writer.writerows(monthly_picks)

print(f"✅ Created {weekly_csv} with {len(weekly_picks)} picks")
print(f"✅ Created {monthly_csv} with {len(monthly_picks)} picks")
