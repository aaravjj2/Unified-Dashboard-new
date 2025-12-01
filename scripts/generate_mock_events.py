"""
Script to generate mock events data for testing
Creates outputs/events_latest.parquet with HIGH severity events
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime, timedelta
from pathlib import Path

# Ensure outputs directory exists
Path('outputs').mkdir(exist_ok=True)

# Generate mock HIGH severity events
events_data = [
    {
        'timestamp': (datetime.now() - timedelta(hours=2)).isoformat(),
        'ticker': 'NVDA',
        'severity': 'HIGH',
        'event_type': 'earnings_beat',
        'title': 'NVIDIA beats earnings expectations by 15%',
        'description': 'Strong AI chip demand drives revenue growth',
        'source': 'Reuters',
        'impact_score': 0.85
    },
    {
        'timestamp': (datetime.now() - timedelta(hours=5)).isoformat(),
        'ticker': 'AAPL',
        'severity': 'HIGH',
        'event_type': 'product_launch',
        'title': 'Apple announces new iPhone with breakthrough battery',
        'description': '48-hour battery life in new iPhone model',
        'source': 'Bloomberg',
        'impact_score': 0.78
    },
    {
        'timestamp': (datetime.now() - timedelta(hours=8)).isoformat(),
        'ticker': 'TSLA',
        'severity': 'HIGH',
        'event_type': 'regulatory',
        'title': 'Tesla receives full self-driving approval in California',
        'description': 'Regulatory milestone for autonomous vehicle deployment',
        'source': 'Wall Street Journal',
        'impact_score': 0.92
    },
    {
        'timestamp': (datetime.now() - timedelta(days=1, hours=3)).isoformat(),
        'ticker': 'META',
        'severity': 'HIGH',
        'event_type': 'partnership',
        'title': 'Meta partners with OpenAI for AI integration',
        'description': 'Strategic partnership to integrate advanced AI models',
        'source': 'TechCrunch',
        'impact_score': 0.81
    },
    {
        'timestamp': (datetime.now() - timedelta(days=1, hours=7)).isoformat(),
        'ticker': 'MSFT',
        'severity': 'HIGH',
        'event_type': 'acquisition',
        'title': 'Microsoft acquires leading cybersecurity firm',
        'description': '$5B acquisition strengthens cloud security portfolio',
        'source': 'CNBC',
        'impact_score': 0.74
    },
]

# Create DataFrame
df = pd.DataFrame(events_data)

# Convert to pyarrow table and save as parquet
table = pa.Table.from_pandas(df)
pq.write_table(table, 'outputs/events_latest.parquet')

print(f"✅ Created outputs/events_latest.parquet with {len(events_data)} HIGH severity events")
print(f"   Events for tickers: {', '.join(df['ticker'].unique())}")
