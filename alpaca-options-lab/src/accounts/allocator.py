"""
Alpaca Options Lab - Capital Allocator

Intelligent capital allocation across accounts:
- Strategy-based allocation
- Risk-weighted distribution
- Dynamic rebalancing
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import math

from src.accounts.manager import Account, AccountManager, AccountStatus, AccountType
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class AllocationStrategy(Enum):
    """Capital allocation strategy."""
    EQUAL = "equal"  # Equal split across accounts
    WEIGHTED = "weighted"  # By account weights
    RISK_PARITY = "risk_parity"  # By inverse volatility
    KELLY = "kelly"  # Kelly criterion
    CUSTOM = "custom"  # Custom allocation logic


@dataclass
class AllocationRequest:
    """Request for capital allocation."""
    strategy_id: str
    total_amount: float
    symbol: str
    order_type: str
    
    # Constraints
    min_per_account: float = 100.0
    max_per_account: Optional[float] = None
    
    # Targeting
    target_accounts: Optional[List[str]] = None  # Specific accounts
    target_types: Optional[List[AccountType]] = None  # Account types
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AllocationResult:
    """Result of capital allocation."""
    request: AllocationRequest
    allocations: Dict[str, float]  # account_id -> allocated amount
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Status
    success: bool = True
    message: str = ""
    
    @property
    def total_allocated(self) -> float:
        """Total amount allocated."""
        return sum(self.allocations.values())
    
    @property
    def num_accounts(self) -> int:
        """Number of accounts with allocations."""
        return len([a for a in self.allocations.values() if a > 0])
    
    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary."""
        return {
            "strategy_id": self.request.strategy_id,
            "total_requested": self.request.total_amount,
            "total_allocated": self.total_allocated,
            "num_accounts": self.num_accounts,
            "allocations": self.allocations,
            "success": self.success,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }


class AllocationAlgorithm(ABC):
    """Base class for allocation algorithms."""
    
    @abstractmethod
    def allocate(
        self,
        request: AllocationRequest,
        accounts: List[Account],
        context: Dict[str, Any],
    ) -> Dict[str, float]:
        """
        Allocate capital across accounts.
        
        Args:
            request: Allocation request
            accounts: Available accounts
            context: Additional context (weights, volatilities, etc.)
        
        Returns:
            Dictionary of account_id -> allocated amount
        """
        pass


class EqualAllocation(AllocationAlgorithm):
    """Equal allocation across accounts."""
    
    def allocate(
        self,
        request: AllocationRequest,
        accounts: List[Account],
        context: Dict[str, Any],
    ) -> Dict[str, float]:
        if not accounts:
            return {}
        
        # Equal split
        per_account = request.total_amount / len(accounts)
        
        # Apply constraints
        allocations = {}
        for account in accounts:
            amount = per_account
            
            # Minimum constraint
            if amount < request.min_per_account:
                amount = 0
            
            # Maximum constraint
            if request.max_per_account:
                amount = min(amount, request.max_per_account)
            
            # Available capital constraint
            amount = min(amount, account.available_buying_power)
            
            allocations[account.account_id] = amount
        
        return allocations


class WeightedAllocation(AllocationAlgorithm):
    """Weighted allocation based on account weights."""
    
    def allocate(
        self,
        request: AllocationRequest,
        accounts: List[Account],
        context: Dict[str, Any],
    ) -> Dict[str, float]:
        weights = context.get("weights", {})
        
        if not accounts:
            return {}
        
        # Get weights for each account
        account_weights = []
        for account in accounts:
            weight = weights.get(account.account_id, 1.0)
            account_weights.append((account, weight))
        
        # Normalize weights
        total_weight = sum(w for _, w in account_weights)
        if total_weight == 0:
            total_weight = 1
        
        # Allocate by weight
        allocations = {}
        for account, weight in account_weights:
            normalized = weight / total_weight
            amount = request.total_amount * normalized
            
            # Apply constraints
            if amount < request.min_per_account:
                amount = 0
            if request.max_per_account:
                amount = min(amount, request.max_per_account)
            amount = min(amount, account.available_buying_power)
            
            allocations[account.account_id] = amount
        
        return allocations


class RiskParityAllocation(AllocationAlgorithm):
    """Risk parity allocation (inverse volatility weighted)."""
    
    def allocate(
        self,
        request: AllocationRequest,
        accounts: List[Account],
        context: Dict[str, Any],
    ) -> Dict[str, float]:
        volatilities = context.get("volatilities", {})
        
        if not accounts:
            return {}
        
        # Calculate inverse volatility weights
        inv_vols = []
        for account in accounts:
            vol = volatilities.get(account.account_id, 0.20)  # Default 20%
            inv_vol = 1.0 / vol if vol > 0 else 1.0
            inv_vols.append((account, inv_vol))
        
        # Normalize
        total_inv_vol = sum(iv for _, iv in inv_vols)
        if total_inv_vol == 0:
            total_inv_vol = 1
        
        # Allocate by inverse volatility
        allocations = {}
        for account, inv_vol in inv_vols:
            normalized = inv_vol / total_inv_vol
            amount = request.total_amount * normalized
            
            # Apply constraints
            if amount < request.min_per_account:
                amount = 0
            if request.max_per_account:
                amount = min(amount, request.max_per_account)
            amount = min(amount, account.available_buying_power)
            
            allocations[account.account_id] = amount
        
        return allocations


class KellyAllocation(AllocationAlgorithm):
    """Kelly criterion allocation."""
    
    def allocate(
        self,
        request: AllocationRequest,
        accounts: List[Account],
        context: Dict[str, Any],
    ) -> Dict[str, float]:
        # Kelly parameters per account
        kelly_params = context.get("kelly_params", {})
        
        if not accounts:
            return {}
        
        allocations = {}
        remaining = request.total_amount
        
        for account in accounts:
            params = kelly_params.get(account.account_id, {})
            
            # Kelly fraction = (p * b - q) / b
            # where p = win probability, b = win/loss ratio, q = 1 - p
            win_prob = params.get("win_probability", 0.55)
            win_loss_ratio = params.get("win_loss_ratio", 1.5)
            
            q = 1 - win_prob
            kelly_fraction = (win_prob * win_loss_ratio - q) / win_loss_ratio
            
            # Apply fractional Kelly (e.g., half Kelly)
            fraction_of_kelly = params.get("fraction", 0.5)
            kelly_fraction *= fraction_of_kelly
            
            # Cap at reasonable maximum
            kelly_fraction = max(0, min(kelly_fraction, 0.25))
            
            # Calculate allocation
            amount = account.equity * kelly_fraction
            amount = min(amount, remaining)
            
            # Apply constraints
            if amount < request.min_per_account:
                amount = 0
            if request.max_per_account:
                amount = min(amount, request.max_per_account)
            amount = min(amount, account.available_buying_power)
            
            allocations[account.account_id] = amount
            remaining -= amount
        
        return allocations


class CapitalAllocator:
    """
    Intelligent capital allocator.
    
    Features:
    - Multiple allocation strategies
    - Dynamic rebalancing
    - Constraint handling
    - Allocation tracking
    """
    
    def __init__(self, account_manager: AccountManager):
        self.account_manager = account_manager
        
        # Allocation algorithms
        self._algorithms: Dict[AllocationStrategy, AllocationAlgorithm] = {
            AllocationStrategy.EQUAL: EqualAllocation(),
            AllocationStrategy.WEIGHTED: WeightedAllocation(),
            AllocationStrategy.RISK_PARITY: RiskParityAllocation(),
            AllocationStrategy.KELLY: KellyAllocation(),
        }
        
        # Account weights
        self._weights: Dict[str, float] = {}
        
        # Volatility estimates
        self._volatilities: Dict[str, float] = {}
        
        # Kelly parameters
        self._kelly_params: Dict[str, Dict[str, float]] = {}
        
        # Allocation history
        self._history: List[AllocationResult] = []
        self._max_history = 1000
        
        logger.info("CapitalAllocator initialized")
    
    # -------------------- Configuration --------------------
    
    def set_account_weight(self, account_id: str, weight: float) -> None:
        """Set allocation weight for account."""
        self._weights[account_id] = max(0, weight)
    
    def set_account_weights(self, weights: Dict[str, float]) -> None:
        """Set weights for multiple accounts."""
        for account_id, weight in weights.items():
            self.set_account_weight(account_id, weight)
    
    def set_volatility(self, account_id: str, volatility: float) -> None:
        """Set volatility estimate for account."""
        self._volatilities[account_id] = max(0.01, volatility)
    
    def set_kelly_params(
        self,
        account_id: str,
        win_probability: float,
        win_loss_ratio: float,
        fraction: float = 0.5,
    ) -> None:
        """Set Kelly criterion parameters for account."""
        self._kelly_params[account_id] = {
            "win_probability": max(0, min(1, win_probability)),
            "win_loss_ratio": max(0.1, win_loss_ratio),
            "fraction": max(0.1, min(1.0, fraction)),
        }
    
    def register_algorithm(
        self,
        strategy: AllocationStrategy,
        algorithm: AllocationAlgorithm,
    ) -> None:
        """Register custom allocation algorithm."""
        self._algorithms[strategy] = algorithm
    
    # -------------------- Allocation --------------------
    
    def allocate(
        self,
        request: AllocationRequest,
        strategy: AllocationStrategy = AllocationStrategy.EQUAL,
    ) -> AllocationResult:
        """
        Allocate capital according to strategy.
        
        Args:
            request: Allocation request
            strategy: Allocation strategy to use
        
        Returns:
            AllocationResult with allocations per account
        """
        # Get eligible accounts
        accounts = self._get_eligible_accounts(request)
        
        if not accounts:
            return AllocationResult(
                request=request,
                allocations={},
                success=False,
                message="No eligible accounts found",
            )
        
        # Build context
        context = {
            "weights": self._weights,
            "volatilities": self._volatilities,
            "kelly_params": self._kelly_params,
        }
        
        # Get algorithm
        algorithm = self._algorithms.get(strategy)
        if not algorithm:
            return AllocationResult(
                request=request,
                allocations={},
                success=False,
                message=f"Unknown allocation strategy: {strategy}",
            )
        
        # Run allocation
        try:
            allocations = algorithm.allocate(request, accounts, context)
            
            result = AllocationResult(
                request=request,
                allocations=allocations,
                success=True,
                message=f"Allocated {sum(allocations.values()):.2f} across {len([a for a in allocations.values() if a > 0])} accounts",
            )
            
            # Record history
            self._record_allocation(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Allocation failed: {e}")
            return AllocationResult(
                request=request,
                allocations={},
                success=False,
                message=str(e),
            )
    
    def _get_eligible_accounts(self, request: AllocationRequest) -> List[Account]:
        """Get accounts eligible for allocation."""
        accounts = []
        
        for account in self.account_manager.get_all_accounts():
            # Check status
            if account.status != AccountStatus.ACTIVE:
                continue
            
            # Check can trade
            if not account.can_trade:
                continue
            
            # Check target accounts
            if request.target_accounts:
                if account.account_id not in request.target_accounts:
                    continue
            
            # Check target types
            if request.target_types:
                if account.account_type not in request.target_types:
                    continue
            
            # Check minimum buying power
            if account.available_buying_power < request.min_per_account:
                continue
            
            accounts.append(account)
        
        return accounts
    
    def _record_allocation(self, result: AllocationResult) -> None:
        """Record allocation in history."""
        self._history.append(result)
        
        # Trim history
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
    
    # -------------------- Rebalancing --------------------
    
    def calculate_rebalance(
        self,
        target_allocations: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Calculate rebalancing trades.
        
        Args:
            target_allocations: Target allocation percentages per account
        
        Returns:
            Dictionary of account_id -> amount to trade (+buy/-sell)
        """
        rebalance = {}
        
        # Get total equity
        total_equity = self.account_manager.get_total_equity()
        
        for account in self.account_manager.get_all_accounts():
            target_pct = target_allocations.get(account.account_id, 0)
            target_value = total_equity * target_pct
            
            current_value = account.equity
            difference = target_value - current_value
            
            # Only include significant differences (> 1%)
            if abs(difference) > current_value * 0.01:
                rebalance[account.account_id] = difference
        
        return rebalance
    
    def get_current_allocation(self) -> Dict[str, float]:
        """Get current allocation percentages."""
        total_equity = self.account_manager.get_total_equity()
        
        if total_equity == 0:
            return {}
        
        allocations = {}
        for account in self.account_manager.get_all_accounts():
            allocations[account.account_id] = account.equity / total_equity
        
        return allocations
    
    # -------------------- Analysis --------------------
    
    def get_allocation_history(
        self,
        strategy_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[AllocationResult]:
        """Get allocation history."""
        history = self._history
        
        if strategy_id:
            history = [h for h in history if h.request.strategy_id == strategy_id]
        
        return history[-limit:]
    
    def get_allocation_stats(self) -> Dict[str, Any]:
        """Get allocation statistics."""
        if not self._history:
            return {}
        
        total_allocated = sum(r.total_allocated for r in self._history)
        successful = len([r for r in self._history if r.success])
        
        return {
            "total_allocations": len(self._history),
            "successful_allocations": successful,
            "success_rate": successful / len(self._history) if self._history else 0,
            "total_capital_allocated": total_allocated,
            "average_allocation": total_allocated / len(self._history) if self._history else 0,
            "current_allocation": self.get_current_allocation(),
        }
    
    def optimize_weights(
        self,
        returns: Dict[str, List[float]],
        risk_free_rate: float = 0.05,
    ) -> Dict[str, float]:
        """
        Optimize account weights using mean-variance optimization.
        
        Args:
            returns: Historical returns per account
            risk_free_rate: Risk-free rate
        
        Returns:
            Optimal weights per account
        """
        accounts = list(returns.keys())
        n = len(accounts)
        
        if n == 0:
            return {}
        
        # Calculate statistics
        means = {}
        variances = {}
        
        for account_id, rets in returns.items():
            if rets:
                means[account_id] = sum(rets) / len(rets)
                variance = sum((r - means[account_id]) ** 2 for r in rets) / len(rets)
                variances[account_id] = variance
            else:
                means[account_id] = 0
                variances[account_id] = 0.04  # Default variance
        
        # Simple risk-adjusted allocation (Sharpe ratio based)
        sharpes = {}
        for account_id in accounts:
            excess_return = means[account_id] - risk_free_rate
            volatility = math.sqrt(variances[account_id]) if variances[account_id] > 0 else 0.2
            sharpes[account_id] = excess_return / volatility if volatility > 0 else 0
        
        # Convert to positive weights
        min_sharpe = min(sharpes.values())
        adjusted = {k: v - min_sharpe + 0.1 for k, v in sharpes.items()}
        
        # Normalize
        total = sum(adjusted.values())
        if total == 0:
            total = 1
        
        optimal_weights = {k: v / total for k, v in adjusted.items()}
        
        return optimal_weights
