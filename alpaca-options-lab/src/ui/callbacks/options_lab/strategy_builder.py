"""
Strategy Builder - Visual multi-leg strategy constructor

Author: Options Lab Enhancement Phase
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
import plotly.graph_objects as go

logger = logging.getLogger(__name__)


# Pre-defined strategy templates
STRATEGY_TEMPLATES = {
    'long_call': {
        'name': 'Long Call',
        'legs': [{'type': 'call', 'action': 'buy', 'strike_offset': 0}],
        'description': 'Bullish, unlimited upside, limited downside',
        'max_profit': 'Unlimited',
        'max_loss': 'Premium paid',
        'breakeven': 'Strike + Premium'
    },
    'long_put': {
        'name': 'Long Put',
        'legs': [{'type': 'put', 'action': 'buy', 'strike_offset': 0}],
        'description': 'Bearish, profit if stock falls',
        'max_profit': 'Strike - Premium (if stock goes to 0)',
        'max_loss': 'Premium paid',
        'breakeven': 'Strike - Premium'
    },
    'covered_call': {
        'name': 'Covered Call',
        'legs': [
            {'type': 'stock', 'action': 'buy', 'quantity': 100},
            {'type': 'call', 'action': 'sell', 'strike_offset': 5}
        ],
        'description': 'Generate income on stock holdings',
        'max_profit': 'Strike - Stock Price + Premium',
        'max_loss': 'Stock Price - Premium (if stock goes to 0)',
        'breakeven': 'Stock Price - Premium'
    },
    'protective_put': {
        'name': 'Protective Put (Married Put)',
        'legs': [
            {'type': 'stock', 'action': 'buy', 'quantity': 100},
            {'type': 'put', 'action': 'buy', 'strike_offset': -5}
        ],
        'description': 'Protect long stock position from downside',
        'max_profit': 'Unlimited',
        'max_loss': 'Stock Price - Strike + Premium',
        'breakeven': 'Stock Price + Premium'
    },
    'bull_call_spread': {
        'name': 'Bull Call Spread',
        'legs': [
            {'type': 'call', 'action': 'buy', 'strike_offset': 0},
            {'type': 'call', 'action': 'sell', 'strike_offset': 10}
        ],
        'description': 'Bullish with limited risk and limited reward',
        'max_profit': 'Spread Width - Net Debit',
        'max_loss': 'Net Debit',
        'breakeven': 'Long Strike + Net Debit'
    },
    'bear_put_spread': {
        'name': 'Bear Put Spread',
        'legs': [
            {'type': 'put', 'action': 'buy', 'strike_offset': 0},
            {'type': 'put', 'action': 'sell', 'strike_offset': -10}
        ],
        'description': 'Bearish with limited risk and limited reward',
        'max_profit': 'Spread Width - Net Debit',
        'max_loss': 'Net Debit',
        'breakeven': 'Long Strike - Net Debit'
    },
    'iron_condor': {
        'name': 'Iron Condor',
        'legs': [
            {'type': 'put', 'action': 'sell', 'strike_offset': -10},
            {'type': 'put', 'action': 'buy', 'strike_offset': -20},
            {'type': 'call', 'action': 'sell', 'strike_offset': 10},
            {'type': 'call', 'action': 'buy', 'strike_offset': 20}
        ],
        'description': 'Neutral, profit from low volatility',
        'max_profit': 'Net Credit',
        'max_loss': 'Spread Width - Net Credit',
        'breakeven': 'Short Strikes ± Net Credit'
    },
    'straddle': {
        'name': 'Long Straddle',
        'legs': [
            {'type': 'call', 'action': 'buy', 'strike_offset': 0},
            {'type': 'put', 'action': 'buy', 'strike_offset': 0}
        ],
        'description': 'Profit from large move in either direction',
        'max_profit': 'Unlimited',
        'max_loss': 'Total Premium',
        'breakeven': 'Strike ± Total Premium'
    },
    'strangle': {
        'name': 'Long Strangle',
        'legs': [
            {'type': 'call', 'action': 'buy', 'strike_offset': 5},
            {'type': 'put', 'action': 'buy', 'strike_offset': -5}
        ],
        'description': 'Cheaper than straddle, needs bigger move',
        'max_profit': 'Unlimited',
        'max_loss': 'Total Premium',
        'breakeven': 'Call Strike + Premium OR Put Strike - Premium'
    },
    'butterfly': {
        'name': 'Long Call Butterfly',
        'legs': [
            {'type': 'call', 'action': 'buy', 'strike_offset': -10},
            {'type': 'call', 'action': 'sell', 'strike_offset': 0, 'quantity': 2},
            {'type': 'call', 'action': 'buy', 'strike_offset': 10}
        ],
        'description': 'Profit if stock stays near middle strike',
        'max_profit': 'Spread Width - Net Debit',
        'max_loss': 'Net Debit',
        'breakeven': 'Lower Strike + Net Debit'
    },
    'calendar_spread': {
        'name': 'Calendar Spread',
        'legs': [
            {'type': 'call', 'action': 'sell', 'strike_offset': 0, 'expiry': 'near'},
            {'type': 'call', 'action': 'buy', 'strike_offset': 0, 'expiry': 'far'}
        ],
        'description': 'Profit from time decay differential',
        'max_profit': 'Varies (near expiry at strike)',
        'max_loss': 'Net Debit',
        'breakeven': 'Complex - depends on IV'
    }
}


class StrategyBuilder:
    """Build and analyze multi-leg options strategies."""
    
    def __init__(self):
        self.legs = []
        self.spot_price = 100
        
    def reset(self):
        """Clear all legs."""
        self.legs = []
        
    def add_leg(self, leg_type: str, action: str, strike: float, 
                premium: float, quantity: int = 1, expiration: str = None) -> None:
        """Add a leg to the strategy."""
        leg = {
            'type': leg_type,  # 'call', 'put', 'stock'
            'action': action,  # 'buy', 'sell'
            'strike': strike,
            'premium': premium,
            'quantity': quantity,
            'expiration': expiration,
            'sign': 1 if action == 'buy' else -1
        }
        self.legs.append(leg)
        logger.info(f"Added leg: {action} {quantity}x {leg_type} @ {strike}")
        
    def load_template(self, template_name: str, spot_price: float, 
                      base_premium: float = 5.0) -> List[Dict]:
        """Load a pre-defined strategy template."""
        self.reset()
        self.spot_price = spot_price
        
        template = STRATEGY_TEMPLATES.get(template_name)
        if not template:
            logger.warning(f"Unknown template: {template_name}")
            return []
        
        for leg_def in template['legs']:
            leg_type = leg_def['type']
            action = leg_def['action']
            qty = leg_def.get('quantity', 1)
            
            if leg_type == 'stock':
                strike = spot_price
                premium = spot_price
            else:
                strike = spot_price + leg_def.get('strike_offset', 0)
                # Estimate premium based on moneyness
                moneyness = abs(strike - spot_price) / spot_price
                premium = max(0.50, base_premium * (1 - moneyness * 2))
            
            self.add_leg(leg_type, action, strike, premium, qty)
        
        return self.legs
    
    def calculate_payoff(self, price_range: List[float] = None) -> pd.DataFrame:
        """Calculate payoff at expiration for a range of prices."""
        if not self.legs:
            return pd.DataFrame()
        
        if price_range is None:
            # Default range: ±30% from spot
            price_range = np.linspace(self.spot_price * 0.7, self.spot_price * 1.3, 100)
        
        payoffs = []
        
        for price in price_range:
            total_pnl = 0
            
            for leg in self.legs:
                leg_type = leg['type']
                strike = leg['strike']
                premium = leg['premium']
                qty = leg['quantity']
                sign = leg['sign']  # 1 for buy, -1 for sell
                
                if leg_type == 'call':
                    # Call payoff = max(0, S - K) - premium
                    intrinsic = max(0, price - strike)
                    pnl = (intrinsic - premium) * sign * qty * 100
                    
                elif leg_type == 'put':
                    # Put payoff = max(0, K - S) - premium
                    intrinsic = max(0, strike - price)
                    pnl = (intrinsic - premium) * sign * qty * 100
                    
                elif leg_type == 'stock':
                    # Stock P&L = (current - purchase) * shares
                    pnl = (price - strike) * qty * sign
                    
                else:
                    pnl = 0
                
                total_pnl += pnl
            
            payoffs.append({'price': price, 'pnl': total_pnl})
        
        return pd.DataFrame(payoffs)
    
    def get_metrics(self) -> Dict:
        """Calculate strategy metrics."""
        if not self.legs:
            return {}
        
        payoff_df = self.calculate_payoff()
        
        if payoff_df.empty:
            return {}
        
        max_profit = payoff_df['pnl'].max()
        max_loss = payoff_df['pnl'].min()
        
        # Find breakeven(s)
        breakevens = []
        for i in range(1, len(payoff_df)):
            if payoff_df.iloc[i-1]['pnl'] * payoff_df.iloc[i]['pnl'] < 0:
                # Linear interpolation
                p1, pnl1 = payoff_df.iloc[i-1]['price'], payoff_df.iloc[i-1]['pnl']
                p2, pnl2 = payoff_df.iloc[i]['price'], payoff_df.iloc[i]['pnl']
                be = p1 - pnl1 * (p2 - p1) / (pnl2 - pnl1)
                breakevens.append(round(be, 2))
        
        # Calculate net cost/credit
        net_premium = sum(
            leg['premium'] * leg['sign'] * leg['quantity'] * 100
            for leg in self.legs if leg['type'] != 'stock'
        )
        
        return {
            'max_profit': round(max_profit, 2),
            'max_profit_unlimited': max_profit > self.spot_price * 100,
            'max_loss': round(max_loss, 2),
            'max_loss_unlimited': max_loss < -self.spot_price * 100,
            'breakevens': breakevens,
            'net_premium': round(net_premium, 2),
            'is_credit': net_premium < 0,
            'risk_reward': abs(max_profit / max_loss) if max_loss != 0 else float('inf'),
            'legs': len(self.legs)
        }


def create_payoff_diagram(strategy: StrategyBuilder, ticker: str = "N/A") -> go.Figure:
    """Create visual payoff diagram for the strategy."""
    payoff_df = strategy.calculate_payoff()
    
    if payoff_df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No strategy defined", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template='plotly_dark')
        return fig
    
    metrics = strategy.get_metrics()
    
    fig = go.Figure()
    
    # Payoff line
    fig.add_trace(go.Scatter(
        x=payoff_df['price'],
        y=payoff_df['pnl'],
        mode='lines',
        line=dict(color='#4CAF50', width=3),
        fill='tozeroy',
        fillcolor='rgba(76, 175, 80, 0.3)',
        name='P&L at Expiration'
    ))
    
    # Zero line
    fig.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5)
    
    # Current price
    fig.add_vline(x=strategy.spot_price, line_dash="dot", line_color="yellow",
                  annotation_text=f"Current: ${strategy.spot_price:.2f}")
    
    # Breakeven points
    for be in metrics.get('breakevens', []):
        fig.add_vline(x=be, line_dash="dash", line_color="orange",
                      annotation_text=f"BE: ${be:.2f}")
    
    # Strike lines for each leg
    for leg in strategy.legs:
        if leg['type'] != 'stock':
            fig.add_vline(x=leg['strike'], line_dash="dot", line_color="cyan", opacity=0.3)
    
    # Title with metrics
    title = f"{ticker} Strategy Payoff"
    if metrics:
        title += f" | Max P/L: ${metrics['max_profit']:,.0f} / ${metrics['max_loss']:,.0f}"
        if metrics.get('breakevens'):
            title += f" | BE: ${metrics['breakevens'][0]:.2f}"
    
    fig.update_layout(
        title=title,
        xaxis_title="Stock Price at Expiration",
        yaxis_title="Profit / Loss ($)",
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,33,62,0.8)',
        height=450,
        hovermode='x unified'
    )
    
    return fig


def create_strategy_comparison(strategies: Dict[str, StrategyBuilder], 
                                spot_price: float) -> go.Figure:
    """Compare multiple strategies on the same chart."""
    fig = go.Figure()
    
    colors = ['#4CAF50', '#2196F3', '#f44336', '#FF9800', '#9C27B0']
    
    for idx, (name, strategy) in enumerate(strategies.items()):
        payoff_df = strategy.calculate_payoff()
        if not payoff_df.empty:
            color = colors[idx % len(colors)]
            fig.add_trace(go.Scatter(
                x=payoff_df['price'],
                y=payoff_df['pnl'],
                mode='lines',
                line=dict(color=color, width=2),
                name=name
            ))
    
    # Zero line
    fig.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5)
    
    # Current price
    fig.add_vline(x=spot_price, line_dash="dot", line_color="yellow",
                  annotation_text=f"Current: ${spot_price:.2f}")
    
    fig.update_layout(
        title="Strategy Comparison",
        xaxis_title="Stock Price at Expiration",
        yaxis_title="Profit / Loss ($)",
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,33,62,0.8)',
        height=450,
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    
    return fig


def get_strategy_templates() -> List[Dict]:
    """Get list of available strategy templates."""
    return [
        {
            'id': key,
            'name': val['name'],
            'description': val['description'],
            'legs': len(val['legs']),
            'max_profit': val['max_profit'],
            'max_loss': val['max_loss']
        }
        for key, val in STRATEGY_TEMPLATES.items()
    ]


# Singleton instance
_strategy_builder = None

def get_strategy_builder() -> StrategyBuilder:
    """Get singleton strategy builder instance."""
    global _strategy_builder
    if _strategy_builder is None:
        _strategy_builder = StrategyBuilder()
    return _strategy_builder
