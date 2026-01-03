"""
User Playbooks & Education System
Phase 9 - User Playbooks & Education (Items 641-700)

Complete implementation of:
- Strategy playbooks library
- Trade journal templates
- Risk allocation guides
- Educational content system
- Interactive tutorials
"""

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime


# =============================================================================
# STRATEGY PLAYBOOKS (Items 641-660)
# =============================================================================

class StrategyCategory(Enum):
    """Strategy categories."""
    INCOME = "income"
    DIRECTIONAL = "directional"
    VOLATILITY = "volatility"
    HEDGING = "hedging"
    EARNINGS = "earnings"
    ADVANCED = "advanced"


class RiskLevel(Enum):
    """Risk level classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class StrategyPlaybook:
    """Strategy playbook definition."""
    id: str
    name: str
    category: StrategyCategory
    risk_level: RiskLevel
    description: str
    market_outlook: str
    max_profit: str
    max_loss: str
    breakeven: str
    legs: List[Dict[str, Any]]
    entry_criteria: List[str]
    exit_criteria: List[str]
    adjustments: List[str]
    best_conditions: List[str]
    avoid_when: List[str]
    example_trade: Dict[str, Any]
    tips: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "risk_level": self.risk_level.value,
            "description": self.description,
            "market_outlook": self.market_outlook,
            "max_profit": self.max_profit,
            "max_loss": self.max_loss,
            "breakeven": self.breakeven,
            "legs": self.legs,
            "entry_criteria": self.entry_criteria,
            "exit_criteria": self.exit_criteria,
            "adjustments": self.adjustments,
            "best_conditions": self.best_conditions,
            "avoid_when": self.avoid_when,
            "example_trade": self.example_trade,
            "tips": self.tips
        }


# Pre-built strategy playbooks
STRATEGY_PLAYBOOKS: Dict[str, StrategyPlaybook] = {
    # INCOME STRATEGIES (10)
    "covered_call": StrategyPlaybook(
        id="covered_call",
        name="Covered Call",
        category=StrategyCategory.INCOME,
        risk_level=RiskLevel.LOW,
        description="Sell a call option against long stock to generate income",
        market_outlook="Neutral to slightly bullish",
        max_profit="Premium received + (Strike - Stock Price)",
        max_loss="Stock price - Premium (if stock goes to zero)",
        breakeven="Stock purchase price - Premium received",
        legs=[
            {"type": "stock", "quantity": 100, "action": "long"},
            {"type": "call", "strike": "ATM/OTM", "action": "sell", "quantity": 1}
        ],
        entry_criteria=[
            "Own 100+ shares of underlying",
            "IV Rank > 30%",
            "Stock in uptrend or consolidating",
            "No major catalysts before expiration"
        ],
        exit_criteria=[
            "Close at 50% profit",
            "Roll if stock above strike near expiration",
            "Let expire worthless if OTM"
        ],
        adjustments=[
            "Roll up and out if stock rallies past strike",
            "Roll down if stock drops significantly",
            "Close early if volatility collapses"
        ],
        best_conditions=["High IV", "Sideways market", "Low volatility stocks"],
        avoid_when=["Expecting big move", "Before earnings", "In strong downtrend"],
        example_trade={
            "stock": "AAPL",
            "stock_price": 175,
            "strike": 180,
            "premium": 3.50,
            "expiration": "30 DTE",
            "max_profit": 850,
            "breakeven": 171.50
        },
        tips=[
            "Target 30-45 DTE for optimal theta decay",
            "Choose strikes with delta 0.25-0.35",
            "Consider ex-dividend dates"
        ]
    ),
    
    "cash_secured_put": StrategyPlaybook(
        id="cash_secured_put",
        name="Cash-Secured Put",
        category=StrategyCategory.INCOME,
        risk_level=RiskLevel.MEDIUM,
        description="Sell a put option with cash to cover potential assignment",
        market_outlook="Neutral to bullish",
        max_profit="Premium received",
        max_loss="Strike price - Premium (if stock goes to zero)",
        breakeven="Strike price - Premium received",
        legs=[
            {"type": "put", "strike": "ATM/OTM", "action": "sell", "quantity": 1}
        ],
        entry_criteria=[
            "Cash available to cover assignment",
            "IV Rank > 30%",
            "Willing to own stock at strike price",
            "Stock at support level"
        ],
        exit_criteria=[
            "Close at 50% profit",
            "Roll down and out if challenged",
            "Take assignment if comfortable"
        ],
        adjustments=[
            "Roll down if stock drops",
            "Roll out in time if near expiration",
            "Convert to covered call if assigned"
        ],
        best_conditions=["High IV", "Stock at support", "Bullish sentiment"],
        avoid_when=["Bearish outlook", "Expecting gap down", "Before earnings"],
        example_trade={
            "stock": "AAPL",
            "strike": 170,
            "premium": 4.00,
            "expiration": "30 DTE",
            "cash_required": 17000,
            "max_profit": 400,
            "breakeven": 166
        },
        tips=[
            "Target stocks you want to own",
            "Use at support levels for better entries",
            "Manage at 50% profit or 21 DTE"
        ]
    ),
    
    "iron_condor": StrategyPlaybook(
        id="iron_condor",
        name="Iron Condor",
        category=StrategyCategory.INCOME,
        risk_level=RiskLevel.MEDIUM,
        description="Sell OTM put spread and call spread for premium",
        market_outlook="Neutral, expecting low volatility",
        max_profit="Net premium received",
        max_loss="Width of spread - Premium",
        breakeven="Short put - Premium / Short call + Premium",
        legs=[
            {"type": "put", "strike": "OTM", "action": "buy", "quantity": 1},
            {"type": "put", "strike": "closer OTM", "action": "sell", "quantity": 1},
            {"type": "call", "strike": "closer OTM", "action": "sell", "quantity": 1},
            {"type": "call", "strike": "OTM", "action": "buy", "quantity": 1}
        ],
        entry_criteria=[
            "IV Rank > 50%",
            "Expecting range-bound movement",
            "No major catalysts",
            "45 DTE optimal"
        ],
        exit_criteria=[
            "Close at 50% profit",
            "Close if tested (delta > 0.30)",
            "Close at 21 DTE"
        ],
        adjustments=[
            "Roll tested side further OTM",
            "Add opposing spread to balance delta",
            "Close tested side and let winner run"
        ],
        best_conditions=["High IV", "Range-bound market", "After IV spike"],
        avoid_when=["Trending market", "Before earnings", "Low IV"],
        example_trade={
            "stock": "SPY",
            "put_spread": "440/435",
            "call_spread": "470/475",
            "premium": 1.50,
            "max_profit": 150,
            "max_loss": 350
        },
        tips=[
            "Collect at least 1/3 of spread width",
            "Keep short strikes at 1 standard deviation",
            "Manage winners early"
        ]
    ),
    
    "put_credit_spread": StrategyPlaybook(
        id="put_credit_spread",
        name="Put Credit Spread (Bull Put)",
        category=StrategyCategory.INCOME,
        risk_level=RiskLevel.MEDIUM,
        description="Sell put spread for credit with bullish bias",
        market_outlook="Bullish to neutral",
        max_profit="Net premium received",
        max_loss="Width of spread - Premium",
        breakeven="Short strike - Premium received",
        legs=[
            {"type": "put", "strike": "OTM", "action": "buy", "quantity": 1},
            {"type": "put", "strike": "closer OTM", "action": "sell", "quantity": 1}
        ],
        entry_criteria=[
            "IV Rank > 30%",
            "Bullish outlook on underlying",
            "Stock at or above support",
            "30-45 DTE"
        ],
        exit_criteria=[
            "Close at 50% profit",
            "Close if short strike breached",
            "Close at 21 DTE"
        ],
        adjustments=[
            "Roll down and out if tested",
            "Convert to iron condor by adding call spread"
        ],
        best_conditions=["High IV", "Bullish trend", "Strong support level"],
        avoid_when=["Bearish trend", "Low IV", "Major resistance above"],
        example_trade={
            "stock": "AAPL",
            "short_put": 170,
            "long_put": 165,
            "premium": 1.20,
            "max_profit": 120,
            "max_loss": 380
        },
        tips=[
            "Target 1/3 width of spread as credit",
            "Place short strike below support",
            "Don't fight the trend"
        ]
    ),
    
    "call_credit_spread": StrategyPlaybook(
        id="call_credit_spread",
        name="Call Credit Spread (Bear Call)",
        category=StrategyCategory.INCOME,
        risk_level=RiskLevel.MEDIUM,
        description="Sell call spread for credit with bearish bias",
        market_outlook="Bearish to neutral",
        max_profit="Net premium received",
        max_loss="Width of spread - Premium",
        breakeven="Short strike + Premium received",
        legs=[
            {"type": "call", "strike": "OTM", "action": "sell", "quantity": 1},
            {"type": "call", "strike": "further OTM", "action": "buy", "quantity": 1}
        ],
        entry_criteria=[
            "IV Rank > 30%",
            "Bearish to neutral outlook",
            "Stock at or below resistance",
            "30-45 DTE"
        ],
        exit_criteria=["Close at 50% profit", "Close if short strike breached"],
        adjustments=["Roll up and out if tested", "Convert to iron condor"],
        best_conditions=["High IV", "Bearish trend", "Strong resistance"],
        avoid_when=["Bullish trend", "Low IV", "Before positive catalyst"],
        example_trade={
            "stock": "AAPL",
            "short_call": 185,
            "long_call": 190,
            "premium": 1.00,
            "max_profit": 100,
            "max_loss": 400
        },
        tips=["Place short strike above resistance", "Use after failed breakouts"]
    ),
    
    # DIRECTIONAL STRATEGIES (10)
    "long_call": StrategyPlaybook(
        id="long_call",
        name="Long Call",
        category=StrategyCategory.DIRECTIONAL,
        risk_level=RiskLevel.HIGH,
        description="Buy a call option for bullish speculation",
        market_outlook="Strongly bullish",
        max_profit="Unlimited",
        max_loss="Premium paid",
        breakeven="Strike price + Premium paid",
        legs=[{"type": "call", "strike": "ATM/ITM", "action": "buy", "quantity": 1}],
        entry_criteria=[
            "Strong bullish conviction",
            "IV Rank < 50% (cheap options)",
            "Clear catalyst expected",
            "60-90 DTE for time"
        ],
        exit_criteria=["Target 50-100% profit", "Cut losses at 50%", "Roll before 21 DTE"],
        adjustments=["Roll up to lock profits", "Sell call against to reduce cost"],
        best_conditions=["Low IV", "Strong uptrend", "Positive catalyst"],
        avoid_when=["High IV", "Downtrend", "No clear catalyst"],
        example_trade={"stock": "AAPL", "strike": 175, "premium": 5.00, "expiration": "60 DTE"},
        tips=["Buy ITM for higher delta", "Don't hold through earnings unless planned"]
    ),
    
    "long_put": StrategyPlaybook(
        id="long_put",
        name="Long Put",
        category=StrategyCategory.DIRECTIONAL,
        risk_level=RiskLevel.HIGH,
        description="Buy a put option for bearish speculation or protection",
        market_outlook="Strongly bearish",
        max_profit="Strike - Premium (stock to zero)",
        max_loss="Premium paid",
        breakeven="Strike price - Premium paid",
        legs=[{"type": "put", "strike": "ATM/ITM", "action": "buy", "quantity": 1}],
        entry_criteria=["Strong bearish conviction", "IV Rank < 50%", "Clear negative catalyst"],
        exit_criteria=["Target 50-100% profit", "Cut losses at 50%"],
        adjustments=["Roll down to lock profits", "Sell put against to reduce cost"],
        best_conditions=["Low IV", "Downtrend", "Negative catalyst"],
        avoid_when=["High IV", "Uptrend", "Strong support below"],
        example_trade={"stock": "AAPL", "strike": 175, "premium": 4.50, "expiration": "60 DTE"},
        tips=["Great for portfolio protection", "Buy ITM for higher delta"]
    ),
    
    "call_debit_spread": StrategyPlaybook(
        id="call_debit_spread",
        name="Call Debit Spread (Bull Call)",
        category=StrategyCategory.DIRECTIONAL,
        risk_level=RiskLevel.MEDIUM,
        description="Buy call spread for bullish directional play with defined risk",
        market_outlook="Moderately bullish",
        max_profit="Width of spread - Debit paid",
        max_loss="Debit paid",
        breakeven="Long strike + Debit paid",
        legs=[
            {"type": "call", "strike": "ATM", "action": "buy", "quantity": 1},
            {"type": "call", "strike": "OTM", "action": "sell", "quantity": 1}
        ],
        entry_criteria=["Bullish outlook", "Target price at or above short strike", "30-60 DTE"],
        exit_criteria=["Close at 50% of max profit", "Cut at 50% loss"],
        adjustments=["Roll up short call if winning big", "Roll out in time if needed"],
        best_conditions=["Any IV environment", "Clear upside target", "Defined move expected"],
        avoid_when=["Expecting big move beyond short strike", "Very low IV"],
        example_trade={"stock": "AAPL", "long_call": 175, "short_call": 185, "debit": 4.00},
        tips=["Reduces cost vs long call", "Max profit if stock at short strike at expiry"]
    ),
    
    "put_debit_spread": StrategyPlaybook(
        id="put_debit_spread",
        name="Put Debit Spread (Bear Put)",
        category=StrategyCategory.DIRECTIONAL,
        risk_level=RiskLevel.MEDIUM,
        description="Buy put spread for bearish directional play with defined risk",
        market_outlook="Moderately bearish",
        max_profit="Width of spread - Debit paid",
        max_loss="Debit paid",
        breakeven="Long strike - Debit paid",
        legs=[
            {"type": "put", "strike": "ATM", "action": "buy", "quantity": 1},
            {"type": "put", "strike": "OTM", "action": "sell", "quantity": 1}
        ],
        entry_criteria=["Bearish outlook", "Target price at or below short strike"],
        exit_criteria=["Close at 50% of max profit", "Cut at 50% loss"],
        adjustments=["Roll down short put if winning"],
        best_conditions=["Any IV", "Clear downside target"],
        avoid_when=["Expecting big move below short strike"],
        example_trade={"stock": "AAPL", "long_put": 175, "short_put": 165, "debit": 4.00},
        tips=["Reduces cost vs long put", "Great for defined bearish plays"]
    ),
    
    # VOLATILITY STRATEGIES (10)
    "long_straddle": StrategyPlaybook(
        id="long_straddle",
        name="Long Straddle",
        category=StrategyCategory.VOLATILITY,
        risk_level=RiskLevel.HIGH,
        description="Buy ATM call and put for volatility expansion play",
        market_outlook="Expecting big move, direction unknown",
        max_profit="Unlimited",
        max_loss="Premium paid for both options",
        breakeven="Strike +/- Total premium paid",
        legs=[
            {"type": "call", "strike": "ATM", "action": "buy", "quantity": 1},
            {"type": "put", "strike": "ATM", "action": "buy", "quantity": 1}
        ],
        entry_criteria=["IV Rank < 30%", "Major catalyst expected", "45-60 DTE"],
        exit_criteria=["Close when premium doubles", "Cut at 50% loss"],
        adjustments=["Sell winning side, hold loser", "Convert to strangle"],
        best_conditions=["Low IV", "Before earnings/events", "Expecting volatility spike"],
        avoid_when=["High IV", "No catalyst", "Range-bound market"],
        example_trade={"stock": "AAPL", "strike": 175, "call_premium": 5.00, "put_premium": 4.50},
        tips=["Need big move to profit", "Time decay is your enemy"]
    ),
    
    "long_strangle": StrategyPlaybook(
        id="long_strangle",
        name="Long Strangle",
        category=StrategyCategory.VOLATILITY,
        risk_level=RiskLevel.HIGH,
        description="Buy OTM call and put for cheaper volatility play",
        market_outlook="Expecting big move, direction unknown",
        max_profit="Unlimited",
        max_loss="Premium paid",
        breakeven="Call strike + Premium / Put strike - Premium",
        legs=[
            {"type": "call", "strike": "OTM", "action": "buy", "quantity": 1},
            {"type": "put", "strike": "OTM", "action": "buy", "quantity": 1}
        ],
        entry_criteria=["IV Rank < 30%", "Major catalyst expected"],
        exit_criteria=["Target 100%+ profit", "Cut at 50% loss"],
        adjustments=["Sell winning side when ITM"],
        best_conditions=["Low IV", "High conviction on big move"],
        avoid_when=["High IV", "Range-bound expectation"],
        example_trade={"stock": "AAPL", "call_strike": 185, "put_strike": 165, "total_premium": 5.00},
        tips=["Cheaper than straddle but needs bigger move"]
    ),
    
    "short_straddle": StrategyPlaybook(
        id="short_straddle",
        name="Short Straddle",
        category=StrategyCategory.VOLATILITY,
        risk_level=RiskLevel.VERY_HIGH,
        description="Sell ATM call and put for premium",
        market_outlook="Expecting low volatility, range-bound",
        max_profit="Premium received",
        max_loss="Unlimited",
        breakeven="Strike +/- Premium received",
        legs=[
            {"type": "call", "strike": "ATM", "action": "sell", "quantity": 1},
            {"type": "put", "strike": "ATM", "action": "sell", "quantity": 1}
        ],
        entry_criteria=["IV Rank > 50%", "No catalysts", "Range-bound expectation"],
        exit_criteria=["Close at 25% profit", "Close if breached"],
        adjustments=["Roll tested side", "Convert to strangle"],
        best_conditions=["High IV", "Low realized volatility expected"],
        avoid_when=["Before earnings", "Trending market", "Low IV"],
        example_trade={"stock": "SPY", "strike": 450, "premium": 10.00},
        tips=["Very risky - unlimited loss potential", "Use only with experience"]
    ),
    
    "iron_butterfly": StrategyPlaybook(
        id="iron_butterfly",
        name="Iron Butterfly",
        category=StrategyCategory.VOLATILITY,
        risk_level=RiskLevel.MEDIUM,
        description="Short straddle with protective wings",
        market_outlook="Expecting very low volatility, pinning at strike",
        max_profit="Premium received",
        max_loss="Width of wings - Premium",
        breakeven="Strike +/- Premium received",
        legs=[
            {"type": "put", "strike": "OTM", "action": "buy", "quantity": 1},
            {"type": "put", "strike": "ATM", "action": "sell", "quantity": 1},
            {"type": "call", "strike": "ATM", "action": "sell", "quantity": 1},
            {"type": "call", "strike": "OTM", "action": "buy", "quantity": 1}
        ],
        entry_criteria=["IV Rank > 50%", "Expecting pin at strike", "45 DTE"],
        exit_criteria=["Close at 25-50% profit"],
        adjustments=["Roll if tested"],
        best_conditions=["Very high IV", "Known pin levels (monthly expiry)"],
        avoid_when=["Trending market", "Before events"],
        example_trade={"stock": "SPY", "short_strike": 450, "wings": 5, "premium": 3.50},
        tips=["Higher probability but needs more precise timing"]
    ),
    
    # EARNINGS STRATEGIES (5)
    "earnings_iron_condor": StrategyPlaybook(
        id="earnings_iron_condor",
        name="Earnings Iron Condor",
        category=StrategyCategory.EARNINGS,
        risk_level=RiskLevel.MEDIUM,
        description="Sell iron condor to capture IV crush after earnings",
        market_outlook="Expecting IV crush, contained move",
        max_profit="Net premium received",
        max_loss="Width of spread - Premium",
        breakeven="Short strikes +/- Premium",
        legs=[
            {"type": "put", "strike": "OTM", "action": "buy", "quantity": 1},
            {"type": "put", "strike": "closer OTM", "action": "sell", "quantity": 1},
            {"type": "call", "strike": "closer OTM", "action": "sell", "quantity": 1},
            {"type": "call", "strike": "OTM", "action": "buy", "quantity": 1}
        ],
        entry_criteria=[
            "High IV before earnings",
            "Expected move < spread width",
            "Enter day before earnings"
        ],
        exit_criteria=["Close day after earnings", "Close at 50% profit immediately"],
        adjustments=["Usually no adjustments - quick trade"],
        best_conditions=["Very high IV", "History of contained moves"],
        avoid_when=["Stock historically gaps big", "Guidance concerns"],
        example_trade={"stock": "AAPL", "put_spread": "165/160", "call_spread": "185/190"},
        tips=["Use expected move to set strikes", "Close immediately after earnings"]
    ),
    
    "earnings_straddle": StrategyPlaybook(
        id="earnings_straddle",
        name="Earnings Straddle",
        category=StrategyCategory.EARNINGS,
        risk_level=RiskLevel.HIGH,
        description="Buy straddle expecting bigger move than priced in",
        market_outlook="Expecting bigger move than expected",
        max_profit="Unlimited",
        max_loss="Premium paid",
        breakeven="Strike +/- Premium",
        legs=[
            {"type": "call", "strike": "ATM", "action": "buy", "quantity": 1},
            {"type": "put", "strike": "ATM", "action": "buy", "quantity": 1}
        ],
        entry_criteria=[
            "Expected move seems too low",
            "History of surprise earnings",
            "Major guidance expected"
        ],
        exit_criteria=["Close immediately after earnings"],
        adjustments=["None - quick trade"],
        best_conditions=["IV not fully pricing the risk", "Potential for big surprise"],
        avoid_when=["IV already very high", "Well-forecasted earnings"],
        example_trade={"stock": "TSLA", "strike": 250, "premium": 15.00},
        tips=["Need move larger than expected move", "Very risky"]
    ),
}


# =============================================================================
# TRADE JOURNAL TEMPLATES (Items 661-670)
# =============================================================================

@dataclass
class JournalTemplate:
    """Trade journal entry template."""
    id: str
    name: str
    fields: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "name": self.name, "fields": self.fields}


JOURNAL_TEMPLATES = {
    "standard": JournalTemplate(
        id="standard",
        name="Standard Trade Journal",
        fields=[
            {"name": "date", "type": "date", "required": True},
            {"name": "symbol", "type": "text", "required": True},
            {"name": "strategy", "type": "select", "options": list(STRATEGY_PLAYBOOKS.keys())},
            {"name": "direction", "type": "select", "options": ["long", "short"]},
            {"name": "entry_price", "type": "number", "required": True},
            {"name": "exit_price", "type": "number"},
            {"name": "quantity", "type": "number", "required": True},
            {"name": "pnl", "type": "number"},
            {"name": "notes", "type": "textarea"},
            {"name": "tags", "type": "tags"},
            {"name": "screenshot", "type": "file"}
        ]
    ),
    
    "options_detailed": JournalTemplate(
        id="options_detailed",
        name="Options Detailed Journal",
        fields=[
            {"name": "date", "type": "date", "required": True},
            {"name": "symbol", "type": "text", "required": True},
            {"name": "strategy", "type": "select", "options": list(STRATEGY_PLAYBOOKS.keys())},
            {"name": "legs", "type": "legs_builder"},
            {"name": "iv_at_entry", "type": "number"},
            {"name": "iv_at_exit", "type": "number"},
            {"name": "delta", "type": "number"},
            {"name": "theta", "type": "number"},
            {"name": "dte_at_entry", "type": "number"},
            {"name": "entry_premium", "type": "number"},
            {"name": "exit_premium", "type": "number"},
            {"name": "commission", "type": "number"},
            {"name": "pnl", "type": "number"},
            {"name": "trade_rationale", "type": "textarea"},
            {"name": "what_went_well", "type": "textarea"},
            {"name": "what_to_improve", "type": "textarea"},
            {"name": "lesson_learned", "type": "textarea"},
            {"name": "emotion_at_entry", "type": "select", "options": ["confident", "fearful", "greedy", "neutral"]},
            {"name": "emotion_at_exit", "type": "select", "options": ["satisfied", "regretful", "relieved", "frustrated"]},
            {"name": "followed_plan", "type": "boolean"},
            {"name": "tags", "type": "tags"}
        ]
    ),
    
    "quick_note": JournalTemplate(
        id="quick_note",
        name="Quick Note",
        fields=[
            {"name": "date", "type": "date", "required": True},
            {"name": "symbol", "type": "text"},
            {"name": "note", "type": "textarea", "required": True},
            {"name": "tags", "type": "tags"}
        ]
    )
}


# =============================================================================
# RISK ALLOCATION GUIDES (Items 671-680)
# =============================================================================

@dataclass
class RiskAllocationGuide:
    """Risk allocation guide definition."""
    id: str
    name: str
    description: str
    account_size_min: int
    max_position_size_pct: float
    max_portfolio_risk_pct: float
    max_single_trade_risk_pct: float
    diversification_rules: List[str]
    position_sizing_method: str
    allocation_by_strategy: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "account_size_min": self.account_size_min,
            "max_position_size_pct": self.max_position_size_pct,
            "max_portfolio_risk_pct": self.max_portfolio_risk_pct,
            "max_single_trade_risk_pct": self.max_single_trade_risk_pct,
            "diversification_rules": self.diversification_rules,
            "position_sizing_method": self.position_sizing_method,
            "allocation_by_strategy": self.allocation_by_strategy
        }


RISK_GUIDES = {
    "conservative": RiskAllocationGuide(
        id="conservative",
        name="Conservative (Wealth Preservation)",
        description="Focus on capital preservation with steady income",
        account_size_min=50000,
        max_position_size_pct=5.0,
        max_portfolio_risk_pct=10.0,
        max_single_trade_risk_pct=1.0,
        diversification_rules=[
            "Maximum 20 positions",
            "Maximum 10% in any single underlying",
            "Maximum 30% in any sector",
            "Always maintain 20% cash reserve"
        ],
        position_sizing_method="fixed_percentage",
        allocation_by_strategy={
            "covered_call": 40,
            "cash_secured_put": 30,
            "iron_condor": 20,
            "protective_puts": 10
        }
    ),
    
    "moderate": RiskAllocationGuide(
        id="moderate",
        name="Moderate (Balanced Growth)",
        description="Balance between growth and risk management",
        account_size_min=25000,
        max_position_size_pct=10.0,
        max_portfolio_risk_pct=20.0,
        max_single_trade_risk_pct=2.0,
        diversification_rules=[
            "Maximum 15 positions",
            "Maximum 15% in any single underlying",
            "Maximum 40% in any sector",
            "Maintain 10% cash reserve"
        ],
        position_sizing_method="volatility_adjusted",
        allocation_by_strategy={
            "credit_spreads": 35,
            "iron_condor": 25,
            "debit_spreads": 20,
            "covered_call": 15,
            "long_options": 5
        }
    ),
    
    "aggressive": RiskAllocationGuide(
        id="aggressive",
        name="Aggressive (Growth Focus)",
        description="Higher risk tolerance for growth potential",
        account_size_min=10000,
        max_position_size_pct=20.0,
        max_portfolio_risk_pct=35.0,
        max_single_trade_risk_pct=5.0,
        diversification_rules=[
            "Maximum 10 positions",
            "Maximum 25% in any single underlying",
            "Maximum 50% in any sector"
        ],
        position_sizing_method="kelly_criterion",
        allocation_by_strategy={
            "debit_spreads": 30,
            "long_options": 25,
            "credit_spreads": 25,
            "straddles_strangles": 15,
            "earnings_plays": 5
        }
    )
}


# =============================================================================
# EDUCATIONAL CONTENT (Items 681-700)
# =============================================================================

@dataclass
class EducationalModule:
    """Educational content module."""
    id: str
    title: str
    description: str
    difficulty: str  # beginner, intermediate, advanced
    duration_minutes: int
    topics: List[str]
    prerequisites: List[str]
    content_sections: List[Dict[str, Any]]
    quiz_questions: List[Dict[str, Any]]


EDUCATIONAL_MODULES = {
    "options_basics": EducationalModule(
        id="options_basics",
        title="Options 101: The Fundamentals",
        description="Learn the basics of options trading",
        difficulty="beginner",
        duration_minutes=45,
        topics=["calls", "puts", "strike price", "expiration", "premium"],
        prerequisites=[],
        content_sections=[
            {"title": "What is an Option?", "type": "text", "content": "An option is a contract..."},
            {"title": "Call Options", "type": "video", "url": "/videos/calls.mp4"},
            {"title": "Put Options", "type": "video", "url": "/videos/puts.mp4"},
            {"title": "Interactive Demo", "type": "interactive", "component": "options_basics_demo"}
        ],
        quiz_questions=[
            {"q": "What gives the holder the right to buy?", "options": ["Call", "Put"], "answer": 0},
            {"q": "What is the price to exercise an option?", "options": ["Premium", "Strike"], "answer": 1}
        ]
    ),
    
    "greeks_explained": EducationalModule(
        id="greeks_explained",
        title="Understanding the Greeks",
        description="Master delta, gamma, theta, vega, and rho",
        difficulty="intermediate",
        duration_minutes=60,
        topics=["delta", "gamma", "theta", "vega", "rho"],
        prerequisites=["options_basics"],
        content_sections=[
            {"title": "Delta: Direction", "type": "interactive", "component": "delta_slider"},
            {"title": "Gamma: Rate of Change", "type": "text"},
            {"title": "Theta: Time Decay", "type": "interactive", "component": "theta_decay"},
            {"title": "Vega: Volatility", "type": "text"},
            {"title": "Rho: Interest Rates", "type": "text"}
        ],
        quiz_questions=[]
    ),
    
    "spread_strategies": EducationalModule(
        id="spread_strategies",
        title="Spread Strategy Mastery",
        description="Learn vertical, horizontal, and diagonal spreads",
        difficulty="intermediate",
        duration_minutes=90,
        topics=["vertical spreads", "calendar spreads", "diagonal spreads"],
        prerequisites=["options_basics", "greeks_explained"],
        content_sections=[
            {"title": "Vertical Spreads", "type": "text"},
            {"title": "Calendar Spreads", "type": "text"},
            {"title": "Diagonal Spreads", "type": "text"},
            {"title": "Spread Builder Practice", "type": "interactive", "component": "spread_builder"}
        ],
        quiz_questions=[]
    ),
    
    "risk_management": EducationalModule(
        id="risk_management",
        title="Risk Management for Options Traders",
        description="Protect your capital with proper risk management",
        difficulty="intermediate",
        duration_minutes=75,
        topics=["position sizing", "stop losses", "portfolio beta", "hedging"],
        prerequisites=["options_basics"],
        content_sections=[
            {"title": "Position Sizing Methods", "type": "text"},
            {"title": "Stop Loss Strategies", "type": "text"},
            {"title": "Portfolio Risk Calculator", "type": "interactive", "component": "risk_calculator"},
            {"title": "Hedging Techniques", "type": "text"}
        ],
        quiz_questions=[]
    ),
    
    "volatility_trading": EducationalModule(
        id="volatility_trading",
        title="Trading Volatility",
        description="Advanced strategies for volatility trading",
        difficulty="advanced",
        duration_minutes=120,
        topics=["IV rank", "IV percentile", "vol surface", "skew", "term structure"],
        prerequisites=["greeks_explained", "spread_strategies"],
        content_sections=[
            {"title": "Understanding Implied Volatility", "type": "text"},
            {"title": "Vol Surface Analysis", "type": "interactive", "component": "vol_surface"},
            {"title": "Trading the Skew", "type": "text"},
            {"title": "Term Structure Strategies", "type": "text"}
        ],
        quiz_questions=[]
    )
}


# =============================================================================
# COMPLETE PHASE 9
# =============================================================================

def get_all_playbooks() -> Dict[str, Dict]:
    """Get all strategy playbooks."""
    return {k: v.to_dict() for k, v in STRATEGY_PLAYBOOKS.items()}


def get_playbook(playbook_id: str) -> Optional[Dict]:
    """Get specific playbook by ID."""
    playbook = STRATEGY_PLAYBOOKS.get(playbook_id)
    return playbook.to_dict() if playbook else None


def get_all_templates() -> Dict[str, Dict]:
    """Get all journal templates."""
    return {k: v.to_dict() for k, v in JOURNAL_TEMPLATES.items()}


def get_all_risk_guides() -> Dict[str, Dict]:
    """Get all risk allocation guides."""
    return {k: v.to_dict() for k, v in RISK_GUIDES.items()}


def complete_phase_9() -> Dict[str, Any]:
    """Complete Phase 9 deliverables."""
    return {
        "playbooks_count": len(STRATEGY_PLAYBOOKS),
        "templates_count": len(JOURNAL_TEMPLATES),
        "risk_guides_count": len(RISK_GUIDES),
        "education_modules_count": len(EDUCATIONAL_MODULES),
        "status": "complete"
    }


if __name__ == "__main__":
    print("Phase 9 Summary:")
    result = complete_phase_9()
    for k, v in result.items():
        print(f"  {k}: {v}")
