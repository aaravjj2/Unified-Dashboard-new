"""
Enhanced AI Recommendations Engine (v2)
=========================================
Provides detailed trade recommendations with:
- Complete option contract details (strike, expiry, current price)
- Clear entry/exit criteria
- Step-by-step action plans
- Risk/reward analysis
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)


class RecommendationType(str, Enum):
    """Trade recommendation categories."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    HIGH_IV = "high_iv"
    LOW_IV = "low_iv"
    EARNINGS = "earnings"
    INCOME = "income"


@dataclass
class OptionLeg:
    """Detailed option leg information."""
    leg_type: str  # 'call', 'put', 'stock'
    action: str  # 'buy', 'sell', 'hold'
    strike: float
    expiration: str
    current_price: float  # Current option premium
    quantity: int = 1
    delta: Optional[float] = None
    iv: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    open_interest: Optional[int] = None
    volume: Optional[int] = None
    
    def to_dict(self) -> Dict:
        return {
            'type': self.leg_type,
            'action': self.action,
            'strike': self.strike,
            'expiration': self.expiration,
            'current_price': self.current_price,
            'quantity': self.quantity,
            'delta': self.delta,
            'iv': self.iv,
            'bid': self.bid,
            'ask': self.ask,
            'open_interest': self.open_interest,
            'volume': self.volume,
        }
    
    def display_string(self) -> str:
        """Human-readable leg description."""
        price_str = f"${self.current_price:.2f}" if self.current_price else "N/A"
        iv_str = f" (IV: {self.iv*100:.1f}%)" if self.iv else ""
        return f"{self.action.upper()} {self.leg_type.upper()} ${self.strike:.2f} exp {self.expiration} @ {price_str}{iv_str}"


@dataclass
class DetailedRecommendation:
    """Complete trade recommendation with all details."""
    ticker: str
    strategy: str
    recommendation_type: RecommendationType
    current_stock_price: float
    
    # Option legs with full details
    legs: List[OptionLeg] = field(default_factory=list)
    
    # Trade metrics
    max_profit: float = 0.0
    max_loss: float = 0.0
    breakeven_prices: List[float] = field(default_factory=list)
    expected_roi: float = 0.0
    probability_of_profit: float = 0.0
    
    # Risk assessment
    risk_level: str = "medium"  # low, medium, high
    confidence: float = 50.0  # 0-100
    
    # Rationale and plan
    rationale: str = ""
    market_thesis: str = ""
    
    # Entry criteria
    entry_criteria: Dict[str, Any] = field(default_factory=dict)
    
    # Exit criteria
    exit_criteria: Dict[str, Any] = field(default_factory=dict)
    
    # Step-by-step action plan
    action_plan: List[str] = field(default_factory=list)
    
    # Time horizon
    time_horizon: str = ""
    days_to_expiry: int = 0
    
    # Metadata
    generated_at: str = ""
    data_source: str = "live"
    
    def to_dict(self) -> Dict:
        return {
            'ticker': self.ticker,
            'strategy': self.strategy,
            'recommendation_type': self.recommendation_type.value,
            'current_stock_price': self.current_stock_price,
            'legs': [leg.to_dict() for leg in self.legs],
            'max_profit': self.max_profit,
            'max_loss': self.max_loss,
            'breakeven_prices': self.breakeven_prices,
            'expected_roi': self.expected_roi,
            'probability_of_profit': self.probability_of_profit,
            'risk_level': self.risk_level,
            'confidence': self.confidence,
            'rationale': self.rationale,
            'market_thesis': self.market_thesis,
            'entry_criteria': self.entry_criteria,
            'exit_criteria': self.exit_criteria,
            'action_plan': self.action_plan,
            'time_horizon': self.time_horizon,
            'days_to_expiry': self.days_to_expiry,
            'generated_at': self.generated_at,
            'data_source': self.data_source,
        }


class EnhancedAIRecommendationEngine:
    """
    Enhanced AI recommendation engine with full trade details.
    """
    
    def __init__(self):
        self.recommendations: List[DetailedRecommendation] = []
        self._market_data_cache: Dict[str, Dict] = {}
    
    def generate_recommendations(
        self,
        tickers: List[str] = None,
        recommendation_types: List[str] = None,
    ) -> List[DetailedRecommendation]:
        """
        Generate detailed recommendations for given tickers.
        
        Args:
            tickers: List of stock tickers
            recommendation_types: Filter by recommendation type
            
        Returns:
            List of DetailedRecommendation objects
        """
        if tickers is None:
            tickers = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMD', 'SPY', 'QQQ']
        
        self.recommendations = []
        
        for ticker in tickers:
            market_data = self._fetch_market_data(ticker)
            ticker_recs = self._analyze_ticker(ticker, market_data)
            self.recommendations.extend(ticker_recs)
        
        # Sort by confidence
        self.recommendations.sort(key=lambda x: x.confidence, reverse=True)
        
        # Filter by type if specified
        if recommendation_types:
            self.recommendations = [
                r for r in self.recommendations
                if r.recommendation_type.value in recommendation_types
            ]
        
        return self.recommendations
    
    def _fetch_market_data(self, ticker: str) -> Dict[str, Any]:
        """Fetch current market data for ticker."""
        if ticker in self._market_data_cache:
            cache = self._market_data_cache[ticker]
            # Check if cache is fresh (< 5 min)
            if (datetime.now() - cache.get('timestamp', datetime.min)).seconds < 300:
                return cache
        
        # Try to get real data
        data = self._get_live_data(ticker)
        if not data:
            data = self._generate_mock_data(ticker)
        
        data['timestamp'] = datetime.now()
        self._market_data_cache[ticker] = data
        return data
    
    def _get_live_data(self, ticker: str) -> Optional[Dict]:
        """Try to fetch live market data."""
        try:
            from financial_dashboard.utils.price_fetch import get_current_price, fetch_options_chain
            
            price = get_current_price(ticker)
            if price is None:
                return None
            
            # Try to get options chain
            chain = None
            try:
                chain = fetch_options_chain(ticker)
            except Exception:
                pass
            
            # Calculate IV metrics
            iv = 0.25  # Default
            iv_percentile = 50
            if chain and 'calls' in chain:
                # Extract ATM IV
                atm_options = [c for c in chain.get('calls', []) if abs(c.get('strike', 0) - price) < price * 0.02]
                if atm_options:
                    iv = atm_options[0].get('impliedVolatility', 0.25)
            
            return {
                'spot': price,
                'iv': iv,
                'iv_percentile': iv_percentile,
                'iv_rank': iv_percentile / 100,
                'trend': self._detect_trend(ticker, price),
                'earnings_soon': self._check_earnings(ticker),
                'support': price * 0.95,
                'resistance': price * 1.05,
                'chain': chain,
                'source': 'live'
            }
        except Exception as e:
            logger.warning(f"Could not fetch live data for {ticker}: {e}")
            return None
    
    def _generate_mock_data(self, ticker: str) -> Dict:
        """Generate deterministic mock data for testing."""
        np.random.seed(hash(ticker) % 10000)
        spot = np.random.uniform(50, 500)
        
        return {
            'spot': spot,
            'iv': np.random.uniform(0.15, 0.60),
            'iv_percentile': np.random.randint(10, 90),
            'iv_rank': np.random.uniform(0.1, 0.9),
            'trend': np.random.choice(['bullish', 'bearish', 'neutral']),
            'earnings_soon': np.random.random() > 0.85,
            'support': spot * np.random.uniform(0.92, 0.98),
            'resistance': spot * np.random.uniform(1.02, 1.08),
            'chain': None,
            'source': 'mock'
        }
    
    def _detect_trend(self, ticker: str, current_price: float) -> str:
        """Simple trend detection."""
        # In production, would use technical analysis
        return 'neutral'
    
    def _check_earnings(self, ticker: str) -> bool:
        """Check if earnings are within 2 weeks."""
        # In production, would check earnings calendar
        return False
    
    def _analyze_ticker(self, ticker: str, data: Dict) -> List[DetailedRecommendation]:
        """Analyze ticker and generate recommendations."""
        recommendations = []
        
        spot = data['spot']
        iv = data['iv']
        iv_percentile = data['iv_percentile']
        trend = data['trend']
        support = data['support']
        resistance = data['resistance']
        earnings_soon = data['earnings_soon']
        
        # High IV strategies (sell premium)
        if iv_percentile > 70:
            recommendations.extend(self._high_iv_strategies(ticker, spot, iv, iv_percentile, support, resistance, data))
        
        # Low IV strategies (buy premium)
        if iv_percentile < 30:
            recommendations.extend(self._low_iv_strategies(ticker, spot, iv, iv_percentile, trend, resistance, data))
        
        # Directional strategies
        if trend == 'bullish':
            recommendations.extend(self._bullish_strategies(ticker, spot, iv, resistance, data))
        elif trend == 'bearish':
            recommendations.extend(self._bearish_strategies(ticker, spot, iv, support, data))
        
        # Income strategies
        recommendations.extend(self._income_strategies(ticker, spot, iv, resistance, data))
        
        # Earnings plays
        if earnings_soon:
            recommendations.extend(self._earnings_strategies(ticker, spot, iv, data))
        
        return recommendations
    
    def _high_iv_strategies(self, ticker: str, spot: float, iv: float, iv_pct: int, support: float, resistance: float, data: Dict) -> List[DetailedRecommendation]:
        """Generate high IV (sell premium) strategies."""
        recs = []
        expiry = self._get_expiry_date(45)
        dte = 45
        
        # Iron Condor
        short_put = round(support * 0.95, 2)
        long_put = round(short_put - 5, 2)
        short_call = round(resistance * 1.05, 2)
        long_call = round(short_call + 5, 2)
        
        # Estimate option prices
        sp_price = self._estimate_option_price(spot, short_put, dte, iv, 'put')
        lp_price = self._estimate_option_price(spot, long_put, dte, iv, 'put')
        sc_price = self._estimate_option_price(spot, short_call, dte, iv, 'call')
        lc_price = self._estimate_option_price(spot, long_call, dte, iv, 'call')
        
        credit = (sp_price - lp_price) + (sc_price - lc_price)
        max_loss = 5.0 - credit  # Width of spread minus credit
        
        rec = DetailedRecommendation(
            ticker=ticker,
            strategy="Iron Condor",
            recommendation_type=RecommendationType.HIGH_IV,
            current_stock_price=spot,
            legs=[
                OptionLeg('put', 'buy', long_put, expiry, round(lp_price, 2), iv=iv),
                OptionLeg('put', 'sell', short_put, expiry, round(sp_price, 2), iv=iv),
                OptionLeg('call', 'sell', short_call, expiry, round(sc_price, 2), iv=iv),
                OptionLeg('call', 'buy', long_call, expiry, round(lc_price, 2), iv=iv),
            ],
            max_profit=round(credit * 100, 2),
            max_loss=round(max_loss * 100, 2),
            breakeven_prices=[short_put - credit, short_call + credit],
            expected_roi=round((credit / max_loss) * 100, 1),
            probability_of_profit=65.0,
            risk_level="medium",
            confidence=75.0,
            rationale=f"IV Percentile at {iv_pct}% - options are expensive. Iron Condor captures premium decay while defining risk.",
            market_thesis=f"Expect {ticker} to trade between ${short_put:.2f} and ${short_call:.2f} over next {dte} days.",
            entry_criteria={
                'iv_percentile_min': 70,
                'price_range': f"${short_put:.2f} - ${short_call:.2f}",
                'ideal_entry': "After a volatility spike, when IV is elevated",
            },
            exit_criteria={
                'profit_target': f"50% of max profit (${round(credit * 50, 2)})",
                'stop_loss': f"2x credit received (${round(credit * 200, 2)} loss)",
                'time_exit': f"Close at 21 DTE if not profitable",
            },
            action_plan=[
                f"1. SELL {ticker} {expiry} ${short_put:.2f} PUT @ ${sp_price:.2f}",
                f"2. BUY {ticker} {expiry} ${long_put:.2f} PUT @ ${lp_price:.2f}",
                f"3. SELL {ticker} {expiry} ${short_call:.2f} CALL @ ${sc_price:.2f}",
                f"4. BUY {ticker} {expiry} ${long_call:.2f} CALL @ ${lc_price:.2f}",
                f"5. Net CREDIT: ${credit:.2f} per spread (${credit*100:.2f} total)",
                f"6. Set profit alert at ${round(credit * 0.5, 2)} remaining value",
                f"7. Monitor daily for breakeven breach",
            ],
            time_horizon=f"{dte} days to expiration",
            days_to_expiry=dte,
            generated_at=datetime.now().isoformat(),
            data_source=data.get('source', 'mock'),
        )
        recs.append(rec)
        
        return recs
    
    def _low_iv_strategies(self, ticker: str, spot: float, iv: float, iv_pct: int, trend: str, resistance: float, data: Dict) -> List[DetailedRecommendation]:
        """Generate low IV (buy premium) strategies."""
        recs = []
        expiry = self._get_expiry_date(60)
        dte = 60
        
        if trend == 'bullish':
            strike = round(resistance, 2)
            price = self._estimate_option_price(spot, strike, dte, iv, 'call')
            
            rec = DetailedRecommendation(
                ticker=ticker,
                strategy="Long Call",
                recommendation_type=RecommendationType.LOW_IV,
                current_stock_price=spot,
                legs=[
                    OptionLeg('call', 'buy', strike, expiry, round(price, 2), iv=iv),
                ],
                max_profit=float('inf'),
                max_loss=round(price * 100, 2),
                breakeven_prices=[strike + price],
                expected_roi=100.0,
                probability_of_profit=45.0,
                risk_level="high",
                confidence=60.0,
                rationale=f"IV Percentile at {iv_pct}% - options are cheap. Bullish trend suggests upside potential.",
                market_thesis=f"Expect {ticker} to break above ${resistance:.2f} resistance within {dte} days.",
                entry_criteria={
                    'iv_percentile_max': 30,
                    'trend_confirmation': 'bullish',
                    'catalyst': 'breakout above resistance',
                },
                exit_criteria={
                    'profit_target': "100%+ of premium paid",
                    'stop_loss': "50% of premium",
                    'time_exit': "Exit at 21 DTE",
                },
                action_plan=[
                    f"1. BUY {ticker} {expiry} ${strike:.2f} CALL @ ${price:.2f}",
                    f"2. Cost: ${price * 100:.2f} per contract",
                    f"3. Breakeven at expiry: ${strike + price:.2f}",
                    f"4. Set alert for ${strike:.2f} resistance breakout",
                    f"5. Take profit at 100% gain (${price * 2:.2f} option value)",
                ],
                time_horizon=f"{dte} days to expiration",
                days_to_expiry=dte,
                generated_at=datetime.now().isoformat(),
                data_source=data.get('source', 'mock'),
            )
            recs.append(rec)
        
        return recs
    
    def _bullish_strategies(self, ticker: str, spot: float, iv: float, resistance: float, data: Dict) -> List[DetailedRecommendation]:
        """Generate bullish strategies."""
        recs = []
        expiry = self._get_expiry_date(45)
        dte = 45
        
        # Bull Call Spread
        long_strike = round(spot, 2)
        short_strike = round(resistance * 1.05, 2)
        
        long_price = self._estimate_option_price(spot, long_strike, dte, iv, 'call')
        short_price = self._estimate_option_price(spot, short_strike, dte, iv, 'call')
        
        debit = long_price - short_price
        max_profit = (short_strike - long_strike) - debit
        
        rec = DetailedRecommendation(
            ticker=ticker,
            strategy="Bull Call Spread",
            recommendation_type=RecommendationType.BULLISH,
            current_stock_price=spot,
            legs=[
                OptionLeg('call', 'buy', long_strike, expiry, round(long_price, 2), iv=iv),
                OptionLeg('call', 'sell', short_strike, expiry, round(short_price, 2), iv=iv),
            ],
            max_profit=round(max_profit * 100, 2),
            max_loss=round(debit * 100, 2),
            breakeven_prices=[long_strike + debit],
            expected_roi=round((max_profit / debit) * 100, 1),
            probability_of_profit=50.0,
            risk_level="medium",
            confidence=65.0,
            rationale=f"Bullish outlook on {ticker} with defined risk. Spread reduces cost vs naked call.",
            market_thesis=f"Expect {ticker} to rise toward ${short_strike:.2f} by expiration.",
            entry_criteria={
                'trend': 'bullish',
                'support_holding': True,
                'volume_confirmation': 'above average',
            },
            exit_criteria={
                'profit_target': "50% of max profit",
                'stop_loss': "50% of debit paid",
                'time_exit': "Roll or close at 14 DTE",
            },
            action_plan=[
                f"1. BUY {ticker} {expiry} ${long_strike:.2f} CALL @ ${long_price:.2f}",
                f"2. SELL {ticker} {expiry} ${short_strike:.2f} CALL @ ${short_price:.2f}",
                f"3. Net DEBIT: ${debit:.2f} (${debit*100:.2f} per spread)",
                f"4. Max profit if {ticker} ≥ ${short_strike:.2f} at expiry",
                f"5. Take profit at 50% max gain",
            ],
            time_horizon=f"{dte} days to expiration",
            days_to_expiry=dte,
            generated_at=datetime.now().isoformat(),
            data_source=data.get('source', 'mock'),
        )
        recs.append(rec)
        
        return recs
    
    def _bearish_strategies(self, ticker: str, spot: float, iv: float, support: float, data: Dict) -> List[DetailedRecommendation]:
        """Generate bearish strategies."""
        recs = []
        expiry = self._get_expiry_date(45)
        dte = 45
        
        # Bear Put Spread
        long_strike = round(spot, 2)
        short_strike = round(support * 0.95, 2)
        
        long_price = self._estimate_option_price(spot, long_strike, dte, iv, 'put')
        short_price = self._estimate_option_price(spot, short_strike, dte, iv, 'put')
        
        debit = long_price - short_price
        max_profit = (long_strike - short_strike) - debit
        
        rec = DetailedRecommendation(
            ticker=ticker,
            strategy="Bear Put Spread",
            recommendation_type=RecommendationType.BEARISH,
            current_stock_price=spot,
            legs=[
                OptionLeg('put', 'buy', long_strike, expiry, round(long_price, 2), iv=iv),
                OptionLeg('put', 'sell', short_strike, expiry, round(short_price, 2), iv=iv),
            ],
            max_profit=round(max_profit * 100, 2),
            max_loss=round(debit * 100, 2),
            breakeven_prices=[long_strike - debit],
            expected_roi=round((max_profit / debit) * 100, 1),
            probability_of_profit=50.0,
            risk_level="medium",
            confidence=65.0,
            rationale=f"Bearish outlook on {ticker}. Spread defines risk while profiting from decline.",
            market_thesis=f"Expect {ticker} to fall toward ${short_strike:.2f} support area.",
            entry_criteria={
                'trend': 'bearish',
                'resistance_rejection': True,
                'weakness_signals': 'present',
            },
            exit_criteria={
                'profit_target': "50% of max profit",
                'stop_loss': "50% of debit paid",
                'time_exit': "Roll or close at 14 DTE",
            },
            action_plan=[
                f"1. BUY {ticker} {expiry} ${long_strike:.2f} PUT @ ${long_price:.2f}",
                f"2. SELL {ticker} {expiry} ${short_strike:.2f} PUT @ ${short_price:.2f}",
                f"3. Net DEBIT: ${debit:.2f} (${debit*100:.2f} per spread)",
                f"4. Max profit if {ticker} ≤ ${short_strike:.2f} at expiry",
            ],
            time_horizon=f"{dte} days to expiration",
            days_to_expiry=dte,
            generated_at=datetime.now().isoformat(),
            data_source=data.get('source', 'mock'),
        )
        recs.append(rec)
        
        return recs
    
    def _income_strategies(self, ticker: str, spot: float, iv: float, resistance: float, data: Dict) -> List[DetailedRecommendation]:
        """Generate income strategies."""
        recs = []
        expiry = self._get_expiry_date(30)
        dte = 30
        
        # Covered Call
        strike = round(resistance * 1.05, 2)
        call_price = self._estimate_option_price(spot, strike, dte, iv, 'call')
        
        rec = DetailedRecommendation(
            ticker=ticker,
            strategy="Covered Call",
            recommendation_type=RecommendationType.INCOME,
            current_stock_price=spot,
            legs=[
                OptionLeg('stock', 'hold', spot, 'N/A', spot, quantity=100),
                OptionLeg('call', 'sell', strike, expiry, round(call_price, 2), iv=iv),
            ],
            max_profit=round(((strike - spot) + call_price) * 100, 2),
            max_loss=round((spot - call_price) * 100, 2),
            breakeven_prices=[spot - call_price],
            expected_roi=round((call_price / spot) * 100 * 12, 1),  # Annualized
            probability_of_profit=75.0,
            risk_level="low",
            confidence=80.0,
            rationale=f"Generate income on {ticker} shares by selling OTM calls.",
            market_thesis=f"Expect {ticker} to stay below ${strike:.2f} through expiration.",
            entry_criteria={
                'position': f'Own 100+ shares of {ticker}',
                'outlook': 'neutral to slightly bullish',
                'willing_to_sell': f'at ${strike:.2f}',
            },
            exit_criteria={
                'expiration': 'Let expire worthless ideally',
                'roll': 'Roll if approaching ITM',
                'assignment': 'Accept if called away',
            },
            action_plan=[
                f"1. Ensure you own 100 shares of {ticker} (current: ${spot:.2f})",
                f"2. SELL 1 {ticker} {expiry} ${strike:.2f} CALL @ ${call_price:.2f}",
                f"3. Collect ${call_price * 100:.2f} premium immediately",
                f"4. If stock stays below ${strike:.2f}, keep premium + shares",
                f"5. If called away, profit = ${((strike - spot) + call_price) * 100:.2f}",
            ],
            time_horizon=f"{dte} days to expiration",
            days_to_expiry=dte,
            generated_at=datetime.now().isoformat(),
            data_source=data.get('source', 'mock'),
        )
        recs.append(rec)
        
        return recs
    
    def _earnings_strategies(self, ticker: str, spot: float, iv: float, data: Dict) -> List[DetailedRecommendation]:
        """Generate earnings play strategies."""
        recs = []
        expiry = self._get_expiry_date(7)
        dte = 7
        
        # Long Straddle
        strike = round(spot, 2)
        call_price = self._estimate_option_price(spot, strike, dte, iv * 1.3, 'call')  # Elevated IV
        put_price = self._estimate_option_price(spot, strike, dte, iv * 1.3, 'put')
        
        total_cost = call_price + put_price
        
        rec = DetailedRecommendation(
            ticker=ticker,
            strategy="Long Straddle (Earnings)",
            recommendation_type=RecommendationType.EARNINGS,
            current_stock_price=spot,
            legs=[
                OptionLeg('call', 'buy', strike, expiry, round(call_price, 2), iv=iv*1.3),
                OptionLeg('put', 'buy', strike, expiry, round(put_price, 2), iv=iv*1.3),
            ],
            max_profit=float('inf'),
            max_loss=round(total_cost * 100, 2),
            breakeven_prices=[strike - total_cost, strike + total_cost],
            expected_roi=50.0,
            probability_of_profit=40.0,
            risk_level="high",
            confidence=55.0,
            rationale=f"Earnings announcement expected. Historical move may exceed implied move.",
            market_thesis=f"Expect big move in {ticker} post-earnings (either direction).",
            entry_criteria={
                'days_to_earnings': '3-5 days',
                'iv_not_extreme': f"Current IV: {iv*100:.1f}%",
                'historical_surprise': 'check past earnings moves',
            },
            exit_criteria={
                'timing': 'Close before earnings or same day after',
                'profit_target': '30%+',
                'max_loss': 'Total premium if held through',
            },
            action_plan=[
                f"1. BUY {ticker} {expiry} ${strike:.2f} CALL @ ${call_price:.2f}",
                f"2. BUY {ticker} {expiry} ${strike:.2f} PUT @ ${put_price:.2f}",
                f"3. Total DEBIT: ${total_cost:.2f} (${total_cost*100:.2f} per straddle)",
                f"4. Need {ticker} to move ±${total_cost:.2f} to breakeven",
                f"5. Consider closing before earnings if IV has spiked",
                f"6. High risk - IV crush post-earnings typical",
            ],
            time_horizon=f"{dte} days to expiration",
            days_to_expiry=dte,
            generated_at=datetime.now().isoformat(),
            data_source=data.get('source', 'mock'),
        )
        recs.append(rec)
        
        return recs
    
    def _estimate_option_price(self, spot: float, strike: float, dte: int, iv: float, option_type: str) -> float:
        """Estimate option price using simplified Black-Scholes approximation."""
        from math import exp, log, sqrt
        
        T = dte / 365.0
        r = 0.05  # Risk-free rate
        
        if T <= 0:
            # At expiry
            if option_type == 'call':
                return max(0, spot - strike)
            else:
                return max(0, strike - spot)
        
        # Simplified BS approximation
        d1 = (log(spot / strike) + (r + 0.5 * iv**2) * T) / (iv * sqrt(T))
        
        # Simple approximation
        if option_type == 'call':
            if spot > strike:
                intrinsic = spot - strike
                time_value = spot * 0.4 * iv * sqrt(T)
            else:
                intrinsic = 0
                time_value = spot * 0.4 * iv * sqrt(T) * exp(-0.5 * ((strike - spot) / (spot * iv * sqrt(T)))**2)
        else:
            if strike > spot:
                intrinsic = strike - spot
                time_value = spot * 0.4 * iv * sqrt(T)
            else:
                intrinsic = 0
                time_value = spot * 0.4 * iv * sqrt(T) * exp(-0.5 * ((spot - strike) / (spot * iv * sqrt(T)))**2)
        
        return max(0.01, intrinsic + time_value)
    
    def _get_expiry_date(self, days: int) -> str:
        """Get expiry date string for given days out."""
        target = datetime.now() + timedelta(days=days)
        # Find next Friday
        days_until_friday = (4 - target.weekday()) % 7
        if days_until_friday == 0 and target.weekday() != 4:
            days_until_friday = 7
        expiry = target + timedelta(days=days_until_friday)
        return expiry.strftime('%Y-%m-%d')


# Singleton
_engine = None

def get_enhanced_recommendation_engine() -> EnhancedAIRecommendationEngine:
    """Get singleton enhanced engine instance."""
    global _engine
    if _engine is None:
        _engine = EnhancedAIRecommendationEngine()
    return _engine


def generate_detailed_recommendations(
    tickers: List[str] = None,
    recommendation_types: List[str] = None
) -> List[Dict]:
    """
    Convenience function to generate recommendations.
    Returns list of dicts for easy JSON serialization.
    """
    engine = get_enhanced_recommendation_engine()
    recs = engine.generate_recommendations(tickers, recommendation_types)
    return [r.to_dict() for r in recs]
