"""
Options Strategy Backtester
============================
Simulates historical trading of options strategies using past data
to evaluate performance metrics.

Features:
- Historical data fetching from TimescaleDB
- Strategy signal generation simulation
- P&L calculation with realistic slippage
- Risk metrics (Sharpe, Max DD, Win Rate)
- Trade log export

Usage:
    from services.options_service.backtester import Backtester
    from services.options_service.strategies.covered_call_screener import CoveredCallScreener
    
    strategy = CoveredCallScreener()
    backtester = Backtester(strategy)
    results = backtester.run(start_date='2023-01-01', end_date='2024-01-01')
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor

from .strategies.base_strategy import BaseStrategy


class Backtester:
    """
    Backtest engine for options trading strategies.
    """
    
    def __init__(self, 
                 strategy: BaseStrategy,
                 initial_capital: float = 100000.0,
                 commission_per_contract: float = 0.65,
                 slippage_pct: float = 0.02):
        """
        Initialize backtester.
        
        Args:
            strategy: Strategy instance to backtest
            initial_capital: Starting portfolio value
            commission_per_contract: Commission per options contract
            slippage_pct: Percentage slippage on fills (default 2%)
        """
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.commission_per_contract = commission_per_contract
        self.slippage_pct = slippage_pct
        
        self.positions = []
        self.closed_trades = []
        self.equity_curve = []
        self.cash = initial_capital
        
        # Database configuration
        self.db_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'portfolio',
            'user': 'postgres',
            'password': 'postgres_dev_pass'
        }
    
    def run(self, 
            start_date: str, 
            end_date: str,
            universe: List[str] = None) -> Dict[str, Any]:
        """
        Run backtest over specified date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            universe: List of tickers to trade (None = all available)
        
        Returns:
            Dictionary with backtest results and metrics
        """
        print(f"Running backtest from {start_date} to {end_date}")
        
        # Load historical price data
        price_data = self._load_price_data(start_date, end_date, universe)
        
        # Load historical options data (if available)
        # Note: For realistic backtesting, we'd need historical options chains
        # For now, we'll simulate options pricing using Black-Scholes
        
        # Iterate through trading days
        trading_days = pd.date_range(start=start_date, end=end_date, freq='B')
        
        for current_date in trading_days:
            # Get market data for current day
            daily_data = price_data[price_data.index == current_date]
            
            if daily_data.empty:
                continue
            
            # Update existing positions (check for expirations, assignments)
            self._update_positions(current_date, price_data)
            
            # Generate new signals
            signals = self.strategy.generate_signals(daily_data)
            
            # Execute signals
            for signal in signals:
                self._execute_signal(signal, current_date, price_data)
            
            # Record equity
            current_equity = self._calculate_equity(current_date, price_data)
            self.equity_curve.append({
                'date': current_date,
                'equity': current_equity,
                'cash': self.cash,
                'positions_value': current_equity - self.cash
            })
        
        # Calculate final metrics
        metrics = self._calculate_metrics()
        
        return {
            'summary': metrics,
            'equity_curve': self.equity_curve,
            'trades': self.closed_trades,
            'final_positions': self.positions
        }
    
    def _load_price_data(self, 
                         start_date: str, 
                         end_date: str,
                         universe: List[str] = None) -> pd.DataFrame:
        """
        Load historical price data from TimescaleDB.
        
        Returns:
            DataFrame with MultiIndex (date, ticker) and OHLCV columns
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            
            where_clause = ""
            if universe:
                tickers_str = "','".join(universe)
                where_clause = f"AND ticker IN ('{tickers_str}')"
            
            query = f"""
            SELECT 
                timestamp::date as date,
                ticker,
                open, high, low, close, volume
            FROM price_history
            WHERE timestamp >= %s AND timestamp <= %s
            {where_clause}
            ORDER BY timestamp, ticker
            """
            
            df = pd.read_sql(query, conn, params=(start_date, end_date))
            conn.close()
            
            # Set MultiIndex
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            return df
            
        except Exception as e:
            print(f"Error loading price data: {e}")
            # Return empty DataFrame if database unavailable
            return pd.DataFrame()
    
    def _execute_signal(self, 
                       signal: Dict[str, Any],
                       current_date: datetime,
                       price_data: pd.DataFrame):
        """Execute a trading signal (open position)."""
        try:
            ticker = signal['ticker']
            
            # Get current stock price
            stock_price = self._get_price(ticker, current_date, price_data)
            
            if signal.get('signal_type') == 'covered_call':
                # Buy 100 shares + sell 1 call
                shares_cost = 100 * stock_price
                commission = 1.0 + self.commission_per_contract  # $1 for stock + $0.65 for option
                
                # Apply slippage
                shares_cost *= (1 + self.slippage_pct)
                
                # Check if we have enough cash
                total_cost = shares_cost + commission
                
                if self.cash < total_cost:
                    print(f"Insufficient cash for {ticker} covered call")
                    return
                
                # Deduct cash
                self.cash -= total_cost
                
                # Collect call premium (credit)
                premium_collected = signal['premium'] * 100  # Premium per share * 100 shares
                self.cash += premium_collected * (1 - self.slippage_pct)  # Apply slippage to premium
                
                # Record position
                position = {
                    'ticker': ticker,
                    'type': 'covered_call',
                    'entry_date': current_date,
                    'stock_shares': 100,
                    'stock_entry_price': stock_price,
                    'call_strike': signal['strike'],
                    'call_expiration': pd.to_datetime(signal['expiration']),
                    'premium_collected': premium_collected,
                    'commission': commission,
                    'status': 'open'
                }
                
                self.positions.append(position)
                
                print(f"Opened covered call: {ticker} @ ${stock_price:.2f}, "
                      f"sold ${signal['strike']} call for ${signal['premium']:.2f}")
                
        except Exception as e:
            print(f"Error executing signal: {e}")
    
    def _update_positions(self, current_date: datetime, price_data: pd.DataFrame):
        """Update existing positions (check expirations, calculate P&L)."""
        for position in self.positions[:]:  # Iterate over copy
            if position['status'] != 'open':
                continue
            
            # Check if option expired
            if current_date >= position['call_expiration']:
                self._close_position(position, current_date, price_data, reason='expiration')
    
    def _close_position(self, 
                       position: Dict[str, Any],
                       current_date: datetime,
                       price_data: pd.DataFrame,
                       reason: str = 'manual'):
        """Close a position and calculate P&L."""
        try:
            ticker = position['ticker']
            current_price = self._get_price(ticker, current_date, price_data)
            
            if position['type'] == 'covered_call':
                # Determine if assigned
                assigned = current_price > position['call_strike']
                
                if assigned:
                    # Shares called away at strike price
                    proceeds = position['call_strike'] * 100
                else:
                    # Sell shares at current market price
                    proceeds = current_price * 100
                
                # Apply slippage and commission
                proceeds *= (1 - self.slippage_pct)
                commission = 1.0 + self.commission_per_contract
                proceeds -= commission
                
                # Add back to cash
                self.cash += proceeds
                
                # Calculate P&L
                cost_basis = position['stock_entry_price'] * 100
                total_commission = position['commission'] + commission
                pnl = (proceeds + position['premium_collected']) - cost_basis - total_commission
                
                # Record closed trade
                trade_record = {
                    **position,
                    'exit_date': current_date,
                    'exit_price': current_price,
                    'assigned': assigned,
                    'proceeds': proceeds,
                    'pnl': pnl,
                    'pnl_pct': (pnl / cost_basis) * 100,
                    'close_reason': reason,
                    'status': 'closed'
                }
                
                self.closed_trades.append(trade_record)
                position['status'] = 'closed'
                
                print(f"Closed covered call: {ticker}, P&L: ${pnl:.2f} ({trade_record['pnl_pct']:.1f}%)")
                
        except Exception as e:
            print(f"Error closing position: {e}")
    
    def _get_price(self, ticker: str, date: datetime, price_data: pd.DataFrame) -> float:
        """Get closing price for ticker on specific date."""
        try:
            price_row = price_data[
                (price_data.index == date) & 
                (price_data['ticker'] == ticker)
            ]
            
            if not price_row.empty:
                return float(price_row['close'].iloc[0])
            
            # If no data for exact date, use last available price
            prior_data = price_data[
                (price_data.index < date) &
                (price_data['ticker'] == ticker)
            ]
            
            if not prior_data.empty:
                return float(prior_data['close'].iloc[-1])
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def _calculate_equity(self, current_date: datetime, price_data: pd.DataFrame) -> float:
        """Calculate total portfolio equity."""
        positions_value = 0
        
        for position in self.positions:
            if position['status'] != 'open':
                continue
            
            # Value of stock holdings
            current_price = self._get_price(position['ticker'], current_date, price_data)
            stock_value = current_price * position['stock_shares']
            
            # Value of short call (liability if ITM)
            call_liability = 0
            if current_price > position['call_strike']:
                # Call is ITM, we have a liability
                call_liability = (current_price - position['call_strike']) * 100
            
            position_value = stock_value - call_liability
            positions_value += position_value
        
        return self.cash + positions_value
    
    def _calculate_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics from backtest results."""
        if not self.equity_curve:
            return {}
        
        # Convert to DataFrame for easier calculation
        equity_df = pd.DataFrame(self.equity_curve)
        equity_df.set_index('date', inplace=True)
        
        # Calculate returns
        equity_df['returns'] = equity_df['equity'].pct_change()
        
        # Total return
        initial_equity = self.initial_capital
        final_equity = equity_df['equity'].iloc[-1]
        total_return = (final_equity - initial_equity) / initial_equity
        
        # Sharpe ratio (annualized)
        mean_return = equity_df['returns'].mean()
        std_return = equity_df['returns'].std()
        sharpe = (mean_return / std_return) * np.sqrt(252) if std_return > 0 else 0
        
        # Max drawdown
        running_max = equity_df['equity'].cummax()
        drawdown = (equity_df['equity'] - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Win rate
        winning_trades = sum(1 for trade in self.closed_trades if trade.get('pnl', 0) > 0)
        total_trades = len(self.closed_trades)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Average P&L
        avg_pnl = np.mean([trade.get('pnl', 0) for trade in self.closed_trades]) if self.closed_trades else 0
        
        return {
            'initial_capital': initial_equity,
            'final_equity': final_equity,
            'total_return': total_return,
            'total_return_pct': total_return * 100,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_drawdown * 100,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': total_trades - winning_trades,
            'win_rate': win_rate,
            'win_rate_pct': win_rate * 100,
            'avg_pnl': avg_pnl,
            'total_pnl': sum(trade.get('pnl', 0) for trade in self.closed_trades)
        }
