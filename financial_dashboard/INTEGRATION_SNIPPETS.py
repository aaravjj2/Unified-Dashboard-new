#!/usr/bin/env python3
"""
Quick integration helper - Shows exact code to add for events integration.
Copy-paste these snippets into the specified files.
"""

print("""
╔══════════════════════════════════════════════════════════════════════╗
║                 EVENTS INTEGRATION - CODE SNIPPETS                   ║
╚══════════════════════════════════════════════════════════════════════╝

═══════════════════════════════════════════════════════════════════════
1. MARKET TRENDS - Add Events Panel (15 minutes)
═══════════════════════════════════════════════════════════════════════

FILE: tabs/market_trends.py

STEP 1: Add to imports (around line 5-15)
───────────────────────────────────────────────────────────────────────
from utils.events_helper import create_events_panel, get_events_summary
───────────────────────────────────────────────────────────────────────

STEP 2: Add to layout() function (around line 357-400)
       Find where main components are added, insert this:
───────────────────────────────────────────────────────────────────────
# Recent Critical Events
dbc.Row([
    dbc.Col([
        create_events_panel(severity_filter='HIGH', max_events=10)
    ], width=12)
], className="mb-4"),
───────────────────────────────────────────────────────────────────────

STEP 3: Enrich narrative in _render_brief_section() (around line 92-120)
       Before returning the brief text, add:
───────────────────────────────────────────────────────────────────────
# Enrich with events data
events_summary = get_events_summary()
if events_summary:
    high_count = events_summary.get('high_severity_count', 0)
    if high_count > 0:
        brief_text += f" Market shows {high_count} high-severity events today, "
        brief_text += "indicating elevated volatility."
───────────────────────────────────────────────────────────────────────

STEP 4: Restart service
───────────────────────────────────────────────────────────────────────
pkill -f analysis_app.py
nohup python3 analysis_app.py > analysis_app.log 2>&1 &
───────────────────────────────────────────────────────────────────────


═══════════════════════════════════════════════════════════════════════
2. PORTFOLIO - Add Event Indicators (30 minutes)
═══════════════════════════════════════════════════════════════════════

FILE: modules/portfolio.py

STEP 1: Add to imports (top of file)
───────────────────────────────────────────────────────────────────────
from utils.events_helper import get_ticker_events
import pandas as pd
from pathlib import Path
───────────────────────────────────────────────────────────────────────

STEP 2: Modify refresh_portfolio_data callback (around line 223-280)
       After positions_df is created, add:
───────────────────────────────────────────────────────────────────────
# Add event indicators
events_file = Path('outputs/events_latest.parquet')
if events_file.exists():
    events_df = pd.read_parquet(events_file)
    high_events = events_df[events_df['severity'] == 'HIGH']
    tickers_with_alerts = set(high_events['ticker'].unique())
    positions_df['Alert'] = positions_df['Ticker'].apply(
        lambda t: '🔔' if t in tickers_with_alerts else ''
    )
else:
    positions_df['Alert'] = ''
───────────────────────────────────────────────────────────────────────

STEP 3: Update positions table columns (around line 150-200)
       Add 'Alert' to the columns list:
───────────────────────────────────────────────────────────────────────
columns=[
    {'name': 'Alert', 'id': 'Alert'},
    {'name': 'Ticker', 'id': 'Ticker'},
    {'name': 'Shares', 'id': 'Shares'},
    # ... rest of columns
]
───────────────────────────────────────────────────────────────────────

STEP 4: Populate Alerts tab (replace callback at line 434-447)
───────────────────────────────────────────────────────────────────────
@callback(
    Output('portfolio-alerts-list', 'children'),
    [Input('portfolio-positions-store', 'data')]
)
def update_alerts_list(positions_data):
    if not positions_data:
        return html.P("No alerts - portfolio is empty", className="text-muted")
    
    # Get held tickers
    positions_df = pd.DataFrame(positions_data)
    held_tickers = positions_df['Ticker'].unique().tolist()
    
    # Load events
    events_file = Path('outputs/events_latest.parquet')
    if not events_file.exists():
        return html.P("No event data available", className="text-muted")
    
    events_df = pd.read_parquet(events_file)
    
    # Filter for held tickers and HIGH severity
    relevant_events = events_df[
        (events_df['ticker'].isin(held_tickers)) & 
        (events_df['severity'] == 'HIGH')
    ].sort_values('timestamp', ascending=False).head(10)
    
    if relevant_events.empty:
        return html.P("No high-severity alerts for your holdings", 
                     className="text-success")
    
    # Build alert items
    alert_items = []
    for _, event in relevant_events.iterrows():
        alert_item = dbc.ListGroupItem([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        dbc.Badge(event['ticker'], color='secondary', className="me-2"),
                        dbc.Badge(event['event_type'], color='primary', className="me-2"),
                        dbc.Badge(f"🔴 {event['severity']}", color='danger')
                    ], className="mb-2"),
                    html.P(event['headline'], className="mb-1"),
                    html.Small(
                        f"{event['timestamp'].strftime('%b %d, %I:%M %p')} • {event['source']}", 
                        className="text-muted"
                    )
                ], width=12)
            ])
        ])
        alert_items.append(alert_item)
    
    return dbc.ListGroup(alert_items, flush=True)
───────────────────────────────────────────────────────────────────────

STEP 5: Restart service
───────────────────────────────────────────────────────────────────────
pkill -f portfolio_app.py
nohup python3 portfolio_app.py > portfolio_app.log 2>&1 &
───────────────────────────────────────────────────────────────────────


═══════════════════════════════════════════════════════════════════════
3. MONTHLY/WEEKLY PICKS - Add Events to Modal (40 minutes)
═══════════════════════════════════════════════════════════════════════

FILES: tabs/monthly_picks.py, tabs/weekly_picks.py

STEP 1: Add to imports
───────────────────────────────────────────────────────────────────────
from utils.events_helper import get_ticker_events
───────────────────────────────────────────────────────────────────────

STEP 2: Find the "Inspect Pick" modal callback
       Search for: @callback with "inspect-pick-modal" or similar
       Inside the callback, after ticker is determined, add:
───────────────────────────────────────────────────────────────────────
# Get recent events for this ticker
ticker_events = get_ticker_events(ticker, max_events=5)

# Build events section
if ticker_events:
    events_section = html.Div([
        html.H6("Recent Events", className="mt-3 mb-2"),
        dbc.ListGroup([
            dbc.ListGroupItem([
                dbc.Badge(evt['event_type'], color='primary', className="me-2"),
                dbc.Badge(
                    f"{'🔴' if evt['severity']=='HIGH' else '🟡' if evt['severity']=='MEDIUM' else '🔵'} {evt['severity']}", 
                    color='danger' if evt['severity']=='HIGH' else 'warning' if evt['severity']=='MEDIUM' else 'info',
                    className="me-2"
                ),
                html.Span(evt['headline'], style={'font-size': '14px'}),
                html.Br(),
                html.Small(
                    f"{pd.to_datetime(evt['timestamp']).strftime('%b %d, %I:%M %p')}", 
                    className="text-muted"
                )
            ]) for evt in ticker_events
        ], flush=True)
    ], className="mb-3")
else:
    events_section = html.Div([
        html.H6("Recent Events", className="mt-3 mb-2"),
        html.P("No recent events", className="text-muted")
    ], className="mb-3")

# Add events_section to modal body (append to existing content)
───────────────────────────────────────────────────────────────────────

STEP 3: Restart service
───────────────────────────────────────────────────────────────────────
pkill -f analysis_app.py
nohup python3 analysis_app.py > analysis_app.log 2>&1 &
───────────────────────────────────────────────────────────────────────


═══════════════════════════════════════════════════════════════════════
4. REMOVE STANDALONE EVENT MONITOR (10 minutes)
═══════════════════════════════════════════════════════════════════════

STEP 1: Delete old files
───────────────────────────────────────────────────────────────────────
rm modules/event_monitor.py
rm event_monitor_app.py
───────────────────────────────────────────────────────────────────────

STEP 2: Edit unified_dashboard.py
       Remove Event Monitor tab button and iframe
       Search for "event-monitor" or "Event Monitor" and delete those sections
───────────────────────────────────────────────────────────────────────

STEP 3: Edit start_all.sh (if exists)
       Remove line that starts event_monitor_app.py
───────────────────────────────────────────────────────────────────────

STEP 4: Restart unified dashboard
───────────────────────────────────────────────────────────────────────
pkill -f "app.py"
nohup python3 app.py > app.log 2>&1 &
───────────────────────────────────────────────────────────────────────


═══════════════════════════════════════════════════════════════════════
5. TESTING & VERIFICATION
═══════════════════════════════════════════════════════════════════════

After each integration step:
───────────────────────────────────────────────────────────────────────
# Run comprehensive tests
python3 test_all_dashboards.py

# Check specific service
curl -I http://localhost:8054  # Analysis (Market Trends, Picks)
curl -I http://localhost:8056  # Portfolio

# Visual verification
# Open browser to http://localhost:8000
# Navigate to each integrated section
# Verify events display correctly
───────────────────────────────────────────────────────────────────────


═══════════════════════════════════════════════════════════════════════
EXPECTED RESULTS
═══════════════════════════════════════════════════════════════════════

Market Trends Tab:
  ✅ "Recent Critical Events" card appears
  ✅ Shows 10 HIGH severity events
  ✅ Each event has ticker, type, severity badges
  ✅ Brief narrative mentions event count

Portfolio Tab:
  ✅ Positions table has 'Alert' column with 🔔
  ✅ Alerts tab shows HIGH severity events for held tickers
  ✅ Each alert has ticker, type, severity, headline, timestamp

Monthly/Weekly Picks:
  ✅ "Inspect Pick" modal has "Recent Events" section
  ✅ Shows last 5 events for selected ticker
  ✅ Events have severity badges and timestamps

Unified Dashboard:
  ✅ Event Monitor tab removed
  ✅ No references to standalone event monitor

═══════════════════════════════════════════════════════════════════════

For detailed documentation, see:
  - EVENTS_INTEGRATION_STATUS.md  (full integration guide)
  - TEST_SUMMARY.md               (test results and metrics)
  - QUICK_REFERENCE.txt           (command reference)

""")
