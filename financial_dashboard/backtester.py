"""
Backtesting Engine for Options Strategies
Simulates strategy execution on historical data to calculate P&L and metrics.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from strategies.base_strategy import BaseStrategy


class BacktestResult:
    """Container for backtest results."""
    
    def __init__(self):
        """Initialize backtest result container."""
        self.trades = []
        self.daily_pnl = []
        self.total_pnl = 0.0
        self.total_return_pct = 0.0
        self.win_rate = 0.0
        self.sharpe_ratio = 0.0
        self.max_drawdown = 0.0
        self.num_trades = 0
        self.num_wins = 0
        self.num_losses = 0
        self.num_days = 0
        self.avg_win = 0.0
        self.avg_loss = 0.0
        self.largest_win = 0.0
        self.largest_loss = 0.0
        self.start_date = None
        self.end_date = None
        self.initial_capital = 0.0
        self.final_capital = 0.0
        
    def to_dict(self) -> Dict:
        """Convert results to dictionary."""
        return {
            'total_pnl': self.total_pnl,
            'total_return_pct': self.total_return_pct,
            'win_rate': self.win_rate,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'num_trades': self.num_trades,
            'num_wins': self.num_wins,
            'num_losses': self.num_losses,
            'avg_win': self.avg_win,
            'avg_loss': self.avg_loss,
            'largest_win': self.largest_win,
            'largest_loss': self.largest_loss,
            'start_date': str(self.start_date) if self.start_date else None,
            'end_date': str(self.end_date) if self.end_date else None,
            'initial_capital': self.initial_capital,
            'final_capital': self.final_capital,
            'num_days': len(self.daily_pnl),
            'trades': self.trades
        }


class Backtester:
    """
    Backtesting engine for options strategies.
    
    Simulates strategy execution on historical data with realistic assumptions:
    - Transaction costs
    - Slippage
    - Position sizing
    - Risk management
    """
    
    def __init__(self, initial_capital: float = 10000.0, 
                 commission_per_contract: float = 0.65,
                 slippage_pct: float = 0.01):
        """
        Initialize backtester.
        
        Args:
            initial_capital: Starting capital for backtest
            commission_per_contract: Commission per contract traded
            slippage_pct: Slippage as percentage of trade value
        """
        self.initial_capital = initial_capital
        self.commission_per_contract = commission_per_contract
        self.slippage_pct = slippage_pct
        
        # State
        self.capital = initial_capital
        self.positions = []  # Open positions
        self.closed_trades = []  # Completed trades
        self.daily_snapshots = []  # Daily capital snapshots
        
    def run(self, strategy: BaseStrategy, market_data: pd.DataFrame, 
            options_data: Optional[Dict] = None) -> BacktestResult:
        """
        Run backtest simulation.
        
        Args:
            strategy: Strategy object implementing BaseStrategy
            market_data: DataFrame with columns ['date', 'symbol', 'close', 'volume']
            options_data: Optional dict with options chain data by date
        
        Returns:
            BacktestResult with performance metrics
        """
        # Reset state
        self.capital = self.initial_capital
        self.positions = []
        self.closed_trades = []
        self.daily_snapshots = []
        
        # Ensure data is sorted by date
        market_data = market_data.sort_values('date').copy()
        
        # Iterate through each trading day
        for idx, row in market_data.iterrows():
            date = row['date']
            symbol = row['symbol']
            close_price = row['close']
            
            # Build market data dict for strategy
            data = {
                'symbol': symbol,
                'current_price': close_price,
                'date': date,
                'volume': row.get('volume', 0)
            }
            
            # Add options chain if available
            if options_data and date in options_data:
                data['options_chain'] = options_data[date]
            else:
                # Generate synthetic options chain for testing
                data['options_chain'] = self._generate_synthetic_options(
                    symbol, close_price, date
                )
            
            # Update existing positions
            self._update_positions(date, close_price, data.get('options_chain'))
            
            # Generate signals
            signals = strategy.generate_signals(data)
            
            # Execute signals
            for signal in signals:
                if strategy.validate_signal(signal):
                    self._execute_signal(signal, date, data)
            
            # Take daily snapshot
            self._take_daily_snapshot(date)
        
        # Close all remaining positions at final prices
        self._close_all_positions(market_data.iloc[-1])
        
        # Calculate and return results
        return self._calculate_results(market_data)
    
    def _generate_synthetic_options(self, symbol: str, stock_price: float, 
                                     date: datetime) -> Dict:
        """
        Generate synthetic options chain for testing.
        
        Args:
            symbol: Stock ticker
            stock_price: Current stock price
            date: Current date
        
        Returns:
            Dict with 'calls' and 'puts' lists
        """
        calls = []
        puts = []
        
        # Generate strikes around current price
        strikes = np.arange(
            stock_price * 0.90,
            stock_price * 1.10,
            stock_price * 0.02
        )
        
        # Calculate expiration (30 days out)
        expiration = date + timedelta(days=30)
        
        for strike in strikes:
            # Simple Black-Scholes-like pricing
            moneyness = strike / stock_price
            
            # Call option
            if moneyness > 1.0:  # OTM
                call_price = max(0.10, (1.05 - moneyness) * stock_price * 0.05)
                delta = 0.3
            else:  # ITM
                call_price = stock_price - strike + (stock_price * 0.02)
                delta = 0.7
            
            calls.append({
                'strike': round(strike, 2),
                'expiration': expiration.strftime('%Y-%m-%d'),
                'bid': round(call_price * 0.98, 2),
                'ask': round(call_price * 1.02, 2),
                'last': round(call_price, 2),
                'volume': 100,
                'open_interest': 500,
                'delta': round(delta, 2),
                'implied_volatility': 0.25,
                'symbol': f"{symbol}{expiration.strftime('%y%m%d')}C{int(strike*1000):08d}"
            })
            
            # Put option (similar logic)
            if moneyness < 1.0:  # OTM
                put_price = max(0.10, (moneyness - 0.95) * stock_price * 0.05)
                put_delta = -0.3
            else:  # ITM
                put_price = strike - stock_price + (stock_price * 0.02)
                put_delta = -0.7
            
            puts.append({
                'strike': round(strike, 2),
                'expiration': expiration.strftime('%Y-%m-%d'),
                'bid': round(put_price * 0.98, 2),
                'ask': round(put_price * 1.02, 2),
                'last': round(put_price, 2),
                'volume': 100,
                'open_interest': 500,
                'delta': round(put_delta, 2),
                'implied_volatility': 0.25,
                'symbol': f"{symbol}{expiration.strftime('%y%m%d')}P{int(strike*1000):08d}"
            })
        
        return {'calls': calls, 'puts': puts}
    
    def _execute_signal(self, signal: Dict, date: datetime, market_data: Dict):
        """
        Execute a trading signal.
        
        Args:
            signal: Signal dict from strategy
            date: Current date
            market_data: Market data dict
        """
        action = signal['action']
        symbol = signal['symbol']
        quantity = signal['quantity']
        
        # Find option in chain
        option_data = self._find_option_in_chain(symbol, market_data.get('options_chain', {}))
        
        if not option_data:
            return  # Skip if option not found
        
        # Calculate execution price (with slippage)
        if action == 'buy':
            price = option_data['ask'] * (1 + self.slippage_pct)
        else:  # sell
            price = option_data['bid'] * (1 - self.slippage_pct)
        
        # Calculate cost
        cost = quantity * price * 100  # Options are per 100 shares
        commission = quantity * self.commission_per_contract
        total_cost = cost + commission
        
        # Check if we have enough capital (for buy signals)
        if action == 'buy' and total_cost > self.capital:
            return  # Skip if insufficient capital
        
        # Execute trade
        if action == 'buy':
            self.capital -= total_cost
            self.positions.append({
                'symbol': symbol,
                'quantity': quantity,
                'entry_price': price,
                'entry_date': date,
                'entry_cost': total_cost,
                'option_data': option_data,
                'signal_reason': signal.get('reason', ''),
                'signal_metadata': signal.get('metadata', {})
            })
        else:  # sell (close existing position or short)
            # Find matching position to close
            for pos in self.positions:
                if pos['symbol'] == symbol:
                    # Close position
                    pnl = (price - pos['entry_price']) * quantity * 100 - commission * 2
                    self.capital += (quantity * price * 100) - commission
                    
                    self.closed_trades.append({
                        'symbol': symbol,
                        'quantity': quantity,
                        'entry_date': pos['entry_date'],
                        'exit_date': date,
                        'entry_price': pos['entry_price'],
                        'exit_price': price,
                        'pnl': pnl,
                        'return_pct': (pnl / pos['entry_cost']) * 100,
                        'hold_days': (date - pos['entry_date']).days
                    })
                    
                    self.positions.remove(pos)
                    break
    
    def _find_option_in_chain(self, symbol: str, options_chain: Dict) -> Optional[Dict]:
        """Find option by symbol in options chain."""
        for option in options_chain.get('calls', []):
            if option['symbol'] == symbol:
                return option
        for option in options_chain.get('puts', []):
            if option['symbol'] == symbol:
                return option
        return None
    
    def _update_positions(self, date: datetime, stock_price: float, 
                         options_chain: Optional[Dict]):
        """Update mark-to-market values of open positions."""
        # This would update position values based on current market prices
        # For simplicity, we'll close positions at expiration
        positions_to_close = []
        
        for pos in self.positions:
            option_data = pos['option_data']
            expiration = datetime.strptime(option_data['expiration'], '%Y-%m-%d')
            
            # Close position if expired
            if date >= expiration:
                positions_to_close.append(pos)
        
        # Close expired positions
        for pos in positions_to_close:
            # Assume we can close at last price (simplified)
            exit_price = pos['option_data']['last'] * 0.95  # Assume some decay
            pnl = (exit_price - pos['entry_price']) * pos['quantity'] * 100
            self.capital += (pos['quantity'] * exit_price * 100)
            
            self.closed_trades.append({
                'symbol': pos['symbol'],
                'quantity': pos['quantity'],
                'entry_date': pos['entry_date'],
                'exit_date': date,
                'entry_price': pos['entry_price'],
                'exit_price': exit_price,
                'pnl': pnl,
                'return_pct': (pnl / pos['entry_cost']) * 100,
                'hold_days': (date - pos['entry_date']).days,
                'exit_reason': 'expiration'
            })
            
            self.positions.remove(pos)
    
    def _close_all_positions(self, final_row: pd.Series):
        """Close all remaining positions at end of backtest."""
        for pos in self.positions:
            exit_price = pos['entry_price'] * 0.90  # Assume loss if still open
            pnl = (exit_price - pos['entry_price']) * pos['quantity'] * 100
            self.capital += (pos['quantity'] * exit_price * 100)
            
            self.closed_trades.append({
                'symbol': pos['symbol'],
                'quantity': pos['quantity'],
                'entry_date': pos['entry_date'],
                'exit_date': final_row['date'],
                'entry_price': pos['entry_price'],
                'exit_price': exit_price,
                'pnl': pnl,
                'return_pct': (pnl / pos['entry_cost']) * 100,
                'hold_days': (final_row['date'] - pos['entry_date']).days,
                'exit_reason': 'forced_close'
            })
        
        self.positions = []
    
    def _take_daily_snapshot(self, date: datetime):
        """Record daily capital snapshot."""
        # Calculate total portfolio value (capital + positions value)
        positions_value = sum([
            pos['quantity'] * pos['entry_price'] * 100 
            for pos in self.positions
        ])
        
        self.daily_snapshots.append({
            'date': date,
            'capital': self.capital,
            'positions_value': positions_value,
            'total_value': self.capital + positions_value
        })
    
    def _calculate_results(self, market_data: pd.DataFrame) -> BacktestResult:
        """Calculate final backtest metrics."""
        result = BacktestResult()
        
        result.initial_capital = self.initial_capital
        result.final_capital = self.capital
        result.trades = self.closed_trades
        
        # Set num_days regardless of trades
        result.num_days = len(self.daily_snapshots)
        
        if len(self.closed_trades) == 0:
            return result
        
        # Basic metrics
        result.num_trades = len(self.closed_trades)
        result.total_pnl = sum([trade['pnl'] for trade in self.closed_trades])
        result.total_return_pct = (result.total_pnl / self.initial_capital) * 100
        
        # Win/Loss stats
        wins = [trade for trade in self.closed_trades if trade['pnl'] > 0]
        losses = [trade for trade in self.closed_trades if trade['pnl'] < 0]
        
        result.num_wins = len(wins)
        result.num_losses = len(losses)
        result.win_rate = (result.num_wins / result.num_trades) * 100 if result.num_trades > 0 else 0
        
        if result.num_wins > 0:
            result.avg_win = sum([trade['pnl'] for trade in wins]) / result.num_wins
            result.largest_win = max([trade['pnl'] for trade in wins])
        
        if result.num_losses > 0:
            result.avg_loss = sum([trade['pnl'] for trade in losses]) / result.num_losses
            result.largest_loss = min([trade['pnl'] for trade in losses])
        
        # Time period
        if len(self.daily_snapshots) > 0:
            result.start_date = self.daily_snapshots[0]['date']
            result.end_date = self.daily_snapshots[-1]['date']
            result.daily_pnl = [snap['total_value'] for snap in self.daily_snapshots]
            
            # Sharpe ratio (simplified)
            if len(result.daily_pnl) > 1:
                returns = np.diff(result.daily_pnl) / result.daily_pnl[:-1]
                if np.std(returns) > 0:
                    result.sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252)
            
            # Max drawdown
            cumulative = np.array(result.daily_pnl)
            running_max = np.maximum.accumulate(cumulative)
            drawdown = (cumulative - running_max) / running_max
            result.max_drawdown = np.min(drawdown) * 100 if len(drawdown) > 0 else 0
        
        return result
