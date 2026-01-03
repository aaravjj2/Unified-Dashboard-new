"""
Visualization Service - Roadmap Items 461-500
Dashboard components and visualization
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ChartConfig:
    """Chart configuration"""
    chart_type: str
    title: str
    x_label: str
    y_label: str
    colors: List[str] = field(default_factory=lambda: ['#1f77b4', '#ff7f0e', '#2ca02c'])
    height: int = 400
    width: int = 800

@dataclass
class DashboardWidget:
    """Dashboard widget definition"""
    widget_id: str
    widget_type: str
    title: str
    data: Dict[str, Any]
    config: Dict[str, Any] = field(default_factory=dict)
    position: Tuple[int, int] = (0, 0)
    size: Tuple[int, int] = (1, 1)

class PlotlyChartGenerator:
    """Generate Plotly chart configurations - Items 461-488"""
    
    @staticmethod
    def candlestick_chart(ohlcv: pd.DataFrame, symbol: str = "") -> Dict[str, Any]:
        """Generate candlestick chart data - Item 483"""
        return {
            'type': 'candlestick',
            'data': [{
                'type': 'candlestick',
                'x': ohlcv.index.strftime('%Y-%m-%d').tolist(),
                'open': ohlcv['open'].tolist(),
                'high': ohlcv['high'].tolist(),
                'low': ohlcv['low'].tolist(),
                'close': ohlcv['close'].tolist(),
                'name': symbol
            }],
            'layout': {
                'title': f'{symbol} Price Chart',
                'xaxis': {'title': 'Date', 'rangeslider': {'visible': False}},
                'yaxis': {'title': 'Price'}
            }
        }
    
    @staticmethod
    def line_chart(data: pd.DataFrame, title: str = "") -> Dict[str, Any]:
        """Generate line chart data"""
        traces = []
        for col in data.columns:
            traces.append({
                'type': 'scatter',
                'mode': 'lines',
                'x': data.index.strftime('%Y-%m-%d').tolist() if hasattr(data.index, 'strftime') else data.index.tolist(),
                'y': data[col].tolist(),
                'name': col
            })
        
        return {
            'type': 'line',
            'data': traces,
            'layout': {
                'title': title,
                'xaxis': {'title': 'Date'},
                'yaxis': {'title': 'Value'}
            }
        }
    
    @staticmethod
    def heatmap(data: pd.DataFrame, title: str = "Correlation Matrix") -> Dict[str, Any]:
        """Generate heatmap - Item 468"""
        return {
            'type': 'heatmap',
            'data': [{
                'type': 'heatmap',
                'z': data.values.tolist(),
                'x': data.columns.tolist(),
                'y': data.index.tolist(),
                'colorscale': 'RdBu',
                'zmid': 0
            }],
            'layout': {
                'title': title,
                'xaxis': {'title': ''},
                'yaxis': {'title': ''}
            }
        }
    
    @staticmethod
    def pie_chart(values: List[float], labels: List[str], 
                  title: str = "Allocation") -> Dict[str, Any]:
        """Generate pie chart - Item 472"""
        return {
            'type': 'pie',
            'data': [{
                'type': 'pie',
                'values': values,
                'labels': labels,
                'hole': 0.4,
                'textinfo': 'label+percent'
            }],
            'layout': {
                'title': title
            }
        }
    
    @staticmethod
    def bar_chart(data: pd.Series, title: str = "") -> Dict[str, Any]:
        """Generate bar chart"""
        return {
            'type': 'bar',
            'data': [{
                'type': 'bar',
                'x': data.index.tolist(),
                'y': data.values.tolist(),
                'marker': {'color': ['#2ca02c' if v >= 0 else '#d62728' for v in data.values]}
            }],
            'layout': {
                'title': title,
                'xaxis': {'title': ''},
                'yaxis': {'title': 'Value'}
            }
        }
    
    @staticmethod
    def scatter_chart(x: List[float], y: List[float], labels: List[str] = None,
                     title: str = "Risk-Return") -> Dict[str, Any]:
        """Generate scatter chart - Item 477"""
        trace = {
            'type': 'scatter',
            'mode': 'markers+text' if labels else 'markers',
            'x': x,
            'y': y,
            'marker': {'size': 10}
        }
        
        if labels:
            trace['text'] = labels
            trace['textposition'] = 'top center'
        
        return {
            'type': 'scatter',
            'data': [trace],
            'layout': {
                'title': title,
                'xaxis': {'title': 'Risk (Volatility)'},
                'yaxis': {'title': 'Return'}
            }
        }
    
    @staticmethod
    def surface_3d(x: List[float], y: List[float], z: List[List[float]],
                   title: str = "Volatility Surface") -> Dict[str, Any]:
        """Generate 3D surface - Item 467"""
        return {
            'type': 'surface',
            'data': [{
                'type': 'surface',
                'x': x,
                'y': y,
                'z': z,
                'colorscale': 'Viridis'
            }],
            'layout': {
                'title': title,
                'scene': {
                    'xaxis': {'title': 'Strike'},
                    'yaxis': {'title': 'Expiry'},
                    'zaxis': {'title': 'Implied Vol'}
                }
            }
        }
    
    @staticmethod
    def drawdown_chart(returns: pd.Series, title: str = "Drawdown") -> Dict[str, Any]:
        """Generate drawdown visualization - Item 475"""
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        
        return {
            'type': 'area',
            'data': [{
                'type': 'scatter',
                'mode': 'lines',
                'fill': 'tozeroy',
                'x': drawdown.index.strftime('%Y-%m-%d').tolist() if hasattr(drawdown.index, 'strftime') else drawdown.index.tolist(),
                'y': (drawdown * 100).tolist(),
                'name': 'Drawdown',
                'fillcolor': 'rgba(255,0,0,0.3)',
                'line': {'color': 'red'}
            }],
            'layout': {
                'title': title,
                'xaxis': {'title': 'Date'},
                'yaxis': {'title': 'Drawdown (%)', 'ticksuffix': '%'}
            }
        }

class DashboardGenerator:
    """Dashboard layout generator - Items 461-500"""
    
    def __init__(self):
        self.widgets: List[DashboardWidget] = []
        self.chart_generator = PlotlyChartGenerator()
        
    def add_widget(self, widget: DashboardWidget):
        """Add widget to dashboard"""
        self.widgets.append(widget)
        
    def create_portfolio_dashboard(self, portfolio_data: Dict[str, Any]) -> List[DashboardWidget]:
        """Create portfolio monitoring dashboard - Item 461"""
        widgets = []
        
        # P&L Widget
        if 'pnl' in portfolio_data:
            widgets.append(DashboardWidget(
                widget_id='pnl_chart',
                widget_type='line_chart',
                title='Portfolio P&L',
                data=self.chart_generator.line_chart(
                    pd.DataFrame({'P&L': portfolio_data['pnl']}),
                    'Cumulative P&L'
                ),
                position=(0, 0),
                size=(2, 1)
            ))
        
        # Allocation Widget
        if 'allocation' in portfolio_data:
            alloc = portfolio_data['allocation']
            widgets.append(DashboardWidget(
                widget_id='allocation_pie',
                widget_type='pie_chart',
                title='Current Allocation',
                data=self.chart_generator.pie_chart(
                    list(alloc.values()),
                    list(alloc.keys()),
                    'Portfolio Allocation'
                ),
                position=(2, 0),
                size=(1, 1)
            ))
        
        # Risk Metrics Widget
        if 'risk_metrics' in portfolio_data:
            metrics = portfolio_data['risk_metrics']
            widgets.append(DashboardWidget(
                widget_id='risk_metrics',
                widget_type='metrics_card',
                title='Risk Metrics',
                data={
                    'metrics': [
                        {'label': 'VaR (95%)', 'value': f"{metrics.get('var_95', 0):.2%}"},
                        {'label': 'Sharpe', 'value': f"{metrics.get('sharpe', 0):.2f}"},
                        {'label': 'Max DD', 'value': f"{metrics.get('max_drawdown', 0):.2%}"},
                        {'label': 'Volatility', 'value': f"{metrics.get('volatility', 0):.2%}"}
                    ]
                },
                position=(0, 1),
                size=(1, 1)
            ))
        
        return widgets
    
    def create_options_dashboard(self, options_data: Dict[str, Any]) -> List[DashboardWidget]:
        """Create options analytics dashboard - Item 466"""
        widgets = []
        
        # Greeks Dashboard
        if 'greeks' in options_data:
            greeks = options_data['greeks']
            widgets.append(DashboardWidget(
                widget_id='greeks_display',
                widget_type='metrics_card',
                title='Portfolio Greeks',
                data={
                    'metrics': [
                        {'label': 'Delta', 'value': f"{greeks.get('delta', 0):.2f}"},
                        {'label': 'Gamma', 'value': f"{greeks.get('gamma', 0):.4f}"},
                        {'label': 'Theta', 'value': f"${greeks.get('theta', 0):.2f}"},
                        {'label': 'Vega', 'value': f"${greeks.get('vega', 0):.2f}"}
                    ]
                },
                position=(0, 0),
                size=(1, 1)
            ))
        
        # Vol Surface
        if 'vol_surface' in options_data:
            vs = options_data['vol_surface']
            widgets.append(DashboardWidget(
                widget_id='vol_surface_3d',
                widget_type='surface_3d',
                title='Volatility Surface',
                data=self.chart_generator.surface_3d(
                    vs.get('strikes', []),
                    vs.get('expiries', []),
                    vs.get('vols', [[]]),
                    'Implied Volatility Surface'
                ),
                position=(1, 0),
                size=(2, 1)
            ))
        
        return widgets
    
    def create_execution_dashboard(self, execution_data: Dict[str, Any]) -> List[DashboardWidget]:
        """Create execution monitoring dashboard - Item 463"""
        widgets = []
        
        # Order Blotter
        if 'orders' in execution_data:
            widgets.append(DashboardWidget(
                widget_id='order_blotter',
                widget_type='data_table',
                title='Order Blotter',
                data={
                    'columns': ['Order ID', 'Symbol', 'Side', 'Qty', 'Price', 'Status'],
                    'rows': execution_data['orders']
                },
                position=(0, 0),
                size=(2, 1)
            ))
        
        # Execution Metrics
        if 'metrics' in execution_data:
            metrics = execution_data['metrics']
            widgets.append(DashboardWidget(
                widget_id='exec_metrics',
                widget_type='metrics_card',
                title='Execution Quality',
                data={
                    'metrics': [
                        {'label': 'Avg Slippage', 'value': f"{metrics.get('avg_slippage', 0):.2%}"},
                        {'label': 'Fill Rate', 'value': f"{metrics.get('fill_rate', 0):.1%}"},
                        {'label': 'VWAP Diff', 'value': f"{metrics.get('vwap_diff', 0):.2%}"}
                    ]
                },
                position=(2, 0),
                size=(1, 1)
            ))
        
        return widgets
    
    def export_layout(self) -> Dict[str, Any]:
        """Export dashboard layout as JSON"""
        return {
            'widgets': [
                {
                    'id': w.widget_id,
                    'type': w.widget_type,
                    'title': w.title,
                    'data': w.data,
                    'config': w.config,
                    'position': {'row': w.position[0], 'col': w.position[1]},
                    'size': {'rows': w.size[0], 'cols': w.size[1]}
                }
                for w in self.widgets
            ],
            'generated_at': datetime.now().isoformat()
        }

class AlertSystem:
    """Alert and notification system - Item 489"""
    
    def __init__(self):
        self.alerts: List[Dict[str, Any]] = []
        self.thresholds: Dict[str, Dict[str, float]] = {}
        
    def set_threshold(self, metric: str, warning: float, critical: float):
        """Set alert thresholds"""
        self.thresholds[metric] = {'warning': warning, 'critical': critical}
    
    def check_threshold(self, metric: str, value: float) -> Optional[Dict[str, Any]]:
        """Check value against thresholds"""
        if metric not in self.thresholds:
            return None
        
        thresh = self.thresholds[metric]
        
        if abs(value) >= thresh['critical']:
            alert = {
                'type': 'critical',
                'metric': metric,
                'value': value,
                'threshold': thresh['critical'],
                'timestamp': datetime.now().isoformat(),
                'message': f"CRITICAL: {metric} = {value:.2%} exceeds threshold {thresh['critical']:.2%}"
            }
            self.alerts.append(alert)
            return alert
        elif abs(value) >= thresh['warning']:
            alert = {
                'type': 'warning',
                'metric': metric,
                'value': value,
                'threshold': thresh['warning'],
                'timestamp': datetime.now().isoformat(),
                'message': f"WARNING: {metric} = {value:.2%} exceeds threshold {thresh['warning']:.2%}"
            }
            self.alerts.append(alert)
            return alert
        
        return None
    
    def get_alerts(self, since: datetime = None) -> List[Dict[str, Any]]:
        """Get alerts"""
        if since:
            return [a for a in self.alerts 
                   if datetime.fromisoformat(a['timestamp']) >= since]
        return self.alerts

class VisualizationService:
    """Main visualization service - Items 461-500"""
    
    def __init__(self):
        self.chart_generator = PlotlyChartGenerator()
        self.dashboard_generator = DashboardGenerator()
        self.alert_system = AlertSystem()
        
        # Setup default thresholds
        self.alert_system.set_threshold('drawdown', 0.10, 0.20)
        self.alert_system.set_threshold('var', 0.03, 0.05)
        self.alert_system.set_threshold('volatility', 0.30, 0.50)
        
    def generate_portfolio_charts(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate all portfolio charts"""
        charts = {}
        
        if 'returns' in portfolio_data:
            returns = pd.Series(portfolio_data['returns'])
            charts['cumulative_returns'] = self.chart_generator.line_chart(
                pd.DataFrame({'Cumulative Return': (1 + returns).cumprod() - 1}),
                'Cumulative Returns'
            )
            charts['drawdown'] = self.chart_generator.drawdown_chart(returns)
        
        if 'allocation' in portfolio_data:
            alloc = portfolio_data['allocation']
            charts['allocation'] = self.chart_generator.pie_chart(
                list(alloc.values()),
                list(alloc.keys())
            )
        
        if 'correlation' in portfolio_data:
            corr = pd.DataFrame(portfolio_data['correlation'])
            charts['correlation'] = self.chart_generator.heatmap(corr)
        
        return charts
    
    def generate_risk_charts(self, risk_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate risk visualization charts"""
        charts = {}
        
        if 'var_distribution' in risk_data:
            dist = risk_data['var_distribution']
            charts['var_histogram'] = {
                'type': 'histogram',
                'data': [{
                    'type': 'histogram',
                    'x': dist,
                    'nbinsx': 50
                }],
                'layout': {'title': 'Return Distribution with VaR'}
            }
        
        if 'stress_results' in risk_data:
            stress = risk_data['stress_results']
            charts['stress_test'] = self.chart_generator.bar_chart(
                pd.Series({s['scenario']: s['loss'] for s in stress}),
                'Stress Test Results'
            )
        
        return charts
    
    def create_full_dashboard(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create complete dashboard"""
        # Portfolio widgets
        if 'portfolio' in data:
            widgets = self.dashboard_generator.create_portfolio_dashboard(data['portfolio'])
            for w in widgets:
                self.dashboard_generator.add_widget(w)
        
        # Options widgets
        if 'options' in data:
            widgets = self.dashboard_generator.create_options_dashboard(data['options'])
            for w in widgets:
                self.dashboard_generator.add_widget(w)
        
        # Execution widgets
        if 'execution' in data:
            widgets = self.dashboard_generator.create_execution_dashboard(data['execution'])
            for w in widgets:
                self.dashboard_generator.add_widget(w)
        
        return self.dashboard_generator.export_layout()
    
    def check_alerts(self, metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        """Check metrics against alert thresholds"""
        triggered = []
        
        for metric, value in metrics.items():
            alert = self.alert_system.check_threshold(metric, value)
            if alert:
                triggered.append(alert)
        
        return triggered
    
    def generate_sample_analysis(self) -> Dict[str, Any]:
        """Generate sample analysis for testing"""
        np.random.seed(42)
        
        # Generate sample data
        n_periods = 252
        
        # Returns
        returns = np.random.normal(0.0004, 0.015, n_periods)
        
        # Allocation
        allocation = {
            'Tech': 0.30,
            'Finance': 0.20,
            'Healthcare': 0.15,
            'Consumer': 0.15,
            'Energy': 0.10,
            'Cash': 0.10
        }
        
        # Risk metrics
        risk_metrics = {
            'var_95': 0.025,
            'sharpe': 1.5,
            'max_drawdown': -0.12,
            'volatility': 0.18
        }
        
        # Greeks
        greeks = {
            'delta': 0.65,
            'gamma': 0.02,
            'theta': -150.0,
            'vega': 500.0
        }
        
        # Create portfolio data
        portfolio_data = {
            'returns': returns.tolist(),
            'allocation': allocation,
            'risk_metrics': risk_metrics
        }
        
        # Generate charts
        charts = self.generate_portfolio_charts({
            'returns': returns,
            'allocation': allocation
        })
        
        # Create dashboard
        dashboard = self.create_full_dashboard({
            'portfolio': {
                'pnl': pd.Series(
                    np.cumsum(returns) * 1000000,
                    index=pd.date_range(end=pd.Timestamp.now(), periods=n_periods, freq='D')
                ),
                'allocation': allocation,
                'risk_metrics': risk_metrics
            },
            'options': {
                'greeks': greeks
            }
        })
        
        # Check alerts
        alerts = self.check_alerts({
            'drawdown': 0.12,
            'var': 0.025,
            'volatility': 0.18
        })
        
        return {
            'charts_generated': list(charts.keys()),
            'dashboard_widgets': len(dashboard['widgets']),
            'alerts_triggered': len(alerts),
            'sample_chart': charts.get('cumulative_returns', {}),
            'dashboard_preview': {
                'widget_types': [w['type'] for w in dashboard['widgets'][:5]]
            }
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        return {
            'total_widgets': len(self.dashboard_generator.widgets),
            'total_alerts': len(self.alert_system.alerts),
            'thresholds_configured': len(self.alert_system.thresholds)
        }


if __name__ == "__main__":
    # Test the service
    service = VisualizationService()
    
    print("Visualization Service Test")
    print("=" * 50)
    
    # Generate sample analysis
    analysis = service.generate_sample_analysis()
    
    print(f"\nCharts Generated: {analysis['charts_generated']}")
    print(f"Dashboard Widgets: {analysis['dashboard_widgets']}")
    print(f"Alerts Triggered: {analysis['alerts_triggered']}")
    
    print("\nDashboard Widget Types:")
    for wtype in analysis['dashboard_preview']['widget_types']:
        print(f"  - {wtype}")
    
    print(f"\nService Stats: {service.get_stats()}")
    
    print("\n✅ Visualization Service operational - Items 461-500")
