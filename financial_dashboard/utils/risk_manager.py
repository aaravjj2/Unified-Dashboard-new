"""
Risk Management Module
Validates trades against risk limits before execution.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta


class RiskManager:
    """Manages risk checks for trades and positions."""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize risk manager.
        
        Args:
            config: Risk configuration dict
        """
        self.config = config or {}
        
        # Load risk limits from config
        self.max_position_size_per_ticker = self.config.get('max_position_size_per_ticker', 1000.0)
        self.max_total_exposure = self.config.get('max_total_exposure', 10000.0)
        self.max_daily_loss = self.config.get('max_daily_loss', 500.0)
        self.max_position_concentration = self.config.get('max_position_concentration', 0.25)
        self.max_contracts_per_order = self.config.get('max_contracts_per_order', 10)
        self.require_approval_above = self.config.get('require_approval_above', 2000.0)
        
        # Track daily P&L
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()
    
    def _reset_daily_counters(self):
        """Reset daily counters if it's a new day."""
        today = datetime.now().date()
        if today > self.last_reset_date:
            self.daily_pnl = 0.0
            self.last_reset_date = today
    
    def check_trade_risk(self, trade: Dict, current_positions: List[Dict], 
                        account_info: Dict) -> Tuple[bool, str]:
        """
        Check if a trade passes risk management rules.
        
        Args:
            trade: Trade dict with 'symbol', 'quantity', 'side', 'estimated_cost'
            current_positions: List of current position dicts
            account_info: Account information dict
        
        Returns:
            Tuple of (approved: bool, reason: str)
        """
        self._reset_daily_counters()
        
        symbol = trade.get('symbol')
        quantity = trade.get('quantity', 0)
        side = trade.get('side', 'buy')
        estimated_cost = trade.get('estimated_cost', 0)
        
        # Check 1: Maximum contracts per order
        if quantity > self.max_contracts_per_order:
            return False, f"Trade rejected: Quantity ({quantity}) exceeds max contracts per order ({self.max_contracts_per_order})"
        
        # Check 2: Minimum quantity
        if quantity <= 0:
            return False, f"Trade rejected: Invalid quantity ({quantity})"
        
        # Check 3: Buying power (check early for quick failure)
        buying_power = account_info.get('buying_power', 0)
        if side == 'buy' and estimated_cost > buying_power:
            return False, f"Trade rejected: Insufficient buying power (${buying_power:.2f} available, ${estimated_cost:.2f} needed)"
        
        # Check 4: Position concentration (if buying)
        if side == 'buy':
            portfolio_value = account_info.get('portfolio_value', 0)
            if portfolio_value > 0:
                new_position_pct = (estimated_cost / portfolio_value)
                if new_position_pct > self.max_position_concentration:
                    return False, f"Trade rejected: Position would be {new_position_pct*100:.1f}% of portfolio, exceeds limit ({self.max_position_concentration*100:.1f}%)"
        
        # Check 5: Position size limit per ticker
        if side == 'buy':
            current_exposure = self._get_ticker_exposure(symbol, current_positions)
            new_total_exposure = current_exposure + estimated_cost
            
            if new_total_exposure > self.max_position_size_per_ticker:
                return False, f"Trade rejected: Total exposure for {symbol} (${new_total_exposure:.2f}) would exceed limit (${self.max_position_size_per_ticker:.2f})"
        
        # Check 6: Total portfolio exposure
        total_exposure = self._get_total_exposure(current_positions)
        if side == 'buy':
            new_total = total_exposure + estimated_cost
            if new_total > self.max_total_exposure:
                return False, f"Trade rejected: Total portfolio exposure (${new_total:.2f}) would exceed limit (${self.max_total_exposure:.2f})"
        
        # Check 7: Daily loss limit
        if self.daily_pnl < -self.max_daily_loss:
            return False, f"Trade rejected: Daily loss limit reached (${-self.daily_pnl:.2f} lost today)"
        
        # Check 8: Manual approval required for large trades
        if estimated_cost > self.require_approval_above:
            return False, f"Trade requires manual approval: Cost (${estimated_cost:.2f}) exceeds auto-approval limit (${self.require_approval_above:.2f})"
        
        # All checks passed
        return True, "Trade approved"
    
    def check_position_risk(self, position: Dict, account_info: Dict) -> Tuple[bool, str]:
        """
        Check if an existing position violates risk limits.
        
        Args:
            position: Position dict
            account_info: Account information dict
        
        Returns:
            Tuple of (ok: bool, reason: str)
        """
        symbol = position.get('symbol')
        market_value = abs(position.get('market_value', 0))
        unrealized_pl = position.get('unrealized_pl', 0)
        
        # Check position size
        if market_value > self.max_position_size_per_ticker:
            return False, f"Position {symbol} exceeds size limit: ${market_value:.2f} > ${self.max_position_size_per_ticker:.2f}"
        
        # Check concentration
        portfolio_value = account_info.get('portfolio_value', 0)
        if portfolio_value > 0:
            concentration = market_value / portfolio_value
            if concentration > self.max_position_concentration:
                return False, f"Position {symbol} concentration too high: {concentration*100:.1f}% > {self.max_position_concentration*100:.1f}%"
        
        return True, "Position within risk limits"
    
    def update_daily_pnl(self, pnl_change: float):
        """
        Update daily P&L tracker.
        
        Args:
            pnl_change: P&L change amount
        """
        self._reset_daily_counters()
        self.daily_pnl += pnl_change
    
    def _get_ticker_exposure(self, symbol: str, positions: List[Dict]) -> float:
        """Get total exposure for a specific ticker."""
        exposure = 0.0
        for pos in positions:
            if pos.get('symbol') == symbol:
                exposure += abs(pos.get('market_value', 0))
        return exposure
    
    def _get_total_exposure(self, positions: List[Dict]) -> float:
        """Get total portfolio exposure."""
        return sum(abs(pos.get('market_value', 0)) for pos in positions)
    
    def get_risk_summary(self, positions: List[Dict], account_info: Dict) -> Dict:
        """
        Get summary of current risk metrics.
        
        Args:
            positions: Current positions
            account_info: Account information
        
        Returns:
            Dict with risk metrics
        """
        self._reset_daily_counters()
        
        total_exposure = self._get_total_exposure(positions)
        portfolio_value = account_info.get('portfolio_value', 0)
        
        # Calculate largest position concentration
        max_concentration = 0.0
        max_concentration_symbol = None
        if portfolio_value > 0:
            for pos in positions:
                concentration = abs(pos.get('market_value', 0)) / portfolio_value
                if concentration > max_concentration:
                    max_concentration = concentration
                    max_concentration_symbol = pos.get('symbol')
        
        return {
            'total_exposure': total_exposure,
            'max_total_exposure': self.max_total_exposure,
            'exposure_utilization_pct': (total_exposure / self.max_total_exposure * 100) if self.max_total_exposure > 0 else 0,
            'daily_pnl': self.daily_pnl,
            'daily_loss_limit': self.max_daily_loss,
            'daily_loss_utilization_pct': (abs(self.daily_pnl) / self.max_daily_loss * 100) if self.daily_pnl < 0 else 0,
            'max_concentration': max_concentration,
            'max_concentration_symbol': max_concentration_symbol,
            'max_concentration_limit': self.max_position_concentration,
            'num_positions': len(positions)
        }
