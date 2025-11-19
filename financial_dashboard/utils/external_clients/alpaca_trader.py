"""
Alpaca Trading API Client for brokerage operations.

This client provides a robust, rate-limited interface to the Alpaca Trading API,
supporting both paper (test) and live trading modes. Handles portfolio positions,
order placement, and comprehensive error scenarios.

Rate Limit: 200 requests/minute (enforced via RateLimiter)
Documentation: https://docs.alpaca.markets/
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any, Literal
from collections import deque
from threading import Lock
import requests


logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Thread-safe rate limiter using sliding window algorithm.
    
    Tracks request timestamps and enforces maximum requests per time window.
    Imported from Agent 1's refactored implementation.
    """
    
    def __init__(self, max_requests: int, window_seconds: int):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed in the window
            window_seconds: Time window in seconds (e.g., 60 for per-minute limit)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()  # Stores timestamps of requests
        self.lock = Lock()
    
    def acquire(self) -> None:
        """
        Acquire permission to make a request. Blocks if rate limit would be exceeded.
        
        This method automatically sleeps if necessary to respect the rate limit.
        """
        with self.lock:
            now = time.time()
            
            # Remove requests outside the current window
            while self.requests and self.requests[0] <= now - self.window_seconds:
                self.requests.popleft()
            
            # If at limit, calculate required sleep time
            if len(self.requests) >= self.max_requests:
                # Sleep until the oldest request falls outside the window
                sleep_time = self.window_seconds - (now - self.requests[0]) + 0.1  # Add 100ms buffer
                if sleep_time > 0:
                    logger.debug(f"Rate limit reached ({self.max_requests}/{self.window_seconds}s). Sleeping {sleep_time:.2f}s")
                    time.sleep(sleep_time)
                    
                    # Clean up again after sleep
                    now = time.time()
                    while self.requests and self.requests[0] <= now - self.window_seconds:
                        self.requests.popleft()
            
            # Record this request
            self.requests.append(now)


class AlpacaTrader:
    """
    Client for interacting with the Alpaca Trading API.
    
    Provides rate-limited access to portfolio positions and order execution.
    Supports both paper (test) and live trading modes. Automatically manages
    API rate limits (200 requests/minute) and handles common error scenarios.
    
    Environment Variables:
        APCA_API_KEY_ID: Your Alpaca API key ID (required)
        APCA_API_SECRET_KEY: Your Alpaca secret key (required)
        
    Example (Paper Trading):
        >>> trader = AlpacaTrader(paper_mode=True)
        >>> positions = trader.get_positions()
        >>> if positions:
        ...     for pos in positions:
        ...         print(f"{pos['symbol']}: {pos['qty']} shares @ ${pos['current_price']}")
        >>> 
        >>> result = trader.place_order("AAPL", 10, "buy", "market")
        >>> if result['success']:
        ...     print(f"Order placed: {result['order_id']}")
        
    Example (Live Trading):
        >>> trader = AlpacaTrader(paper_mode=False)
        >>> # Same API, but trades execute against real account
    """
    
    PAPER_BASE_URL = "https://paper-api.alpaca.markets"
    LIVE_BASE_URL = "https://api.alpaca.markets"
    
    def __init__(
        self, 
        paper_mode: bool = True,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None
    ):
        """
        Initialize the Alpaca trading client.
        
        Args:
            paper_mode: If True, uses paper trading environment. If False, uses live trading.
            api_key: Optional API key ID. If not provided, reads from APCA_API_KEY_ID.
            secret_key: Optional secret key. If not provided, reads from APCA_API_SECRET_KEY.
            
        Raises:
            ValueError: If credentials are not provided and environment variables are not set.
        """
        self.paper_mode = paper_mode
        self.api_key = api_key or os.getenv("APCA_API_KEY_ID")
        self.secret_key = secret_key or os.getenv("APCA_API_SECRET_KEY")
        
        if not self.api_key or not self.secret_key:
            raise ValueError(
                "Alpaca credentials not provided. "
                "Set APCA_API_KEY_ID and APCA_API_SECRET_KEY environment variables "
                "or pass api_key and secret_key parameters."
            )
        
        # Set base URL based on trading mode
        self.base_url = self.PAPER_BASE_URL if paper_mode else self.LIVE_BASE_URL
        
        # Initialize rate limiter: 200 requests per minute
        self.rate_limiter = RateLimiter(max_requests=200, window_seconds=60)
        
        # Create session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key,
            "Content-Type": "application/json"
        })
        
        mode_str = "PAPER" if paper_mode else "LIVE"
        logger.info(f"✅ AlpacaTrader initialized in {mode_str} mode with rate limiting (200 req/min)")
        
        # Verify credentials on initialization
        if not self._verify_credentials():
            logger.warning("⚠️  Failed to verify Alpaca credentials. API calls may fail.")
    
    def _verify_credentials(self) -> bool:
        """
        Verify that the provided credentials are valid.
        
        Returns:
            True if credentials are valid, False otherwise.
        """
        try:
            # Try to fetch account info as a credential check
            response = self.session.get(f"{self.base_url}/v2/account", timeout=5)
            if response.status_code == 200:
                logger.debug("✅ Alpaca credentials verified")
                return True
            else:
                logger.error(f"❌ Credential verification failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Error verifying credentials: {e}")
            return False
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Make a rate-limited request to the Alpaca API.
        
        Args:
            method: HTTP method ("GET", "POST", "DELETE", etc.)
            endpoint: API endpoint path (e.g., "/v2/positions")
            params: Optional query parameters
            json_data: Optional JSON body data
            
        Returns:
            JSON response as dictionary or list, or None if request failed
        """
        # Acquire rate limit permission (will block if necessary)
        self.rate_limiter.acquire()
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(
                method=method.upper(),
                url=url,
                params=params,
                json=json_data,
                timeout=10
            )
            
            # Handle common HTTP errors
            if response.status_code == 401:
                logger.error(f"❌ Alpaca API authentication failed (401 Unauthorized). Check your credentials.")
                return None
            
            elif response.status_code == 403:
                logger.error(f"❌ Alpaca API forbidden (403). Check account permissions and trading mode.")
                return None
            
            elif response.status_code == 429:
                logger.warning(f"⚠️  Alpaca API rate limit exceeded (429 Too Many Requests).")
                return None
            
            elif response.status_code == 422:
                # Unprocessable entity - usually invalid order parameters
                error_detail = response.json() if response.text else {}
                logger.error(f"❌ Invalid request parameters (422): {error_detail}")
                return {"error": "invalid_parameters", "detail": error_detail}
            
            elif response.status_code not in [200, 201, 204]:
                logger.error(f"❌ Alpaca API request failed with status {response.status_code}: {response.text}")
                return None
            
            # Handle empty responses (e.g., from DELETE)
            if response.status_code == 204 or not response.text:
                return {"success": True}
            
            data = response.json()
            return data
            
        except requests.exceptions.Timeout:
            logger.error(f"❌ Alpaca API request timed out for {endpoint}")
            return None
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ Network error connecting to Alpaca API: {e}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Unexpected error making Alpaca API request: {e}")
            return None
            
        except ValueError as e:
            logger.error(f"❌ Invalid JSON response from Alpaca API: {e}")
            return None
    
    def get_positions(self) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve all current portfolio positions.
        
        Returns:
            List of position dictionaries, each containing:
                - 'symbol': Stock ticker symbol
                - 'qty': Number of shares held (can be negative for short positions)
                - 'avg_entry_price': Average entry price per share
                - 'current_price': Current market price per share
                - 'market_value': Current market value of position
                - 'unrealized_pl': Unrealized profit/loss
                - 'unrealized_plpc': Unrealized profit/loss percentage
                - 'side': Position side ('long' or 'short')
                
            Returns empty list if no positions exist.
            Returns None if the request fails.
            
        Example:
            >>> positions = trader.get_positions()
            >>> if positions is not None:
            ...     total_value = sum(float(pos['market_value']) for pos in positions)
            ...     print(f"Portfolio value: ${total_value:,.2f}")
            ...     for pos in positions:
            ...         pl_pct = float(pos['unrealized_plpc']) * 100
            ...         print(f"{pos['symbol']}: {pos['qty']} shares, P/L: {pl_pct:.2f}%")
        """
        logger.debug("Fetching portfolio positions")
        
        data = self._make_request("GET", "/v2/positions")
        
        if data is None:
            logger.error("❌ Failed to fetch positions")
            return None
        
        # Alpaca returns a list directly
        if isinstance(data, list):
            logger.debug(f"✅ Fetched {len(data)} positions")
            return data
        
        logger.warning(f"⚠️  Unexpected response format for positions: {type(data)}")
        return None
    
    def place_order(
        self,
        symbol: str,
        qty: float,
        side: Literal["buy", "sell"],
        order_type: Literal["market", "limit", "stop", "stop_limit"] = "market",
        time_in_force: Literal["day", "gtc", "ioc", "fok"] = "day",
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        extended_hours: bool = False
    ) -> Dict[str, Any]:
        """
        Submit a trade order to Alpaca.
        
        Args:
            symbol: Stock ticker symbol (e.g., "AAPL", "TSLA")
            qty: Quantity of shares to trade (fractional shares supported)
            side: Order side - "buy" or "sell"
            order_type: Type of order - "market", "limit", "stop", or "stop_limit"
            time_in_force: Order duration - "day", "gtc" (good til canceled), 
                          "ioc" (immediate or cancel), "fok" (fill or kill)
            limit_price: Limit price (required for "limit" and "stop_limit" orders)
            stop_price: Stop price (required for "stop" and "stop_limit" orders)
            extended_hours: If True, allow order execution during extended hours
            
        Returns:
            Dictionary with keys:
                - 'success': Boolean indicating if order was placed successfully
                - 'order_id': Alpaca order ID (if successful)
                - 'symbol': Symbol traded
                - 'status': Order status ("new", "accepted", etc.)
                - 'error': Error message (if unsuccessful)
                - 'detail': Additional error details (if unsuccessful)
                
        Example:
            >>> # Market buy order
            >>> result = trader.place_order("AAPL", 10, "buy", "market")
            >>> if result['success']:
            ...     print(f"✅ Order {result['order_id']} placed")
            >>> 
            >>> # Limit sell order
            >>> result = trader.place_order("TSLA", 5, "sell", "limit", limit_price=250.00)
            >>> if not result['success']:
            ...     print(f"❌ Order failed: {result['error']}")
        """
        if not symbol:
            logger.warning("⚠️  Empty symbol provided to place_order()")
            return {"success": False, "error": "empty_symbol", "detail": "Symbol cannot be empty"}
        
        if qty <= 0:
            logger.warning(f"⚠️  Invalid quantity {qty} for place_order()")
            return {"success": False, "error": "invalid_quantity", "detail": f"Quantity must be positive, got {qty}"}
        
        if side not in ["buy", "sell"]:
            logger.warning(f"⚠️  Invalid side '{side}' for place_order()")
            return {"success": False, "error": "invalid_side", "detail": f"Side must be 'buy' or 'sell', got '{side}'"}
        
        # Validate order type requirements
        if order_type in ["limit", "stop_limit"] and limit_price is None:
            return {"success": False, "error": "missing_limit_price", "detail": f"{order_type} order requires limit_price"}
        
        if order_type in ["stop", "stop_limit"] and stop_price is None:
            return {"success": False, "error": "missing_stop_price", "detail": f"{order_type} order requires stop_price"}
        
        # Build order request
        order_data = {
            "symbol": symbol.upper(),
            "qty": qty,
            "side": side,
            "type": order_type,
            "time_in_force": time_in_force,
        }
        
        if limit_price is not None:
            order_data["limit_price"] = limit_price
        
        if stop_price is not None:
            order_data["stop_price"] = stop_price
        
        if extended_hours:
            order_data["extended_hours"] = True
        
        logger.info(f"📤 Placing {side} order: {qty} {symbol} @ {order_type}")
        
        response = self._make_request("POST", "/v2/orders", json_data=order_data)
        
        if response is None:
            logger.error(f"❌ Order submission failed for {symbol}")
            return {
                "success": False,
                "symbol": symbol,
                "error": "request_failed",
                "detail": "Failed to communicate with Alpaca API"
            }
        
        # Check for API-level errors (422 responses)
        if "error" in response:
            logger.error(f"❌ Order rejected: {response.get('detail', 'Unknown error')}")
            return {
                "success": False,
                "symbol": symbol,
                "error": response["error"],
                "detail": response.get("detail", {})
            }
        
        # Successful order submission
        order_id = response.get("id")
        status = response.get("status")
        
        logger.info(f"✅ Order placed: {order_id} (status: {status})")
        
        return {
            "success": True,
            "order_id": order_id,
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "type": order_type,
            "status": status,
            "submitted_at": response.get("submitted_at"),
            "filled_qty": response.get("filled_qty", 0)
        }
    
    def get_account(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve account information including buying power and equity.
        
        Returns:
            Dictionary containing account data:
                - 'equity': Total account equity
                - 'cash': Available cash
                - 'buying_power': Current buying power
                - 'portfolio_value': Current portfolio value
                - 'pattern_day_trader': Whether account is flagged as PDT
                
            Returns None if the request fails.
            
        Example:
            >>> account = trader.get_account()
            >>> if account:
            ...     print(f"Buying power: ${float(account['buying_power']):,.2f}")
            ...     print(f"Portfolio value: ${float(account['portfolio_value']):,.2f}")
        """
        logger.debug("Fetching account information")
        
        data = self._make_request("GET", "/v2/account")
        
        if data is None:
            logger.error("❌ Failed to fetch account information")
            return None
        
        logger.debug(f"✅ Account info fetched (equity: ${data.get('equity', 0)})")
        return data
    
    def close(self):
        """
        Close the HTTP session and clean up resources.
        
        Should be called when the client is no longer needed.
        """
        if hasattr(self, 'session'):
            self.session.close()
            logger.debug("AlpacaTrader session closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures session is closed."""
        self.close()


if __name__ == "__main__":
    """
    Quick test of the AlpacaTrader functionality.
    
    Usage:
        export APCA_API_KEY_ID=your_key_id
        export APCA_API_SECRET_KEY=your_secret_key
        python alpaca_trader.py
    """
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🧪 Testing AlpacaTrader (PAPER MODE)...\n")
    
    with AlpacaTrader(paper_mode=True) as trader:
        # Test 1: Get account info
        print("Test 1: Fetching account information...")
        account = trader.get_account()
        if account:
            print(f"✅ Account equity: ${float(account.get('equity', 0)):,.2f}")
            print(f"   Buying power: ${float(account.get('buying_power', 0)):,.2f}")
            print(f"   Cash: ${float(account.get('cash', 0)):,.2f}")
        else:
            print("❌ Account fetch failed")
        
        print()
        
        # Test 2: Get positions
        print("Test 2: Fetching portfolio positions...")
        positions = trader.get_positions()
        if positions is not None:
            if len(positions) > 0:
                print(f"✅ Found {len(positions)} positions:")
                for pos in positions[:5]:  # Show first 5
                    pl_pct = float(pos.get('unrealized_plpc', 0)) * 100
                    print(f"   {pos['symbol']}: {pos['qty']} shares @ ${pos['current_price']} (P/L: {pl_pct:+.2f}%)")
            else:
                print("✅ No positions (empty portfolio)")
        else:
            print("❌ Positions fetch failed")
        
        print()
        
        # Test 3: Place a test order (will fail without sufficient buying power)
        print("Test 3: Testing order placement (dry run - may fail on paper account)...")
        result = trader.place_order(
            symbol="AAPL",
            qty=1,
            side="buy",
            order_type="market"
        )
        
        if result['success']:
            print(f"✅ Order placed: {result['order_id']}")
            print(f"   Status: {result['status']}")
        else:
            print(f"⚠️  Order failed (expected on test): {result.get('error', 'Unknown')}")
    
    print("\n✅ AlpacaTrader test complete")
