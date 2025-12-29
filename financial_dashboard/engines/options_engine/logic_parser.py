"""
Logic Parser - Dynamic Condition Evaluation
============================================

Parses and evaluates condition strings from Recipe JSON.
Supports OptionsAlpha-style conditions with nested AND/OR logic.

Supported Condition Patterns:
----------------------------
- Symbol conditions: "SPY.price > 450", "AAPL.change_pct < -2"
- Indicator conditions: "SPY.RSI > 70", "QQQ.MACD.histogram > 0"
- Position conditions: "position.pnl_pct > 50", "position.dte < 7"
- General conditions: "market.is_open", "time.hour == 9"
- Opportunity conditions: "spread.return > 0.5", "spread.pop > 65"

Operators:
---------
- Comparison: >, <, >=, <=, ==, !=
- Range: between, not_between (e.g., "RSI between 30 and 70")
- List: in, not_in (e.g., "symbol in ['AAPL', 'MSFT']")
- Boolean: is_true, is_false

Frontend Integration:
-------------------
```javascript
// Condition builder UI component
<ConditionBuilder
    conditions={[
        { indicator: "RSI", operator: ">", value: 70 },
        { indicator: "price", operator: "<", value: 150 }
    ]}
    logic="AND"
    onChange={handleConditionChange}
/>

// Preview condition string
<pre>{conditions.map(c => `${c.indicator} ${c.operator} ${c.value}`).join(' && ')}</pre>
```
"""

from __future__ import annotations
import operator
import re
from dataclasses import dataclass
from datetime import datetime, time as dt_time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
import logging

from .schema import (
    ConditionGroup,
    ConditionOperator,
    ComparisonOperator,
    IndicatorCondition,
    SymbolCondition,
    PositionCondition,
    GeneralCondition,
    OpportunityCondition,
    Indicator,
)

logger = logging.getLogger(__name__)


# =============================================================================
# OPERATORS MAPPING
# =============================================================================

COMPARISON_OPS: Dict[str, Callable[[Any, Any], bool]] = {
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
    "greater_than": operator.gt,
    "less_than": operator.lt,
    "greater_than_or_equal": operator.ge,
    "less_than_or_equal": operator.le,
    "equals": operator.eq,
    "not_equals": operator.ne,
}


def between(value: float, bounds: tuple) -> bool:
    """Check if value is between two bounds (inclusive)."""
    low, high = bounds
    return low <= value <= high


def not_between(value: float, bounds: tuple) -> bool:
    """Check if value is NOT between two bounds."""
    return not between(value, bounds)


def in_list(value: Any, items: list) -> bool:
    """Check if value is in list."""
    return value in items


def not_in_list(value: Any, items: list) -> bool:
    """Check if value is NOT in list."""
    return value not in items


def is_true(value: Any, _: Any = None) -> bool:
    """Check if value is truthy."""
    return bool(value)


def is_false(value: Any, _: Any = None) -> bool:
    """Check if value is falsy."""
    return not bool(value)


SPECIAL_OPS: Dict[str, Callable] = {
    "between": between,
    "not_between": not_between,
    "in": in_list,
    "not_in": not_in_list,
    "is_true": is_true,
    "is_false": is_false,
    "crosses_above": lambda cur, prev, thresh: prev < thresh <= cur,
    "crosses_below": lambda cur, prev, thresh: prev > thresh >= cur,
}


# =============================================================================
# EVALUATION CONTEXT
# =============================================================================

@dataclass
class EvaluationContext:
    """
    Context for condition evaluation.
    
    Contains all data needed to evaluate conditions:
    - Market data from DataHandler
    - Position data from Broker
    - Time/schedule data
    """
    data_handler: Any  # DataHandler instance
    broker: Any  # BrokerInterface instance
    position: Optional[Any] = None  # Current position being evaluated
    symbol: Optional[str] = None  # Current symbol being evaluated
    bot_id: Optional[str] = None  # Bot context
    
    # Cache for expensive lookups
    _cache: Dict[str, Any] = None
    
    def __post_init__(self):
        self._cache = {}
    
    def get_quote(self, symbol: str) -> Any:
        """Get cached quote data."""
        key = f"quote:{symbol}"
        if key not in self._cache:
            self._cache[key] = self.data_handler.get_quote(symbol)
        return self._cache[key]
    
    def get_indicator(self, symbol: str, indicator: str, **params) -> Any:
        """Get cached indicator value."""
        key = f"indicator:{symbol}:{indicator}:{params}"
        if key not in self._cache:
            result = self.data_handler.get_indicator(symbol, indicator, **params)
            # Extract raw value from IndicatorData if needed
            if hasattr(result, 'value'):
                self._cache[key] = result.value
            else:
                self._cache[key] = result
        return self._cache[key]
    
    def clear_cache(self):
        """Clear the data cache."""
        self._cache.clear()


# =============================================================================
# CONDITION EVALUATORS
# =============================================================================

class ConditionEvaluator:
    """Base class for condition evaluators."""
    
    def evaluate(self, condition: Any, context: EvaluationContext) -> bool:
        raise NotImplementedError


class SymbolConditionEvaluator(ConditionEvaluator):
    """
    Evaluates symbol-based conditions.
    
    Examples:
        - "SPY.price > 450"
        - "AAPL.change_pct < -2"
        - "QQQ.volume > 50000000"
    """
    
    SYMBOL_FIELDS = {
        "price": lambda q: q.price,
        "bid": lambda q: q.bid,
        "ask": lambda q: q.ask,
        "volume": lambda q: q.volume,
        "open": lambda q: getattr(q, "open", q.price),
        "high": lambda q: getattr(q, "high", q.price),
        "low": lambda q: getattr(q, "low", q.price),
        "close": lambda q: q.price,
        "change": lambda q: getattr(q, "change", 0),
        "change_pct": lambda q: getattr(q, "change_pct", 0),
    }
    
    def evaluate(self, condition: SymbolCondition, context: EvaluationContext) -> bool:
        symbol = getattr(condition, 'symbol', None) or context.symbol
        if not symbol:
            logger.warning("No symbol specified for SymbolCondition")
            return False
        
        try:
            quote = context.get_quote(symbol)
            field = condition.field.lower()
            
            if field not in self.SYMBOL_FIELDS:
                logger.warning(f"Unknown symbol field: {field}")
                return False
            
            actual_value = self.SYMBOL_FIELDS[field](quote)
            value2 = getattr(condition, 'value2', None)
            return self._compare(actual_value, condition.operator, condition.value, value2)
            
        except Exception as e:
            logger.error(f"Failed to evaluate symbol condition: {e}")
            return False
    
    def _compare(
        self,
        actual: Any,
        op: ComparisonOperator,
        value: Any,
        value2: Optional[Any] = None
    ) -> bool:
        op_str = op.value if isinstance(op, ComparisonOperator) else str(op)
        
        if op_str in COMPARISON_OPS:
            return COMPARISON_OPS[op_str](actual, value)
        elif op_str == "between":
            return between(actual, (value, value2))
        elif op_str == "not_between":
            return not_between(actual, (value, value2))
        elif op_str == "in":
            return in_list(actual, value if isinstance(value, list) else [value])
        elif op_str == "not_in":
            return not_in_list(actual, value if isinstance(value, list) else [value])
        else:
            logger.warning(f"Unknown operator: {op_str}")
            return False


class IndicatorConditionEvaluator(ConditionEvaluator):
    """
    Evaluates indicator-based conditions.
    
    Examples:
        - "RSI > 70"
        - "MACD.histogram > 0"
        - "SMA(20) > SMA(50)"
    """
    
    def evaluate(self, condition: IndicatorCondition, context: EvaluationContext) -> bool:
        symbol = getattr(condition, 'symbol', None) or context.symbol
        if not symbol:
            logger.warning("No symbol specified for IndicatorCondition")
            return False
        
        try:
            # Get indicator value
            indicator = condition.indicator
            indicator_str = indicator.value if isinstance(indicator, Indicator) else str(indicator)
            
            params = {}
            period = getattr(condition, 'period', None)
            if period:
                params["period"] = period
            timeframe = getattr(condition, 'timeframe', None)
            if timeframe:
                params["timeframe"] = timeframe
            
            actual_value = context.get_indicator(symbol, indicator_str, **params)
            
            # Handle sub-fields (e.g., MACD.histogram)
            field = getattr(condition, 'field', None)
            if field and isinstance(actual_value, dict):
                actual_value = actual_value.get(field, actual_value)
            
            value2 = getattr(condition, 'value2', None)
            return self._compare(actual_value, condition.operator, condition.value, value2)
            
        except Exception as e:
            logger.error(f"Failed to evaluate indicator condition: {e}")
            return False
    
    def _compare(
        self,
        actual: Any,
        op: ComparisonOperator,
        value: Any,
        value2: Optional[Any] = None
    ) -> bool:
        op_str = op.value if isinstance(op, ComparisonOperator) else str(op)
        
        if op_str in COMPARISON_OPS:
            return COMPARISON_OPS[op_str](actual, value)
        elif op_str == "between":
            return between(actual, (value, value2))
        elif op_str == "not_between":
            return not_between(actual, (value, value2))
        else:
            logger.warning(f"Unknown operator: {op_str}")
            return False


class PositionConditionEvaluator(ConditionEvaluator):
    """
    Evaluates position-based conditions.
    
    Examples:
        - "position.pnl_pct > 50" (take profit)
        - "position.pnl_pct < -25" (stop loss)
        - "position.dte < 7" (close before expiration)
        - "position.days_held > 30"
    """
    
    POSITION_FIELDS = {
        "pnl": lambda p: p.unrealized_pnl,
        "pnl_pct": lambda p: p.unrealized_pnl_pct,
        "dte": lambda p: p.dte or 999,
        "days_held": lambda p: p.days_held,
        "entry_price": lambda p: p.entry_price,
        "current_price": lambda p: p.current_price,
        "quantity": lambda p: p.quantity,
        "entry_value": lambda p: p.entry_value,
        "current_value": lambda p: p.current_value,
        "max_profit_pct": lambda p: (p.unrealized_pnl / p.max_profit * 100) if p.max_profit else 0,
        "max_loss_pct": lambda p: (abs(p.unrealized_pnl) / abs(p.max_loss) * 100) if p.max_loss else 0,
    }
    
    def evaluate(self, condition: PositionCondition, context: EvaluationContext) -> bool:
        position = context.position
        if not position:
            logger.warning("No position in context for PositionCondition")
            return False
        
        try:
            field = condition.field.lower()
            
            if field not in self.POSITION_FIELDS:
                logger.warning(f"Unknown position field: {field}")
                return False
            
            actual_value = self.POSITION_FIELDS[field](position)
            value2 = getattr(condition, 'value2', None)
            return self._compare(actual_value, condition.operator, condition.value, value2)
            
        except Exception as e:
            logger.error(f"Failed to evaluate position condition: {e}")
            return False
    
    def _compare(
        self,
        actual: Any,
        op: ComparisonOperator,
        value: Any,
        value2: Optional[Any] = None
    ) -> bool:
        op_str = op.value if isinstance(op, ComparisonOperator) else str(op)
        
        if op_str in COMPARISON_OPS:
            return COMPARISON_OPS[op_str](actual, value)
        elif op_str == "between":
            return between(actual, (value, value2))
        else:
            logger.warning(f"Unknown operator: {op_str}")
            return False


class GeneralConditionEvaluator(ConditionEvaluator):
    """
    Evaluates general/time-based conditions.
    
    Examples:
        - "market.is_open"
        - "time.hour == 9"
        - "day_of_week in ['Monday', 'Wednesday', 'Friday']"
    """
    
    def evaluate(self, condition: GeneralCondition, context: EvaluationContext) -> bool:
        field = condition.field.lower()
        value2 = getattr(condition, 'value2', None)
        
        try:
            # Market conditions
            if field == "market.is_open" or field == "is_market_hours":
                is_open = context.data_handler.get_market_status().get("is_open", False)
                return self._compare(is_open, condition.operator, condition.value)
            
            # Time conditions
            now = datetime.now()
            
            if field == "time.hour":
                return self._compare(now.hour, condition.operator, condition.value, value2)
            elif field == "time.minute":
                return self._compare(now.minute, condition.operator, condition.value, value2)
            elif field == "day_of_week":
                days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                day_name = days[now.weekday()]
                return self._compare(day_name, condition.operator, condition.value)
            elif field == "day_of_month":
                return self._compare(now.day, condition.operator, condition.value, value2)
            elif field == "week_of_month":
                week = (now.day - 1) // 7 + 1
                return self._compare(week, condition.operator, condition.value, value2)
            
            logger.warning(f"Unknown general condition field: {field}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to evaluate general condition: {e}")
            return False
    
    def _compare(
        self,
        actual: Any,
        op: ComparisonOperator,
        value: Any,
        value2: Optional[Any] = None
    ) -> bool:
        op_str = op.value if isinstance(op, ComparisonOperator) else str(op)
        
        if op_str == "is_true":
            return bool(actual) == bool(value)
        elif op_str == "is_false":
            return not bool(actual)
        elif op_str in COMPARISON_OPS:
            return COMPARISON_OPS[op_str](actual, value)
        elif op_str == "in":
            return in_list(actual, value if isinstance(value, list) else [value])
        elif op_str == "not_in":
            return not_in_list(actual, value if isinstance(value, list) else [value])
        else:
            logger.warning(f"Unknown operator: {op_str}")
            return False


class OpportunityConditionEvaluator(ConditionEvaluator):
    """
    Evaluates opportunity/scanner conditions.
    
    Examples:
        - "spread.return > 0.5" (50% return)
        - "spread.pop > 65" (probability of profit)
        - "spread.delta < 0.3"
    """
    
    def evaluate(self, condition: OpportunityCondition, context: EvaluationContext) -> bool:
        # This would integrate with scanner results
        # For now, return True as placeholder
        logger.info(f"OpportunityCondition evaluation: {condition.field}")
        return True


# =============================================================================
# LOGIC PARSER
# =============================================================================

class LogicParser:
    """
    Main logic parser for evaluating Recipe conditions.
    
    Supports nested AND/OR condition groups with arbitrary depth.
    
    Usage:
        parser = LogicParser()
        context = EvaluationContext(data_handler, broker, position=pos)
        
        # Single condition
        result = parser.evaluate_condition(condition, context)
        
        # Condition group (AND/OR)
        result = parser.evaluate_group(condition_group, context)
    """
    
    def __init__(self):
        self.evaluators = {
            "symbol": SymbolConditionEvaluator(),
            "indicator": IndicatorConditionEvaluator(),
            "position": PositionConditionEvaluator(),
            "general": GeneralConditionEvaluator(),
            "opportunity": OpportunityConditionEvaluator(),
        }
    
    def evaluate_condition(
        self,
        condition: Union[SymbolCondition, IndicatorCondition, PositionCondition, GeneralCondition, OpportunityCondition],
        context: EvaluationContext
    ) -> bool:
        """Evaluate a single condition."""
        condition_type = self._get_condition_type(condition)
        
        evaluator = self.evaluators.get(condition_type)
        if not evaluator:
            logger.warning(f"No evaluator for condition type: {condition_type}")
            return False
        
        result = evaluator.evaluate(condition, context)
        logger.debug(f"Condition {condition_type} evaluated to: {result}")
        return result
    
    def _get_condition_type(self, condition: Any) -> str:
        """Determine condition type from instance."""
        if isinstance(condition, SymbolCondition):
            return "symbol"
        elif isinstance(condition, IndicatorCondition):
            return "indicator"
        elif isinstance(condition, PositionCondition):
            return "position"
        elif isinstance(condition, GeneralCondition):
            return "general"
        elif isinstance(condition, OpportunityCondition):
            return "opportunity"
        else:
            return "unknown"
    
    def evaluate_group(
        self,
        group: ConditionGroup,
        context: EvaluationContext
    ) -> bool:
        """
        Evaluate a condition group with AND/OR logic.
        
        Supports nested groups for complex conditions like:
        (A AND B) OR (C AND D)
        """
        if not group.conditions:
            return True  # Empty group is truthy
        
        results = []
        
        for item in group.conditions:
            if isinstance(item, ConditionGroup):
                # Recursive evaluation of nested group
                result = self.evaluate_group(item, context)
            else:
                # Single condition
                result = self.evaluate_condition(item, context)
            
            results.append(result)
            
            # Short-circuit evaluation
            if group.operator == ConditionOperator.AND and not result:
                logger.debug("Short-circuit AND: False")
                return False
            elif group.operator == ConditionOperator.OR and result:
                logger.debug("Short-circuit OR: True")
                return True
        
        # Final result based on operator
        if group.operator == ConditionOperator.AND:
            final = all(results)
        else:  # OR
            final = any(results)
        
        logger.debug(f"Group ({group.operator.value}) result: {final}")
        return final
    
    def evaluate_conditions_list(
        self,
        conditions: List[Union[ConditionGroup, Any]],
        context: EvaluationContext,
        default_operator: ConditionOperator = ConditionOperator.AND
    ) -> bool:
        """
        Evaluate a list of conditions with default AND logic.
        
        This is the main entry point for Recipe entry/exit conditions.
        """
        if not conditions:
            return True
        
        results = []
        
        for item in conditions:
            if isinstance(item, ConditionGroup):
                result = self.evaluate_group(item, context)
            else:
                result = self.evaluate_condition(item, context)
            
            results.append(result)
            
            # Short-circuit for AND
            if default_operator == ConditionOperator.AND and not result:
                return False
        
        if default_operator == ConditionOperator.AND:
            return all(results)
        else:
            return any(results)


# =============================================================================
# STRING PARSER (for human-readable conditions)
# =============================================================================

class ConditionStringParser:
    """
    Parse human-readable condition strings into Condition objects.
    
    This is useful for quick testing and REPL-style interfaces.
    
    Supported formats:
        - "SPY.RSI > 70"
        - "AAPL.price < 150"
        - "position.pnl_pct > 50"
        - "market.is_open"
    """
    
    PATTERN = re.compile(
        r"^(?P<target>\w+)\.(?P<field>\w+(?:\.\w+)?)\s*"
        r"(?P<operator>[><=!]+|between|in|not_in|is_true|is_false)\s*"
        r"(?P<value>[\d.]+|\[.*\]|True|False)?(?:\s+and\s+(?P<value2>[\d.]+))?$",
        re.IGNORECASE
    )
    
    INDICATOR_NAMES = {
        "rsi", "macd", "sma", "ema", "atr", "vix", "iv_rank", "iv_percentile",
        "bollinger", "stochastic", "adx", "obv", "williams_r"
    }
    
    def parse(self, condition_str: str) -> Union[SymbolCondition, IndicatorCondition, PositionCondition, GeneralCondition, None]:
        """Parse a condition string into a Condition object."""
        condition_str = condition_str.strip()
        match = self.PATTERN.match(condition_str)
        
        if not match:
            logger.warning(f"Could not parse condition: {condition_str}")
            return None
        
        target = match.group("target").upper()
        field = match.group("field").lower()
        operator_str = match.group("operator")
        value_str = match.group("value")
        value2_str = match.group("value2")
        
        # Parse value
        value = self._parse_value(value_str)
        value2 = self._parse_value(value2_str) if value2_str else None
        
        # Determine operator
        operator = self._parse_operator(operator_str)
        
        # Determine condition type
        if target == "POSITION":
            return PositionCondition(field=field, operator=operator, value=value, value2=value2)
        elif target == "MARKET" or target == "TIME":
            return GeneralCondition(field=f"{target.lower()}.{field}", operator=operator, value=value)
        elif field in self.INDICATOR_NAMES or "." in field:
            # Indicator condition
            parts = field.split(".")
            indicator = parts[0]
            sub_field = parts[1] if len(parts) > 1 else None
            return IndicatorCondition(
                symbol=target,
                indicator=Indicator(indicator.upper()) if indicator.upper() in [i.value for i in Indicator] else indicator,
                field=sub_field,
                operator=operator,
                value=value,
                value2=value2
            )
        else:
            # Symbol condition
            return SymbolCondition(symbol=target, field=field, operator=operator, value=value, value2=value2)
    
    def _parse_value(self, value_str: Optional[str]) -> Any:
        """Parse value string to appropriate type."""
        if value_str is None:
            return None
        
        value_str = value_str.strip()
        
        # Boolean
        if value_str.lower() == "true":
            return True
        if value_str.lower() == "false":
            return False
        
        # List
        if value_str.startswith("["):
            try:
                import ast
                return ast.literal_eval(value_str)
            except:
                return value_str
        
        # Number
        try:
            if "." in value_str:
                return float(value_str)
            return int(value_str)
        except:
            return value_str
    
    def _parse_operator(self, op_str: str) -> ComparisonOperator:
        """Parse operator string to ComparisonOperator."""
        op_map = {
            ">": ComparisonOperator.GREATER_THAN,
            "<": ComparisonOperator.LESS_THAN,
            ">=": ComparisonOperator.GREATER_THAN_OR_EQUAL,
            "<=": ComparisonOperator.LESS_THAN_OR_EQUAL,
            "==": ComparisonOperator.EQUALS,
            "=": ComparisonOperator.EQUALS,
            "!=": ComparisonOperator.NOT_EQUALS,
            "<>": ComparisonOperator.NOT_EQUALS,
            "between": ComparisonOperator.BETWEEN,
            "in": ComparisonOperator.IN,
            "not_in": ComparisonOperator.NOT_IN,
            "is_true": ComparisonOperator.IS_TRUE,
            "is_false": ComparisonOperator.IS_FALSE,
        }
        return op_map.get(op_str.lower(), ComparisonOperator.EQUALS)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def evaluate_condition_string(
    condition_str: str,
    context: EvaluationContext
) -> bool:
    """
    Quick evaluation of a condition string.
    
    Usage:
        result = evaluate_condition_string("SPY.RSI > 70", context)
    """
    parser = ConditionStringParser()
    condition = parser.parse(condition_str)
    
    if not condition:
        return False
    
    logic_parser = LogicParser()
    return logic_parser.evaluate_condition(condition, context)


def create_condition_from_dict(data: Dict[str, Any]) -> Any:
    """
    Create a Condition object from a dictionary.
    
    This is useful for deserializing conditions from JSON.
    """
    condition_type = data.get("type", "symbol")
    
    if condition_type == "symbol":
        return SymbolCondition(**data)
    elif condition_type == "indicator":
        return IndicatorCondition(**data)
    elif condition_type == "position":
        return PositionCondition(**data)
    elif condition_type == "general":
        return GeneralCondition(**data)
    elif condition_type == "opportunity":
        return OpportunityCondition(**data)
    elif condition_type == "group":
        # Recursive for groups
        conditions = [create_condition_from_dict(c) for c in data.get("conditions", [])]
        return ConditionGroup(
            operator=ConditionOperator(data.get("operator", "and")),
            conditions=conditions
        )
    else:
        raise ValueError(f"Unknown condition type: {condition_type}")
