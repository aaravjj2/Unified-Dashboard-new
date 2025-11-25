"""
Simple standalone Monthly Picks Dashboard
Displays the latest monthly picks CSV (from full_run) in a clean Dash table.
Run: python3 monthly_picks_simple.py
"""
from dash import Dash, html, dash_table
import pandas as pd
import os
import glob

app = Dash(__name__)
app.title = "Monthly Picks Dashboard"

def find_latest_monthly_csv():
    """Find the most recent picks CSV from full_run (monthly)"""
    base_dir = os.path.dirname(__file__)
    patterns = [
        'models/full_run/picks*.csv',
        'models/monthly_run/picks*.csv'
    ]
    candidates = []
    for pattern in patterns:
        path = os.path.join(base_dir, pattern)
        candidates.extend(glob.glob(path, recursive=True))
    
    if not candidates:
        return None
    
    return max(candidates, key=os.path.getmtime)

def load_picks_data():
    """Load and format picks data"""
    csv_path = find_latest_monthly_csv()
    
    if not csv_path:
        return None, "No monthly picks CSV found"
    
    try:
        df = pd.read_csv(csv_path)
        
        # Select key columns for display
        display_cols = ['ticker', 'score', 'pred_rank', 'last_price', 'market_cap', 'sector']
        display_cols = [c for c in display_cols if c in df.columns]
        
        if display_cols:
            df_display = df[display_cols].copy()
        else:
            # Show first 10 columns if specific columns not found
            df_display = df.iloc[:, :10].copy()
        
        # Format numbers
        if 'score' in df_display.columns:
            df_display['score'] = df_display['score'].round(3)
        if 'last_price' in df_display.columns:
            df_display['last_price'] = df_display['last_price'].round(2)
        
        return df_display, csv_path
    except Exception as e:
        return None, f"Error loading CSV: {str(e)}"

# Load data
df, csv_info = load_picks_data()

if df is not None:
    # Create table
    table = dash_table.DataTable(
        data=df.to_dict('records'),
        columns=[{'name': col, 'id': col} for col in df.columns],
        page_size=50,
        sort_action='native',
        filter_action='native',
        style_table={'overflowX': 'auto'},
        style_cell={
            'textAlign': 'left',
            'padding': '10px',
            'backgroundColor': '#1e1e1e',
            'color': '#e0e0e0'
        },
        style_header={
            'backgroundColor': '#2c2c2c',
            'fontWeight': 'bold',
            'color': '#ffffff'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#252525'
            }
        ]
    )
    
    layout_children = [
        html.H1("📈 Monthly Picks Dashboard", style={'color': '#e0e0e0'}),
        html.P(f"Loaded from: {csv_info}", style={'color': '#888', 'fontSize': '12px'}),
        html.P(f"Total picks: {len(df)}", style={'color': '#888', 'marginBottom': '20px'}),
        table
    ]
else:
    layout_children = [
        html.H1("📈 Monthly Picks Dashboard"),
        html.Div([
            html.H3("⚠️ No Data Available", style={'color': '#ff6b6b'}),
            html.P(csv_info, style={'color': '#888'})
        ])
    ]

app.layout = html.Div(
    layout_children,
    style={
        'padding': '20px',
        'backgroundColor': '#1a1a1a',
        'minHeight': '100vh',
        'fontFamily': 'Arial, sans-serif'
    }
)

if __name__ == '__main__':
    print("="*60)
    print("Monthly Picks Dashboard")
    print("="*60)
    if df is not None:
        print(f"✅ Loaded: {csv_info}")
        print(f"📊 Total picks: {len(df)}")
        print(f"🎯 Top 3 tickers: {', '.join(df['ticker'].head(3).tolist())}")
    else:
        print(f"❌ {csv_info}")
    print("="*60)
    print("🌐 Starting server at http://0.0.0.0:8052")
    print("="*60)
    app.run(debug=False, host='0.0.0.0', port=8052)
