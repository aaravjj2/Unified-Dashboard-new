#!/usr/bin/env python3
"""
Generate mock event data for testing the events integration.
"""
import pandas as pd
from datetime import datetime, timedelta
import random
import json
from pathlib import Path

# Ensure directories exist
Path('outputs').mkdir(exist_ok=True)
Path('cache').mkdir(exist_ok=True)

# Mock events data
tickers = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA', 'AMZN', 'META']
event_types = ['Earnings', 'M&A', 'Regulatory', 'Product', 'Management', 'Financial']
severities = ['HIGH', 'MEDIUM', 'LOW']
sources = ['MarketWatch', 'Bloomberg', 'Reuters', 'CNBC', 'WSJ']

headlines_templates = {
    'Earnings': [
        "{ticker} Reports Q3 Earnings Beat Estimates",
        "{ticker} Quarterly Results Disappoint Analysts",
        "{ticker} Raises Full-Year Guidance After Strong Quarter",
        "{ticker} Misses Revenue Expectations in Q3"
    ],
    'M&A': [
        "{ticker} Announces $2B Acquisition Deal",
        "{ticker} In Talks to Acquire AI Startup",
        "Regulatory Approval for {ticker} Merger Expected",
        "{ticker} Divests Non-Core Business Unit"
    ],
    'Regulatory': [
        "{ticker} Faces New EU Regulatory Scrutiny",
        "SEC Opens Investigation Into {ticker}",
        "{ticker} Settles Antitrust Case for $500M",
        "New Privacy Rules Impact {ticker} Operations"
    ],
    'Product': [
        "{ticker} Launches Revolutionary New Product Line",
        "{ticker} Delays Flagship Product Release",
        "{ticker} Product Recall Affects 2M Units",
        "{ticker} Unveils Next-Gen AI Platform"
    ],
    'Management': [
        "{ticker} CEO Steps Down Amid Restructuring",
        "{ticker} Appoints New CFO from Fortune 500",
        "{ticker} Board Member Resigns",
        "{ticker} Announces Executive Compensation Changes"
    ],
    'Financial': [
        "{ticker} Announces $10B Share Buyback Program",
        "{ticker} Increases Dividend by 15%",
        "{ticker} Issues $5B in Corporate Bonds",
        "{ticker} Credit Rating Upgraded by Moody's"
    ]
}

# Generate events
events = []
now = datetime.now()

for i in range(100):
    ticker = random.choice(tickers)
    event_type = random.choice(event_types)
    severity = random.choice(severities)
    
    # Higher probability for recent events
    days_ago = random.randint(0, 30)
    hours_ago = random.randint(0, 23)
    timestamp = now - timedelta(days=days_ago, hours=hours_ago)
    
    # Generate headline
    headline_template = random.choice(headlines_templates[event_type])
    headline = headline_template.format(ticker=ticker)
    
    # Generate summary
    summary = f"Summary for {headline.lower()}. This is a {severity.lower()} severity {event_type.lower()} event affecting {ticker}."
    
    event = {
        'ticker': ticker,
        'headline': headline,
        'summary': summary,
        'event_type': event_type,
        'severity': severity,
        'timestamp': timestamp,
        'source': random.choice(sources),
        'url': f'https://example.com/news/{ticker.lower()}/{i}'
    }
    events.append(event)

# Create DataFrame and save
events_df = pd.DataFrame(events)
events_df = events_df.sort_values('timestamp', ascending=False)

# Save to parquet
events_df.to_parquet('outputs/events_latest.parquet', index=False)
print(f"✅ Created outputs/events_latest.parquet with {len(events_df)} events")

# Create aggregated summary
summary = {
    'total_events': len(events_df),
    'high_severity_count': len(events_df[events_df['severity'] == 'HIGH']),
    'medium_severity_count': len(events_df[events_df['severity'] == 'MEDIUM']),
    'low_severity_count': len(events_df[events_df['severity'] == 'LOW']),
    'by_type': events_df['event_type'].value_counts().to_dict(),
    'by_severity': events_df['severity'].value_counts().to_dict(),
    'by_ticker': events_df['ticker'].value_counts().to_dict(),
    'recent_high_severity': events_df[events_df['severity'] == 'HIGH'].head(10)[['ticker', 'headline', 'event_type']].to_dict('records'),
    'last_updated': now.isoformat()
}

# Save summary
with open('cache/events_agg_daily.json', 'w') as f:
    json.dump(summary, f, indent=2)
print(f"✅ Created cache/events_agg_daily.json")

# Print summary stats
print(f"\n📊 Event Summary:")
print(f"   Total events: {summary['total_events']}")
print(f"   HIGH severity: {summary['high_severity_count']}")
print(f"   MEDIUM severity: {summary['medium_severity_count']}")
print(f"   LOW severity: {summary['low_severity_count']}")
print(f"\n📈 By event type:")
for event_type, count in summary['by_type'].items():
    print(f"   {event_type}: {count}")
print(f"\n📈 By ticker:")
for ticker, count in sorted(summary['by_ticker'].items(), key=lambda x: x[1], reverse=True):
    print(f"   {ticker}: {count}")
