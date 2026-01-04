"""
Capital Ramp-Up Manager - Gradual Capital Allocation

Gradually increases trading capital based on performance:
- Week 1: 10% capital
- Week 2: 25% capital (if profitable)
- Week 3: 50% capital (if cumulative profitable)
- Week 4: 100% capital (if Sharpe >1.0)

Safety: If any day loses >2%, drop back to previous level.

Usage:
    from src.live_trading.capital_manager import CapitalRampUpManager
    
    manager = CapitalRampUpManager(total_capital=100000)
    
    # After each trading day
    new_level = await manager.evaluate_ramp_up(daily_return=0.02)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
from enum import Enum

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class RampDirection(Enum):
    """Ramp direction"""
    UP = "up"
    DOWN = "down"
    HOLD = "hold"


@dataclass
class RampUpEvent:
    """Record of ramp-up/down event"""
    timestamp: datetime
    old_level: float
    new_level: float
    direction: RampDirection
    reason: str
    daily_return: float
    cumulative_return: float


@dataclass
class RampUpStats:
    """Ramp-up statistics"""
    current_level: float
    current_capital: float
    consecutive_profitable_days: int
    total_days_at_level: int
    cumulative_return: float
    sharpe_estimate: float
    can_ramp_up: bool
    next_level: Optional[float]
    days_until_eligible: int


class CapitalRampUpManager:
    """
    Gradually increase trading capital based on performance.
    
    Schedule:
    - Level 1: 10% capital (initial)
    - Level 2: 25% capital (if 3+ profitable days)
    - Level 3: 50% capital (if cumulative profitable)
    - Level 4: 75% capital (if Sharpe > 0.75)
    - Level 5: 100% capital (if Sharpe > 1.0)
    
    Safety rules:
    - If any day loses >2%, drop back to previous level
    - Minimum 3 profitable days before advancing
    - Cumulative return must be positive
    - Sharpe ratio gates for higher levels
    
    Attributes:
        total_capital: Total capital available
        current_level: Current allocation percentage
        ramp_schedule: List of allocation levels
        consecutive_profitable_days: Days profitable in a row
        required_profitable_days: Days needed before ramp-up
    """
    
    DEFAULT_RAMP_SCHEDULE = [0.10, 0.25, 0.50, 0.75, 1.00]
    DEFAULT_REQUIRED_PROFITABLE_DAYS = 3
    DEFAULT_RAMP_DOWN_THRESHOLD = -0.02  # -2%
    DEFAULT_MIN_SHARPE_FOR_50 = 0.5
    DEFAULT_MIN_SHARPE_FOR_75 = 0.75
    DEFAULT_MIN_SHARPE_FOR_100 = 1.0
    
    def __init__(
        self,
        total_capital: Optional[float] = None,
        initial_capital: Optional[float] = None,
        ramp_schedule: Optional[List[float]] = None,
        required_profitable_days: int = DEFAULT_REQUIRED_PROFITABLE_DAYS,
        ramp_down_threshold: float = DEFAULT_RAMP_DOWN_THRESHOLD,
        alerting_service: Optional[object] = None,
    ):
        """
        Initialize capital ramp-up manager.
        
        Args:
            total_capital: Total capital available for trading
            ramp_schedule: Custom ramp-up schedule (default: [0.10, 0.25, 0.50, 0.75, 1.00])
            required_profitable_days: Consecutive profitable days required before ramp-up
            ramp_down_threshold: Daily return threshold for ramp-down
            alerting_service: Optional alerting service for notifications
        """
        # Accept either `total_capital` (existing callers) or `initial_capital`
        if total_capital is None and initial_capital is not None:
            total_capital = initial_capital

        if total_capital is None:
            raise ValueError("total_capital (or initial_capital) must be provided")

        self.total_capital = total_capital
        self.ramp_schedule = ramp_schedule or self.DEFAULT_RAMP_SCHEDULE
        self.required_profitable_days = required_profitable_days
        self.ramp_down_threshold = ramp_down_threshold
        self.alerting = alerting_service
        
        # Current state
        self.current_level = self.ramp_schedule[0]
        self.consecutive_profitable_days = 0
        self.total_days_at_level = 0
        
        # Performance tracking
        self.daily_returns: List[float] = []
        self.cumulative_return = 0.0
        
        # History
        self.ramp_events: List[RampUpEvent] = []
        
        logger.info(
            "capital_ramp_up_manager_initialized",
            total_capital=total_capital,
            starting_level=self.current_level,
            schedule=self.ramp_schedule,
        )
    
    def get_current_capital(self) -> float:
        """Get current allocated capital"""
        return self.total_capital * self.current_level
    
    def get_current_level(self) -> float:
        """Get current allocation level (0-1)"""
        return self.current_level
    
    async def evaluate_ramp_up(self, daily_return: float) -> float:
        """
        Evaluate if should ramp up/down capital based on daily return.
        
        Args:
            daily_return: Today's return (e.g., 0.02 for 2%)
            
        Returns:
            New capital allocation level (0-1)
        """
        self.daily_returns.append(daily_return)
        self.cumulative_return = (1 + self.cumulative_return) * (1 + daily_return) - 1
        self.total_days_at_level += 1
        
        logger.info(
            "evaluating_ramp_up",
            daily_return=daily_return,
            cumulative_return=self.cumulative_return,
            current_level=self.current_level,
        )
        
        # Check for ramp-down trigger
        if daily_return < self.ramp_down_threshold:
            logger.warning(
                "ramp_down_triggered",
                daily_return=daily_return,
                threshold=self.ramp_down_threshold,
            )
            await self._ramp_down(f"Daily loss {daily_return*100:.1f}% exceeded threshold")
            self.consecutive_profitable_days = 0
            return self.current_level
        
        # Track profitability
        if daily_return > 0:
            self.consecutive_profitable_days += 1
        else:
            self.consecutive_profitable_days = 0
        
        # Check if eligible for ramp-up
        if self._can_ramp_up():
            current_idx = self.ramp_schedule.index(self.current_level)
            
            if current_idx < len(self.ramp_schedule) - 1:
                next_level = self.ramp_schedule[current_idx + 1]
                
                # Check additional requirements for higher levels
                if self._meets_level_requirements(next_level):
                    await self._ramp_up(next_level)
                    self.consecutive_profitable_days = 0  # Reset counter
                    self.total_days_at_level = 0
        
        return self.current_level
    
    def _can_ramp_up(self) -> bool:
        """Check if basic ramp-up conditions are met"""
        # Need consecutive profitable days
        if self.consecutive_profitable_days < self.required_profitable_days:
            return False
        
        # Cumulative return must be positive
        if self.cumulative_return <= 0:
            return False
        
        # Must already be at a level in schedule
        if self.current_level not in self.ramp_schedule:
            return False
        
        # Can't exceed maximum level
        if self.current_level >= self.ramp_schedule[-1]:
            return False
        
        return True
    
    def _meets_level_requirements(self, target_level: float) -> bool:
        """Check if additional requirements for target level are met"""
        sharpe = self._calculate_sharpe()
        
        # Level-specific requirements
        if target_level >= 0.50 and sharpe < self.DEFAULT_MIN_SHARPE_FOR_50:
            logger.info(
                "sharpe_requirement_not_met",
                target_level=target_level,
                current_sharpe=sharpe,
                required_sharpe=self.DEFAULT_MIN_SHARPE_FOR_50,
            )
            return False
        
        if target_level >= 0.75 and sharpe < self.DEFAULT_MIN_SHARPE_FOR_75:
            logger.info(
                "sharpe_requirement_not_met",
                target_level=target_level,
                current_sharpe=sharpe,
                required_sharpe=self.DEFAULT_MIN_SHARPE_FOR_75,
            )
            return False
        
        if target_level >= 1.00 and sharpe < self.DEFAULT_MIN_SHARPE_FOR_100:
            logger.info(
                "sharpe_requirement_not_met",
                target_level=target_level,
                current_sharpe=sharpe,
                required_sharpe=self.DEFAULT_MIN_SHARPE_FOR_100,
            )
            return False
        
        return True
    
    def _calculate_sharpe(self, risk_free_rate: float = 0.05) -> float:
        """Calculate annualized Sharpe ratio from daily returns"""
        if len(self.daily_returns) < 5:
            return 0.0
        
        import numpy as np
        
        returns = np.array(self.daily_returns)
        mean_return = np.mean(returns)
        std_return = np.std(returns, ddof=1)
        
        if std_return == 0:
            return 0.0
        
        # Annualize
        daily_rf = risk_free_rate / 252
        excess_return = mean_return - daily_rf
        
        # Annualized Sharpe
        sharpe = (excess_return / std_return) * np.sqrt(252)
        
        return sharpe
    
    async def _ramp_up(self, new_level: float) -> None:
        """Increase capital allocation"""
        old_level = self.current_level
        self.current_level = new_level
        
        event = RampUpEvent(
            timestamp=datetime.now(timezone.utc),
            old_level=old_level,
            new_level=new_level,
            direction=RampDirection.UP,
            reason=f"Met requirements: {self.consecutive_profitable_days} profitable days",
            daily_return=self.daily_returns[-1] if self.daily_returns else 0,
            cumulative_return=self.cumulative_return,
        )
        self.ramp_events.append(event)
        
        logger.info(
            "capital_ramp_up",
            old_level=old_level,
            new_level=new_level,
            old_capital=self.total_capital * old_level,
            new_capital=self.total_capital * new_level,
        )
        
        if self.alerting:
            await self.alerting.send_info_alert(
                title="📈 Capital Ramp-Up",
                message=(
                    f"Increasing capital allocation from {old_level*100:.0f}% to {new_level*100:.0f}%\n"
                    f"New capital: ${self.total_capital * new_level:,.2f}\n"
                    f"Consecutive profitable days: {self.consecutive_profitable_days}"
                ),
                channels=['slack', 'email'],
            )
    
    async def _ramp_down(self, reason: str) -> None:
        """Decrease capital allocation due to losses"""
        current_idx = self.ramp_schedule.index(self.current_level)
        
        if current_idx > 0:
            new_level = self.ramp_schedule[current_idx - 1]
            old_level = self.current_level
            self.current_level = new_level
            
            event = RampUpEvent(
                timestamp=datetime.now(timezone.utc),
                old_level=old_level,
                new_level=new_level,
                direction=RampDirection.DOWN,
                reason=reason,
                daily_return=self.daily_returns[-1] if self.daily_returns else 0,
                cumulative_return=self.cumulative_return,
            )
            self.ramp_events.append(event)
            
            logger.warning(
                "capital_ramp_down",
                old_level=old_level,
                new_level=new_level,
                reason=reason,
            )
            
            if self.alerting:
                await self.alerting.send_warning_alert(
                    title="📉 Capital Ramp-Down",
                    message=(
                        f"Decreasing capital from {old_level*100:.0f}% to {new_level*100:.0f}%\n"
                        f"Reason: {reason}\n"
                        f"New capital: ${self.total_capital * new_level:,.2f}"
                    ),
                    channels=['slack', 'email', 'sms'],
                )
        else:
            logger.warning("already_at_minimum_level_cannot_ramp_down")
    
    async def manual_ramp_up(self) -> bool:
        """Manually trigger ramp-up (bypasses profit requirements)"""
        current_idx = self.ramp_schedule.index(self.current_level)
        
        if current_idx < len(self.ramp_schedule) - 1:
            new_level = self.ramp_schedule[current_idx + 1]
            
            event = RampUpEvent(
                timestamp=datetime.now(timezone.utc),
                old_level=self.current_level,
                new_level=new_level,
                direction=RampDirection.UP,
                reason="Manual override",
                daily_return=0,
                cumulative_return=self.cumulative_return,
            )
            
            self.current_level = new_level
            self.ramp_events.append(event)
            
            logger.info("manual_ramp_up", new_level=new_level)
            return True
        
        return False
    
    async def manual_ramp_down(self) -> bool:
        """Manually trigger ramp-down"""
        current_idx = self.ramp_schedule.index(self.current_level)
        
        if current_idx > 0:
            new_level = self.ramp_schedule[current_idx - 1]
            
            event = RampUpEvent(
                timestamp=datetime.now(timezone.utc),
                old_level=self.current_level,
                new_level=new_level,
                direction=RampDirection.DOWN,
                reason="Manual override",
                daily_return=0,
                cumulative_return=self.cumulative_return,
            )
            
            self.current_level = new_level
            self.ramp_events.append(event)
            
            logger.info("manual_ramp_down", new_level=new_level)
            return True
        
        return False
    
    def reset(self) -> None:
        """Reset to initial state"""
        self.current_level = self.ramp_schedule[0]
        self.consecutive_profitable_days = 0
        self.total_days_at_level = 0
        self.daily_returns = []
        self.cumulative_return = 0.0
        self.ramp_events = []
        
        logger.info("capital_manager_reset")
    
    def get_stats(self) -> RampUpStats:
        """Get current ramp-up statistics"""
        current_idx = self.ramp_schedule.index(self.current_level)
        
        if current_idx < len(self.ramp_schedule) - 1:
            next_level = self.ramp_schedule[current_idx + 1]
            days_until = max(0, self.required_profitable_days - self.consecutive_profitable_days)
        else:
            next_level = None
            days_until = 0
        
        sharpe = self._calculate_sharpe()
        can_ramp = self._can_ramp_up() and (next_level is None or self._meets_level_requirements(next_level))
        
        return RampUpStats(
            current_level=self.current_level,
            current_capital=self.get_current_capital(),
            consecutive_profitable_days=self.consecutive_profitable_days,
            total_days_at_level=self.total_days_at_level,
            cumulative_return=self.cumulative_return,
            sharpe_estimate=sharpe,
            can_ramp_up=can_ramp,
            next_level=next_level,
            days_until_eligible=days_until,
        )
    
    def get_history(self) -> List[RampUpEvent]:
        """Get ramp-up/down history"""
        return self.ramp_events.copy()
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary"""
        stats = self.get_stats()
        return {
            'current_level': stats.current_level,
            'current_capital': stats.current_capital,
            'consecutive_profitable_days': stats.consecutive_profitable_days,
            'total_days_at_level': stats.total_days_at_level,
            'cumulative_return': stats.cumulative_return,
            'sharpe_estimate': stats.sharpe_estimate,
            'can_ramp_up': stats.can_ramp_up,
            'next_level': stats.next_level,
            'days_until_eligible': stats.days_until_eligible,
            'total_capital': self.total_capital,
            'ramp_schedule': self.ramp_schedule,
            'event_count': len(self.ramp_events),
        }
