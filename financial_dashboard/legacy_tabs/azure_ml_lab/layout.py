"""
Azure ML Lab - Layout Module

Creates the Azure ML integration dashboard with 4 main sections:
1. ML Model Setup - Model selection and configuration
2. Prediction Configuration - Input parameters and feature toggles
3. Insights & Metrics - Prediction results and performance metrics
4. Logs / Diagnostics - System logs and validation results

Phase 3 Scaffold - All UI components are placeholders.
Real ML execution will be added in Phase 4.

All text in black (#000000) with tooltips for beginner guidance.
"""

import logging
from dash_extensions.enrich import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ============================================================================
# MAIN LAYOUT
# ============================================================================

def create_azure_ml_lab_layout():
    """
    Create the Azure ML Lab main layout with 4 sections.
    
    Returns:
        dbc.Container: Complete layout component
    """
    logger.info("📐 Creating Azure ML Lab layout (Phase 3 Scaffold)")
    
    return dbc.Container([
        # Header Section
        _create_header_section(),
        
        html.Hr(),
        
        # Section 1: ML Model Setup
        _create_ml_model_setup_section(),
        
        html.Hr(className="my-4"),
        
        # Section 2: Prediction Configuration
        _create_prediction_config_section(),
        
        html.Hr(className="my-4"),
        
        # Section 3: Insights & Metrics
        _create_insights_metrics_section(),
        
        html.Hr(className="my-4"),
        
        # Section 4: Logs / Diagnostics
        _create_logs_diagnostics_section(),
        
    ], fluid=True, className="py-4")


# ============================================================================
# SECTION: HEADER
# ============================================================================

def _create_header_section():
    """
    Create header with overview and status badges.
    """
    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.H3([
                        html.I(className="bi bi-brain me-2"),
                        "🤖 Azure ML Lab"
                    ], className="mb-2", style={'color': '#000000'}),
                    html.P([
                        "Predictive analytics powered by Azure Machine Learning. ",
                        "Generate market forecasts, strategy simulations, and risk assessments."
                    ], className="mb-3", style={'color': '#000000'}),
                ], md=8),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Status", className="mb-2", style={'color': '#000000'}),
                            dbc.Badge("Active", color="success", className="me-2", id='azure-ml-status-badge'),
                            dbc.Tooltip(
                                "Azure ML Lab operational with database persistence and real-time predictions.",
                                target='azure-ml-status-badge'
                            ),
                            html.Div([
                                html.Small("Phase 20B Complete", className="text-muted d-block"),
                                html.Small("PostgreSQL + Azure ML", className="text-muted d-block")
                            ])
                        ])
                    ], color="light")
                ], md=4)
            ]),
            
            # Overview Section
            dbc.Alert([
                html.H5("📚 What This Shows", className="alert-heading", style={'color': '#000000'}),
                html.P([
                    "The Azure ML Lab provides machine learning-powered insights for your portfolio:",
                    html.Ul([
                        html.Li([html.Strong("Market Forecasts:"), " Predict future returns and volatility"]),
                        html.Li([html.Strong("Strategy Simulations:"), " Backtest ML-driven strategies"]),
                        html.Li([html.Strong("Risk Assessment:"), " Identify risk factors and exposure"]),
                        html.Li([html.Strong("Feature Analysis:"), " Understand what drives predictions"])
                    ])
                ], className="mb-2", style={'color': '#000000'}),
                html.P([
                    html.Strong("How to Use:"),
                    " (1) Select ML model and configure parameters, ",
                    "(2) Choose prediction horizon and features, ",
                    "(3) Click 'Run Prediction' to generate insights, ",
                    "(4) Review results and diagnostics below."
                ], className="mb-0", style={'color': '#000000'})
            ], color="info", className="mt-3")
        ])
    ])


# ============================================================================
# SECTION 1: ML MODEL SETUP
# ============================================================================

def _create_ml_model_setup_section():
    """
    Section for selecting and configuring ML models.
    """
    return dbc.Card([
        dbc.CardHeader([
            html.H5([
                html.I(className="bi bi-gear me-2"),
                "1️⃣ ML Model Setup"
            ], className="mb-0", style={'color': '#000000'})
        ]),
        dbc.CardBody([
            dbc.Row([
                # Model Selection
                dbc.Col([
                    html.Label("Select Model Type", className="fw-bold", style={'color': '#000000'}),
                    dcc.Dropdown(
                        id='azure-ml-model-type',
                        options=[
                            {'label': '🎯 Ensemble (Recommended)', 'value': 'ensemble'},
                            {'label': '🧠 LSTM Neural Network', 'value': 'lstm'},
                            {'label': '🌲 XGBoost Gradient Boosting', 'value': 'xgboost'},
                            {'label': '📊 Linear Regression (Baseline)', 'value': 'linear'}
                        ],
                        value='ensemble',
                        clearable=False,
                        className="mb-3"
                    ),
                    dbc.Tooltip(
                        "Ensemble combines multiple models for robust predictions. "
                        "LSTM captures time series patterns. XGBoost handles non-linear relationships.",
                        target='azure-ml-model-type'
                    )
                ], md=6),
                
                # Model Confidence Threshold
                dbc.Col([
                    html.Label("Confidence Threshold", className="fw-bold", style={'color': '#000000'}, id='azure-ml-confidence-label'),
                    dcc.Slider(
                        id='azure-ml-confidence-threshold',
                        min=0.5,
                        max=0.95,
                        step=0.05,
                        value=0.7,
                        marks={0.5: '50%', 0.7: '70%', 0.9: '90%'},
                        tooltip={"placement": "bottom", "always_visible": True}
                    ),
                    dbc.Tooltip(
                        "Only show predictions above this confidence level. "
                        "Higher threshold = fewer but more reliable predictions.",
                        target='azure-ml-confidence-label'
                    )
                ], md=6)
            ]),
            
            html.Hr(),
            
            # Model Configuration
            dbc.Row([
                dbc.Col([
                    html.H6("Model Configuration", className="mb-3", style={'color': '#000000'}),
                    dbc.Checklist(
                        id='azure-ml-model-features',
                        options=[
                            {'label': ' Use Technical Indicators (RSI, MACD, Bollinger)', 'value': 'technical'},
                            {'label': ' Include Fama-French Factors (MKT, SMB, HML, RMW, CMA)', 'value': 'factors'},
                            {'label': ' Add Volatility Forecasts (GARCH, realized vol)', 'value': 'volatility'},
                            {'label': ' Incorporate Sentiment Scores (news, social)', 'value': 'sentiment'}
                        ],
                        value=['technical', 'factors'],
                        switch=True,
                        className="mb-3"
                    )
                ], md=6),
                
                dbc.Col([
                    html.H6("Advanced Options", className="mb-3", style={'color': '#000000'}),
                    dbc.Checklist(
                        id='azure-ml-advanced-options',
                        options=[
                            {'label': ' Enable Feature Selection (auto-select top features)', 'value': 'feature_selection'},
                            {'label': ' Use Cross-Validation (slower but more robust)', 'value': 'cross_validation'},
                            {'label': ' Generate SHAP Values (interpretability)', 'value': 'shap'},
                            {'label': ' Cache Predictions (faster re-runs)', 'value': 'cache'}
                        ],
                        value=['cache'],
                        switch=True
                    )
                ], md=6)
            ]),
            
            # Model Status
            dbc.Alert([
                html.Div(id='azure-ml-model-status', children=[
                    html.I(className="bi bi-info-circle me-2"),
                    html.Span("Model status will appear here after configuration.", style={'color': '#000000'})
                ])
            ], color="light", className="mt-3")
        ])
    ])


# ============================================================================
# SECTION 2: PREDICTION CONFIGURATION
# ============================================================================

def _create_prediction_config_section():
    """
    Section for configuring prediction parameters.
    """
    return dbc.Card([
        dbc.CardHeader([
            html.H5([
                html.I(className="bi bi-sliders me-2"),
                "2️⃣ Prediction Configuration"
            ], className="mb-0", style={'color': '#000000'})
        ]),
        dbc.CardBody([
            dbc.Row([
                # Prediction Horizon
                dbc.Col([
                    html.Label("Prediction Horizon", className="fw-bold", style={'color': '#000000'}, id='azure-ml-horizon-label'),
                    dcc.Dropdown(
                        id='azure-ml-prediction-horizon',
                        options=[
                            {'label': '1 Day (Short-term)', 'value': 1},
                            {'label': '5 Days (Weekly)', 'value': 5},
                            {'label': '21 Days (Monthly)', 'value': 21},
                            {'label': '63 Days (Quarterly)', 'value': 63}
                        ],
                        value=5,
                        clearable=False,
                        className="mb-3"
                    ),
                    dbc.Tooltip(
                        "How far into the future to predict. "
                        "Shorter horizons generally have higher accuracy.",
                        target='azure-ml-horizon-label'
                    )
                ], md=4),
                
                # Date Range
                dbc.Col([
                    html.Label("Training Data Range", className="fw-bold", style={'color': '#000000'}, id='azure-ml-daterange-label'),
                    dcc.DatePickerRange(
                        id='azure-ml-date-range',
                        start_date=(datetime.now() - timedelta(days=365)),
                        end_date=datetime.now(),
                        display_format='YYYY-MM-DD',
                        className="mb-3"
                    ),
                    dbc.Tooltip(
                        "Historical data window for model training. "
                        "Minimum 3 months recommended.",
                        target='azure-ml-daterange-label'
                    )
                ], md=4),
                
                # Rebalancing Frequency
                dbc.Col([
                    html.Label("Update Frequency", className="fw-bold", style={'color': '#000000'}),
                    dcc.Dropdown(
                        id='azure-ml-update-frequency',
                        options=[
                            {'label': 'Real-time (live)', 'value': 'realtime'},
                            {'label': 'Daily', 'value': 'daily'},
                            {'label': 'Weekly', 'value': 'weekly'},
                            {'label': 'Manual', 'value': 'manual'}
                        ],
                        value='manual',
                        clearable=False,
                        className="mb-3"
                    )
                ], md=4)
            ]),
            
            html.Hr(),
            
            # Target Selection
            dbc.Row([
                dbc.Col([
                    html.H6("What to Predict", className="mb-3", style={'color': '#000000'}),
                    dcc.RadioItems(
                        id='azure-ml-prediction-target',
                        options=[
                            {'label': ' Returns (price movement)', 'value': 'returns'},
                            {'label': ' Volatility (risk level)', 'value': 'volatility'},
                            {'label': ' Both (returns + volatility)', 'value': 'both'}
                        ],
                        value='both',
                        className="mb-3",
                        labelStyle={'display': 'block'}
                    )
                ], md=4),
                
                dbc.Col([
                    html.H6("Portfolio Universe", className="mb-3", style={'color': '#000000'}),
                    dcc.RadioItems(
                        id='azure-ml-universe',
                        options=[
                            {'label': ' Current Portfolio Only', 'value': 'current'},
                            {'label': ' Top 20 Weekly Picks', 'value': 'top20'},
                            {'label': ' Custom Ticker List', 'value': 'custom'}
                        ],
                        value='current',
                        className="mb-3",
                        labelStyle={'display': 'block'}
                    )
                ], md=4),
                
                dbc.Col([
                    html.H6("Risk Constraints", className="mb-3", style={'color': '#000000'}),
                    html.Label("Max Position Size", className="small", style={'color': '#000000'}),
                    dcc.Slider(
                        id='azure-ml-max-position',
                        min=5,
                        max=50,
                        step=5,
                        value=20,
                        marks={5: '5%', 20: '20%', 50: '50%'},
                        tooltip={"placement": "bottom"}
                    )
                ], md=4)
            ]),
            
            # Run Button
            html.Div([
                dbc.Button([
                    html.I(className="bi bi-play-circle me-2"),
                    "Run Prediction"
                ], id='azure-ml-run-prediction-btn', color="primary", size="lg", className="w-100")
            ], className="mt-4")
        ])
    ])


# ============================================================================
# SECTION 3: INSIGHTS & METRICS
# ============================================================================

def _create_model_insight_explorer():
    """
    Phase 1: Model Insight Explorer
    
    Interactive explainability interface showing:
    - Feature importance rankings
    - SHAP-like visualizations
    - Textual prediction rationales
    
    All black text with beginner-friendly tooltips.
    """
    return html.Div([
        # Beginner Guide Accordion
        dbc.Accordion([
            dbc.AccordionItem([
                dcc.Markdown("""
**🔍 What is Model Explainability?**

Machine learning models can seem like "black boxes" - they make predictions, but it's hard to understand *why*. 
The Model Insight Explorer helps you understand which factors most influenced each prediction.

**Key Concepts:**

- **Feature Importance**: Which data points (features) had the biggest impact on the prediction?
- **SHAP Values**: How much did each feature push the prediction up or down?
- **Contribution**: The percentage of the total prediction explained by each feature.

**How to Use:**

1. Select a ticker from your portfolio
2. Click "Generate Explanation"
3. Review the top contributing features and textual rationale
4. Use insights to validate or question the model's reasoning

**💡 Tip:** If a prediction seems wrong, check if the top features make logical sense. 
Unexpected feature importance can reveal data quality issues or market regime changes.
                """, className="small", style={'color': '#000000', 'backgroundColor': '#f0f8ff', 
                                                'padding': '15px', 'borderRadius': '8px'})
            ], title="📖 Beginner's Guide: Understanding Model Predictions")
        ], start_collapsed=True, className="mb-4"),
        
        # Ticker Selection & Controls
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label([
                            "Select Ticker ",
                            html.I(className="bi bi-info-circle ms-1", id='insight-ticker-info')
                        ], className="fw-bold", style={'color': '#000000'}),
                        dbc.Tooltip(
                            "Choose a ticker to explain. The model will show which features "
                            "contributed most to its prediction for this stock.",
                            target='insight-ticker-info',
                            placement='top'
                        ),
                        dcc.Dropdown(
                            id='insight-ticker-selector',
                            options=[
                                {'label': 'AAPL - Apple Inc.', 'value': 'AAPL'},
                                {'label': 'TSLA - Tesla Inc.', 'value': 'TSLA'},
                                {'label': 'NVDA - NVIDIA Corp.', 'value': 'NVDA'},
                                {'label': 'MSFT - Microsoft Corp.', 'value': 'MSFT'},
                                {'label': 'GOOGL - Alphabet Inc.', 'value': 'GOOGL'}
                            ],
                            value='AAPL',
                            clearable=False,
                            className="mb-3"
                        )
                    ], md=4),
                    
                    dbc.Col([
                        html.Label([
                            "Top Features ",
                            html.I(className="bi bi-info-circle ms-1", id='insight-topn-info')
                        ], className="fw-bold", style={'color': '#000000'}),
                        dbc.Tooltip(
                            "How many of the most important features to display. "
                            "Default is 10 - enough to understand the prediction without overwhelming detail.",
                            target='insight-topn-info',
                            placement='top'
                        ),
                        dcc.Slider(
                            id='insight-top-n-slider',
                            min=5,
                            max=20,
                            step=1,
                            value=10,
                            marks={5: '5', 10: '10', 15: '15', 20: '20'},
                            tooltip={"placement": "bottom", "always_visible": False}
                        )
                    ], md=4),
                    
                    dbc.Col([
                        html.Label("Action", className="fw-bold", style={'color': '#000000'}),
                        html.Div([
                            dbc.Button([
                                html.I(className="bi bi-lightbulb me-2"),
                                "Generate Explanation"
                            ], id='insight-generate-btn', color="primary", className="w-100 mt-2")
                        ])
                    ], md=4)
                ])
            ])
        ], className="mb-4"),
        
        # Phase 6: Batch Portfolio Explanation
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label([
                            "Portfolio Analysis (Phase 6) ",
                            html.I(className="bi bi-info-circle ms-1", id='explain-portfolio-info')
                        ], className="fw-bold", style={'color': '#000000'}),
                        dbc.Tooltip(
                            "Analyze SHAP explanations for all portfolio tickers simultaneously. "
                            "Shows aggregated feature importance and top contributing factors across your entire portfolio.",
                            target='explain-portfolio-info',
                            placement='top'
                        ),
                        html.P(
                            "Generate batch SHAP explanations for all portfolio holdings to identify "
                            "common drivers and divergent factors.",
                            className="small mb-3",
                            style={'color': '#000000'}
                        )
                    ], md=8),
                    
                    dbc.Col([
                        html.Label("Batch Action", className="fw-bold", style={'color': '#000000'}),
                        html.Div([
                            dbc.Button([
                                html.I(className="bi bi-stack me-2"),
                                "Explain All Portfolio"
                            ], id='explain-portfolio-btn', color="success", className="w-100 mt-2"),
                            dcc.Loading(
                                id="insight-loading-spinner",
                                type="default",
                                children=html.Div(id="insight-loading-output")
                            )
                        ])
                    ], md=4)
                ])
            ])
        ], className="mb-4"),
        
        # Results Container
        html.Div(id='insight-results-container', children=[
            dbc.Alert([
                html.I(className="bi bi-arrow-up-circle me-2"),
                html.Span([
                    "Select a ticker and click ",
                    html.Strong("'Generate Explanation'"),
                    " to see why the model made its prediction."
                ], style={'color': '#000000'})
            ], color="light")
        ])
    ], className="mt-3")


def _create_insights_metrics_section():
    """
    Section for displaying prediction results and metrics.
    """
    return dbc.Card([
        dbc.CardHeader([
            html.H5([
                html.I(className="bi bi-graph-up me-2"),
                "3️⃣ Insights & Metrics"
            ], className="mb-0", style={'color': '#000000'})
        ]),
        dbc.CardBody([
            # Placeholder for prediction results
            html.Div(id='azure-ml-prediction-results', children=[
                dbc.Alert([
                    html.I(className="bi bi-info-circle me-2"),
                    html.Span([
                        "Click ",
                        html.Strong("'Run Prediction'"),
                        " above to generate ML insights. Results will appear here."
                    ], style={'color': '#000000'})
                ], color="light")
            ]),
            
            # Tabs for different views
            dbc.Tabs([
                # Tab 1: Predictions
                dbc.Tab([
                    html.Div(id='azure-ml-predictions-table', className="mt-3")
                ], label="📊 Predictions", tab_id='predictions'),
                
                # Tab 2: Performance Metrics
                dbc.Tab([
                    html.Div(id='azure-ml-performance-metrics', className="mt-3")
                ], label="📈 Performance", tab_id='performance'),
                
                # Tab 3: Feature Importance
                dbc.Tab([
                    html.Div(id='azure-ml-feature-importance', className="mt-3")
                ], label="🔍 Feature Importance", tab_id='features'),
                
                # Tab 4: Risk Analysis
                dbc.Tab([
                    html.Div(id='azure-ml-risk-analysis', className="mt-3")
                ], label="⚠️ Risk Analysis", tab_id='risk'),
                
                # Tab 5: Model Insight Explorer (Phase 1)
                dbc.Tab([
                    _create_model_insight_explorer()
                ], label="🧠 Model Insights", tab_id='insights')
            ], id='azure-ml-insights-tabs', active_tab='predictions', className="mt-3")
        ])
    ])


# ============================================================================
# SECTION 4: LOGS / DIAGNOSTICS
# ============================================================================

def _create_logs_diagnostics_section():
    """
    Section for system logs and diagnostic information.
    """
    return dbc.Card([
        dbc.CardHeader([
            html.H5([
                html.I(className="bi bi-file-text me-2"),
                "4️⃣ Logs / Diagnostics"
            ], className="mb-0", style={'color': '#000000'})
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.H6("System Status", className="mb-3", style={'color': '#000000'}),
                    html.Div(id='azure-ml-system-status', children=[
                        html.Pre([
                            "Status: Scaffold Mode\n",
                            "Version: 1.0.0\n",
                            "Azure Connection: Not Configured\n",
                            "Last Prediction: N/A\n",
                            "Cache Status: Available"
                        ], style={'backgroundColor': '#f8f9fa', 'padding': '10px', 'borderRadius': '5px', 'color': '#000000'})
                    ])
                ], md=6),
                
                dbc.Col([
                    html.H6("Execution Logs", className="mb-3", style={'color': '#000000'}),
                    html.Div(id='azure-ml-execution-logs', children=[
                        html.Pre([
                            "[INFO] Azure ML Lab initialized\n",
                            "[INFO] Phase 3 Scaffold - Mock mode active\n",
                            "[WARN] No live ML execution configured\n",
                            "[INFO] Ready for prediction requests"
                        ], style={'backgroundColor': '#f8f9fa', 'padding': '10px', 'borderRadius': '5px', 'color': '#000000', 'maxHeight': '200px', 'overflowY': 'auto'})
                    ])
                ], md=6)
            ]),
            
            html.Hr(),
            
            # Diagnostic Buttons
            dbc.Row([
                dbc.Col([
                    dbc.Button([
                        html.I(className="bi bi-arrow-clockwise me-2"),
                        "Refresh Diagnostics"
                    ], id='azure-ml-refresh-diagnostics-btn', color="secondary", outline=True, className="w-100")
                ], md=3),
                dbc.Col([
                    dbc.Button([
                        html.I(className="bi bi-download me-2"),
                        "Export Logs"
                    ], id='azure-ml-export-logs-btn', color="secondary", outline=True, className="w-100")
                ], md=3),
                dbc.Col([
                    dbc.Button([
                        html.I(className="bi bi-trash me-2"),
                        "Clear Cache"
                    ], id='azure-ml-clear-cache-btn', color="warning", outline=True, className="w-100")
                ], md=3),
                dbc.Col([
                    dbc.Button([
                        html.I(className="bi bi-check-circle me-2"),
                        "Run Pre-Flight Check"
                    ], id='azure-ml-preflight-btn', color="info", outline=True, className="w-100")
                ], md=3)
            ], className="mt-3")
        ])
    ])


logger.info("✓ Azure ML Lab layout loaded (Phase 3 Scaffold)")
