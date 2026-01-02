"""
Shared UI Components for Dashboard Improvements
================================================
Implements reusable components for tab improvements.
"""

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from datetime import datetime

# ============================================================================
# LOADING COMPONENTS
# ============================================================================

def create_loading_skeleton(height="200px", width="100%"):
    """Create a loading skeleton placeholder."""
    return html.Div(
        className="loading-skeleton",
        style={
            "height": height,
            "width": width,
            "background": "linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%)",
            "backgroundSize": "200% 100%",
            "animation": "shimmer 1.5s infinite",
            "borderRadius": "8px"
        }
    )

def create_loading_spinner(text="Loading...", size="md"):
    """Create a loading spinner with text."""
    return html.Div([
        dbc.Spinner(size=size, color="primary"),
        html.Span(text, className="ms-2 text-muted")
    ], className="d-flex align-items-center justify-content-center p-4")

# ============================================================================
# BUTTON COMPONENTS
# ============================================================================

def create_refresh_button(callback_id, tooltip_text="Refresh data"):
    """Create a refresh button with tooltip."""
    return html.Div([
        dbc.Button(
            html.I(className="fas fa-sync-alt"),
            id=callback_id,
            color="outline-primary",
            size="sm",
            className="btn-refresh"
        ),
        dbc.Tooltip(tooltip_text, target=callback_id, placement="top")
    ], className="d-inline-block")

def create_export_button(callback_id, tooltip_text="Export data"):
    """Create an export button with tooltip."""
    return html.Div([
        dbc.Button(
            [html.I(className="fas fa-download me-1"), "Export"],
            id=callback_id,
            color="outline-secondary",
            size="sm",
            className="btn-export"
        ),
        dbc.Tooltip(tooltip_text, target=callback_id, placement="top")
    ], className="d-inline-block ms-2")

def create_help_popover(target_id, title, content):
    """Create a help popover button."""
    return html.Div([
        dbc.Button(
            html.I(className="fas fa-question-circle"),
            id=f"{target_id}-help-btn",
            color="link",
            size="sm",
            className="btn-help p-0 ms-2"
        ),
        dbc.Popover(
            [
                dbc.PopoverHeader(title),
                dbc.PopoverBody(content)
            ],
            target=f"{target_id}-help-btn",
            trigger="click",
            placement="auto"
        )
    ], className="d-inline-block")

# ============================================================================
# STATUS COMPONENTS
# ============================================================================

def create_status_indicator(status, text=None):
    """Create a status indicator badge."""
    colors = {
        "online": "success",
        "offline": "danger",
        "warning": "warning",
        "loading": "info",
        "connected": "success",
        "disconnected": "danger"
    }
    icons = {
        "online": "fas fa-check-circle",
        "offline": "fas fa-times-circle",
        "warning": "fas fa-exclamation-triangle",
        "loading": "fas fa-spinner fa-spin",
        "connected": "fas fa-plug",
        "disconnected": "fas fa-plug"
    }
    return dbc.Badge([
        html.I(className=f"{icons.get(status, 'fas fa-circle')} me-1"),
        text or status.capitalize()
    ], color=colors.get(status, "secondary"), className="status-indicator")

def create_last_updated_timestamp(timestamp=None, suffix=""):
    """Create last updated timestamp display."""
    if timestamp is None:
        timestamp = datetime.now()
    # Use unique id with suffix to avoid duplicates
    unique_id = f"last-updated-timestamp-{suffix}" if suffix else f"last-updated-timestamp-{id(timestamp)}"
    return html.Div([
        html.I(className="fas fa-clock me-1 text-muted"),
        html.Span(f"Updated: {timestamp.strftime('%H:%M:%S')}", className="small text-muted")
    ], className="last-updated", id=unique_id)

# ============================================================================
# METRIC CARD COMPONENTS
# ============================================================================

def create_metric_card(title, value, subtitle=None, icon=None, color="primary", change=None):
    """Create a metric card with optional change indicator."""
    change_element = None
    if change is not None:
        change_color = "text-success" if change >= 0 else "text-danger"
        change_icon = "fa-arrow-up" if change >= 0 else "fa-arrow-down"
        change_element = html.Span([
            html.I(className=f"fas {change_icon} me-1"),
            f"{abs(change):.2f}%"
        ], className=f"{change_color} small")
    
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.I(className=f"fas {icon or 'fa-chart-line'} fa-2x", 
                       style={"color": f"var(--bs-{color})"}) if icon else None,
                html.Div([
                    html.P(title, className="text-muted small mb-1"),
                    html.H4(value, className="mb-0 fw-bold"),
                    html.Div([subtitle, change_element], className="d-flex justify-content-between") if subtitle or change_element else None
                ], className="ms-3 flex-grow-1")
            ], className="d-flex align-items-center")
        ])
    ], className="metric-card h-100")

def create_summary_stats_row(stats_list):
    """Create a row of summary statistics."""
    cols = []
    col_width = 12 // len(stats_list) if stats_list else 12
    for stat in stats_list:
        cols.append(dbc.Col(
            create_metric_card(
                title=stat.get("title", ""),
                value=stat.get("value", "--"),
                subtitle=stat.get("subtitle"),
                icon=stat.get("icon"),
                color=stat.get("color", "primary"),
                change=stat.get("change")
            ),
            md=col_width,
            className="mb-3"
        ))
    return dbc.Row(cols, className="summary-stats-row")

# ============================================================================
# FILTER COMPONENTS
# ============================================================================

def create_date_range_filter(callback_id):
    """Create date range filter dropdown."""
    return dbc.Select(
        id=callback_id,
        options=[
            {"label": "1 Day", "value": "1D"},
            {"label": "1 Week", "value": "1W"},
            {"label": "1 Month", "value": "1M"},
            {"label": "3 Months", "value": "3M"},
            {"label": "6 Months", "value": "6M"},
            {"label": "1 Year", "value": "1Y"},
            {"label": "YTD", "value": "YTD"},
            {"label": "All Time", "value": "ALL"}
        ],
        value="1M",
        className="form-select-sm"
    )

def create_sector_filter(callback_id):
    """Create sector/industry filter dropdown."""
    return dbc.Select(
        id=callback_id,
        options=[
            {"label": "All Sectors", "value": "ALL"},
            {"label": "Technology", "value": "XLK"},
            {"label": "Healthcare", "value": "XLV"},
            {"label": "Financials", "value": "XLF"},
            {"label": "Consumer Discretionary", "value": "XLY"},
            {"label": "Communication Services", "value": "XLC"},
            {"label": "Industrials", "value": "XLI"},
            {"label": "Consumer Staples", "value": "XLP"},
            {"label": "Energy", "value": "XLE"},
            {"label": "Utilities", "value": "XLU"},
            {"label": "Real Estate", "value": "XLRE"},
            {"label": "Materials", "value": "XLB"}
        ],
        value="ALL",
        className="form-select-sm"
    )

def create_ticker_filter(callback_id, default_tickers=None):
    """Create ticker selection filter."""
    if default_tickers is None:
        default_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
    return dcc.Dropdown(
        id=callback_id,
        options=[{"label": t, "value": t} for t in default_tickers],
        value=default_tickers[:3],
        multi=True,
        placeholder="Select tickers...",
        className="ticker-filter"
    )

def create_historical_toggle(callback_id, label="Show Historical"):
    """Create historical data toggle."""
    return dbc.Switch(
        id=callback_id,
        label=label,
        value=False,
        className="historical-toggle"
    )

# ============================================================================
# CHART COMPONENTS
# ============================================================================

def create_chart_container(chart_id, title, help_text=None, with_controls=True):
    """Create a standardized chart container with controls."""
    header_items = [
        html.Span(title, className="fw-bold"),
        create_help_popover(chart_id, title, help_text) if help_text else None
    ]
    
    controls = None
    if with_controls:
        controls = html.Div([
            dbc.Button(html.I(className="fas fa-camera"), 
                       id=f"{chart_id}-download", size="sm", color="outline-secondary")
        ], className="chart-controls")
    
    return dbc.Card([
        dbc.CardHeader([
            html.Div(header_items, className="d-flex align-items-center"),
            controls
        ], className="d-flex justify-content-between align-items-center"),
        dbc.CardBody([
            dcc.Loading(
                dcc.Graph(id=chart_id, className="chart-graph", config={
                    "displayModeBar": True,
                    "displaylogo": False,
                    "modeBarButtonsToRemove": ["lasso2d", "select2d"]
                }),
                type="circle"
            )
        ])
    ], className="chart-container mb-3")

# ============================================================================
# ERROR BOUNDARY COMPONENTS
# ============================================================================

def create_empty_state(icon="fa-inbox", title="No Data", subtitle="Data will appear here once available"):
    """Create an empty state placeholder."""
    return html.Div([
        html.I(className=f"fas {icon} fa-3x text-muted mb-3"),
        html.H5(title, className="text-muted"),
        html.P(subtitle, className="text-muted small")
    ], className="empty-state text-center p-5")

# ============================================================================
# NOTIFICATION COMPONENTS
# ============================================================================

def create_notification_toast(toast_id, header="Notification", icon="fa-bell"):
    """Create a notification toast."""
    return dbc.Toast(
        id=toast_id,
        header=[
            html.I(className=f"fas {icon} me-2"),
            header
        ],
        is_open=False,
        dismissable=True,
        duration=4000,
        style={"position": "fixed", "top": 66, "right": 10, "width": 350, "zIndex": 1050}
    )

# ============================================================================
# TOOLBAR COMPONENT
# ============================================================================

def create_tab_toolbar(tab_name, filters=None, show_refresh=True, show_export=True,
                       show_help=True, help_text=None):
    """Create a standardized toolbar for tabs."""
    left_items = []
    right_items = []
    
    # Add filters on the left
    if filters:
        for filter_item in filters:
            left_items.append(html.Div(filter_item, className="me-2"))
    
    # Add buttons on the right
    if show_refresh:
        right_items.append(create_refresh_button(f"{tab_name}-refresh"))
    if show_export:
        right_items.append(create_export_button(f"{tab_name}-export"))
    if show_help and help_text:
        right_items.append(create_help_popover(tab_name, f"{tab_name} Help", help_text))
    
    # Use tab_name as suffix to avoid duplicate IDs
    right_items.append(create_last_updated_timestamp(suffix=tab_name))
    
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.Div(left_items, className="d-flex align-items-center"),
                html.Div(right_items, className="d-flex align-items-center gap-2")
            ], className="d-flex justify-content-between align-items-center flex-wrap")
        ], className="py-2")
    ], className="tab-toolbar mb-3")


# ============================================================================
# PART 4: ENHANCED UI COMPONENTS
# ============================================================================

def create_metric_card_v2(
    title: str,
    value: str,
    change: str = None,
    change_type: str = "neutral",
    icon: str = None,
    id: str = None
):
    """
    Create a professional metric card with enhanced styling.
    
    Args:
        title: Metric label
        value: Main value to display
        change: Change value (e.g., "+5.2%")
        change_type: 'positive', 'negative', or 'neutral'
        icon: Optional emoji icon
        id: Component ID
    """
    change_class = {
        'positive': 'text-success',
        'negative': 'text-danger',
        'neutral': 'text-muted'
    }.get(change_type, 'text-muted')
    
    arrow = ""
    if change:
        if change_type == "positive":
            arrow = "↑ "
        elif change_type == "negative":
            arrow = "↓ "
    
    content = [
        html.Div([
            html.Small(title, className="text-muted text-uppercase", style={"letterSpacing": "0.05em"}),
            html.Div([
                html.Span(icon + " ", style={"marginRight": "8px"}) if icon else None,
                html.Span(value, className="h3 mb-0 fw-bold"),
            ], className="d-flex align-items-center mt-1"),
        ])
    ]
    
    if change:
        content.append(
            html.Small(f"{arrow}{change}", className=f"metric-change {change_class} mt-2 d-block")
        )
    
    return dbc.Card(
        dbc.CardBody(content, className="py-3"),
        className="metric-card hover-lift",
        id=id
    )


def create_status_badge_v2(status: str, text: str = None, live: bool = False):
    """
    Create a modern status badge.
    
    Args:
        status: 'success', 'warning', 'error', 'info', 'neutral'
        text: Display text (defaults to capitalized status)
        live: Show pulsing indicator
    """
    status_icons = {
        'success': '✓',
        'warning': '⚠',
        'error': '✗',
        'info': 'ℹ',
        'neutral': '•'
    }
    
    display_text = text or status.capitalize()
    icon = status_icons.get(status, '•')
    
    classes = f"status-badge status-badge-{status}"
    if live:
        classes += " status-badge-live"
    
    return html.Span(
        [icon, " ", display_text] if not live else display_text,
        className=classes
    )


def create_section_header_v2(
    title: str,
    subtitle: str = None,
    action_button: dict = None,
    badge: dict = None
):
    """
    Create a section header with optional action button or badge.
    
    Args:
        title: Section title
        subtitle: Optional subtitle text
        action_button: Dict with 'label', 'id', 'color' keys
        badge: Dict with 'text', 'type' keys
    """
    header_content = [html.H4(title, className="mb-0")]
    
    if badge:
        badge_type = badge.get('type', 'info')
        header_content.append(
            create_status_badge_v2(badge_type, badge.get('text', ''))
        )
    
    left_side = html.Div(header_content, className="d-flex align-items-center gap-2")
    
    if subtitle:
        left_side = html.Div([
            html.Div(header_content, className="d-flex align-items-center gap-2"),
            html.Small(subtitle, className="text-muted")
        ])
    
    right_side = None
    if action_button:
        right_side = dbc.Button(
            action_button.get('label', 'Action'),
            id=action_button.get('id'),
            color=action_button.get('color', 'primary'),
            size='sm',
            outline=action_button.get('outline', False)
        )
    
    return html.Div([
        left_side,
        right_side
    ] if right_side else [left_side], 
    className="section-header d-flex justify-content-between align-items-center mb-4 pb-3"
    )


def create_progress_bar_modern(
    value: float,
    max_value: float = 100,
    label: str = None,
    variant: str = "info",
    show_percent: bool = True
):
    """
    Create a modern progress bar.
    
    Args:
        value: Current value
        max_value: Maximum value
        label: Optional label above bar
        variant: 'success', 'warning', 'danger', 'info'
        show_percent: Show percentage text
    """
    percent = min(100, (value / max_value) * 100) if max_value > 0 else 0
    
    content = []
    
    if label or show_percent:
        header = []
        if label:
            header.append(html.Span(label, className="text-muted"))
        if show_percent:
            header.append(html.Span(f"{percent:.1f}%", className="text-muted"))
        content.append(
            html.Div(
                header, 
                className="d-flex justify-content-between mb-1",
                style={"fontSize": "0.875rem"}
            )
        )
    
    content.append(
        html.Div(
            html.Div(
                className=f"progress-bar-fill progress-{variant}",
                style={"width": f"{percent}%"}
            ),
            className="progress-bar-modern"
        )
    )
    
    return html.Div(content)


def create_card_modern(
    title: str = None,
    children=None,
    footer=None,
    header_right=None,
    id: str = None,
    className: str = ""
):
    """
    Create a modern card component.
    
    Args:
        title: Card header title
        children: Card body content
        footer: Optional footer content
        header_right: Optional right-aligned header content
        id: Component ID
        className: Additional CSS classes
    """
    parts = []
    
    if title or header_right:
        header_content = []
        if title:
            header_content.append(html.H5(title, className="mb-0"))
        if header_right:
            header_content.append(header_right)
        parts.append(
            html.Div(
                header_content,
                className="dash-card-header d-flex justify-content-between align-items-center"
            )
        )
    
    if children:
        parts.append(
            html.Div(children, className="dash-card-body")
        )
    
    if footer:
        parts.append(
            html.Div(footer, className="dash-card-footer")
        )
    
    return html.Div(
        parts,
        className=f"dash-card-modern {className}",
        id=id
    )
