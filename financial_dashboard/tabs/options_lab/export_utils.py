"""
Options Chain Export Module

Provides CSV and JSON export functionality for options data.
"""

import json
import csv
import io
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd
import base64

logger = logging.getLogger(__name__)


def export_chain_to_csv(
    chain_data: Dict[str, Any],
    expiration: str,
    include_header: bool = True
) -> str:
    """
    Export options chain to CSV format.
    
    Args:
        chain_data: Full chain data dict
        expiration: Expiration date to export
        include_header: Include column headers
        
    Returns:
        CSV string
    """
    if not chain_data or expiration not in chain_data.get('chains', {}):
        return ""
    
    chain = chain_data['chains'][expiration]
    calls_df = pd.DataFrame(chain.get('calls', []))
    puts_df = pd.DataFrame(chain.get('puts', []))
    
    # Merge on strike
    if calls_df.empty and puts_df.empty:
        return ""
    
    # Prepare calls with prefix
    if not calls_df.empty:
        calls_df = calls_df.add_prefix('call_')
        if 'call_strike' in calls_df.columns:
            calls_df['strike'] = calls_df['call_strike']
    
    # Prepare puts with prefix
    if not puts_df.empty:
        puts_df = puts_df.add_prefix('put_')
        if 'put_strike' in puts_df.columns:
            puts_df['strike'] = puts_df['put_strike']
    
    # Merge on strike
    if not calls_df.empty and not puts_df.empty:
        merged = pd.merge(
            calls_df, puts_df, 
            on='strike', 
            how='outer'
        ).sort_values('strike')
    elif not calls_df.empty:
        merged = calls_df
    else:
        merged = puts_df
    
    # Add metadata
    ticker = chain_data.get('ticker', 'UNKNOWN')
    spot = chain_data.get('spot_price', 0)
    timestamp = chain_data.get('timestamp', datetime.now().isoformat())
    
    # Create CSV
    output = io.StringIO()
    
    # Write metadata as comments
    output.write(f"# Ticker: {ticker}\n")
    output.write(f"# Expiration: {expiration}\n")
    output.write(f"# Spot Price: {spot}\n")
    output.write(f"# Export Time: {timestamp}\n")
    output.write(f"# Source: Alpaca Options\n")
    output.write("#\n")
    
    merged.to_csv(output, index=False, header=include_header)
    
    return output.getvalue()


def export_chain_to_json(
    chain_data: Dict[str, Any],
    expiration: Optional[str] = None,
    pretty: bool = True
) -> str:
    """
    Export options chain to JSON format.
    
    Args:
        chain_data: Full chain data dict
        expiration: Optional specific expiration (exports all if None)
        pretty: Pretty-print JSON
        
    Returns:
        JSON string
    """
    if not chain_data:
        return "{}"
    
    export_data = {
        'ticker': chain_data.get('ticker'),
        'spot_price': chain_data.get('spot_price'),
        'timestamp': chain_data.get('timestamp'),
        'export_time': datetime.now().isoformat(),
        'source': 'alpaca_options'
    }
    
    if expiration and expiration in chain_data.get('chains', {}):
        # Export single expiration
        export_data['expirations'] = [expiration]
        export_data['chains'] = {
            expiration: chain_data['chains'][expiration]
        }
    else:
        # Export all expirations
        export_data['expirations'] = chain_data.get('expirations', [])
        export_data['chains'] = chain_data.get('chains', {})
    
    indent = 2 if pretty else None
    return json.dumps(export_data, indent=indent, default=str)


def create_download_link(
    data: str,
    filename: str,
    mime_type: str = "text/csv"
) -> Dict[str, Any]:
    """
    Create a download link for Dash dcc.Download component.
    
    Args:
        data: File content
        filename: Download filename
        mime_type: MIME type
        
    Returns:
        Dict for dcc.Download component
    """
    # Encode data as base64 for data URI
    b64 = base64.b64encode(data.encode()).decode()
    
    return {
        'content': data,
        'filename': filename,
        'type': mime_type
    }


def export_greeks_summary(chain_data: Dict[str, Any], expiration: str) -> str:
    """
    Export Greeks summary to CSV.
    
    Args:
        chain_data: Full chain data
        expiration: Expiration to summarize
        
    Returns:
        CSV string with Greeks summary
    """
    if not chain_data or expiration not in chain_data.get('chains', {}):
        return ""
    
    chain = chain_data['chains'][expiration]
    calls = chain.get('calls', [])
    puts = chain.get('puts', [])
    
    # Calculate aggregate Greeks
    summary = []
    
    for strike_data in calls:
        summary.append({
            'strike': strike_data.get('strike'),
            'type': 'call',
            'delta': strike_data.get('delta', 0),
            'gamma': strike_data.get('gamma', 0),
            'theta': strike_data.get('theta', 0),
            'vega': strike_data.get('vega', 0),
            'iv': strike_data.get('impliedVolatility', 0),
            'volume': strike_data.get('volume', 0),
            'oi': strike_data.get('openInterest', 0)
        })
    
    for strike_data in puts:
        summary.append({
            'strike': strike_data.get('strike'),
            'type': 'put',
            'delta': strike_data.get('delta', 0),
            'gamma': strike_data.get('gamma', 0),
            'theta': strike_data.get('theta', 0),
            'vega': strike_data.get('vega', 0),
            'iv': strike_data.get('impliedVolatility', 0),
            'volume': strike_data.get('volume', 0),
            'oi': strike_data.get('openInterest', 0)
        })
    
    df = pd.DataFrame(summary).sort_values(['strike', 'type'])
    
    output = io.StringIO()
    output.write(f"# Greeks Summary - {chain_data.get('ticker')} {expiration}\n")
    output.write(f"# Spot: {chain_data.get('spot_price')}\n")
    df.to_csv(output, index=False)
    
    return output.getvalue()


def generate_export_filename(
    ticker: str,
    expiration: Optional[str] = None,
    format: str = "csv"
) -> str:
    """Generate standardized export filename."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if expiration:
        return f"{ticker}_{expiration}_{timestamp}.{format}"
    return f"{ticker}_chain_{timestamp}.{format}"
