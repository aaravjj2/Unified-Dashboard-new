"""
Broker Execution Utility - Alpaca Integration

This module provides a broker-agnostic execution layer for automated trading.
Currently supports Alpaca API but designed to be extensible to other brokers.

Usage:
    from utils.execution import AlpacaExecutor
    
    executor = AlpacaExecutor()
    portfolio_value = executor.get_portfolio_value()
    positions = executor.get_open_positions()
    
    target_portfolio = {'AAPL': 5000, 'MSFT': 4500, 'GOOGL': 3000}
    executor.rebalance_to_target(target_portfolio, dry_run=False)
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

# Try to import Alpaca SDK
try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce, OrderType
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockLatestQuoteRequest
    ALPACA_AVAILABLE = True
except ImportError:
    logger.warning("Alpaca SDK not available. Install with: pip install alpaca-py")
    ALPACA_AVAILABLE = False


class AlpacaExecutor:
    """
    Alpaca-based trade execution engine.
    
    Handles all communication with Alpaca API including:
    - Portfolio value and position queries
    - Order placement and management
    - Intelligent rebalancing to target portfolio
    """
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, 
                 paper: bool = True):
        """
        Initialize Alpaca executor.
        
        Args:
            api_key: Alpaca API key (defaults to APCA_API_KEY_ID env var)
            api_secret: Alpaca API secret (defaults to APCA_API_SECRET_KEY env var)
            paper: If True, use paper trading account (default)
        """
        if not ALPACA_AVAILABLE:
            raise ImportError("Alpaca SDK not installed. Run: pip install alpaca-py")
        
        # Load credentials from environment or parameters
        self.api_key = api_key or os.getenv("APCA_API_KEY_ID")
        self.api_secret = api_secret or os.getenv("APCA_API_SECRET_KEY")
        
        if not self.api_key or not self.api_secret:
            raise ValueError(
                "Alpaca credentials not found. Set APCA_API_KEY_ID and "
                "APCA_API_SECRET_KEY environment variables or pass them as parameters."
            )
        
        self.paper = paper
        
        # Initialize clients
        self.trading_client = TradingClient(
            api_key=self.api_key,
            secret_key=self.api_secret,
            paper=paper
        )
        
        self.data_client = StockHistoricalDataClient(
            api_key=self.api_key,
            secret_key=self.api_secret
        )
        
        logger.info(f"AlpacaExecutor initialized ({'PAPER' if paper else 'LIVE'} trading)")
    
    def get_account_info(self) -> Dict:
        """
        Get account information including cash, equity, buying power.
        
        Returns:
            Dictionary with account details
        """
        try:
            account = self.trading_client.get_account()
            return {
                'cash': float(account.cash),
                'equity': float(account.equity),
                'buying_power': float(account.buying_power),
                'portfolio_value': float(account.portfolio_value),
                'long_market_value': float(account.long_market_value),
                'short_market_value': float(account.short_market_value),
                'initial_margin': float(account.initial_margin),
                'maintenance_margin': float(account.maintenance_margin),
                'last_equity': float(account.last_equity),
                'multiplier': float(account.multiplier),
                'status': account.status
            }
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            raise
    
    def get_portfolio_value(self) -> float:
        """
        Get total portfolio value (equity).
        
        Returns:
            Total portfolio value in dollars
        """
        account_info = self.get_account_info()
        return account_info['portfolio_value']
    
    def get_open_positions(self) -> Dict[str, Dict]:
        """
        Get all current open positions.
        
        Returns:
            Dictionary mapping ticker to position details:
            {
                'AAPL': {
                    'qty': 10,
                    'market_value': 1500.50,
                    'cost_basis': 1450.00,
                    'unrealized_pl': 50.50,
                    'unrealized_plpc': 0.0348,
                    'current_price': 150.05,
                    'avg_entry_price': 145.00
                },
                ...
            }
        """
        try:
            positions = self.trading_client.get_all_positions()
            
            result = {}
            for pos in positions:
                result[pos.symbol] = {
                    'qty': float(pos.qty),
                    'market_value': float(pos.market_value),
                    'cost_basis': float(pos.cost_basis),
                    'unrealized_pl': float(pos.unrealized_pl),
                    'unrealized_plpc': float(pos.unrealized_plpc),
                    'current_price': float(pos.current_price),
                    'avg_entry_price': float(pos.avg_entry_price),
                    'side': pos.side
                }
            
            return result
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            raise
    
    def get_current_prices(self, tickers: List[str]) -> Dict[str, float]:
        """
        Get current market prices for a list of tickers.
        
        Args:
            tickers: List of ticker symbols
            
        Returns:
            Dictionary mapping ticker to current price
        """
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=tickers)
            quotes = self.data_client.get_stock_latest_quote(request)
            
            prices = {}
            for ticker in tickers:
                if ticker in quotes:
                    quote = quotes[ticker]
                    # Use mid-point of bid-ask as current price
                    prices[ticker] = (quote.bid_price + quote.ask_price) / 2.0
            
            return prices
        except Exception as e:
            logger.warning(f"Error getting prices: {e}. Will use position prices instead.")
            return {}
    
    def place_market_order(self, ticker: str, qty: float, side: str, 
                          dry_run: bool = True) -> Optional[Dict]:
        """
        Place a market order.
        
        Args:
            ticker: Stock symbol
            qty: Number of shares (can be fractional for supported stocks)
            side: 'buy' or 'sell'
            dry_run: If True, don't actually place the order (default)
            
        Returns:
            Order details if successful, None if failed
        """
        if dry_run:
            logger.info(f"DRY RUN: Would place market order: {side.upper()} {qty} {ticker}")
            return {
                'ticker': ticker,
                'qty': qty,
                'side': side,
                'type': 'market',
                'dry_run': True
            }
        
        try:
            order_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
            
            order_data = MarketOrderRequest(
                symbol=ticker,
                qty=qty,
                side=order_side,
                time_in_force=TimeInForce.DAY
            )
            
            order = self.trading_client.submit_order(order_data)
            
            logger.info(f"Placed market order: {side.upper()} {qty} {ticker} (Order ID: {order.id})")
            
            return {
                'ticker': ticker,
                'qty': float(order.qty),
                'side': side,
                'type': 'market',
                'order_id': order.id,
                'status': order.status,
                'submitted_at': order.submitted_at
            }
        except Exception as e:
            logger.error(f"Error placing market order for {ticker}: {e}")
            return None
    
    def close_position(self, ticker: str, dry_run: bool = True) -> Optional[Dict]:
        """
        Close an entire position.
        
        Args:
            ticker: Stock symbol
            dry_run: If True, don't actually close the position (default)
            
        Returns:
            Order details if successful, None if failed
        """
        if dry_run:
            logger.info(f"DRY RUN: Would close position in {ticker}")
            return {'ticker': ticker, 'action': 'close', 'dry_run': True}
        
        try:
            order = self.trading_client.close_position(ticker)
            logger.info(f"Closed position in {ticker} (Order ID: {order.id})")
            
            return {
                'ticker': ticker,
                'action': 'close',
                'order_id': order.id,
                'status': order.status
            }
        except Exception as e:
            logger.error(f"Error closing position in {ticker}: {e}")
            return None
    
    def rebalance_to_target(self, target_portfolio: Dict[str, float], 
                           dry_run: bool = True, 
                           tolerance: float = 0.02) -> Dict[str, List]:
        """
        Rebalance portfolio to match target allocations.
        
        This is the key method for automated trading. It:
        1. Gets current positions
        2. Calculates which stocks to buy, sell, or adjust
        3. Places orders to minimize deviation from target
        
        Args:
            target_portfolio: Dict mapping ticker to target dollar amount
                             e.g., {'AAPL': 5000, 'MSFT': 4500}
            dry_run: If True, only simulate the rebalancing (default)
            tolerance: Ignore adjustments smaller than this fraction (default 2%)
            
        Returns:
            Dictionary with:
                'orders_placed': List of orders placed
                'positions_closed': List of positions closed
                'skipped': List of adjustments skipped due to tolerance
                'errors': List of any errors encountered
        """
        logger.info(f"Starting rebalance to target portfolio ({len(target_portfolio)} tickers)")
        
        # Get current positions
        current_positions = self.get_open_positions()
        
        # Track actions
        orders_placed = []
        positions_closed = []
        skipped = []
        errors = []
        
        # 1. Close positions not in target
        for ticker in current_positions:
            if ticker not in target_portfolio:
                logger.info(f"Closing position in {ticker} (not in target)")
                result = self.close_position(ticker, dry_run=dry_run)
                if result:
                    positions_closed.append(result)
                else:
                    errors.append(f"Failed to close position in {ticker}")
        
        # 2. Adjust positions to match target
        for ticker, target_value in target_portfolio.items():
            current_value = current_positions.get(ticker, {}).get('market_value', 0.0)
            delta_value = target_value - current_value
            
            # Skip if change is within tolerance
            if abs(delta_value) < tolerance * target_value:
                skipped.append({
                    'ticker': ticker,
                    'current_value': current_value,
                    'target_value': target_value,
                    'delta_value': delta_value,
                    'reason': 'within_tolerance'
                })
                continue
            
            # Get current price to calculate shares needed
            prices = self.get_current_prices([ticker])
            if ticker not in prices:
                errors.append(f"Could not get price for {ticker}")
                continue
            
            price = prices[ticker]
            delta_shares = delta_value / price
            
            # Determine buy or sell
            side = 'buy' if delta_shares > 0 else 'sell'
            qty = abs(delta_shares)
            
            # Place order
            result = self.place_market_order(ticker, qty, side, dry_run=dry_run)
            if result:
                orders_placed.append(result)
            else:
                errors.append(f"Failed to place order for {ticker}")
        
        summary = {
            'orders_placed': orders_placed,
            'positions_closed': positions_closed,
            'skipped': skipped,
            'errors': errors
        }
        
        logger.info(f"Rebalance complete: {len(orders_placed)} orders, "
                   f"{len(positions_closed)} closures, {len(skipped)} skipped, "
                   f"{len(errors)} errors")
        
        return summary


def example_usage():
    """Example demonstrating how to use the AlpacaExecutor."""
    print("=== Alpaca Executor Example ===\n")
    
    # Initialize executor (uses paper trading by default)
    try:
        executor = AlpacaExecutor(paper=True)
    except Exception as e:
        print(f"Error initializing executor: {e}")
        print("\nMake sure APCA_API_KEY_ID and APCA_API_SECRET_KEY are set in keys.env")
        return
    
    # Get account info
    print("1. Account Information:")
    account = executor.get_account_info()
    print(f"   Portfolio Value: ${account['portfolio_value']:,.2f}")
    print(f"   Cash: ${account['cash']:,.2f}")
    print(f"   Buying Power: ${account['buying_power']:,.2f}\n")
    
    # Get current positions
    print("2. Current Positions:")
    positions = executor.get_open_positions()
    if positions:
        for ticker, pos in positions.items():
            print(f"   {ticker}: {pos['qty']} shares @ ${pos['current_price']:.2f} "
                  f"(${pos['market_value']:,.2f})")
    else:
        print("   No open positions\n")
    
    # Example: Rebalance to target portfolio (DRY RUN)
    print("\n3. Simulating Rebalance (DRY RUN):")
    target_portfolio = {
        'AAPL': 5000,
        'MSFT': 4500,
        'GOOGL': 3000,
        'NVDA': 2500
    }
    
    print(f"   Target Portfolio:")
    for ticker, value in target_portfolio.items():
        print(f"     {ticker}: ${value:,.2f}")
    
    result = executor.rebalance_to_target(target_portfolio, dry_run=True)
    
    print(f"\n   Results:")
    print(f"     Orders to place: {len(result['orders_placed'])}")
    print(f"     Positions to close: {len(result['positions_closed'])}")
    print(f"     Adjustments skipped: {len(result['skipped'])}")
    
    if result['orders_placed']:
        print(f"\n   Orders:")
        for order in result['orders_placed']:
            print(f"     {order['side'].upper()} {order['qty']:.2f} {order['ticker']}")


if __name__ == '__main__':
    example_usage()
