"""
Compatibility shim for top-level imports: the container imports `utils.events_helper` from /app/utils.
This file mirrors the safe fallback behavior implemented under `financial_dashboard/utils/events_helper.py`.
"""
import logging
from pathlib import Path
import pandas as pd
from typing import Union
from dash import html
import dash_bootstrap_components as dbc

logger = logging.getLogger(__name__)

EVENTS_FILE = Path('outputs/events_latest.parquet')
EVENTS_AGG_FILE = Path('cache/events_agg_daily.json')


def create_events_panel(filter_tickers=None, severity_filter='HIGH', max_events=10):
    try:
        if not EVENTS_FILE.exists():
            return dbc.Card([
                dbc.CardBody([
                    html.H6("Recent Critical Events", className="mb-3"),
                    html.P("No events data available. Run event classifier pipeline:", className="text-muted"),
                    html.Code("python3 pipelines/event_classifier.py --tickers AAPL,MSFT --since 2025-10-01",
                             className="d-block p-2 bg-dark text-light")
                ])
            ], className="mb-4")

        events_df_or_err = _safe_read_parquet(EVENTS_FILE)
        # older code returned an error dict; prefer DataFrame-only path
        if isinstance(events_df_or_err, dict) and events_df_or_err.get('error'):
            return dbc.Card([
                dbc.CardBody([
                    html.H6("Recent Critical Events", className="mb-3"),
                    html.P(f"Error loading events: {events_df_or_err.get('message')}", className="text-danger")
                ])
            ], className="mb-4")

        events_df = events_df_or_err

        if filter_tickers:
            events_df = events_df[events_df['ticker'].isin(filter_tickers)]

        if severity_filter:
            events_df = events_df[events_df['severity'] == severity_filter]

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
                    html.P(message, className="text-muted")
                ])
            ], className="mb-4")

        # Build list items
        event_items = []
        for _, event in events_df.iterrows():
            if event['severity'] == 'HIGH':
                badge_color = 'danger'
                icon = '🔴'
            elif event['severity'] == 'MEDIUM':
                badge_color = 'warning'
                icon = '🟡'
            else:
                badge_color = 'info'
                icon = '🔵'

            try:
                if isinstance(event['timestamp'], str):
                    ts = pd.to_datetime(event['timestamp'])
                else:
                    ts = event['timestamp']
                time_str = ts.strftime('%b %d, %I:%M %p')
            except Exception:
                time_str = str(event['timestamp'])

            event_items.append(dbc.ListGroupItem([
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            dbc.Badge(event['ticker'], color='secondary', className="me-2"),
                            dbc.Badge(event['event_type'], color='primary', className="me-2"),
                            dbc.Badge(f"{icon} {event['severity']}", color=badge_color)
                        ], className="mb-2"),
                        html.P(event['headline'], className="mb-1", style={'font-size': '14px'}),
                        html.Small(f"{time_str} • {event.get('source', 'Unknown')}", className="text-muted")
                    ], width=12)
                ])
            ]))

        return dbc.Card([
            dbc.CardHeader([
                html.H6("🔔 Recent Critical Events", className="mb-0"),
                html.Small(f"{len(events_df)} events", className="text-muted float-end")
            ]),
            dbc.CardBody([dbc.ListGroup(event_items, flush=True)])
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
            assert not isinstance(events_df_or_err, dict)
            events_df = events_df_or_err
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
    try:
        if not EVENTS_FILE.exists():
            return []
        events_df_or_err = _safe_read_parquet(EVENTS_FILE)
        if isinstance(events_df_or_err, dict) and events_df_or_err.get('error'):
            logger.warning('Parquet read failed in get_ticker_events: %s', events_df_or_err.get('message'))
            return []
        assert not isinstance(events_df_or_err, dict)
        events_df = events_df_or_err
        ticker_events = events_df[events_df['ticker'] == ticker].sort_values('timestamp', ascending=False).head(max_events)
        return ticker_events.to_dict('records')
    except Exception as e:
        logger.error(f"Error getting ticker events: {e}")
        return []


def _safe_read_parquet(path: Path) -> Union[pd.DataFrame, dict]:
    try:
        return pd.read_parquet(path)
    except Exception as e:
        logger.warning("Parquet read failed (%s); attempting CSV fallback if present", e)
        csv_path = path.with_suffix('.csv')
        try:
            if csv_path.exists():
                df = pd.read_csv(csv_path, parse_dates=['timestamp'])
                return df
        except Exception as e2:
            logger.warning('CSV fallback read failed: %s', e2)
        cols = ['ticker', 'severity', 'timestamp', 'event_type', 'headline', 'source']
        empty = pd.DataFrame(columns=cols)
        return empty
