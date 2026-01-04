"""
Alpaca Options Lab - Rolling Engine

Production-grade option roll automation with:
- Strategy-based roll identification
- Optimal roll timing detection
- Multi-leg roll execution
- P&L impact analysis

Roll Types:
1. Calendar Roll: Same strike, new expiration
2. Diagonal Roll: New strike + new expiration
3. Strike Roll: New strike, same expiration
4. Width Roll: Spread width adjustment

Roll Triggers:
- Time-based: DTE threshold reached
- Profit-based: Target profit achieved
- Defense: Position threatened (delta breach)
- Dividend: Roll to avoid assignment

Usage:
    from src.lifecycle.rolling import RollingEngine, get_rolling_engine
    
    engine = get_rolling_engine()
    
    # Find roll opportunities
    opportunities = engine.find_roll_opportunities(
        position=position,
        spot=152.50,
        option_chain=chain,
    )
    
    # Execute best roll
    if opportunities:
        result = await engine.execute_roll(opportunities[0])
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from src.data.symbology import (
    OptionSymbol,
    OptionType,
    build_osi_symbol,
    parse_osi_symbol,
)
from src.lifecycle.fsm import (
    Position,
    PositionEvent,
    PositionFSM,
    PositionState,
    get_position_manager,
)
from src.pricing.black_scholes import price_option
from src.utils.config import get_config
from src.utils.logging_config import get_logger
from src.utils.metrics import get_metrics, increment_counter

logger = get_logger(__name__)
metrics = get_metrics()


class RollStrategy(Enum):
    """Types of option rolls."""
    CALENDAR = "calendar"       # Same strike, new expiration
    DIAGONAL = "diagonal"       # New strike + new expiration  
    STRIKE = "strike"           # New strike, same expiration
    WIDTH = "width"             # Spread width adjustment
    DEFENSIVE = "defensive"     # Emergency roll for rescue


class RollTrigger(Enum):
    """Reasons to initiate a roll."""
    TIME_DECAY = "time_decay"           # DTE threshold reached
    PROFIT_TARGET = "profit_target"     # Target profit achieved
    DELTA_BREACH = "delta_breach"       # Delta out of bounds
    GAMMA_RISK = "gamma_risk"           # Too close to strike near expiry
    DIVIDEND = "dividend"               # Avoid assignment before ex-div
    VOLATILITY = "volatility"           # IV crush/spike opportunity
    MANUAL = "manual"                   # User-initiated


@dataclass
class RollConfig:
    """Configuration for roll identification."""
    # Time-based triggers
    min_dte_to_roll: int = 21       # Start considering rolls at 21 DTE
    target_dte_after_roll: int = 45  # Target DTE for new position
    
    # Profit triggers
    profit_take_pct: float = 0.50   # Take profit at 50% of max
    
    # Delta management
    max_delta_short_call: float = 0.30  # Roll if short call delta > 0.30
    max_delta_short_put: float = -0.30  # Roll if short put delta < -0.30
    
    # Credit requirements
    min_credit_to_roll: float = 0.00    # Minimum credit to accept
    max_debit_to_roll: float = -0.50    # Maximum debit to accept
    
    # Strike selection
    target_delta: float = 0.30      # Target delta for new position
    delta_tolerance: float = 0.05   # Delta tolerance
    
    # Risk filters
    max_gamma_exposure: float = 0.10    # Max gamma to avoid
    min_time_value_pct: float = 0.20    # Min time value %


@dataclass
class OptionQuote:
    """Simplified option quote for roll analysis."""
    symbol: str
    bid: float
    ask: float
    mid: float
    delta: float
    gamma: float
    theta: float
    vega: float
    iv: float
    volume: int = 0
    open_interest: int = 0
    
    @property
    def spread(self) -> float:
        """Bid-ask spread."""
        return self.ask - self.bid
    
    @property
    def spread_pct(self) -> float:
        """Spread as percentage of mid."""
        return (self.spread / self.mid * 100) if self.mid > 0 else 100.0


@dataclass
class RollOpportunity:
    """
    Represents a potential roll opportunity.
    
    Contains full analysis of rolling from current position
    to new position including P&L impact.
    """
    id: str
    strategy: RollStrategy
    trigger: RollTrigger
    
    # Current position
    current_symbol: str
    current_price: float
    current_qty: int
    
    # New position
    new_symbol: str
    new_price: float
    new_strike: float
    new_expiry: date
    
    # Greeks comparison
    current_delta: float
    new_delta: float
    current_theta: float
    new_theta: float
    
    # P&L impact
    credit_debit: float  # Positive = credit, Negative = debit
    net_premium: float   # Total premium collected/paid
    breakeven_move: float  # % move to breakeven on debit
    
    # Risk metrics
    max_loss_change: float  # Change in max loss
    probability_profit: float  # Estimated P(profit) change
    
    # Scoring
    score: float = 0.0  # Composite score (higher = better)
    rationale: str = ""
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "strategy": self.strategy.value,
            "trigger": self.trigger.value,
            "current_symbol": self.current_symbol,
            "new_symbol": self.new_symbol,
            "credit_debit": round(self.credit_debit, 2),
            "net_premium": round(self.net_premium, 2),
            "current_delta": round(self.current_delta, 3),
            "new_delta": round(self.new_delta, 3),
            "score": round(self.score, 2),
            "rationale": self.rationale,
        }


@dataclass
class RollResult:
    """Result of executing a roll."""
    success: bool
    opportunity: RollOpportunity
    
    # Execution details
    close_fill_price: Optional[float] = None
    open_fill_price: Optional[float] = None
    actual_credit_debit: Optional[float] = None
    
    # New position
    new_position_id: Optional[str] = None
    
    # Errors
    error: Optional[str] = None
    
    # Timing
    executed_at: Optional[datetime] = None
    execution_time_ms: Optional[float] = None


class RollingEngine:
    """
    Option rolling automation engine.
    
    Features:
    - Automatic roll opportunity detection
    - Multiple roll strategies (calendar, diagonal, strike)
    - P&L and risk impact analysis
    - Configurable trigger conditions
    - Execution with slippage management
    
    Roll Scoring:
    - Credit received (positive contribution)
    - Delta improvement (toward target)
    - Theta increase
    - DTE extension
    - Spread quality (tighter = better)
    
    Example:
        engine = RollingEngine(config=RollConfig(
            min_dte_to_roll=21,
            profit_take_pct=0.50,
        ))
        
        # Find opportunities
        opportunities = engine.find_roll_opportunities(
            position=position,
            spot=150.0,
            option_chain=chain,
        )
        
        # Get best opportunity
        if opportunities:
            best = engine.rank_opportunities(opportunities)[0]
            result = await engine.execute_roll(best)
    """
    
    def __init__(
        self,
        config: Optional[RollConfig] = None,
        position_manager: Optional[PositionFSM] = None,
        order_executor: Optional[Callable] = None,
    ) -> None:
        """
        Initialize the rolling engine.
        
        Args:
            config: Roll configuration (default: RollConfig())
            position_manager: Position FSM instance
            order_executor: Callback to execute orders
        """
        self.config = config or RollConfig()
        self._position_manager = position_manager or get_position_manager()
        self._order_executor = order_executor
        
        # Roll history
        self._roll_history: List[RollResult] = []
        
        logger.info("RollingEngine initialized", config=vars(self.config))
    
    def should_consider_roll(
        self,
        position: Position,
        spot: float,
        current_delta: Optional[float] = None,
    ) -> Tuple[bool, RollTrigger]:
        """
        Determine if position should be considered for rolling.
        
        Args:
            position: Position to evaluate
            spot: Current underlying price
            current_delta: Current position delta
            
        Returns:
            Tuple of (should_roll, trigger_reason)
        """
        option = parse_osi_symbol(position.symbol)
        dte = option.days_to_expiry
        
        # Time decay trigger
        if dte <= self.config.min_dte_to_roll:
            return True, RollTrigger.TIME_DECAY
        
        # Profit target trigger
        if position.side == "short":
            # For short positions, profit = entry - current
            pnl_pct = position.unrealized_pnl / abs(position.entry_price * position.quantity * 100)
            if pnl_pct >= self.config.profit_take_pct:
                return True, RollTrigger.PROFIT_TARGET
        
        # Delta breach trigger
        if current_delta is not None:
            if position.side == "short":
                if option.option_type.is_call and abs(current_delta) > self.config.max_delta_short_call:
                    return True, RollTrigger.DELTA_BREACH
                if option.option_type.is_put and current_delta < self.config.max_delta_short_put:
                    return True, RollTrigger.DELTA_BREACH
        
        # Gamma risk trigger (close to expiry near the strike)
        if dte <= 7:
            moneyness = abs(spot - option.strike) / option.strike
            if moneyness < 0.02:  # Within 2% of strike
                return True, RollTrigger.GAMMA_RISK
        
        return False, RollTrigger.MANUAL
    
    def find_roll_opportunities(
        self,
        position: Position,
        spot: float,
        option_chain: Dict[date, List[OptionQuote]],
        trigger: Optional[RollTrigger] = None,
    ) -> List[RollOpportunity]:
        """
        Find all viable roll opportunities for a position.
        
        Args:
            position: Current position to roll
            spot: Current underlying price
            option_chain: Option chain organized by expiration
            trigger: Roll trigger (auto-detected if not provided)
            
        Returns:
            List of roll opportunities
        """
        opportunities = []
        current_option = parse_osi_symbol(position.symbol)
        
        # Auto-detect trigger
        if trigger is None:
            should_roll, trigger = self.should_consider_roll(position, spot)
            if not should_roll:
                trigger = RollTrigger.MANUAL
        
        # Get current option quote
        current_quote = self._find_quote_in_chain(position.symbol, option_chain)
        
        # Find target expirations
        target_expiries = self._select_target_expirations(option_chain, current_option.expiry)
        
        for expiry in target_expiries:
            quotes = option_chain.get(expiry, [])
            
            # Filter to same option type
            type_quotes = [
                q for q in quotes
                if parse_osi_symbol(q.symbol).option_type == current_option.option_type
            ]
            
            for new_quote in type_quotes:
                opportunity = self._evaluate_roll(
                    position=position,
                    current_quote=current_quote,
                    new_quote=new_quote,
                    spot=spot,
                    trigger=trigger,
                )
                
                if opportunity is not None:
                    opportunities.append(opportunity)
        
        return opportunities
    
    def _select_target_expirations(
        self,
        option_chain: Dict[date, List[OptionQuote]],
        current_expiry: date,
    ) -> List[date]:
        """Select target expirations for rolling."""
        today = date.today()
        target_dte = self.config.target_dte_after_roll
        
        candidates = []
        for expiry in option_chain.keys():
            dte = (expiry - today).days
            
            # Skip current or earlier expirations
            if expiry <= current_expiry:
                continue
            
            # Prefer expirations near target DTE
            if 30 <= dte <= 60:  # Standard range
                candidates.append(expiry)
        
        # Sort by distance from target DTE
        candidates.sort(key=lambda e: abs((e - today).days - target_dte))
        
        return candidates[:3]  # Top 3 closest to target
    
    def _find_quote_in_chain(
        self,
        symbol: str,
        chain: Dict[date, List[OptionQuote]],
    ) -> Optional[OptionQuote]:
        """Find a specific option quote in chain."""
        option = parse_osi_symbol(symbol)
        
        if option.expiry in chain:
            for quote in chain[option.expiry]:
                if quote.symbol == symbol:
                    return quote
        
        return None
    
    def _evaluate_roll(
        self,
        position: Position,
        current_quote: Optional[OptionQuote],
        new_quote: OptionQuote,
        spot: float,
        trigger: RollTrigger,
    ) -> Optional[RollOpportunity]:
        """Evaluate a potential roll."""
        current_option = parse_osi_symbol(position.symbol)
        new_option = parse_osi_symbol(new_quote.symbol)
        
        # Calculate credit/debit
        if position.side == "short":
            # Closing short = buy, opening new short = sell
            close_cost = current_quote.ask if current_quote else position.current_price
            open_credit = new_quote.bid
            credit_debit = open_credit - close_cost  # Positive = net credit
        else:
            # Closing long = sell, opening new long = buy
            close_credit = current_quote.bid if current_quote else position.current_price
            open_cost = new_quote.ask
            credit_debit = close_credit - open_cost  # Positive = net credit
        
        # Check credit/debit constraints
        if credit_debit < self.config.max_debit_to_roll:
            return None  # Debit too large
        
        # Determine roll strategy
        if new_option.strike == current_option.strike:
            strategy = RollStrategy.CALENDAR
        elif new_option.expiry == current_option.expiry:
            strategy = RollStrategy.STRIKE
        else:
            strategy = RollStrategy.DIAGONAL
        
        # Calculate delta improvement
        current_delta = current_quote.delta if current_quote else 0.0
        delta_improvement = abs(new_quote.delta) - abs(current_delta)
        
        # Calculate theta improvement
        current_theta = current_quote.theta if current_quote else 0.0
        theta_improvement = new_quote.theta - current_theta
        
        # Calculate DTE extension
        dte_extension = (new_option.expiry - current_option.expiry).days
        
        # Calculate breakeven move (for debits)
        breakeven_move = 0.0
        if credit_debit < 0:
            breakeven_move = abs(credit_debit) / spot * 100
        
        # Score the opportunity
        score = self._score_opportunity(
            credit_debit=credit_debit,
            delta_improvement=delta_improvement,
            theta_improvement=theta_improvement,
            dte_extension=dte_extension,
            new_delta=new_quote.delta,
            spread_quality=1.0 / (1.0 + new_quote.spread_pct),
        )
        
        # Generate rationale
        rationale = self._generate_rationale(
            strategy=strategy,
            trigger=trigger,
            credit_debit=credit_debit,
            dte_extension=dte_extension,
            new_option=new_option,
        )
        
        return RollOpportunity(
            id=f"roll_{position.id}_{new_quote.symbol}_{datetime.now().strftime('%H%M%S')}",
            strategy=strategy,
            trigger=trigger,
            current_symbol=position.symbol,
            current_price=position.current_price,
            current_qty=position.quantity,
            new_symbol=new_quote.symbol,
            new_price=new_quote.mid,
            new_strike=new_option.strike,
            new_expiry=new_option.expiry,
            current_delta=current_delta,
            new_delta=new_quote.delta,
            current_theta=current_theta,
            new_theta=new_quote.theta,
            credit_debit=credit_debit,
            net_premium=credit_debit * abs(position.quantity) * 100,
            breakeven_move=breakeven_move,
            max_loss_change=0.0,  # Would need full analysis
            probability_profit=0.0,  # Would need Monte Carlo
            score=score,
            rationale=rationale,
        )
    
    def _score_opportunity(
        self,
        credit_debit: float,
        delta_improvement: float,
        theta_improvement: float,
        dte_extension: int,
        new_delta: float,
        spread_quality: float,
    ) -> float:
        """
        Score a roll opportunity.
        
        Higher score = better opportunity.
        """
        score = 0.0
        
        # Credit contribution (most important)
        score += credit_debit * 10.0  # $1 credit = 10 points
        
        # Delta toward target
        delta_diff = abs(abs(new_delta) - self.config.target_delta)
        score += (0.5 - delta_diff) * 20.0  # On target = +10, off by 0.5 = 0
        
        # Theta improvement (for short positions)
        score += theta_improvement * 5.0
        
        # DTE extension
        if 30 <= dte_extension <= 60:
            score += 5.0  # Ideal range
        elif dte_extension > 0:
            score += 2.0  # Any extension is good
        
        # Spread quality
        score += spread_quality * 3.0
        
        return score
    
    def _generate_rationale(
        self,
        strategy: RollStrategy,
        trigger: RollTrigger,
        credit_debit: float,
        dte_extension: int,
        new_option: OptionSymbol,
    ) -> str:
        """Generate human-readable rationale."""
        parts = []
        
        # Strategy description
        if strategy == RollStrategy.CALENDAR:
            parts.append(f"Calendar roll to {new_option.expiry}")
        elif strategy == RollStrategy.DIAGONAL:
            parts.append(f"Diagonal roll to ${new_option.strike} {new_option.expiry}")
        elif strategy == RollStrategy.STRIKE:
            parts.append(f"Strike roll to ${new_option.strike}")
        
        # Credit/debit
        if credit_debit > 0:
            parts.append(f"for ${credit_debit:.2f} credit")
        else:
            parts.append(f"for ${abs(credit_debit):.2f} debit")
        
        # DTE
        parts.append(f"(+{dte_extension} DTE)")
        
        # Trigger reason
        trigger_text = {
            RollTrigger.TIME_DECAY: "due to time decay",
            RollTrigger.PROFIT_TARGET: "to lock in profit",
            RollTrigger.DELTA_BREACH: "to manage delta",
            RollTrigger.GAMMA_RISK: "to reduce gamma risk",
            RollTrigger.DIVIDEND: "to avoid dividend assignment",
        }
        
        if trigger in trigger_text:
            parts.append(trigger_text[trigger])
        
        return " ".join(parts)
    
    def rank_opportunities(
        self,
        opportunities: List[RollOpportunity],
    ) -> List[RollOpportunity]:
        """Rank opportunities by score descending."""
        return sorted(opportunities, key=lambda o: o.score, reverse=True)
    
    async def execute_roll(
        self,
        opportunity: RollOpportunity,
        max_slippage: float = 0.05,
    ) -> RollResult:
        """
        Execute a roll by closing current and opening new position.
        
        Args:
            opportunity: Roll opportunity to execute
            max_slippage: Maximum acceptable slippage
            
        Returns:
            RollResult with execution details
        """
        start_time = datetime.now(timezone.utc)
        
        if self._order_executor is None:
            return RollResult(
                success=False,
                opportunity=opportunity,
                error="No order executor configured",
            )
        
        try:
            # Step 1: Close current position
            close_result = await self._order_executor(
                action="close",
                symbol=opportunity.current_symbol,
                quantity=abs(opportunity.current_qty),
            )
            
            if not close_result.get("success"):
                return RollResult(
                    success=False,
                    opportunity=opportunity,
                    error=f"Failed to close: {close_result.get('error')}",
                )
            
            close_fill = close_result.get("fill_price", opportunity.current_price)
            
            # Step 2: Open new position
            open_result = await self._order_executor(
                action="open",
                symbol=opportunity.new_symbol,
                quantity=abs(opportunity.current_qty),
                side="short" if opportunity.current_qty < 0 else "long",
            )
            
            if not open_result.get("success"):
                # Try to revert close (complex - may need manual intervention)
                logger.error(
                    "Roll failed after close - manual intervention may be needed",
                    opportunity=opportunity.id,
                )
                return RollResult(
                    success=False,
                    opportunity=opportunity,
                    close_fill_price=close_fill,
                    error=f"Failed to open new position: {open_result.get('error')}",
                )
            
            open_fill = open_result.get("fill_price", opportunity.new_price)
            
            # Calculate actual credit/debit
            if opportunity.current_qty < 0:  # Short position
                actual_credit_debit = open_fill - close_fill
            else:
                actual_credit_debit = close_fill - open_fill
            
            # Check slippage
            expected = opportunity.credit_debit
            slippage = abs(actual_credit_debit - expected) / max(abs(expected), 0.01)
            
            if slippage > max_slippage:
                logger.warning(
                    "Roll executed with high slippage",
                    expected=expected,
                    actual=actual_credit_debit,
                    slippage_pct=slippage * 100,
                )
            
            end_time = datetime.now(timezone.utc)
            execution_ms = (end_time - start_time).total_seconds() * 1000
            
            # Record in history
            result = RollResult(
                success=True,
                opportunity=opportunity,
                close_fill_price=close_fill,
                open_fill_price=open_fill,
                actual_credit_debit=actual_credit_debit,
                new_position_id=open_result.get("position_id"),
                executed_at=end_time,
                execution_time_ms=execution_ms,
            )
            
            self._roll_history.append(result)
            increment_counter("rolls_executed_total")
            
            logger.info(
                "Roll executed successfully",
                opportunity=opportunity.id,
                actual_credit_debit=actual_credit_debit,
                execution_time_ms=execution_ms,
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Roll execution error: {e}", opportunity=opportunity.id)
            return RollResult(
                success=False,
                opportunity=opportunity,
                error=str(e),
            )
    
    def find_portfolio_roll_opportunities(
        self,
        spots: Dict[str, float],
        option_chains: Dict[str, Dict[date, List[OptionQuote]]],
    ) -> Dict[str, List[RollOpportunity]]:
        """
        Find roll opportunities for all positions.
        
        Args:
            spots: Dict mapping underlying to spot price
            option_chains: Dict mapping underlying to option chain
            
        Returns:
            Dict mapping position ID to list of opportunities
        """
        all_opportunities: Dict[str, List[RollOpportunity]] = {}
        
        for position in self._position_manager.get_active_positions():
            option = parse_osi_symbol(position.symbol)
            
            spot = spots.get(option.underlying)
            chain = option_chains.get(option.underlying)
            
            if spot is None or chain is None:
                continue
            
            opportunities = self.find_roll_opportunities(
                position=position,
                spot=spot,
                option_chain=chain,
            )
            
            if opportunities:
                all_opportunities[position.id] = self.rank_opportunities(opportunities)
        
        return all_opportunities
    
    def get_roll_history(
        self,
        limit: int = 100,
    ) -> List[RollResult]:
        """Get recent roll history."""
        return self._roll_history[-limit:]
    
    def get_roll_statistics(self) -> Dict[str, Any]:
        """Get roll execution statistics."""
        if not self._roll_history:
            return {
                "total_rolls": 0,
                "successful_rolls": 0,
                "success_rate": 0.0,
            }
        
        successful = [r for r in self._roll_history if r.success]
        
        credits = [
            r.actual_credit_debit
            for r in successful
            if r.actual_credit_debit is not None and r.actual_credit_debit > 0
        ]
        
        debits = [
            r.actual_credit_debit
            for r in successful
            if r.actual_credit_debit is not None and r.actual_credit_debit < 0
        ]
        
        return {
            "total_rolls": len(self._roll_history),
            "successful_rolls": len(successful),
            "success_rate": len(successful) / len(self._roll_history),
            "total_credits": sum(credits) if credits else 0.0,
            "total_debits": sum(debits) if debits else 0.0,
            "net_premium": sum(credits) + sum(debits),
            "avg_credit": sum(credits) / len(credits) if credits else 0.0,
            "avg_debit": sum(debits) / len(debits) if debits else 0.0,
        }


# =============================================================================
# MODULE-LEVEL UTILITIES
# =============================================================================

_rolling_engine: Optional[RollingEngine] = None


def get_rolling_engine(config: Optional[RollConfig] = None) -> RollingEngine:
    """Get global rolling engine instance."""
    global _rolling_engine
    if _rolling_engine is None:
        _rolling_engine = RollingEngine(config=config)
    return _rolling_engine
