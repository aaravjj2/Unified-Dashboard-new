"""
Event Classification Pipeline

Classifies news headlines by event type and severity.
Generates outputs/events_latest.parquet for UI consumption.

Usage:
    python3 pipelines/event_classifier.py --tickers AAPL,MSFT,GOOGL --since 2025-10-01
"""

import os
import re
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Tuple
import pandas as pd
import numpy as np
import argparse
import json

# Add parent directory to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent))

from utils import news_fetch

logger = logging.getLogger(__name__)

# Event Classification Rules
EVENT_PATTERNS = {
    'Earnings': {
        'keywords': ['earnings', 'eps', 'revenue', 'beat', 'miss', 'guidance', 'quarter', 'q1', 'q2', 'q3', 'q4', 'fiscal'],
        'severity_high': ['miss', 'cut guidance', 'warning', 'disappoint'],
        'severity_medium': ['beat', 'raise guidance', 'outlook'],
        'severity_low': ['report', 'announce', 'release']
    },
    'M&A': {
        'keywords': ['acquire', 'acquisition', 'merge', 'merger', 'takeover', 'buyout', 'deal', 'purchase'],
        'severity_high': ['hostile', 'reject', 'block'],
        'severity_medium': ['announce', 'close', 'complete'],
        'severity_low': ['explore', 'consider', 'rumor']
    },
    'Regulatory': {
        'keywords': ['fda', 'sec', 'ftc', 'doj', 'investigation', 'lawsuit', 'compliance', 'regulation', 'approval', 'clearance'],
        'severity_high': ['investigation', 'lawsuit', 'reject', 'deny', 'ban', 'fine', 'penalty'],
        'severity_medium': ['review', 'inquiry', 'subpoena'],
        'severity_low': ['approval', 'clearance', 'submit', 'file']
    },
    'Product': {
        'keywords': ['launch', 'release', 'unveil', 'announce', 'recall', 'discontinue', 'defect', 'upgrade'],
        'severity_high': ['recall', 'defect', 'safety', 'discontinue'],
        'severity_medium': ['launch', 'release', 'unveil'],
        'severity_low': ['announce', 'tease', 'preview']
    },
    'Management': {
        'keywords': ['ceo', 'cfo', 'executive', 'resign', 'retire', 'appoint', 'hire', 'fire', 'depart', 'leave'],
        'severity_high': ['resign', 'fire', 'terminate', 'scandal'],
        'severity_medium': ['retire', 'depart', 'appoint'],
        'severity_low': ['hire', 'promote', 'join']
    },
    'Financial': {
        'keywords': ['buyback', 'dividend', 'debt', 'financing', 'raise', 'offering', 'ipo', 'downgrade', 'upgrade'],
        'severity_high': ['downgrade', 'cut', 'suspend', 'default'],
        'severity_medium': ['upgrade', 'raise', 'offering'],
        'severity_low': ['buyback', 'dividend', 'maintain']
    }
}


def classify_headline(headline: str, summary: str = '') -> Tuple[str, str]:
    """
    Classify a headline by event type and severity.
    
    Args:
        headline: News headline text
        summary: Optional summary text
    
    Returns:
        Tuple of (event_type, severity)
    """
    text = (headline + ' ' + summary).lower()
    
    # Find matching event types
    matches = []
    for event_type, patterns in EVENT_PATTERNS.items():
        if any(keyword in text for keyword in patterns['keywords']):
            # Determine severity
            if any(word in text for word in patterns['severity_high']):
                severity = 'HIGH'
            elif any(word in text for word in patterns['severity_medium']):
                severity = 'MEDIUM'
            else:
                severity = 'LOW'
            
            matches.append((event_type, severity))
    
    # Return highest priority match, or General/LOW if no match
    if not matches:
        return ('General', 'LOW')
    
    # Prioritize by severity
    severity_priority = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    matches.sort(key=lambda x: severity_priority[x[1]])
    
    return matches[0]


def run_classification(tickers: list, since_ts: str = None) -> pd.DataFrame:
    """
    Fetch and classify news headlines for given tickers.
    
    Args:
        tickers: List of stock tickers
        since_ts: Fetch news since this date (YYYY-MM-DD)
    
    Returns:
        DataFrame with classified events
    """
    logger.info(f"Fetching headlines for {len(tickers)} tickers...")
    
    # Fetch headlines
    headlines_df = news_fetch.fetch_headlines(tickers, since_ts)
    
    if headlines_df.empty:
        logger.warning("No headlines fetched")
        return pd.DataFrame(columns=['ticker', 'headline', 'timestamp', 'event_type', 'severity', 'source', 'url'])
    
    logger.info(f"Classifying {len(headlines_df)} headlines...")
    
    # Classify each headline
    classifications = []
    for _, row in headlines_df.iterrows():
        event_type, severity = classify_headline(row['headline'], row['summary'])
        classifications.append({
            'ticker': row['ticker'],
            'headline': row['headline'],
            'summary': row['summary'],
            'timestamp': row['timestamp'],
            'event_type': event_type,
            'severity': severity,
            'source': row['source'],
            'url': row['url']
        })
    
    events_df = pd.DataFrame(classifications)
    
    logger.info(f"Classified {len(events_df)} events")
    logger.info(f"Event types: {events_df['event_type'].value_counts().to_dict()}")
    logger.info(f"Severities: {events_df['severity'].value_counts().to_dict()}")
    
    return events_df


def save_outputs(events_df: pd.DataFrame):
    """Save classified events to output files."""
    output_dir = Path('outputs')
    output_dir.mkdir(exist_ok=True)
    
    cache_dir = Path('cache')
    cache_dir.mkdir(exist_ok=True)
    
    # Save main output file
    output_file = output_dir / 'events_latest.parquet'
    events_df.to_parquet(output_file, index=False)
    logger.info(f"Saved events to {output_file}")
    
    # Create aggregated summary for Market Trends
    agg_data = {
        'total_events': len(events_df),
        'high_severity_count': len(events_df[events_df['severity'] == 'HIGH']),
        'by_type': events_df['event_type'].value_counts().to_dict(),
        'by_severity': events_df['severity'].value_counts().to_dict(),
        'by_ticker': events_df['ticker'].value_counts().head(10).to_dict(),
        'generated_at': datetime.now().isoformat()
    }
    
    agg_file = cache_dir / 'events_agg_daily.json'
    with open(agg_file, 'w') as f:
        json.dump(agg_data, f, indent=2)
    logger.info(f"Saved aggregated data to {agg_file}")
    
    # Also save a dated backup
    dated_file = output_dir / f"events_{datetime.now().strftime('%Y%m%d')}.parquet"
    events_df.to_parquet(dated_file, index=False)
    logger.info(f"Saved dated backup to {dated_file}")


def main():
    """Main pipeline execution."""
    parser = argparse.ArgumentParser(description='Classify news headlines')
    parser.add_argument('--tickers', type=str, help='Comma-separated list of tickers')
    parser.add_argument('--ticker-file', type=str, help='Path to file with tickers (one per line)')
    parser.add_argument('--since', type=str, help='Fetch news since date (YYYY-MM-DD)', 
                       default=(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
    parser.add_argument('--universe', type=str, choices=['sp500', 'nasdaq100', 'top200'],
                       help='Use predefined ticker universe')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Determine ticker list
    tickers = []
    
    if args.universe:
        # Load from predefined universe (would need to implement)
        logger.info(f"Loading {args.universe} universe...")
        # Placeholder - would load from data/universes/{args.universe}.txt
        tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'JPM', 'V', 'JNJ']
        logger.info(f"Loaded {len(tickers)} tickers from {args.universe}")
    elif args.ticker_file:
        with open(args.ticker_file, 'r') as f:
            tickers = [line.strip() for line in f if line.strip()]
        logger.info(f"Loaded {len(tickers)} tickers from {args.ticker_file}")
    elif args.tickers:
        tickers = [t.strip() for t in args.tickers.split(',')]
        logger.info(f"Using {len(tickers)} tickers from command line")
    else:
        logger.error("Must specify --tickers, --ticker-file, or --universe")
        return 1
    
    logger.info(f"Starting event classification for {len(tickers)} tickers since {args.since}")
    
    # Run classification
    events_df = run_classification(tickers, args.since)
    
    if events_df.empty:
        logger.warning("No events classified")
        return 0
    
    # Save outputs
    save_outputs(events_df)
    
    # Print summary
    print("\n" + "="*60)
    print("EVENT CLASSIFICATION SUMMARY")
    print("="*60)
    print(f"Total events: {len(events_df)}")
    print(f"High severity: {len(events_df[events_df['severity'] == 'HIGH'])}")
    print(f"Medium severity: {len(events_df[events_df['severity'] == 'MEDIUM'])}")
    print(f"Low severity: {len(events_df[events_df['severity'] == 'LOW'])}")
    print("\nTop event types:")
    print(events_df['event_type'].value_counts().head())
    print("\nTop tickers:")
    print(events_df['ticker'].value_counts().head(10))
    print("="*60)
    
    return 0


if __name__ == '__main__':
    exit(main())
