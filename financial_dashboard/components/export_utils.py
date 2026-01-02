"""
Export Utilities Component
Phase 6 - Visualization & UX (Item 504)

Provides export functionality for:
- Chart images (PNG/SVG)
- Data as CSV
- Data as Parquet
- Trade journal export
"""

from dash import html, dcc
import dash_bootstrap_components as dbc
from typing import Optional

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


def create_export_dropdown() -> dbc.DropdownMenu:
    """Create the export dropdown menu."""
    
    return dbc.DropdownMenu([
        dbc.DropdownMenuItem([
            html.Span("📷", style={"marginRight": "8px"}),
            "Export Chart as PNG",
        ], id="export-chart-png", style={"fontSize": "13px"}),
        
        dbc.DropdownMenuItem([
            html.Span("🖼️", style={"marginRight": "8px"}),
            "Export Chart as SVG",
        ], id="export-chart-svg", style={"fontSize": "13px"}),
        
        dbc.DropdownMenuItem(divider=True),
        
        dbc.DropdownMenuItem([
            html.Span("📊", style={"marginRight": "8px"}),
            "Export Data as CSV",
        ], id="export-data-csv", style={"fontSize": "13px"}),
        
        dbc.DropdownMenuItem([
            html.Span("📦", style={"marginRight": "8px"}),
            "Export Data as Parquet",
        ], id="export-data-parquet", style={"fontSize": "13px"}),
        
        dbc.DropdownMenuItem([
            html.Span("📋", style={"marginRight": "8px"}),
            "Export to Clipboard",
        ], id="export-clipboard", style={"fontSize": "13px"}),
        
        dbc.DropdownMenuItem(divider=True),
        
        dbc.DropdownMenuItem([
            html.Span("📓", style={"marginRight": "8px"}),
            "Export Trade Journal",
        ], id="export-journal", style={"fontSize": "13px"}),
        
        dbc.DropdownMenuItem([
            html.Span("📈", style={"marginRight": "8px"}),
            "Export Performance Report",
        ], id="export-report", style={"fontSize": "13px"}),
        
    ], label=[
        html.Span("⬇️", style={"marginRight": "6px"}),
        "Export",
    ], id="export-dropdown", color="secondary", size="sm", style={
        "marginRight": "8px",
    })


def create_export_modal() -> dbc.Modal:
    """Create the export options modal."""
    
    return dbc.Modal([
        dbc.ModalHeader([
            html.Div([
                html.Span("⬇️", style={"fontSize": "24px", "marginRight": "12px"}),
                html.Span("Export Data", style={
                    "fontSize": "18px",
                    "fontWeight": "600",
                    "color": THEME["text_primary"],
                }),
            ], style={"display": "flex", "alignItems": "center"}),
        ], style={
            "backgroundColor": THEME["bg_secondary"],
            "borderBottom": f"1px solid {THEME['border']}",
        }, close_button=True),
        
        dbc.ModalBody([
            # Export Type Selection
            html.Div([
                html.Label("Export Type", style={
                    "color": THEME["text_secondary"],
                    "fontSize": "12px",
                    "marginBottom": "8px",
                    "display": "block",
                }),
                dcc.RadioItems(
                    id="export-type",
                    options=[
                        {"label": " CSV (Spreadsheet)", "value": "csv"},
                        {"label": " Parquet (Analytics)", "value": "parquet"},
                        {"label": " JSON (API)", "value": "json"},
                        {"label": " Excel (xlsx)", "value": "xlsx"},
                    ],
                    value="csv",
                    style={"fontSize": "13px"},
                    labelStyle={
                        "display": "block",
                        "color": THEME["text_primary"],
                        "marginBottom": "8px",
                        "cursor": "pointer",
                    },
                ),
            ], style={"marginBottom": "20px"}),
            
            # Data Selection
            html.Div([
                html.Label("Include Data", style={
                    "color": THEME["text_secondary"],
                    "fontSize": "12px",
                    "marginBottom": "8px",
                    "display": "block",
                }),
                dcc.Checklist(
                    id="export-data-selection",
                    options=[
                        {"label": " Options Chain Data", "value": "chain"},
                        {"label": " Greeks History", "value": "greeks"},
                        {"label": " Trade Journal", "value": "journal"},
                        {"label": " Volatility Metrics", "value": "volatility"},
                        {"label": " Strategy Analysis", "value": "strategy"},
                    ],
                    value=["chain", "journal"],
                    style={"fontSize": "13px"},
                    labelStyle={
                        "display": "block",
                        "color": THEME["text_primary"],
                        "marginBottom": "8px",
                        "cursor": "pointer",
                    },
                ),
            ], style={"marginBottom": "20px"}),
            
            # Date Range
            html.Div([
                html.Label("Date Range", style={
                    "color": THEME["text_secondary"],
                    "fontSize": "12px",
                    "marginBottom": "8px",
                    "display": "block",
                }),
                dcc.DatePickerRange(
                    id="export-date-range",
                    display_format="YYYY-MM-DD",
                    style={"width": "100%"},
                ),
            ], style={"marginBottom": "20px"}),
            
            # Filename
            html.Div([
                html.Label("Filename", style={
                    "color": THEME["text_secondary"],
                    "fontSize": "12px",
                    "marginBottom": "8px",
                    "display": "block",
                }),
                dcc.Input(
                    id="export-filename",
                    type="text",
                    value="alpaca_options_export",
                    placeholder="Enter filename",
                    style={
                        "width": "100%",
                        "padding": "8px 12px",
                        "backgroundColor": THEME["bg_tertiary"],
                        "border": f"1px solid {THEME['border']}",
                        "borderRadius": "6px",
                        "color": THEME["text_primary"],
                        "fontSize": "13px",
                    }
                ),
            ]),
            
        ], style={
            "backgroundColor": THEME["bg_primary"],
            "padding": "24px",
        }),
        
        dbc.ModalFooter([
            dbc.Button("Cancel", id="export-cancel", color="secondary", outline=True, size="sm"),
            dbc.Button([
                html.Span("⬇️", style={"marginRight": "6px"}),
                "Download",
            ], id="export-download-btn", color="warning", size="sm", style={
                "backgroundColor": THEME["gold"],
                "color": "#0D1117",
                "border": "none",
            }),
        ], style={
            "backgroundColor": THEME["bg_secondary"],
            "borderTop": f"1px solid {THEME['border']}",
        }),
        
        # Hidden download component
        dcc.Download(id="export-download"),
        
    ], id="export-modal", is_open=False, centered=True)


def create_chart_export_button(chart_id: str) -> html.Button:
    """Create an export button for a specific chart."""
    
    return html.Button([
        html.Span("📷", style={"fontSize": "12px"}),
    ], id=f"export-chart-{chart_id}", title="Export Chart", style={
        "position": "absolute",
        "top": "8px",
        "right": "8px",
        "padding": "4px 8px",
        "backgroundColor": THEME["bg_tertiary"],
        "border": f"1px solid {THEME['border']}",
        "borderRadius": "4px",
        "cursor": "pointer",
        "opacity": "0.7",
        "transition": "opacity 0.2s ease",
        "zIndex": "10",
    })


def create_quick_export_bar() -> html.Div:
    """Create a quick export bar for the current view."""
    
    return html.Div([
        html.Span("Quick Export:", style={
            "color": THEME["text_muted"],
            "fontSize": "11px",
            "marginRight": "12px",
        }),
        
        html.Button([
            html.Span("CSV", style={"fontSize": "11px"}),
        ], id="quick-export-csv", title="Export as CSV", style={
            "padding": "4px 10px",
            "backgroundColor": "transparent",
            "border": f"1px solid {THEME['border']}",
            "borderRadius": "4px",
            "color": THEME["text_secondary"],
            "fontSize": "11px",
            "cursor": "pointer",
            "marginRight": "6px",
        }),
        
        html.Button([
            html.Span("PNG", style={"fontSize": "11px"}),
        ], id="quick-export-png", title="Export as PNG", style={
            "padding": "4px 10px",
            "backgroundColor": "transparent",
            "border": f"1px solid {THEME['border']}",
            "borderRadius": "4px",
            "color": THEME["text_secondary"],
            "fontSize": "11px",
            "cursor": "pointer",
            "marginRight": "6px",
        }),
        
        html.Button([
            html.Span("📋", style={"fontSize": "11px"}),
        ], id="quick-export-clipboard", title="Copy to Clipboard", style={
            "padding": "4px 10px",
            "backgroundColor": "transparent",
            "border": f"1px solid {THEME['border']}",
            "borderRadius": "4px",
            "color": THEME["text_secondary"],
            "fontSize": "11px",
            "cursor": "pointer",
        }),
        
    ], style={
        "display": "flex",
        "alignItems": "center",
        "padding": "8px 12px",
        "backgroundColor": THEME["bg_secondary"],
        "borderRadius": "6px",
    })


# Export utility functions
def export_to_csv(data: list, filename: str = "export.csv") -> str:
    """Export data to CSV format.
    
    Args:
        data: List of dicts to export
        filename: Output filename
        
    Returns:
        CSV string content
    """
    if not data:
        return ""
    
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()


def export_to_json(data: dict, filename: str = "export.json") -> str:
    """Export data to JSON format.
    
    Args:
        data: Data to export
        filename: Output filename
        
    Returns:
        JSON string content
    """
    import json
    return json.dumps(data, indent=2, default=str)


def export_to_pdf(html_content: str, filename: str = "export.pdf") -> bytes:
    """Export HTML content to PDF (placeholder).
    
    Note: Requires weasyprint or similar library for actual PDF generation.
    
    Args:
        html_content: HTML content to convert
        filename: Output filename
        
    Returns:
        PDF bytes (placeholder returns empty bytes)
    """
    # Placeholder - would require weasyprint or pdfkit
    return b""


# JavaScript for chart export functionality
EXPORT_JS = """
<script>
// Export chart as PNG
function exportChartAsPNG(chartId) {
    const chart = document.querySelector(`#${chartId} .js-plotly-plot`);
    if (chart) {
        Plotly.toImage(chart, {format: 'png', width: 1200, height: 600})
            .then(function(dataUrl) {
                const link = document.createElement('a');
                link.download = `${chartId}_chart.png`;
                link.href = dataUrl;
                link.click();
            });
    }
}

// Export chart as SVG
function exportChartAsSVG(chartId) {
    const chart = document.querySelector(`#${chartId} .js-plotly-plot`);
    if (chart) {
        Plotly.toImage(chart, {format: 'svg', width: 1200, height: 600})
            .then(function(dataUrl) {
                const link = document.createElement('a');
                link.download = `${chartId}_chart.svg`;
                link.href = dataUrl;
                link.click();
            });
    }
}

// Copy data to clipboard
function copyToClipboard(data) {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2))
        .then(() => {
            // Show toast notification
            console.log('Data copied to clipboard');
        });
}
</script>
"""
