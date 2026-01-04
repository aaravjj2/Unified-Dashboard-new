"""
Alpaca Options Lab - Account Manager

Multi-account management:
- Account registration and configuration
- Credential management
- Account status monitoring
- Order routing
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol
import uuid

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class AccountType(Enum):
    """Account type."""
    LIVE = "live"
    PAPER = "paper"
    BACKTEST = "backtest"


class AccountStatus(Enum):
    """Account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    ERROR = "error"


@dataclass
class AccountCredentials:
    """Account API credentials."""
    api_key: str
    api_secret: str
    endpoint: str = "https://api.alpaca.markets"
    
    def __post_init__(self):
        # Mask credentials in logs
        self._masked_key = f"{self.api_key[:4]}...{self.api_key[-4:]}" if len(self.api_key) > 8 else "****"


@dataclass
class Account:
    """Trading account."""
    account_id: str
    name: str
    account_type: AccountType
    credentials: Optional[AccountCredentials] = None
    
    # Account details
    buying_power: float = 0.0
    cash: float = 0.0
    portfolio_value: float = 0.0
    equity: float = 0.0
    
    # Margin
    initial_margin: float = 0.0
    maintenance_margin: float = 0.0
    margin_multiplier: float = 1.0
    
    # Status
    status: AccountStatus = AccountStatus.INACTIVE
    last_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: str = ""
    
    # Trading permissions
    options_level: int = 0  # 0-4 options trading level
    day_trading: bool = False
    shorting_enabled: bool = False
    
    # Limits
    max_position_size: float = 10000.0
    max_daily_trades: int = 100
    daily_trades_used: int = 0
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.account_id:
            self.account_id = str(uuid.uuid4())[:12]
    
    @property
    def available_buying_power(self) -> float:
        """Available buying power for new positions."""
        return self.buying_power
    
    @property
    def can_trade(self) -> bool:
        """Check if account can trade."""
        return (
            self.status == AccountStatus.ACTIVE and
            self.daily_trades_used < self.max_daily_trades
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary."""
        return {
            "account_id": self.account_id,
            "name": self.name,
            "type": self.account_type.value,
            "status": self.status.value,
            "buying_power": self.buying_power,
            "cash": self.cash,
            "portfolio_value": self.portfolio_value,
            "equity": self.equity,
            "options_level": self.options_level,
            "can_trade": self.can_trade,
            "last_update": self.last_update.isoformat(),
        }


class BrokerConnection(Protocol):
    """Protocol for broker API connections."""
    
    async def get_account(self) -> Dict[str, Any]:
        """Get account information."""
        ...
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get positions."""
        ...
    
    async def submit_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Submit order."""
        ...
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order."""
        ...


class AccountManager:
    """
    Multi-account manager.
    
    Manages multiple trading accounts with:
    - Credential management
    - Status monitoring
    - Order routing
    - Position tracking
    """
    
    def __init__(self):
        # Accounts
        self._accounts: Dict[str, Account] = {}
        
        # Broker connections
        self._connections: Dict[str, BrokerConnection] = {}
        
        # Default account
        self._default_account_id: Optional[str] = None
        
        # Callbacks
        self._on_status_change: List[Callable] = []
        
        # Monitoring
        self._monitor_task: Optional[asyncio.Task] = None
        self._monitor_interval = 60  # seconds
        
        logger.info("AccountManager initialized")
    
    # -------------------- Account Management --------------------
    
    def add_account(
        self,
        name: str,
        account_type: AccountType,
        credentials: Optional[AccountCredentials] = None,
        **kwargs,
    ) -> Account:
        """
        Add a new account.
        
        Args:
            name: Account display name
            account_type: Live, paper, or backtest
            credentials: API credentials
            **kwargs: Additional account attributes
        
        Returns:
            Created Account
        """
        account = Account(
            account_id="",  # Will be generated
            name=name,
            account_type=account_type,
            credentials=credentials,
            **kwargs,
        )
        
        self._accounts[account.account_id] = account
        
        # Set as default if first account
        if self._default_account_id is None:
            self._default_account_id = account.account_id
        
        logger.info(f"Account added: {account.name} ({account.account_id})")
        
        return account
    
    def remove_account(self, account_id: str) -> bool:
        """Remove an account."""
        if account_id not in self._accounts:
            return False
        
        # Close connection
        if account_id in self._connections:
            del self._connections[account_id]
        
        del self._accounts[account_id]
        
        # Update default
        if self._default_account_id == account_id:
            self._default_account_id = next(iter(self._accounts.keys()), None)
        
        logger.info(f"Account removed: {account_id}")
        return True
    
    def get_account(self, account_id: str) -> Optional[Account]:
        """Get account by ID."""
        return self._accounts.get(account_id)
    
    def get_all_accounts(self) -> List[Account]:
        """Get all accounts."""
        return list(self._accounts.values())
    
    def get_default_account(self) -> Optional[Account]:
        """Get default account."""
        if self._default_account_id:
            return self._accounts.get(self._default_account_id)
        return None
    
    def set_default_account(self, account_id: str) -> bool:
        """Set default account."""
        if account_id not in self._accounts:
            return False
        self._default_account_id = account_id
        return True
    
    def get_accounts_by_type(self, account_type: AccountType) -> List[Account]:
        """Get accounts by type."""
        return [a for a in self._accounts.values() if a.account_type == account_type]
    
    def get_active_accounts(self) -> List[Account]:
        """Get all active accounts."""
        return [a for a in self._accounts.values() if a.status == AccountStatus.ACTIVE]
    
    # -------------------- Connection Management --------------------
    
    async def connect_account(
        self,
        account_id: str,
        connection: BrokerConnection,
    ) -> bool:
        """
        Connect to broker for an account.
        
        Args:
            account_id: Account ID
            connection: Broker connection implementation
        
        Returns:
            True if connection successful
        """
        account = self._accounts.get(account_id)
        if not account:
            return False
        
        try:
            # Store connection
            self._connections[account_id] = connection
            
            # Fetch initial account data
            await self.refresh_account(account_id)
            
            account.status = AccountStatus.ACTIVE
            account.last_update = datetime.now(timezone.utc)
            
            logger.info(f"Account connected: {account.name}")
            return True
            
        except Exception as e:
            account.status = AccountStatus.ERROR
            account.error_message = str(e)
            logger.error(f"Failed to connect account {account_id}: {e}")
            return False
    
    async def disconnect_account(self, account_id: str) -> None:
        """Disconnect account."""
        if account_id in self._connections:
            del self._connections[account_id]
        
        if account_id in self._accounts:
            self._accounts[account_id].status = AccountStatus.INACTIVE
    
    async def refresh_account(self, account_id: str) -> bool:
        """Refresh account data from broker."""
        account = self._accounts.get(account_id)
        connection = self._connections.get(account_id)
        
        if not account or not connection:
            return False
        
        try:
            data = await connection.get_account()
            
            # Update account fields
            account.buying_power = float(data.get("buying_power", 0))
            account.cash = float(data.get("cash", 0))
            account.portfolio_value = float(data.get("portfolio_value", 0))
            account.equity = float(data.get("equity", 0))
            account.initial_margin = float(data.get("initial_margin", 0))
            account.maintenance_margin = float(data.get("maintenance_margin", 0))
            account.day_trading = data.get("daytrade_count", 0) > 0
            
            account.last_update = datetime.now(timezone.utc)
            account.error_message = ""
            
            return True
            
        except Exception as e:
            account.error_message = str(e)
            logger.error(f"Failed to refresh account {account_id}: {e}")
            return False
    
    async def refresh_all_accounts(self) -> Dict[str, bool]:
        """Refresh all connected accounts."""
        results = {}
        
        tasks = [
            self.refresh_account(account_id)
            for account_id in self._connections.keys()
        ]
        
        if tasks:
            refresh_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for account_id, result in zip(self._connections.keys(), refresh_results):
                results[account_id] = result if isinstance(result, bool) else False
        
        return results
    
    # -------------------- Order Routing --------------------
    
    async def submit_order(
        self,
        order: Dict[str, Any],
        account_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Submit order to specific account.
        
        Args:
            order: Order details
            account_id: Target account (uses default if not specified)
        
        Returns:
            Order result from broker
        """
        target_id = account_id or self._default_account_id
        
        if not target_id:
            return {"success": False, "error": "No account specified"}
        
        account = self._accounts.get(target_id)
        connection = self._connections.get(target_id)
        
        if not account or not connection:
            return {"success": False, "error": "Account not found or not connected"}
        
        if not account.can_trade:
            return {"success": False, "error": "Account cannot trade"}
        
        try:
            result = await connection.submit_order(order)
            
            # Update trade count
            account.daily_trades_used += 1
            
            return {"success": True, **result}
            
        except Exception as e:
            logger.error(f"Order submission failed for {target_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def cancel_order(
        self,
        order_id: str,
        account_id: Optional[str] = None,
    ) -> bool:
        """Cancel order on specific account."""
        target_id = account_id or self._default_account_id
        
        if not target_id:
            return False
        
        connection = self._connections.get(target_id)
        if not connection:
            return False
        
        try:
            return await connection.cancel_order(order_id)
        except Exception as e:
            logger.error(f"Order cancellation failed: {e}")
            return False
    
    async def get_positions(
        self,
        account_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get positions for account."""
        target_id = account_id or self._default_account_id
        
        if not target_id:
            return []
        
        connection = self._connections.get(target_id)
        if not connection:
            return []
        
        try:
            return await connection.get_positions()
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []
    
    # -------------------- Monitoring --------------------
    
    async def start_monitoring(self, interval: int = 60) -> None:
        """Start account monitoring."""
        self._monitor_interval = interval
        
        if self._monitor_task is None or self._monitor_task.done():
            self._monitor_task = asyncio.create_task(self._monitor_loop())
            logger.info(f"Account monitoring started (interval: {interval}s)")
    
    async def stop_monitoring(self) -> None:
        """Stop account monitoring."""
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            logger.info("Account monitoring stopped")
    
    async def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while True:
            try:
                await self.refresh_all_accounts()
                
                # Check for status changes
                for account in self._accounts.values():
                    if account.error_message:
                        await self._notify_status_change(account)
                
                await asyncio.sleep(self._monitor_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(self._monitor_interval)
    
    def on_status_change(self, callback: Callable) -> None:
        """Register status change callback."""
        self._on_status_change.append(callback)
    
    async def _notify_status_change(self, account: Account) -> None:
        """Notify status change callbacks."""
        for callback in self._on_status_change:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(account)
                else:
                    callback(account)
            except Exception as e:
                logger.error(f"Status callback error: {e}")
    
    # -------------------- Aggregation --------------------
    
    def get_total_equity(self) -> float:
        """Get total equity across all accounts."""
        return sum(a.equity for a in self._accounts.values())
    
    def get_total_buying_power(self) -> float:
        """Get total buying power across all accounts."""
        return sum(a.buying_power for a in self._accounts.values())
    
    def get_summary(self) -> Dict[str, Any]:
        """Get multi-account summary."""
        accounts = list(self._accounts.values())
        
        return {
            "total_accounts": len(accounts),
            "active_accounts": len([a for a in accounts if a.status == AccountStatus.ACTIVE]),
            "total_equity": sum(a.equity for a in accounts),
            "total_buying_power": sum(a.buying_power for a in accounts),
            "total_cash": sum(a.cash for a in accounts),
            "accounts": [a.to_dict() for a in accounts],
        }
    
    def reset_daily_counters(self) -> None:
        """Reset daily trade counters (call at market open)."""
        for account in self._accounts.values():
            account.daily_trades_used = 0
        logger.info("Daily trade counters reset")
