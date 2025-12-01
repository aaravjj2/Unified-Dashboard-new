"""
Covered Call Screener Strategy
Identifies potential covered call trades based on delta, premium, and other criteria.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from strategies.base_strategy import BaseStrategy


class CoveredCallScreener(BaseStrategy):
    """Strategy for finding covered call opportunities."""
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize covered call screener strategy."""
        super().__init__(name="Covered Call Screener", config=config)
        
        # Strategy parameters from config
        self.min_stock_price = self.config.get('min_stock_price', 10.0)
        self.max_stock_price = self.config.get('max_stock_price', 500.0)
        self.min_volume = self.config.get('min_volume', 100000)
        self.target_delta = self.config.get('target_delta', 0.30)
        self.min_premium = self.config.get('min_premium', 0.50)
        self.days_to_expiration_min = self.config.get('days_to_expiration_min', 7)
        self.days_to_expiration_max = self.config.get('days_to_expiration_max', 45)
        self.delta_tolerance = 0.05  # Allow +/- 0.05 delta
    
    def generate_signals(self, data: Dict[str, Any]) -> List[Dict]:
        """
        Generate covered call signals.
        
        Args:
            data: Market data containing:
                - symbol: Stock ticker
                - current_price: Current stock price
                - options_chain: Options chain data
                - volume: Stock volume
        
        Returns:
            List of signal dicts
        """
        signals = []
        
        # Extract data
        symbol = data.get('symbol')
        current_price = data.get('current_price')
        options_chain = data.get('options_chain', {})
        volume = data.get('volume', 0)
        
        # Validate basic criteria
        if not self._validate_stock_criteria(current_price, volume):
            return signals
        
        # Find suitable call options
        calls = options_chain.get('calls', [])
        
        for call in calls:
            signal = self._evaluate_call_option(call, current_price, symbol)
            if signal:
                signals.append(signal)
        
        # Sort by premium (highest first) and limit to top 3
        signals.sort(key=lambda x: x.get('metadata', {}).get('premium', 0), reverse=True)
        return signals[:3]
    
    def _validate_stock_criteria(self, current_price: float, volume: int) -> bool:
        """
        Check if stock meets basic criteria.
        
        Args:
            current_price: Current stock price
            volume: Daily volume
        
        Returns:
            True if stock passes criteria
        """
        if not current_price:
            return False
        
        if current_price < self.min_stock_price or current_price > self.max_stock_price:
            return False
        
        if volume < self.min_volume:
            return False
        
        return True
    
    def _evaluate_call_option(self, call: Dict, current_price: float, stock_symbol: str) -> Optional[Dict]:
        """
        Evaluate a single call option for covered call suitability.
        
        Args:
            call: Call option data
            current_price: Current stock price
            stock_symbol: Stock ticker
        
        Returns:
            Signal dict if suitable, None otherwise
        """
        # Extract option data
        strike = call.get('strike')
        expiration = call.get('expiration')
        delta = call.get('delta')
        bid = call.get('bid', 0)
        ask = call.get('ask', 0)
        volume = call.get('volume', 0)
        open_interest = call.get('open_interest', 0)
        option_symbol = call.get('symbol')
        
        # Calculate mid premium
        premium = (bid + ask) / 2 if bid and ask else 0
        
        # Check days to expiration
        if expiration:
            try:
                exp_date = datetime.strptime(expiration, '%Y-%m-%d')
                days_to_exp = (exp_date - datetime.now()).days
                
                if days_to_exp < self.days_to_expiration_min or days_to_exp > self.days_to_expiration_max:
                    return None
            except:
                return None
        else:
            return None
        
        # Check delta (should be around target, e.g., 0.30 for OTM calls)
        if not delta or abs(delta - self.target_delta) > self.delta_tolerance:
            return None
        
        # Check minimum premium
        if premium < self.min_premium:
            return None
        
        # Check liquidity (volume or open interest)
        if volume < 10 and open_interest < 50:
            return None
        
        # Calculate annualized return
        return_pct = (premium / current_price) * 100
        annualized_return = (return_pct / days_to_exp) * 365
        
        # Generate signal
        signal = {
            'action': 'sell',  # Sell covered call
            'symbol': option_symbol or f"{stock_symbol}_CALL_{strike}_{expiration}",
            'quantity': 1,  # Start with 1 contract
            'reason': f"Covered call @ ${strike:.2f} strike, ${premium:.2f} premium, {days_to_exp}d to exp, {annualized_return:.1f}% annualized return",
            'confidence': min(0.5 + (premium / 5.0), 0.95),  # Higher premium = higher confidence
            'metadata': {
                'strike': strike,
                'expiration': expiration,
                'days_to_expiration': days_to_exp,
                'premium': premium,
                'delta': delta,
                'return_pct': return_pct,
                'annualized_return': annualized_return,
                'bid': bid,
                'ask': ask,
                'volume': volume,
                'open_interest': open_interest,
                'underlying_price': current_price
            }
        }
        
        return signal
    
    def get_status(self) -> Dict:
        """Get strategy status with parameters."""
        status = super().get_status()
        status['parameters'] = {
            'target_delta': self.target_delta,
            'min_premium': self.min_premium,
            'days_to_expiration_range': f"{self.days_to_expiration_min}-{self.days_to_expiration_max}",
            'stock_price_range': f"${self.min_stock_price}-${self.max_stock_price}",
            'min_volume': self.min_volume
        }
        return status
