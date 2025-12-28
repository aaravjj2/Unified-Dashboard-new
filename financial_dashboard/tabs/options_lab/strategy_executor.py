"""
Options Strategy Executor
=========================
Execute real options strategies using Alpaca Trading API.

Supports:
- Covered Call
- Cash-Secured Put
- Iron Condor
- Bull Call Spread
- Bear Put Spread
- Straddle/Strangle

Author: Options Lab Enhancement
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Alpaca Trading API keys
ALPACA_KEY = os.getenv('ALPACA3_KEY') or os.getenv('APCA_API_KEY_ID')
ALPACA_SECRET = os.getenv('ALPACA3_SECRET') or os.getenv('APCA_API_SECRET_KEY')
ALPACA_ENDPOINT = os.getenv('ALPACA3_ENDPOINT', 'https://paper-api.alpaca.markets')


class OrderSide(Enum):
    BUY = 'buy'
    SELL = 'sell'


class OrderType(Enum):
    MARKET = 'market'
    LIMIT = 'limit'


class OptionType(Enum):
    CALL = 'call'
    PUT = 'put'


@dataclass
class OptionLeg:
    """Single leg of an options strategy."""
    symbol: str  # OCC symbol
    side: OrderSide
    quantity: int
    option_type: OptionType
    strike: float
    expiration: str
    limit_price: Optional[float] = None


@dataclass
class StrategyOrder:
    """Multi-leg strategy order."""
    legs: List[OptionLeg]
    strategy_name: str
    underlying: str
    max_loss: float
    max_profit: float
    breakeven: List[float]


class AlpacaTradingClient:
    """Client for Alpaca Trading API."""
    
    def __init__(self, api_key: str = None, secret_key: str = None, paper: bool = True):
        self.api_key = api_key or ALPACA_KEY
        self.secret_key = secret_key or ALPACA_SECRET
        self.base_url = ALPACA_ENDPOINT if paper else 'https://api.alpaca.markets'
        self.headers = {
            'APCA-API-KEY-ID': self.api_key,
            'APCA-API-SECRET-KEY': self.secret_key,
            'Content-Type': 'application/json'
        }
        self._account_info = None
        
    def is_configured(self) -> bool:
        """Check if trading credentials are configured."""
        return bool(self.api_key and self.secret_key)
    
    def get_account(self) -> Dict:
        """Get account information."""
        if not self.is_configured():
            return {'error': 'Alpaca not configured'}
        
        import requests
        try:
            url = f"{self.base_url}/v2/account"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                self._account_info = response.json()
                return self._account_info
            else:
                return {'error': f'API error: {response.status_code}'}
                
        except Exception as e:
            return {'error': str(e)}
    
    def get_positions(self) -> List[Dict]:
        """Get all current positions."""
        if not self.is_configured():
            return []
        
        import requests
        try:
            url = f"{self.base_url}/v2/positions"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            return []
            
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []
    
    def place_order(self, symbol: str, qty: int, side: str, order_type: str = 'market',
                    limit_price: float = None, time_in_force: str = 'day') -> Dict:
        """
        Place a single order (stock or option).
        
        Args:
            symbol: Stock symbol or OCC option symbol
            qty: Number of shares/contracts
            side: 'buy' or 'sell'
            order_type: 'market' or 'limit'
            limit_price: Required for limit orders
            time_in_force: 'day', 'gtc', 'ioc', 'fok'
            
        Returns:
            Order response dict
        """
        if not self.is_configured():
            return {'error': 'Alpaca not configured'}
        
        import requests
        
        order_data = {
            'symbol': symbol,
            'qty': str(qty),
            'side': side,
            'type': order_type,
            'time_in_force': time_in_force
        }
        
        if order_type == 'limit' and limit_price:
            order_data['limit_price'] = str(limit_price)
        
        try:
            url = f"{self.base_url}/v2/orders"
            response = requests.post(url, headers=self.headers, json=order_data, timeout=10)
            
            if response.status_code in (200, 201):
                order = response.json()
                logger.info(f"✅ Order placed: {side} {qty} {symbol} - ID: {order.get('id')}")
                return order
            else:
                error = response.json() if response.text else {'message': response.status_code}
                logger.error(f"❌ Order failed: {error}")
                return {'error': error}
                
        except Exception as e:
            logger.error(f"Order failed: {e}")
            return {'error': str(e)}
    
    def place_option_order(self, underlying: str, option_type: str, strike: float,
                           expiration: str, side: str, qty: int = 1,
                           order_type: str = 'limit', limit_price: float = None) -> Dict:
        """
        Place an option order.
        
        Args:
            underlying: Stock symbol (e.g., 'SPY')
            option_type: 'call' or 'put'
            strike: Strike price
            expiration: Expiration date (YYYY-MM-DD)
            side: 'buy' or 'sell'
            qty: Number of contracts
            order_type: 'market' or 'limit'
            limit_price: Required for limit orders
            
        Returns:
            Order response dict
        """
        # Convert to OCC symbol format
        # Format: SPY240119C00450000
        exp_str = expiration.replace('-', '')[2:]  # YYMMDD
        opt_char = 'C' if option_type.lower() == 'call' else 'P'
        strike_str = f"{int(strike * 1000):08d}"
        occ_symbol = f"{underlying}{exp_str}{opt_char}{strike_str}"
        
        return self.place_order(
            symbol=occ_symbol,
            qty=qty,
            side=side,
            order_type=order_type,
            limit_price=limit_price
        )
    
    def place_multi_leg_order(self, strategy: StrategyOrder) -> Dict:
        """
        Place a multi-leg options order.
        
        Args:
            strategy: StrategyOrder with multiple legs
            
        Returns:
            Order response dict
        """
        if not self.is_configured():
            return {'error': 'Alpaca not configured'}
        
        import requests
        
        # Build legs array for Alpaca API
        legs = []
        for leg in strategy.legs:
            legs.append({
                'symbol': leg.symbol,
                'qty': str(leg.quantity),
                'side': leg.side.value,
                'type': 'limit' if leg.limit_price else 'market',
                'limit_price': str(leg.limit_price) if leg.limit_price else None
            })
        
        order_data = {
            'order_class': 'bracket' if len(legs) > 1 else 'simple',
            'type': 'limit',
            'time_in_force': 'day',
            'legs': legs
        }
        
        try:
            url = f"{self.base_url}/v2/orders"
            response = requests.post(url, headers=self.headers, json=order_data, timeout=10)
            
            if response.status_code in (200, 201):
                order = response.json()
                logger.info(f"✅ Multi-leg order placed: {strategy.strategy_name} - ID: {order.get('id')}")
                return order
            else:
                error = response.json() if response.text else {'message': response.status_code}
                logger.error(f"❌ Multi-leg order failed: {error}")
                return {'error': error}
                
        except Exception as e:
            logger.error(f"Multi-leg order failed: {e}")
            return {'error': str(e)}
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order by ID."""
        if not self.is_configured():
            return False
        
        import requests
        try:
            url = f"{self.base_url}/v2/orders/{order_id}"
            response = requests.delete(url, headers=self.headers, timeout=10)
            return response.status_code in (200, 204)
            
        except Exception:
            return False


class StrategyBuilder:
    """Build common options strategies."""
    
    @staticmethod
    def build_occ_symbol(underlying: str, expiration: str, option_type: str, strike: float) -> str:
        """Build OCC option symbol."""
        exp_str = expiration.replace('-', '')[2:]  # YYMMDD from YYYY-MM-DD
        opt_char = 'C' if option_type.lower() == 'call' else 'P'
        strike_str = f"{int(strike * 1000):08d}"
        return f"{underlying}{exp_str}{opt_char}{strike_str}"
    
    @staticmethod
    def covered_call(underlying: str, spot: float, call_strike: float, 
                     expiration: str, shares: int = 100, call_premium: float = 2.0) -> StrategyOrder:
        """
        Build covered call strategy.
        
        - Own 100 shares of stock
        - Sell 1 OTM call
        
        Args:
            underlying: Stock symbol
            spot: Current stock price
            call_strike: Strike for sold call (should be > spot)
            expiration: Expiration date
            shares: Number of shares (usually 100 per contract)
            call_premium: Expected premium received
            
        Returns:
            StrategyOrder
        """
        call_symbol = StrategyBuilder.build_occ_symbol(underlying, expiration, 'call', call_strike)
        
        legs = [
            OptionLeg(
                symbol=call_symbol,
                side=OrderSide.SELL,
                quantity=shares // 100,
                option_type=OptionType.CALL,
                strike=call_strike,
                expiration=expiration,
                limit_price=call_premium
            )
        ]
        
        max_profit = (call_strike - spot) * 100 + call_premium * 100
        max_loss = spot * 100 - call_premium * 100  # If stock goes to 0
        breakeven = spot - call_premium
        
        return StrategyOrder(
            legs=legs,
            strategy_name='Covered Call',
            underlying=underlying,
            max_loss=max_loss,
            max_profit=max_profit,
            breakeven=[breakeven]
        )
    
    @staticmethod
    def cash_secured_put(underlying: str, spot: float, put_strike: float,
                         expiration: str, put_premium: float = 2.0) -> StrategyOrder:
        """
        Build cash-secured put strategy.
        
        - Sell 1 OTM put
        - Keep cash to buy shares if assigned
        
        Args:
            underlying: Stock symbol
            spot: Current stock price
            put_strike: Strike for sold put (should be < spot)
            expiration: Expiration date
            put_premium: Expected premium received
            
        Returns:
            StrategyOrder
        """
        put_symbol = StrategyBuilder.build_occ_symbol(underlying, expiration, 'put', put_strike)
        
        legs = [
            OptionLeg(
                symbol=put_symbol,
                side=OrderSide.SELL,
                quantity=1,
                option_type=OptionType.PUT,
                strike=put_strike,
                expiration=expiration,
                limit_price=put_premium
            )
        ]
        
        max_profit = put_premium * 100
        max_loss = (put_strike - put_premium) * 100  # If stock goes to 0
        breakeven = put_strike - put_premium
        
        return StrategyOrder(
            legs=legs,
            strategy_name='Cash-Secured Put',
            underlying=underlying,
            max_loss=max_loss,
            max_profit=max_profit,
            breakeven=[breakeven]
        )
    
    @staticmethod
    def bull_call_spread(underlying: str, spot: float, 
                         long_strike: float, short_strike: float,
                         expiration: str, net_debit: float = 2.0) -> StrategyOrder:
        """
        Build bull call spread.
        
        - Buy 1 ATM/ITM call
        - Sell 1 OTM call (higher strike)
        
        Args:
            underlying: Stock symbol
            spot: Current stock price
            long_strike: Strike for bought call (lower)
            short_strike: Strike for sold call (higher)
            expiration: Expiration date
            net_debit: Net cost of spread
            
        Returns:
            StrategyOrder
        """
        long_symbol = StrategyBuilder.build_occ_symbol(underlying, expiration, 'call', long_strike)
        short_symbol = StrategyBuilder.build_occ_symbol(underlying, expiration, 'call', short_strike)
        
        legs = [
            OptionLeg(
                symbol=long_symbol,
                side=OrderSide.BUY,
                quantity=1,
                option_type=OptionType.CALL,
                strike=long_strike,
                expiration=expiration,
                limit_price=net_debit + 1.5  # Long leg premium
            ),
            OptionLeg(
                symbol=short_symbol,
                side=OrderSide.SELL,
                quantity=1,
                option_type=OptionType.CALL,
                strike=short_strike,
                expiration=expiration,
                limit_price=1.5  # Short leg premium
            )
        ]
        
        max_profit = (short_strike - long_strike - net_debit) * 100
        max_loss = net_debit * 100
        breakeven = long_strike + net_debit
        
        return StrategyOrder(
            legs=legs,
            strategy_name='Bull Call Spread',
            underlying=underlying,
            max_loss=max_loss,
            max_profit=max_profit,
            breakeven=[breakeven]
        )
    
    @staticmethod
    def iron_condor(underlying: str, spot: float,
                    put_short: float, put_long: float,
                    call_short: float, call_long: float,
                    expiration: str, net_credit: float = 2.0) -> StrategyOrder:
        """
        Build iron condor.
        
        - Sell OTM put
        - Buy further OTM put (protection)
        - Sell OTM call
        - Buy further OTM call (protection)
        
        Args:
            underlying: Stock symbol
            spot: Current stock price
            put_short: Short put strike (below spot)
            put_long: Long put strike (below short put)
            call_short: Short call strike (above spot)
            call_long: Long call strike (above short call)
            expiration: Expiration date
            net_credit: Expected net credit received
            
        Returns:
            StrategyOrder
        """
        legs = [
            OptionLeg(
                symbol=StrategyBuilder.build_occ_symbol(underlying, expiration, 'put', put_long),
                side=OrderSide.BUY,
                quantity=1,
                option_type=OptionType.PUT,
                strike=put_long,
                expiration=expiration
            ),
            OptionLeg(
                symbol=StrategyBuilder.build_occ_symbol(underlying, expiration, 'put', put_short),
                side=OrderSide.SELL,
                quantity=1,
                option_type=OptionType.PUT,
                strike=put_short,
                expiration=expiration
            ),
            OptionLeg(
                symbol=StrategyBuilder.build_occ_symbol(underlying, expiration, 'call', call_short),
                side=OrderSide.SELL,
                quantity=1,
                option_type=OptionType.CALL,
                strike=call_short,
                expiration=expiration
            ),
            OptionLeg(
                symbol=StrategyBuilder.build_occ_symbol(underlying, expiration, 'call', call_long),
                side=OrderSide.BUY,
                quantity=1,
                option_type=OptionType.CALL,
                strike=call_long,
                expiration=expiration
            )
        ]
        
        wing_width = put_short - put_long  # Assume symmetric
        max_profit = net_credit * 100
        max_loss = (wing_width - net_credit) * 100
        breakeven_low = put_short - net_credit
        breakeven_high = call_short + net_credit
        
        return StrategyOrder(
            legs=legs,
            strategy_name='Iron Condor',
            underlying=underlying,
            max_loss=max_loss,
            max_profit=max_profit,
            breakeven=[breakeven_low, breakeven_high]
        )
    
    @staticmethod
    def straddle(underlying: str, spot: float, strike: float,
                 expiration: str, is_long: bool = True, total_premium: float = 5.0) -> StrategyOrder:
        """
        Build straddle (ATM call + ATM put).
        
        - Long straddle: Buy call + Buy put (bet on movement)
        - Short straddle: Sell call + Sell put (bet on no movement)
        
        Args:
            underlying: Stock symbol
            spot: Current stock price
            strike: ATM strike (usually = spot)
            expiration: Expiration date
            is_long: True for long straddle, False for short
            total_premium: Total premium paid/received
            
        Returns:
            StrategyOrder
        """
        side = OrderSide.BUY if is_long else OrderSide.SELL
        
        legs = [
            OptionLeg(
                symbol=StrategyBuilder.build_occ_symbol(underlying, expiration, 'call', strike),
                side=side,
                quantity=1,
                option_type=OptionType.CALL,
                strike=strike,
                expiration=expiration,
                limit_price=total_premium / 2
            ),
            OptionLeg(
                symbol=StrategyBuilder.build_occ_symbol(underlying, expiration, 'put', strike),
                side=side,
                quantity=1,
                option_type=OptionType.PUT,
                strike=strike,
                expiration=expiration,
                limit_price=total_premium / 2
            )
        ]
        
        if is_long:
            max_profit = float('inf')  # Unlimited on upside
            max_loss = total_premium * 100
        else:
            max_profit = total_premium * 100
            max_loss = float('inf')  # Unlimited on movement
        
        breakeven_low = strike - total_premium
        breakeven_high = strike + total_premium
        
        return StrategyOrder(
            legs=legs,
            strategy_name='Long Straddle' if is_long else 'Short Straddle',
            underlying=underlying,
            max_loss=max_loss,
            max_profit=max_profit,
            breakeven=[breakeven_low, breakeven_high]
        )


class StrategyExecutor:
    """Execute and manage options strategies."""
    
    def __init__(self):
        self.client = AlpacaTradingClient()
        self.builder = StrategyBuilder()
        self.active_strategies = []
        
    def is_ready(self) -> bool:
        """Check if executor is ready to trade."""
        return self.client.is_configured()
    
    def get_account_summary(self) -> Dict:
        """Get trading account summary."""
        account = self.client.get_account()
        if 'error' in account:
            return account
        
        return {
            'buying_power': float(account.get('buying_power', 0)),
            'cash': float(account.get('cash', 0)),
            'portfolio_value': float(account.get('portfolio_value', 0)),
            'equity': float(account.get('equity', 0)),
            'pattern_day_trader': account.get('pattern_day_trader', False),
            'trading_blocked': account.get('trading_blocked', False),
            'account_number': account.get('account_number', ''),
            'status': account.get('status', 'unknown')
        }
    
    def execute_covered_call(self, ticker: str, spot: float, call_strike: float,
                             expiration: str, call_premium: float = None) -> Dict:
        """Execute a covered call strategy."""
        if call_premium is None:
            call_premium = spot * 0.02  # Default 2% premium
        
        strategy = self.builder.covered_call(
            underlying=ticker,
            spot=spot,
            call_strike=call_strike,
            expiration=expiration,
            call_premium=call_premium
        )
        
        # For covered call, we just need to sell the call (assuming stock owned)
        leg = strategy.legs[0]
        result = self.client.place_option_order(
            underlying=ticker,
            option_type='call',
            strike=call_strike,
            expiration=expiration,
            side='sell',
            qty=1,
            order_type='limit',
            limit_price=call_premium
        )
        
        if 'error' not in result:
            self.active_strategies.append({
                'strategy': strategy,
                'order': result,
                'created_at': datetime.now().isoformat()
            })
        
        return {
            'strategy': 'Covered Call',
            'underlying': ticker,
            'call_strike': call_strike,
            'expiration': expiration,
            'premium': call_premium,
            'max_profit': strategy.max_profit,
            'max_loss': strategy.max_loss,
            'breakeven': strategy.breakeven,
            'order_result': result
        }
    
    def execute_cash_secured_put(self, ticker: str, spot: float, put_strike: float,
                                  expiration: str, put_premium: float = None) -> Dict:
        """Execute a cash-secured put strategy."""
        if put_premium is None:
            put_premium = spot * 0.015  # Default 1.5% premium
        
        strategy = self.builder.cash_secured_put(
            underlying=ticker,
            spot=spot,
            put_strike=put_strike,
            expiration=expiration,
            put_premium=put_premium
        )
        
        leg = strategy.legs[0]
        result = self.client.place_option_order(
            underlying=ticker,
            option_type='put',
            strike=put_strike,
            expiration=expiration,
            side='sell',
            qty=1,
            order_type='limit',
            limit_price=put_premium
        )
        
        if 'error' not in result:
            self.active_strategies.append({
                'strategy': strategy,
                'order': result,
                'created_at': datetime.now().isoformat()
            })
        
        return {
            'strategy': 'Cash-Secured Put',
            'underlying': ticker,
            'put_strike': put_strike,
            'expiration': expiration,
            'premium': put_premium,
            'max_profit': strategy.max_profit,
            'max_loss': strategy.max_loss,
            'breakeven': strategy.breakeven,
            'order_result': result
        }
    
    def get_active_strategies(self) -> List[Dict]:
        """Get list of active strategies."""
        return self.active_strategies
    
    def close_strategy(self, strategy_idx: int) -> Dict:
        """Close an active strategy by index."""
        if strategy_idx >= len(self.active_strategies):
            return {'error': 'Invalid strategy index'}
        
        strategy = self.active_strategies[strategy_idx]
        order = strategy.get('order', {})
        
        # Cancel if still open
        order_id = order.get('id')
        if order_id and order.get('status') in ('new', 'accepted', 'pending_new'):
            self.client.cancel_order(order_id)
        
        self.active_strategies.pop(strategy_idx)
        return {'status': 'closed', 'strategy': strategy}


# Singleton executor
_executor = None

def get_strategy_executor() -> StrategyExecutor:
    """Get singleton strategy executor."""
    global _executor
    if _executor is None:
        _executor = StrategyExecutor()
    return _executor


# Convenience functions
def execute_covered_call(ticker: str, spot: float, strike: float, 
                         expiration: str, premium: float = None) -> Dict:
    """Quick execute covered call."""
    return get_strategy_executor().execute_covered_call(ticker, spot, strike, expiration, premium)


def execute_cash_secured_put(ticker: str, spot: float, strike: float,
                             expiration: str, premium: float = None) -> Dict:
    """Quick execute cash-secured put."""
    return get_strategy_executor().execute_cash_secured_put(ticker, spot, strike, expiration, premium)


def get_account_info() -> Dict:
    """Get trading account info."""
    return get_strategy_executor().get_account_summary()
