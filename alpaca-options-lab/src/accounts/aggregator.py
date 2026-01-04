"""
Alpaca Options Lab - Position Aggregator

Aggregate positions across multiple accounts:
- Position consolidation
- P&L aggregation
- Risk aggregation
- Account summaries
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict

from src.accounts.manager import Account, AccountManager, AccountStatus
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class Position:
    """Position in a single account."""
    symbol: str
    quantity: float
    avg_entry_price: float
    current_price: float
    
    # Options specific
    is_option: bool = False
    strike: Optional[float] = None
    expiration: Optional[str] = None
    option_type: Optional[str] = None  # "call" or "put"
    
    # P&L
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    
    # Account info
    account_id: str = ""
    account_name: str = ""
    
    @property
    def market_value(self) -> float:
        """Current market value."""
        return self.quantity * self.current_price
    
    @property
    def cost_basis(self) -> float:
        """Cost basis."""
        return self.quantity * self.avg_entry_price
    
    @property
    def pnl_pct(self) -> float:
        """P&L percentage."""
        if self.cost_basis == 0:
            return 0.0
        return (self.market_value - self.cost_basis) / self.cost_basis * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary."""
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "avg_entry_price": self.avg_entry_price,
            "current_price": self.current_price,
            "market_value": self.market_value,
            "cost_basis": self.cost_basis,
            "unrealized_pnl": self.unrealized_pnl,
            "pnl_pct": self.pnl_pct,
            "account_id": self.account_id,
            "account_name": self.account_name,
            "is_option": self.is_option,
        }


@dataclass
class AggregatedPosition:
    """Aggregated position across multiple accounts."""
    symbol: str
    positions: List[Position] = field(default_factory=list)
    
    @property
    def total_quantity(self) -> float:
        """Total quantity across all accounts."""
        return sum(p.quantity for p in self.positions)
    
    @property
    def weighted_avg_price(self) -> float:
        """Weighted average entry price."""
        total_cost = sum(p.cost_basis for p in self.positions)
        total_qty = self.total_quantity
        return total_cost / total_qty if total_qty != 0 else 0
    
    @property
    def current_price(self) -> float:
        """Current price (from first position)."""
        return self.positions[0].current_price if self.positions else 0
    
    @property
    def total_market_value(self) -> float:
        """Total market value."""
        return sum(p.market_value for p in self.positions)
    
    @property
    def total_cost_basis(self) -> float:
        """Total cost basis."""
        return sum(p.cost_basis for p in self.positions)
    
    @property
    def total_unrealized_pnl(self) -> float:
        """Total unrealized P&L."""
        return sum(p.unrealized_pnl for p in self.positions)
    
    @property
    def pnl_pct(self) -> float:
        """Aggregate P&L percentage."""
        if self.total_cost_basis == 0:
            return 0.0
        return (self.total_market_value - self.total_cost_basis) / self.total_cost_basis * 100
    
    @property
    def account_count(self) -> int:
        """Number of accounts with this position."""
        return len(set(p.account_id for p in self.positions))
    
    def add_position(self, position: Position) -> None:
        """Add a position to aggregate."""
        self.positions.append(position)
    
    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary."""
        return {
            "symbol": self.symbol,
            "total_quantity": self.total_quantity,
            "weighted_avg_price": self.weighted_avg_price,
            "current_price": self.current_price,
            "total_market_value": self.total_market_value,
            "total_cost_basis": self.total_cost_basis,
            "total_unrealized_pnl": self.total_unrealized_pnl,
            "pnl_pct": self.pnl_pct,
            "account_count": self.account_count,
            "positions": [p.to_dict() for p in self.positions],
        }


@dataclass
class AccountSummary:
    """Summary for a single account."""
    account_id: str
    account_name: str
    
    # Values
    equity: float = 0.0
    cash: float = 0.0
    buying_power: float = 0.0
    portfolio_value: float = 0.0
    
    # P&L
    total_unrealized_pnl: float = 0.0
    total_realized_pnl: float = 0.0
    daily_pnl: float = 0.0
    
    # Positions
    position_count: int = 0
    option_position_count: int = 0
    stock_position_count: int = 0
    
    # Risk metrics
    exposure_long: float = 0.0
    exposure_short: float = 0.0
    net_exposure: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary."""
        return {
            "account_id": self.account_id,
            "account_name": self.account_name,
            "equity": self.equity,
            "cash": self.cash,
            "buying_power": self.buying_power,
            "portfolio_value": self.portfolio_value,
            "total_unrealized_pnl": self.total_unrealized_pnl,
            "total_realized_pnl": self.total_realized_pnl,
            "daily_pnl": self.daily_pnl,
            "position_count": self.position_count,
            "net_exposure": self.net_exposure,
        }


@dataclass
class PortfolioSummary:
    """Aggregate summary across all accounts."""
    accounts: List[AccountSummary] = field(default_factory=list)
    positions: List[AggregatedPosition] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def total_equity(self) -> float:
        return sum(a.equity for a in self.accounts)
    
    @property
    def total_cash(self) -> float:
        return sum(a.cash for a in self.accounts)
    
    @property
    def total_buying_power(self) -> float:
        return sum(a.buying_power for a in self.accounts)
    
    @property
    def total_unrealized_pnl(self) -> float:
        return sum(a.total_unrealized_pnl for a in self.accounts)
    
    @property
    def total_realized_pnl(self) -> float:
        return sum(a.total_realized_pnl for a in self.accounts)
    
    @property
    def total_daily_pnl(self) -> float:
        return sum(a.daily_pnl for a in self.accounts)
    
    @property
    def unique_symbols(self) -> int:
        return len(self.positions)
    
    @property
    def total_positions(self) -> int:
        return sum(a.position_count for a in self.accounts)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_accounts": len(self.accounts),
            "total_equity": self.total_equity,
            "total_cash": self.total_cash,
            "total_buying_power": self.total_buying_power,
            "total_unrealized_pnl": self.total_unrealized_pnl,
            "total_realized_pnl": self.total_realized_pnl,
            "total_daily_pnl": self.total_daily_pnl,
            "unique_symbols": self.unique_symbols,
            "total_positions": self.total_positions,
            "accounts": [a.to_dict() for a in self.accounts],
            "positions": [p.to_dict() for p in self.positions],
            "timestamp": self.timestamp.isoformat(),
        }


class PositionAggregator:
    """
    Aggregates positions across multiple accounts.
    
    Features:
    - Position consolidation by symbol
    - P&L aggregation
    - Risk metrics calculation
    - Account summaries
    """
    
    def __init__(self, account_manager: AccountManager):
        self.account_manager = account_manager
        
        # Cache
        self._position_cache: Dict[str, List[Position]] = {}
        self._last_update: Optional[datetime] = None
        self._cache_ttl_seconds = 30
        
        logger.info("PositionAggregator initialized")
    
    # -------------------- Position Aggregation --------------------
    
    async def aggregate_positions(
        self,
        symbols: Optional[List[str]] = None,
        account_ids: Optional[List[str]] = None,
        use_cache: bool = True,
    ) -> List[AggregatedPosition]:
        """
        Aggregate positions across accounts.
        
        Args:
            symbols: Filter by symbols (None for all)
            account_ids: Filter by accounts (None for all)
            use_cache: Use cached positions if available
        
        Returns:
            List of aggregated positions
        """
        # Refresh if needed
        if not use_cache or self._is_cache_stale():
            await self._refresh_positions(account_ids)
        
        # Group by symbol
        by_symbol: Dict[str, AggregatedPosition] = {}
        
        for account_id, positions in self._position_cache.items():
            if account_ids and account_id not in account_ids:
                continue
            
            for position in positions:
                if symbols and position.symbol not in symbols:
                    continue
                
                if position.symbol not in by_symbol:
                    by_symbol[position.symbol] = AggregatedPosition(symbol=position.symbol)
                
                by_symbol[position.symbol].add_position(position)
        
        return list(by_symbol.values())
    
    async def _refresh_positions(
        self,
        account_ids: Optional[List[str]] = None,
    ) -> None:
        """Refresh position cache from accounts."""
        self._position_cache.clear()
        
        accounts = self.account_manager.get_all_accounts()
        
        for account in accounts:
            if account_ids and account.account_id not in account_ids:
                continue
            
            if account.status != AccountStatus.ACTIVE:
                continue
            
            try:
                raw_positions = await self.account_manager.get_positions(account.account_id)
                
                positions = []
                for raw in raw_positions:
                    position = Position(
                        symbol=raw.get("symbol", ""),
                        quantity=float(raw.get("qty", 0)),
                        avg_entry_price=float(raw.get("avg_entry_price", 0)),
                        current_price=float(raw.get("current_price", 0)),
                        unrealized_pnl=float(raw.get("unrealized_pl", 0)),
                        realized_pnl=float(raw.get("realized_pl", 0)),
                        account_id=account.account_id,
                        account_name=account.name,
                    )
                    
                    # Check if option
                    if "option_type" in raw or "strike" in raw:
                        position.is_option = True
                        position.strike = raw.get("strike")
                        position.expiration = raw.get("expiration")
                        position.option_type = raw.get("option_type")
                    
                    positions.append(position)
                
                self._position_cache[account.account_id] = positions
                
            except Exception as e:
                logger.error(f"Failed to get positions for {account.account_id}: {e}")
        
        self._last_update = datetime.now(timezone.utc)
    
    def _is_cache_stale(self) -> bool:
        """Check if position cache is stale."""
        if self._last_update is None:
            return True
        
        age = (datetime.now(timezone.utc) - self._last_update).total_seconds()
        return age > self._cache_ttl_seconds
    
    # -------------------- Account Summaries --------------------
    
    async def get_account_summary(self, account_id: str) -> Optional[AccountSummary]:
        """Get summary for a single account."""
        account = self.account_manager.get_account(account_id)
        if not account:
            return None
        
        # Get positions
        positions = self._position_cache.get(account_id, [])
        if not positions:
            await self._refresh_positions([account_id])
            positions = self._position_cache.get(account_id, [])
        
        # Calculate metrics
        total_unrealized = sum(p.unrealized_pnl for p in positions)
        total_realized = sum(p.realized_pnl for p in positions)
        
        option_count = len([p for p in positions if p.is_option])
        stock_count = len([p for p in positions if not p.is_option])
        
        exposure_long = sum(p.market_value for p in positions if p.quantity > 0)
        exposure_short = abs(sum(p.market_value for p in positions if p.quantity < 0))
        
        return AccountSummary(
            account_id=account.account_id,
            account_name=account.name,
            equity=account.equity,
            cash=account.cash,
            buying_power=account.buying_power,
            portfolio_value=account.portfolio_value,
            total_unrealized_pnl=total_unrealized,
            total_realized_pnl=total_realized,
            position_count=len(positions),
            option_position_count=option_count,
            stock_position_count=stock_count,
            exposure_long=exposure_long,
            exposure_short=exposure_short,
            net_exposure=exposure_long - exposure_short,
        )
    
    async def get_portfolio_summary(self) -> PortfolioSummary:
        """Get aggregate portfolio summary."""
        # Refresh all positions
        await self._refresh_positions()
        
        # Get account summaries
        summaries = []
        for account in self.account_manager.get_all_accounts():
            summary = await self.get_account_summary(account.account_id)
            if summary:
                summaries.append(summary)
        
        # Aggregate positions
        positions = await self.aggregate_positions(use_cache=True)
        
        return PortfolioSummary(
            accounts=summaries,
            positions=positions,
        )
    
    # -------------------- Risk Aggregation --------------------
    
    async def get_exposure_by_symbol(self) -> Dict[str, float]:
        """Get total exposure by symbol."""
        positions = await self.aggregate_positions()
        
        return {
            p.symbol: p.total_market_value
            for p in positions
        }
    
    async def get_exposure_by_account(self) -> Dict[str, float]:
        """Get total exposure by account."""
        exposure = {}
        
        for account_id, positions in self._position_cache.items():
            exposure[account_id] = sum(p.market_value for p in positions)
        
        return exposure
    
    async def get_concentration_risk(
        self,
        threshold: float = 0.20,  # 20% of portfolio
    ) -> List[Dict[str, Any]]:
        """Get positions that exceed concentration threshold."""
        positions = await self.aggregate_positions()
        total_value = sum(p.total_market_value for p in positions)
        
        if total_value == 0:
            return []
        
        concentrated = []
        for position in positions:
            concentration = position.total_market_value / total_value
            if concentration > threshold:
                concentrated.append({
                    "symbol": position.symbol,
                    "market_value": position.total_market_value,
                    "concentration": concentration,
                    "threshold": threshold,
                    "excess": concentration - threshold,
                })
        
        return sorted(concentrated, key=lambda x: x["concentration"], reverse=True)
    
    async def get_greek_exposure(self) -> Dict[str, float]:
        """Get aggregate Greek exposure (for options)."""
        # This would require option pricing data
        # Placeholder for now
        return {
            "delta": 0.0,
            "gamma": 0.0,
            "theta": 0.0,
            "vega": 0.0,
        }
    
    # -------------------- P&L Analysis --------------------
    
    async def get_pnl_by_symbol(self) -> Dict[str, Dict[str, float]]:
        """Get P&L breakdown by symbol."""
        positions = await self.aggregate_positions()
        
        return {
            p.symbol: {
                "unrealized": p.total_unrealized_pnl,
                "pnl_pct": p.pnl_pct,
                "market_value": p.total_market_value,
            }
            for p in positions
        }
    
    async def get_pnl_by_account(self) -> Dict[str, Dict[str, float]]:
        """Get P&L breakdown by account."""
        pnl = {}
        
        for account_id, positions in self._position_cache.items():
            unrealized = sum(p.unrealized_pnl for p in positions)
            realized = sum(p.realized_pnl for p in positions)
            
            pnl[account_id] = {
                "unrealized": unrealized,
                "realized": realized,
                "total": unrealized + realized,
            }
        
        return pnl
    
    async def get_winners_losers(
        self,
        top_n: int = 5,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get top winners and losers."""
        positions = await self.aggregate_positions()
        
        sorted_positions = sorted(
            positions,
            key=lambda p: p.total_unrealized_pnl,
            reverse=True,
        )
        
        winners = [
            {
                "symbol": p.symbol,
                "pnl": p.total_unrealized_pnl,
                "pnl_pct": p.pnl_pct,
            }
            for p in sorted_positions[:top_n]
            if p.total_unrealized_pnl > 0
        ]
        
        losers = [
            {
                "symbol": p.symbol,
                "pnl": p.total_unrealized_pnl,
                "pnl_pct": p.pnl_pct,
            }
            for p in reversed(sorted_positions[-top_n:])
            if p.total_unrealized_pnl < 0
        ]
        
        return {
            "winners": winners,
            "losers": losers,
        }
    
    # -------------------- Utilities --------------------
    
    def clear_cache(self) -> None:
        """Clear position cache."""
        self._position_cache.clear()
        self._last_update = None
    
    def set_cache_ttl(self, seconds: int) -> None:
        """Set cache TTL in seconds."""
        self._cache_ttl_seconds = max(1, seconds)
