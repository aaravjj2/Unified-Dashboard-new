"""
Kill Switch - Emergency Trading Halt

Provides emergency shutdown capabilities:
- Immediate position liquidation
- Trading halt
- Multi-channel alerts
- Audit trail

Usage:
    from src.live_trading.kill_switch import KillSwitch
    
    kill_switch = KillSwitch(broker, alerting)
    await kill_switch.activate("market_crash")
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol
from enum import Enum, auto

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class KillSwitchReason(Enum):
    """Reasons for kill switch activation"""
    DAILY_LOSS_LIMIT = auto()
    BROKER_DISCONNECTED = auto()
    DATA_FEED_STALE = auto()
    RISK_LIMIT_BREACH = auto()
    MANUAL_ACTIVATION = auto()
    UNEXPECTED_ERROR = auto()
    MARKET_CIRCUIT_BREAKER = auto()
    POSITION_RECONCILIATION_FAILED = auto()


@dataclass
class KillSwitchEvent:
    """Kill switch activation event"""
    timestamp: datetime
    reason: KillSwitchReason
    details: str
    positions_closed: int
    positions_failed: int
    time_to_close_ms: float
    final_pnl: Optional[float] = None


@dataclass
class PositionCloseResult:
    """Result of closing a position"""
    position_id: str
    contract: str
    success: bool
    fill_price: Optional[float] = None
    error: Optional[str] = None
    time_ms: float = 0


class BrokerAdapter(Protocol):
    """Protocol for broker operations"""
    async def get_positions(self) -> List[Any]: ...
    async def close_position_market(self, position_id: str) -> str: ...
    async def cancel_all_orders(self) -> int: ...


class AlertingService(Protocol):
    """Protocol for alerting"""
    async def send_critical_alert(
        self, 
        title: str, 
        message: str, 
        channels: List[str]
    ) -> None: ...


class KillSwitch:
    """
    Emergency trading halt with position liquidation.
    
    Features:
    - Immediate activation (no delays)
    - Parallel position closing for speed
    - Multi-channel alerts (Slack, Email, SMS)
    - Complete audit trail
    - Irreversible (requires manual restart)
    
    Attributes:
        broker: Broker adapter for order execution
        alerting: Alerting service
        is_active: Whether kill switch is currently active
        activation_event: Details of the activation
    """
    
    # Maximum time to wait for all positions to close
    MAX_CLOSE_TIMEOUT = 30  # seconds
    
    # Concurrent position close limit
    MAX_CONCURRENT_CLOSES = 10
    
    def __init__(
        self,
        broker: Optional[BrokerAdapter] = None,
        alerting: Optional[AlertingService] = None,
        max_close_timeout: int = MAX_CLOSE_TIMEOUT,
    ):
        """
        Initialize kill switch.
        
        Args:
            broker: Broker adapter
            alerting: Optional alerting service
            max_close_timeout: Maximum seconds to wait for position closing
        """
        self.broker = broker
        self.alerting = alerting
        self.max_close_timeout = max_close_timeout
        
        # State
        self.is_active = False
        self.activation_event: Optional[KillSwitchEvent] = None
        self.close_results: List[PositionCloseResult] = []
        
        logger.info("kill_switch_initialized")
    
    async def activate(
        self,
        reason: KillSwitchReason,
        details: str = "",
    ) -> KillSwitchEvent:
        """
        Activate kill switch - EMERGENCY STOP.
        
        This will:
        1. Cancel all pending orders
        2. Close all open positions at market
        3. Send critical alerts
        4. Create audit record
        
        Args:
            reason: Reason for activation
            details: Additional details
            
        Returns:
            KillSwitchEvent with activation details
        """
        if self.is_active:
            logger.warning("kill_switch_already_active")
            return self.activation_event
        
        start_time = datetime.now(timezone.utc)
        logger.critical(
            "kill_switch_activating",
            reason=reason.name,
            details=details,
        )
        
        self.is_active = True
        
        # Send immediate alert
        if self.alerting:
            await self._send_activation_alert(reason, details)
        
        # Cancel all pending orders first
        try:
            cancelled_count = await self.broker.cancel_all_orders()
            logger.info("pending_orders_cancelled", count=cancelled_count)
        except Exception as e:
            logger.error("failed_to_cancel_orders", error=str(e))
        
        # Get all positions and close them
        positions_closed = 0
        positions_failed = 0
        self.close_results = []
        
        try:
            positions = await self.broker.get_positions()
            logger.info("closing_positions", count=len(positions))
            
            if positions:
                # Close positions in parallel with limit
                semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_CLOSES)
                
                async def close_with_semaphore(position):
                    async with semaphore:
                        return await self._close_position(position)
                
                # Create tasks for all positions
                tasks = [close_with_semaphore(p) for p in positions]
                
                # Wait with timeout
                try:
                    results = await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True),
                        timeout=self.max_close_timeout,
                    )
                    
                    for result in results:
                        if isinstance(result, PositionCloseResult):
                            self.close_results.append(result)
                            if result.success:
                                positions_closed += 1
                            else:
                                positions_failed += 1
                        elif isinstance(result, Exception):
                            positions_failed += 1
                            logger.error("position_close_exception", error=str(result))
                
                except asyncio.TimeoutError:
                    logger.error(
                        "position_close_timeout",
                        timeout=self.max_close_timeout,
                    )
                    positions_failed = len(positions) - positions_closed
        
        except Exception as e:
            logger.error("failed_to_get_positions", error=str(e))
        
        # Calculate time taken
        end_time = datetime.now(timezone.utc)
        time_to_close_ms = (end_time - start_time).total_seconds() * 1000
        
        # Create event
        self.activation_event = KillSwitchEvent(
            timestamp=start_time,
            reason=reason,
            details=details,
            positions_closed=positions_closed,
            positions_failed=positions_failed,
            time_to_close_ms=time_to_close_ms,
        )
        
        logger.critical(
            "kill_switch_activated",
            reason=reason.name,
            positions_closed=positions_closed,
            positions_failed=positions_failed,
            time_ms=time_to_close_ms,
        )
        
        # Send completion alert
        if self.alerting:
            await self._send_completion_alert()
        
        return self.activation_event
    
    async def _close_position(self, position: Any) -> PositionCloseResult:
        """Close a single position at market"""
        start = datetime.now(timezone.utc)
        
        try:
            order_id = await self.broker.close_position_market(position.id)
            
            elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            
            logger.info(
                "position_closed",
                position_id=position.id,
                contract=getattr(position, 'contract', 'unknown'),
                order_id=order_id,
                time_ms=elapsed,
            )
            
            return PositionCloseResult(
                position_id=position.id,
                contract=getattr(position, 'contract', 'unknown'),
                success=True,
                time_ms=elapsed,
            )
        
        except Exception as e:
            elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            
            logger.error(
                "position_close_failed",
                position_id=position.id,
                error=str(e),
            )
            
            return PositionCloseResult(
                position_id=position.id,
                contract=getattr(position, 'contract', 'unknown'),
                success=False,
                error=str(e),
                time_ms=elapsed,
            )
    
    async def _send_activation_alert(
        self,
        reason: KillSwitchReason,
        details: str,
    ) -> None:
        """Send activation alert"""
        try:
            await self.alerting.send_critical_alert(
                title="🚨 KILL SWITCH ACTIVATED",
                message=(
                    f"Emergency trading halt initiated.\n\n"
                    f"**Reason:** {reason.name}\n"
                    f"**Details:** {details}\n"
                    f"**Time:** {datetime.now(timezone.utc).isoformat()}\n\n"
                    f"All positions are being closed at market."
                ),
                channels=['slack', 'email', 'sms'],
            )
        except Exception as e:
            logger.error("failed_to_send_activation_alert", error=str(e))
    
    async def _send_completion_alert(self) -> None:
        """Send completion alert"""
        if not self.activation_event:
            return
        
        try:
            event = self.activation_event
            
            failed_positions = [
                r for r in self.close_results if not r.success
            ]
            
            message = (
                f"Kill switch execution complete.\n\n"
                f"**Positions Closed:** {event.positions_closed}\n"
                f"**Positions Failed:** {event.positions_failed}\n"
                f"**Time to Close:** {event.time_to_close_ms:.0f}ms\n"
            )
            
            if failed_positions:
                message += "\n**Failed Positions:**\n"
                for fp in failed_positions[:5]:  # Limit to 5
                    message += f"- {fp.contract}: {fp.error}\n"
            
            await self.alerting.send_critical_alert(
                title="🚨 KILL SWITCH COMPLETE",
                message=message,
                channels=['slack', 'email'],
            )
        except Exception as e:
            logger.error("failed_to_send_completion_alert", error=str(e))
    
    def reset(self) -> None:
        """
        Reset kill switch (allows trading to resume).
        
        WARNING: This should only be called after thorough investigation
        of why the kill switch was activated.
        """
        logger.warning("kill_switch_reset_manually")
        self.is_active = False
        self.activation_event = None
        self.close_results = []
    
    def get_status(self) -> Dict[str, Any]:
        """Get kill switch status"""
        return {
            'is_active': self.is_active,
            'activation_event': (
                {
                    'timestamp': self.activation_event.timestamp.isoformat(),
                    'reason': self.activation_event.reason.name,
                    'details': self.activation_event.details,
                    'positions_closed': self.activation_event.positions_closed,
                    'positions_failed': self.activation_event.positions_failed,
                    'time_to_close_ms': self.activation_event.time_to_close_ms,
                }
                if self.activation_event else None
            ),
            'close_results_count': len(self.close_results),
        }
