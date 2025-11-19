"""
Helper function to create events panel for dashboards
Used by Market Trends, Portfolio, and Picks
"""
import os
import pandas as pd
import logging
from typing import Union
from dash import html
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# Resolve outputs/cache relative to the Dash package directory or _shared.OUT_ROOT
try:
    # Prefer shared OUT_ROOT when the dashboard is running (keeps a single canonical outputs dir)
    from _shared import OUT_ROOT as _OUT_ROOT
    BASE_DIR = Path(_OUT_ROOT).parent
except Exception:
    # Fallback: compute base as package root (two levels up from this file)
    BASE_DIR = Path(__file__).resolve().parents[1]

EVENTS_FILE = BASE_DIR / 'outputs' / 'events_latest.parquet'
EVENTS_AGG_FILE = BASE_DIR / 'cache' / 'events_agg_daily.json'


def create_events_panel(filter_tickers=None, severity_filter='HIGH', max_events=10):
    """
    Create a panel displaying recent critical events.
    
    Args:
        filter_tickers: List of tickers to filter for (None = all)
        severity_filter: 'HIGH', 'MEDIUM', 'LOW', or None for all
        max_events: Maximum number of events to display
    
    Returns:
        Dash component with events list
    """
    try:
        if not EVENTS_FILE.exists():
            return dbc.Card([
                dbc.CardBody([
                    html.H6("Recent Critical Events", className="mb-3"),
                    html.P("No events data available. Run event classifier pipeline:", 
                          style={'color': '#000000'}),
                    html.Code("python3 pipelines/event_classifier.py --tickers AAPL,MSFT --since 2025-10-01",
                             className="d-block p-2 bg-dark text-light")
                ])
            ], className="mb-4")
        
        # Load events (use safe reader to handle missing parquet engines)
        events_df_or_err = _safe_read_parquet(EVENTS_FILE)
        if isinstance(events_df_or_err, dict) and events_df_or_err.get('error'):
            # bubble up friendly error to UI
            return dbc.Card([
                dbc.CardBody([
                    html.H6("Recent Critical Events", className="mb-3"),
                    html.P(f"Error loading events: {events_df_or_err.get('message')}", className="text-danger")
                ])
            ], className="mb-4")

        events_df = events_df_or_err
        
        # Filter by tickers if specified
        if filter_tickers:
            events_df = events_df[events_df['ticker'].isin(filter_tickers)]
        
        # Filter by severity
        if severity_filter:
            events_df = events_df[events_df['severity'] == severity_filter]
        
        # Sort by timestamp descending
        events_df = events_df.sort_values('timestamp', ascending=False).head(max_events)
        
        if events_df.empty:
            message = "No "
            if severity_filter:
                message += f"{severity_filter} severity "
            message += "events found"
            if filter_tickers:
                message += f" for tickers: {', '.join(filter_tickers)}"
            
            return dbc.Card([
                dbc.CardBody([
                    html.H6("Recent Critical Events", className="mb-3"),
                    html.P(message, style={'color': '#000000'})
                ])
            ], className="mb-4")
        
        # Build event items
        event_items = []
        for _, event in events_df.iterrows():
            # Severity badge color
            if event['severity'] == 'HIGH':
                badge_color = 'danger'
                icon = '🔴'
            elif event['severity'] == 'MEDIUM':
                badge_color = 'warning'
                icon = '🟡'
            else:
                badge_color = 'info'
                icon = '🔵'
            
            # Format timestamp
            try:
                if isinstance(event['timestamp'], str):
                    ts = pd.to_datetime(event['timestamp'])
                else:
                    ts = event['timestamp']
                time_str = ts.strftime('%b %d, %I:%M %p')
            except:
                time_str = str(event['timestamp'])
            
            event_item = dbc.ListGroupItem([
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            dbc.Badge(event['ticker'], color='secondary', className="me-2"),
                            dbc.Badge(event['event_type'], color='primary', className="me-2"),
                            dbc.Badge(f"{icon} {event['severity']}", color=badge_color)
                        ], className="mb-2"),
                        html.P(event.get('title', event.get('headline', 'No title')), className="mb-1", 
                              style={'font-size': '14px'}),
                        html.Small(f"{time_str} • {event.get('source', 'Unknown')}", 
                                  style={'color': '#000000'})
                    ], width=12)
                ])
            ])
            event_items.append(event_item)
        
        return dbc.Card([
            dbc.CardHeader([
                html.H6("🔔 Recent Critical Events", className="mb-0"),
                html.Small(f"{len(events_df)} events", className="float-end", style={'color': '#000000'})
            ]),
            dbc.CardBody([
                dbc.ListGroup(event_items, flush=True)
            ])
        ], className="mb-4")
        
    except Exception as e:
        logger.error(f"Error creating events panel: {e}")
        return dbc.Card([
            dbc.CardBody([
                html.H6("Recent Critical Events", className="mb-3"),
                html.P(f"Error loading events: {str(e)}", className="text-danger")
            ])
        ], className="mb-4")


def get_events_summary():
    """
    Get summary statistics about recent events for narrative enrichment.
    
    Returns:
        Dict with event counts and summary data
    """
    try:
        import json
        
        if EVENTS_AGG_FILE.exists():
            with open(EVENTS_AGG_FILE, 'r') as f:
                return json.load(f)
        
        if EVENTS_FILE.exists():
            events_df_or_err = _safe_read_parquet(EVENTS_FILE)
            if isinstance(events_df_or_err, dict) and events_df_or_err.get('error'):
                logger.warning('Parquet read failed in get_events_summary: %s', events_df_or_err.get('message'))
                return {}

            # Narrow type for static analyzers
            assert not isinstance(events_df_or_err, dict)
            events_df: pd.DataFrame = events_df_or_err
            return {
                'total_events': len(events_df),
                'high_severity_count': len(events_df[events_df['severity'] == 'HIGH']),
                'by_type': events_df['event_type'].value_counts().to_dict(),
                'by_severity': events_df['severity'].value_counts().to_dict()
            }
        
        return {}
    except Exception as e:
        logger.error(f"Error getting events summary: {e}")
        return {}


def get_ticker_events(ticker, max_events=5):
    """
    Get recent events for a specific ticker.
    
    Args:
        ticker: Stock ticker
        max_events: Maximum events to return
    
    Returns:
        List of event dicts
    """
    try:
        if not EVENTS_FILE.exists():
            return []
        events_df_or_err = _safe_read_parquet(EVENTS_FILE)
        if isinstance(events_df_or_err, dict) and events_df_or_err.get('error'):
            logger.warning('Parquet read failed in get_ticker_events: %s', events_df_or_err.get('message'))
            return []

        # Narrow type for static analyzers
        assert not isinstance(events_df_or_err, dict)
        events_df: pd.DataFrame = events_df_or_err
        ticker_events = events_df[events_df['ticker'] == ticker].sort_values('timestamp', ascending=False).head(max_events)

        return ticker_events.to_dict('records')
    except Exception as e:
        logger.error(f"Error getting ticker events: {e}")
        return []


def _safe_read_parquet(path: Path) -> Union[pd.DataFrame, dict]:
    """
    Safe parquet reader that catches missing engine errors (pyarrow/fastparquet) and returns
    either a DataFrame or a dict with an 'error' key describing the issue.
    Also supports pickle fallback for testing environments.
    """
    try:
        return pd.read_parquet(path)
    except Exception as e:
        # If parquet reading fails (often because no engine installed), attempt
        # a CSV fallback or pickle fallback
        logger.warning("Parquet read failed (%s); attempting fallback formats", e)
        
        # Try pickle first (used in tests)
        pkl_path = path.with_suffix('.pkl')
        try:
            if pkl_path.exists():
                df = pd.read_pickle(pkl_path)
                logger.info(f"Loaded events from pickle: {pkl_path}")
                return df
        except Exception as e_pkl:
            logger.warning('Pickle fallback read failed: %s', e_pkl)
        
        # Try CSV fallback
        csv_path = path.with_suffix('.csv')
        try:
            if csv_path.exists():
                df = pd.read_csv(csv_path, parse_dates=['timestamp'])
                logger.info(f"Loaded events from CSV: {csv_path}")
                return df
        except Exception as e2:
            logger.warning('CSV fallback read failed: %s', e2)

        # Return empty DataFrame with common expected columns
        cols = ['ticker', 'severity', 'timestamp', 'event_type', 'headline', 'source']
        empty = pd.DataFrame(columns=cols)
        return empty


if __name__ == '__main__':
    # Test the helper functions
    logging.basicConfig(level=logging.INFO)
    
    print("Testing events helper...")
    print("\n1. Events summary:")
    summary = get_events_summary()
    print(summary)
    
    print("\n2. Ticker events:")
    ticker_events = get_ticker_events('AAPL')
    print(f"Found {len(ticker_events)} events for AAPL")
    
    print("\n3. Events panel (would render in Dash):")
    panel = create_events_panel(severity_filter='HIGH', max_events=5)
    print(f"Panel created: {type(panel)}")
