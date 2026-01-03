"""
Session Summary & Offline Mode Components
Phase 6 - Visualization & UX (Items 505-510)

Provides:
- Session summary with trading activity
- Daily/weekly recap
- Offline data caching
- Connection status indicator
- Auto-reconnect functionality
"""

from dash import html, dcc
import dash_bootstrap_components as dbc
from typing import Dict, List, Optional
from datetime import datetime

# Design tokens
THEME = {
    "bg_primary": "#0D1117",
    "bg_secondary": "#161B22",
    "bg_tertiary": "#21262D",
    "gold": "#F5C211",
    "success": "#3FB950",
    "danger": "#F85149",
    "warning": "#D29922",
    "info": "#58A6FF",
    "text_primary": "#E6EDF3",
    "text_secondary": "#8B949E",
    "text_muted": "#6E7681",
    "border": "#30363D",
}


def create_session_summary_panel() -> html.Div:
    """Create session summary panel showing trading activity."""
    
    return html.Div([
        # Header
        html.Div([
            html.Div([
                html.Span("📋", style={"fontSize": "20px", "marginRight": "10px"}),
                html.Span("Session Summary", style={
                    "fontSize": "16px",
                    "fontWeight": "600",
                    "color": THEME["text_primary"],
                }),
            ], style={"display": "flex", "alignItems": "center"}),
            
            html.Div([
                html.Span("Dec 31, 2025", style={
                    "color": THEME["text_muted"],
                    "fontSize": "12px",
                    "marginRight": "8px",
                }),
                html.Span("●", style={
                    "color": THEME["success"],
                    "fontSize": "8px",
                    "marginRight": "4px",
                }),
                html.Span("Live", style={
                    "color": THEME["success"],
                    "fontSize": "11px",
                }),
            ]),
        ], style={
            "display": "flex",
            "justifyContent": "space-between",
            "alignItems": "center",
            "marginBottom": "20px",
            "paddingBottom": "12px",
            "borderBottom": f"2px solid {THEME['gold']}",
        }),
        
        # Session Stats
        html.Div([
            _create_session_stat("Session Duration", "4h 32m", "⏱️"),
            _create_session_stat("Trades Executed", "7", "📊"),
            _create_session_stat("Session P/L", "+$342", "💰", THEME["success"]),
            _create_session_stat("Win Rate", "71%", "🎯"),
        ], style={
            "display": "grid",
            "gridTemplateColumns": "repeat(4, 1fr)",
            "gap": "12px",
            "marginBottom": "20px",
        }),
        
        # Activity Timeline
        html.Div([
            html.H6("Activity Timeline", style={
                "color": THEME["text_secondary"],
                "fontSize": "13px",
                "marginBottom": "12px",
            }),
            _create_activity_timeline(),
        ], style={"marginBottom": "20px"}),
        
        # Key Metrics
        html.Div([
            html.H6("Key Metrics", style={
                "color": THEME["text_secondary"],
                "fontSize": "13px",
                "marginBottom": "12px",
            }),
            html.Div([
                _create_metric_row("Portfolio Delta", "-8.2", "Δ"),
                _create_metric_row("Theta Collected", "+$67.40", "Θ"),
                _create_metric_row("Max Drawdown", "-$124", "📉"),
                _create_metric_row("Realized P/L", "+$218", "✓"),
                _create_metric_row("Unrealized P/L", "+$124", "⏳"),
            ]),
        ], style={"marginBottom": "20px"}),
        
        # Actions
        html.Div([
            dbc.Button([
                html.Span("📧", style={"marginRight": "6px"}),
                "Email Summary",
            ], id="email-summary-btn", color="secondary", size="sm", outline=True, className="me-2"),
            dbc.Button([
                html.Span("📄", style={"marginRight": "6px"}),
                "Export PDF",
            ], id="export-pdf-btn", color="secondary", size="sm", outline=True, className="me-2"),
            dbc.Button([
                html.Span("🔄", style={"marginRight": "6px"}),
                "Refresh",
            ], id="refresh-summary-btn", color="warning", size="sm", style={
                "backgroundColor": THEME["gold"],
                "border": "none",
                "color": "#0D1117",
            }),
        ], style={"display": "flex", "justifyContent": "flex-end"}),
        
    ], style={
        "backgroundColor": THEME["bg_secondary"],
        "border": f"1px solid {THEME['border']}",
        "borderRadius": "12px",
        "padding": "20px",
    })


def _create_session_stat(label: str, value: str, icon: str, color: str = None) -> html.Div:
    """Create a session stat card."""
    return html.Div([
        html.Div([
            html.Span(icon, style={"fontSize": "16px", "marginRight": "6px"}),
            html.Span(label, style={
                "color": THEME["text_muted"],
                "fontSize": "11px",
            }),
        ]),
        html.Div(value, style={
            "fontSize": "20px",
            "fontWeight": "700",
            "fontFamily": "'JetBrains Mono', monospace",
            "color": color or THEME["text_primary"],
        }),
    ], style={
        "backgroundColor": THEME["bg_tertiary"],
        "padding": "12px",
        "borderRadius": "8px",
    })


def _create_activity_timeline() -> html.Div:
    """Create activity timeline."""
    activities = [
        ("14:32", "Opened SPY Iron Condor", "entry", "+$2.45 credit"),
        ("13:15", "Closed NVDA Put Spread", "exit", "+$85 profit"),
        ("11:48", "Adjusted AAPL position", "adjust", "Rolled to next week"),
        ("10:22", "Alert triggered: IV spike", "alert", "QQQ IV > 25"),
        ("09:35", "Session started", "start", "Market open"),
    ]
    
    return html.Div([
        html.Div([
            html.Div([
                html.Span(time, style={
                    "color": THEME["text_muted"],
                    "fontSize": "11px",
                    "fontFamily": "'JetBrains Mono', monospace",
                    "width": "50px",
                }),
                html.Div(style={
                    "width": "8px",
                    "height": "8px",
                    "borderRadius": "50%",
                    "backgroundColor": _get_activity_color(activity_type),
                    "margin": "0 12px",
                }),
                html.Div([
                    html.Span(action, style={
                        "color": THEME["text_primary"],
                        "fontSize": "13px",
                    }),
                    html.Span(f" — {detail}", style={
                        "color": THEME["text_muted"],
                        "fontSize": "12px",
                    }),
                ]),
            ], style={
                "display": "flex",
                "alignItems": "center",
                "padding": "8px 0",
                "borderLeft": f"1px solid {THEME['border']}",
                "marginLeft": "54px",
                "paddingLeft": "16px",
            })
        ])
        for time, action, activity_type, detail in activities
    ])


def _get_activity_color(activity_type: str) -> str:
    """Get color for activity type."""
    colors = {
        "entry": THEME["success"],
        "exit": THEME["info"],
        "adjust": THEME["warning"],
        "alert": THEME["danger"],
        "start": THEME["gold"],
    }
    return colors.get(activity_type, THEME["text_muted"])


def _create_metric_row(label: str, value: str, icon: str) -> html.Div:
    """Create a metric row."""
    is_positive = value.startswith("+")
    is_negative = value.startswith("-")
    
    color = THEME["text_primary"]
    if is_positive and "$" in value:
        color = THEME["success"]
    elif is_negative and "$" in value:
        color = THEME["danger"]
    
    return html.Div([
        html.Div([
            html.Span(icon, style={"marginRight": "8px", "fontSize": "12px"}),
            html.Span(label, style={
                "color": THEME["text_secondary"],
                "fontSize": "12px",
            }),
        ]),
        html.Span(value, style={
            "color": color,
            "fontSize": "13px",
            "fontWeight": "500",
            "fontFamily": "'JetBrains Mono', monospace",
        }),
    ], style={
        "display": "flex",
        "justifyContent": "space-between",
        "alignItems": "center",
        "padding": "8px 0",
        "borderBottom": f"1px solid {THEME['border']}",
    })


def create_connection_status_indicator() -> html.Div:
    """Create connection status indicator."""
    
    return html.Div([
        html.Div([
            html.Span(id="connection-dot", style={
                "width": "8px",
                "height": "8px",
                "borderRadius": "50%",
                "backgroundColor": THEME["success"],
                "display": "inline-block",
                "marginRight": "6px",
            }),
            html.Span("Connected", id="connection-text", style={
                "color": THEME["success"],
                "fontSize": "11px",
            }),
        ], style={"display": "flex", "alignItems": "center"}),
        
        html.Div([
            html.Span("Last sync: ", style={
                "color": THEME["text_muted"],
                "fontSize": "10px",
            }),
            html.Span("2s ago", id="last-sync-time", style={
                "color": THEME["text_secondary"],
                "fontSize": "10px",
            }),
        ], style={"marginTop": "2px"}),
        
        # Store for connection state
        dcc.Store(id="connection-state", data={"connected": True, "lastSync": datetime.now().isoformat()}),
        
        # Interval for connection check
        dcc.Interval(id="connection-check-interval", interval=5000, n_intervals=0),
        
    ], id="connection-status", style={
        "padding": "8px 12px",
        "backgroundColor": THEME["bg_tertiary"],
        "borderRadius": "6px",
        "border": f"1px solid {THEME['border']}",
    })


def create_offline_mode_banner() -> html.Div:
    """Create offline mode banner."""
    
    return html.Div([
        html.Div([
            html.Span("⚠️", style={"fontSize": "16px", "marginRight": "8px"}),
            html.Span("Offline Mode", style={
                "fontWeight": "600",
                "marginRight": "8px",
            }),
            html.Span("— Using cached data", style={
                "color": THEME["text_secondary"],
                "fontSize": "13px",
            }),
        ], style={"display": "flex", "alignItems": "center"}),
        
        html.Div([
            html.Button("Retry Connection", id="retry-connection-btn", style={
                "padding": "4px 12px",
                "backgroundColor": "transparent",
                "border": f"1px solid {THEME['warning']}",
                "borderRadius": "4px",
                "color": THEME["warning"],
                "fontSize": "11px",
                "cursor": "pointer",
            }),
        ]),
    ], id="offline-banner", style={
        "display": "none",  # Hidden by default
        "justifyContent": "space-between",
        "alignItems": "center",
        "padding": "12px 20px",
        "backgroundColor": f"{THEME['warning']}20",
        "borderBottom": f"2px solid {THEME['warning']}",
    })


def create_cached_data_indicator() -> html.Div:
    """Create indicator for cached data sections."""
    
    return html.Div([
        html.Span("💾", style={"marginRight": "4px", "fontSize": "10px"}),
        html.Span("Cached", style={
            "fontSize": "9px",
            "color": THEME["text_muted"],
        }),
    ], className="cached-indicator", style={
        "display": "inline-flex",
        "alignItems": "center",
        "padding": "2px 6px",
        "backgroundColor": THEME["bg_tertiary"],
        "borderRadius": "4px",
        "marginLeft": "8px",
    })


# JavaScript for offline detection and caching
OFFLINE_JS = """
<script>
// Service worker registration for offline support
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(err => {
        console.log('Service worker registration failed:', err);
    });
}

// Connection status monitoring
let isOnline = navigator.onLine;

window.addEventListener('online', () => {
    isOnline = true;
    document.getElementById('offline-banner').style.display = 'none';
    document.getElementById('connection-dot').style.backgroundColor = '#3FB950';
    document.getElementById('connection-text').textContent = 'Connected';
    document.getElementById('connection-text').style.color = '#3FB950';
});

window.addEventListener('offline', () => {
    isOnline = false;
    document.getElementById('offline-banner').style.display = 'flex';
    document.getElementById('connection-dot').style.backgroundColor = '#D29922';
    document.getElementById('connection-text').textContent = 'Offline';
    document.getElementById('connection-text').style.color = '#D29922';
});

// Local storage caching for critical data
function cacheData(key, data) {
    try {
        localStorage.setItem(`alpaca_cache_${key}`, JSON.stringify({
            data: data,
            timestamp: Date.now()
        }));
    } catch (e) {
        console.warn('Failed to cache data:', e);
    }
}

function getCachedData(key, maxAge = 3600000) { // 1 hour default
    try {
        const cached = localStorage.getItem(`alpaca_cache_${key}`);
        if (cached) {
            const { data, timestamp } = JSON.parse(cached);
            if (Date.now() - timestamp < maxAge) {
                return data;
            }
        }
    } catch (e) {
        console.warn('Failed to get cached data:', e);
    }
    return null;
}

// Auto-reconnect with exponential backoff
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

function attemptReconnect() {
    if (reconnectAttempts >= maxReconnectAttempts) {
        console.log('Max reconnection attempts reached');
        return;
    }
    
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
    reconnectAttempts++;
    
    setTimeout(() => {
        fetch('/api/options/ready')
            .then(response => {
                if (response.ok) {
                    reconnectAttempts = 0;
                    window.dispatchEvent(new Event('online'));
                } else {
                    attemptReconnect();
                }
            })
            .catch(() => attemptReconnect());
    }, delay);
}

// Retry button handler
document.getElementById('retry-connection-btn')?.addEventListener('click', () => {
    reconnectAttempts = 0;
    attemptReconnect();
});
</script>
"""
