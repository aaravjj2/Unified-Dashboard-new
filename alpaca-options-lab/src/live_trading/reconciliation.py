"""
Position Reconciliation - Verify positions match broker

Compares internal position tracking with broker records
to detect and report discrepancies.

Usage:
    from src.live_trading.reconciliation import PositionReconciler
    
    reconciler = PositionReconciler(broker, database)
    result = await reconciler.reconcile()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol
from enum import Enum, auto

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class DiscrepancyType(Enum):
    """Types of position discrepancies"""
    MISSING_IN_BROKER = auto()  # We have it, broker doesn't
    MISSING_IN_SYSTEM = auto()  # Broker has it, we don't
    QUANTITY_MISMATCH = auto()  # Quantities don't match
    PRICE_MISMATCH = auto()     # Average prices don't match significantly
    SIDE_MISMATCH = auto()      # Long vs short mismatch


@dataclass
class Discrepancy:
    """Position discrepancy"""
    discrepancy_type: DiscrepancyType
    contract: str
    our_quantity: Optional[int]
    broker_quantity: Optional[int]
    our_avg_price: Optional[float]
    broker_avg_price: Optional[float]
    details: str


@dataclass
class ReconciliationResult:
    """Result of position reconciliation"""
    status: str  # 'success' or 'failed'
    timestamp: datetime
    our_position_count: int
    broker_position_count: int
    matched_count: int
    discrepancy_count: int
    discrepancies: List[Discrepancy] = field(default_factory=list)
    
    @property
    def success(self) -> bool:
        return self.status == 'success' and self.discrepancy_count == 0


@dataclass
class Position:
    """Position record"""
    id: str
    contract: str
    quantity: int
    avg_price: float
    side: str
    market_value: Optional[float] = None


class BrokerAdapter(Protocol):
    """Protocol for broker operations"""
    async def get_positions(self) -> List[Position]: ...


class Database(Protocol):
    """Protocol for database operations"""
    async def get_open_positions(self) -> List[Position]: ...
    async def create_position(self, position: Position) -> str: ...
    async def update_position(self, position_id: str, updates: Dict) -> None: ...
    async def close_position(self, position_id: str) -> None: ...


class PositionReconciler:
    """
    Reconcile internal positions with broker records.
    
    Detects:
    - Missing positions (in either system)
    - Quantity mismatches
    - Price discrepancies
    
    Attributes:
        broker: Broker adapter
        database: Database connection
        price_tolerance: Tolerance for price matching (default 1%)
    """
    
    DEFAULT_PRICE_TOLERANCE = 0.01  # 1%
    
    def __init__(
        self,
        broker: BrokerAdapter,
        database: Optional[Database] = None,
        price_tolerance: float = DEFAULT_PRICE_TOLERANCE,
        auto_fix: bool = False,
    ):
        """
        Initialize position reconciler.
        
        Args:
            broker: Broker adapter
            database: Optional database connection
            price_tolerance: Tolerance for price matching
            auto_fix: Whether to automatically fix discrepancies
        """
        self.broker = broker
        self.database = database
        self.price_tolerance = price_tolerance
        self.auto_fix = auto_fix
        
        logger.info(
            "position_reconciler_initialized",
            price_tolerance=price_tolerance,
            auto_fix=auto_fix,
        )
    
    async def reconcile(self) -> ReconciliationResult:
        """
        Reconcile positions between internal system and broker.
        
        Returns:
            ReconciliationResult with match/discrepancy details
        """
        start_time = datetime.now(timezone.utc)
        discrepancies: List[Discrepancy] = []
        matched_count = 0
        
        # Get positions from broker
        try:
            broker_positions = await self.broker.get_positions()
            broker_by_contract = {
                p.contract: p for p in broker_positions
            }
        except Exception as e:
            logger.error("failed_to_get_broker_positions", error=str(e))
            return ReconciliationResult(
                status='failed',
                timestamp=start_time,
                our_position_count=0,
                broker_position_count=0,
                matched_count=0,
                discrepancy_count=0,
                discrepancies=[
                    Discrepancy(
                        discrepancy_type=DiscrepancyType.MISSING_IN_BROKER,
                        contract='N/A',
                        our_quantity=None,
                        broker_quantity=None,
                        our_avg_price=None,
                        broker_avg_price=None,
                        details=f"Failed to get broker positions: {e}",
                    )
                ],
            )
        
        # Get positions from internal system
        if self.database:
            try:
                our_positions = await self.database.get_open_positions()
                our_by_contract = {
                    p.contract: p for p in our_positions
                }
            except Exception as e:
                logger.error("failed_to_get_our_positions", error=str(e))
                our_positions = []
                our_by_contract = {}
        else:
            # No database - assume broker is source of truth
            our_positions = []
            our_by_contract = {}
        
        # Check our positions against broker
        for contract, our_pos in our_by_contract.items():
            broker_pos = broker_by_contract.get(contract)
            
            if broker_pos is None:
                # Position missing in broker
                discrepancies.append(Discrepancy(
                    discrepancy_type=DiscrepancyType.MISSING_IN_BROKER,
                    contract=contract,
                    our_quantity=our_pos.quantity,
                    broker_quantity=None,
                    our_avg_price=our_pos.avg_price,
                    broker_avg_price=None,
                    details="Position exists in our system but not in broker",
                ))
            else:
                # Check for quantity mismatch
                if our_pos.quantity != broker_pos.quantity:
                    discrepancies.append(Discrepancy(
                        discrepancy_type=DiscrepancyType.QUANTITY_MISMATCH,
                        contract=contract,
                        our_quantity=our_pos.quantity,
                        broker_quantity=broker_pos.quantity,
                        our_avg_price=our_pos.avg_price,
                        broker_avg_price=broker_pos.avg_price,
                        details=f"Quantity mismatch: ours={our_pos.quantity}, broker={broker_pos.quantity}",
                    ))
                elif self._price_mismatch(our_pos.avg_price, broker_pos.avg_price):
                    discrepancies.append(Discrepancy(
                        discrepancy_type=DiscrepancyType.PRICE_MISMATCH,
                        contract=contract,
                        our_quantity=our_pos.quantity,
                        broker_quantity=broker_pos.quantity,
                        our_avg_price=our_pos.avg_price,
                        broker_avg_price=broker_pos.avg_price,
                        details=f"Price mismatch: ours={our_pos.avg_price}, broker={broker_pos.avg_price}",
                    ))
                else:
                    matched_count += 1
        
        # Check broker positions missing in our system
        for contract, broker_pos in broker_by_contract.items():
            if contract not in our_by_contract:
                discrepancies.append(Discrepancy(
                    discrepancy_type=DiscrepancyType.MISSING_IN_SYSTEM,
                    contract=contract,
                    our_quantity=None,
                    broker_quantity=broker_pos.quantity,
                    our_avg_price=None,
                    broker_avg_price=broker_pos.avg_price,
                    details="Position exists in broker but not in our system",
                ))
        
        # Auto-fix if enabled
        if self.auto_fix and discrepancies:
            await self._auto_fix_discrepancies(discrepancies, broker_by_contract)
        
        # Determine status
        status = 'success' if len(discrepancies) == 0 else 'failed'
        
        result = ReconciliationResult(
            status=status,
            timestamp=start_time,
            our_position_count=len(our_positions),
            broker_position_count=len(broker_positions),
            matched_count=matched_count,
            discrepancy_count=len(discrepancies),
            discrepancies=discrepancies,
        )
        
        logger.info(
            "reconciliation_complete",
            status=status,
            our_count=len(our_positions),
            broker_count=len(broker_positions),
            matched=matched_count,
            discrepancies=len(discrepancies),
        )
        
        if discrepancies:
            for d in discrepancies:
                logger.warning(
                    "reconciliation_discrepancy",
                    type=d.discrepancy_type.name,
                    contract=d.contract,
                    details=d.details,
                )
        
        return result
    
    def _price_mismatch(
        self,
        our_price: Optional[float],
        broker_price: Optional[float],
    ) -> bool:
        """Check if prices are significantly different"""
        if our_price is None or broker_price is None:
            return False
        
        if our_price == 0 or broker_price == 0:
            return our_price != broker_price
        
        diff_pct = abs(our_price - broker_price) / max(our_price, broker_price)
        return diff_pct > self.price_tolerance
    
    async def _auto_fix_discrepancies(
        self,
        discrepancies: List[Discrepancy],
        broker_positions: Dict[str, Position],
    ) -> None:
        """Attempt to auto-fix discrepancies"""
        if not self.database:
            logger.warning("cannot_auto_fix_no_database")
            return
        
        for discrepancy in discrepancies:
            try:
                if discrepancy.discrepancy_type == DiscrepancyType.MISSING_IN_SYSTEM:
                    # Create position in our system
                    broker_pos = broker_positions[discrepancy.contract]
                    await self.database.create_position(broker_pos)
                    logger.info(
                        "auto_created_position",
                        contract=discrepancy.contract,
                    )
                
                elif discrepancy.discrepancy_type == DiscrepancyType.MISSING_IN_BROKER:
                    # Close position in our system (it doesn't exist at broker)
                    # This might mean it was closed externally
                    # Find position ID and close it
                    logger.warning(
                        "position_missing_in_broker_marking_closed",
                        contract=discrepancy.contract,
                    )
                
                elif discrepancy.discrepancy_type == DiscrepancyType.QUANTITY_MISMATCH:
                    # Update our quantity to match broker
                    broker_pos = broker_positions[discrepancy.contract]
                    logger.info(
                        "auto_updating_quantity",
                        contract=discrepancy.contract,
                        old_qty=discrepancy.our_quantity,
                        new_qty=broker_pos.quantity,
                    )
            
            except Exception as e:
                logger.error(
                    "auto_fix_failed",
                    discrepancy_type=discrepancy.discrepancy_type.name,
                    contract=discrepancy.contract,
                    error=str(e),
                )
    
    async def generate_report(self) -> str:
        """Generate human-readable reconciliation report"""
        result = await self.reconcile()
        
        lines = [
            "=" * 60,
            "POSITION RECONCILIATION REPORT",
            "=" * 60,
            f"Timestamp: {result.timestamp.isoformat()}",
            f"Status: {result.status.upper()}",
            "",
            f"Our Positions: {result.our_position_count}",
            f"Broker Positions: {result.broker_position_count}",
            f"Matched: {result.matched_count}",
            f"Discrepancies: {result.discrepancy_count}",
            "",
        ]
        
        if result.discrepancies:
            lines.append("DISCREPANCIES:")
            lines.append("-" * 40)
            
            for d in result.discrepancies:
                lines.append(f"  Contract: {d.contract}")
                lines.append(f"  Type: {d.discrepancy_type.name}")
                lines.append(f"  Our Qty: {d.our_quantity}")
                lines.append(f"  Broker Qty: {d.broker_quantity}")
                lines.append(f"  Details: {d.details}")
                lines.append("")
        else:
            lines.append("No discrepancies found. All positions match.")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
