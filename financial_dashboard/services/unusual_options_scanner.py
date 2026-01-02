"""
Unusual Options Activity Scanner
Implements #134 from ROADMAP_ULTIMATE.md
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class FlowType(Enum):
    """Type of unusual options flow"""
    BULLISH_CALL = "bullish_call"
    BEARISH_PUT = "bearish_put"
    BULLISH_PUT_SELL = "bullish_put_sell"
    BEARISH_CALL_SELL = "bearish_call_sell"
    SWEEP = "sweep"
    BLOCK = "block"
    SPLIT = "split"
    UNUSUAL_SIZE = "unusual_size"
    UNUSUAL_PREMIUM = "unusual_premium"


@dataclass
class UnusualActivity:
    """Represents a single unusual options activity"""
    ticker: str
    timestamp: datetime
    strike: float
    expiry: datetime
    option_type: str  # 'call' or 'put'
    side: str  # 'bid', 'ask', 'mid'
    volume: int
    open_interest: int
    premium: float
    implied_vol: float
    underlying_price: float
    flow_type: FlowType
    score: float
    details: Dict[str, Any]


class UnusualOptionsScanner:
    """
    Scans for unusual options activity:
    - Volume spikes
    - Premium flow
    - Sweeps
    - Block trades
    - OI changes
    """
    
    # Thresholds
    MIN_VOLUME_RATIO = 5.0  # Volume/OI ratio
    MIN_PREMIUM = 50000  # Minimum premium for unusual
    MIN_CONTRACTS = 500
    SWEEP_MIN_CONTRACTS = 1000
    BLOCK_MIN_CONTRACTS = 5000
    
    def __init__(self):
        self.alerts = []
        self.historical_avg = {}
        
    def scan_ticker(self, ticker: str, 
                   options_data: pd.DataFrame,
                   price: float) -> List[UnusualActivity]:
        """Scan a single ticker for unusual activity"""
        unusual = []
        
        if options_data is None or len(options_data) == 0:
            return unusual
        
        # Group by strike/expiry
        for _, row in options_data.iterrows():
            score = 0
            flags = []
            
            volume = row.get('volume', 0)
            oi = row.get('open_interest', 1)
            premium = row.get('last_price', 0) * volume * 100
            iv = row.get('implied_volatility', 0)
            strike = row.get('strike', 0)
            
            # Volume/OI ratio check
            vol_oi_ratio = volume / max(oi, 1)
            if vol_oi_ratio >= self.MIN_VOLUME_RATIO:
                score += 20
                flags.append(f"Vol/OI: {vol_oi_ratio:.1f}x")
            
            # Premium check
            if premium >= self.MIN_PREMIUM:
                score += 25
                flags.append(f"Premium: ${premium:,.0f}")
            
            # Volume check
            if volume >= self.MIN_CONTRACTS:
                score += 15
                flags.append(f"Volume: {volume:,}")
            
            # IV rank check (if available)
            iv_rank = row.get('iv_rank', 0.5)
            if iv_rank > 0.8:
                score += 10
                flags.append(f"IV Rank: {iv_rank:.0%}")
            
            # Determine flow type
            option_type = row.get('option_type', 'call')
            bid_ask = row.get('trade_side', 'mid')
            
            if score >= 30:  # Threshold for unusual
                flow_type = self._determine_flow_type(
                    option_type, bid_ask, volume, premium
                )
                
                activity = UnusualActivity(
                    ticker=ticker,
                    timestamp=datetime.now(),
                    strike=strike,
                    expiry=row.get('expiry', datetime.now()),
                    option_type=option_type,
                    side=bid_ask,
                    volume=volume,
                    open_interest=oi,
                    premium=premium,
                    implied_vol=iv,
                    underlying_price=price,
                    flow_type=flow_type,
                    score=score,
                    details={
                        'vol_oi_ratio': vol_oi_ratio,
                        'iv_rank': iv_rank,
                        'flags': flags,
                        'moneyness': self._get_moneyness(strike, price, option_type),
                        'days_to_expiry': (row.get('expiry', datetime.now()) - 
                                          datetime.now()).days
                    }
                )
                unusual.append(activity)
        
        return unusual
    
    def _determine_flow_type(self, option_type: str, side: str, 
                            volume: int, premium: float) -> FlowType:
        """Determine the type of flow"""
        if volume >= self.BLOCK_MIN_CONTRACTS:
            return FlowType.BLOCK
        elif volume >= self.SWEEP_MIN_CONTRACTS:
            return FlowType.SWEEP
        elif premium >= self.MIN_PREMIUM * 2:
            return FlowType.UNUSUAL_PREMIUM
        elif option_type == 'call' and side == 'ask':
            return FlowType.BULLISH_CALL
        elif option_type == 'put' and side == 'ask':
            return FlowType.BEARISH_PUT
        elif option_type == 'put' and side == 'bid':
            return FlowType.BULLISH_PUT_SELL
        elif option_type == 'call' and side == 'bid':
            return FlowType.BEARISH_CALL_SELL
        else:
            return FlowType.UNUSUAL_SIZE
    
    def _get_moneyness(self, strike: float, price: float, 
                      option_type: str) -> str:
        """Get moneyness description"""
        pct_otm = abs(strike - price) / price * 100
        
        if option_type == 'call':
            if strike < price * 0.98:
                return f"ITM ({pct_otm:.1f}%)"
            elif strike > price * 1.02:
                return f"OTM ({pct_otm:.1f}%)"
            else:
                return "ATM"
        else:
            if strike > price * 1.02:
                return f"ITM ({pct_otm:.1f}%)"
            elif strike < price * 0.98:
                return f"OTM ({pct_otm:.1f}%)"
            else:
                return "ATM"
    
    def scan_market(self, tickers: List[str],
                   get_options_fn,
                   get_price_fn) -> List[UnusualActivity]:
        """Scan multiple tickers for unusual activity"""
        all_unusual = []
        
        for ticker in tickers:
            try:
                options_data = get_options_fn(ticker)
                price = get_price_fn(ticker)
                unusual = self.scan_ticker(ticker, options_data, price)
                all_unusual.extend(unusual)
            except Exception as e:
                logger.warning(f"Error scanning {ticker}: {e}")
                continue
        
        # Sort by score
        all_unusual.sort(key=lambda x: x.score, reverse=True)
        
        return all_unusual
    
    def get_flow_summary(self, activities: List[UnusualActivity]) -> Dict[str, Any]:
        """Get summary of flow activity"""
        if not activities:
            return {
                'total_premium': 0,
                'bullish_premium': 0,
                'bearish_premium': 0,
                'call_volume': 0,
                'put_volume': 0,
                'top_tickers': []
            }
        
        bullish_types = {FlowType.BULLISH_CALL, FlowType.BULLISH_PUT_SELL}
        bearish_types = {FlowType.BEARISH_PUT, FlowType.BEARISH_CALL_SELL}
        
        total_premium = sum(a.premium for a in activities)
        bullish_premium = sum(a.premium for a in activities 
                             if a.flow_type in bullish_types)
        bearish_premium = sum(a.premium for a in activities 
                             if a.flow_type in bearish_types)
        
        call_volume = sum(a.volume for a in activities if a.option_type == 'call')
        put_volume = sum(a.volume for a in activities if a.option_type == 'put')
        
        # Top tickers by premium
        ticker_premium = {}
        for a in activities:
            ticker_premium[a.ticker] = ticker_premium.get(a.ticker, 0) + a.premium
        
        top_tickers = sorted(ticker_premium.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'total_premium': total_premium,
            'bullish_premium': bullish_premium,
            'bearish_premium': bearish_premium,
            'bullish_ratio': bullish_premium / max(total_premium, 1),
            'call_volume': call_volume,
            'put_volume': put_volume,
            'put_call_ratio': put_volume / max(call_volume, 1),
            'top_tickers': top_tickers,
            'total_alerts': len(activities),
            'avg_score': np.mean([a.score for a in activities])
        }
    
    def filter_by_criteria(self, activities: List[UnusualActivity],
                          min_score: float = 0,
                          min_premium: float = 0,
                          flow_types: List[FlowType] = None,
                          tickers: List[str] = None,
                          expiry_days: int = None) -> List[UnusualActivity]:
        """Filter unusual activities by criteria"""
        filtered = activities.copy()
        
        if min_score > 0:
            filtered = [a for a in filtered if a.score >= min_score]
        
        if min_premium > 0:
            filtered = [a for a in filtered if a.premium >= min_premium]
        
        if flow_types:
            filtered = [a for a in filtered if a.flow_type in flow_types]
        
        if tickers:
            filtered = [a for a in filtered if a.ticker in tickers]
        
        if expiry_days:
            max_expiry = datetime.now() + timedelta(days=expiry_days)
            filtered = [a for a in filtered if a.expiry <= max_expiry]
        
        return filtered
    
    def to_dataframe(self, activities: List[UnusualActivity]) -> pd.DataFrame:
        """Convert activities to DataFrame"""
        if not activities:
            return pd.DataFrame()
        
        records = []
        for a in activities:
            records.append({
                'ticker': a.ticker,
                'timestamp': a.timestamp,
                'strike': a.strike,
                'expiry': a.expiry,
                'type': a.option_type,
                'side': a.side,
                'volume': a.volume,
                'oi': a.open_interest,
                'premium': a.premium,
                'iv': a.implied_vol,
                'spot': a.underlying_price,
                'flow_type': a.flow_type.value,
                'score': a.score,
                'moneyness': a.details.get('moneyness', ''),
                'vol_oi': a.details.get('vol_oi_ratio', 0),
                'dte': a.details.get('days_to_expiry', 0)
            })
        
        df = pd.DataFrame(records)
        df = df.sort_values('score', ascending=False)
        
        return df
    
    def get_sweep_detector(self, trades: List[Dict]) -> List[Dict]:
        """Detect sweeps from trade data"""
        sweeps = []
        
        # Group trades by ticker/strike/expiry within time window
        # A sweep is multiple smaller trades in rapid succession
        if not trades:
            return sweeps
        
        df = pd.DataFrame(trades)
        
        # Group by ticker, strike, expiry
        grouped = df.groupby(['ticker', 'strike', 'expiry'])
        
        for (ticker, strike, expiry), group in grouped:
            # Check for rapid succession trades
            if len(group) >= 3:
                group = group.sort_values('timestamp')
                time_diff = group['timestamp'].diff().mean()
                
                # If trades are within 1 second average
                if time_diff and time_diff.total_seconds() < 1:
                    total_volume = group['volume'].sum()
                    total_premium = group['premium'].sum()
                    
                    if total_volume >= self.SWEEP_MIN_CONTRACTS:
                        sweeps.append({
                            'ticker': ticker,
                            'strike': strike,
                            'expiry': expiry,
                            'type': group['option_type'].iloc[0],
                            'total_volume': total_volume,
                            'total_premium': total_premium,
                            'num_trades': len(group),
                            'time_span': (group['timestamp'].max() - 
                                        group['timestamp'].min()).total_seconds()
                        })
        
        return sweeps


# Singleton instance
_scanner = None

def get_unusual_scanner() -> UnusualOptionsScanner:
    global _scanner
    if _scanner is None:
        _scanner = UnusualOptionsScanner()
    return _scanner


def format_unusual_alert(activity: UnusualActivity) -> str:
    """Format unusual activity as alert text"""
    emoji = "🟢" if activity.flow_type in {FlowType.BULLISH_CALL, FlowType.BULLISH_PUT_SELL} else "🔴"
    
    return f"""
{emoji} **{activity.ticker}** - {activity.flow_type.value.upper()}
Strike: ${activity.strike:.2f} | Expiry: {activity.expiry.strftime('%Y-%m-%d')}
Type: {activity.option_type.upper()} @ {activity.side.upper()}
Volume: {activity.volume:,} | OI: {activity.open_interest:,}
Premium: ${activity.premium:,.0f} | IV: {activity.implied_vol:.1%}
Score: {activity.score:.0f} | {activity.details.get('moneyness', '')}
""".strip()
