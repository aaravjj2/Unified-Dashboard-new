"""
Options Volume Scanner Service
Implements #136 from ROADMAP_ULTIMATE.md

Based on: https://github.com/GamestonkTerminal/OpenBBTerminal
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
import asyncio

logger = logging.getLogger(__name__)


class VolumeAlertType(Enum):
    """Types of volume alerts"""
    UNUSUAL_CALL_VOLUME = "unusual_call_volume"
    UNUSUAL_PUT_VOLUME = "unusual_put_volume"
    HIGH_PUT_CALL_RATIO = "high_put_call_ratio"
    LOW_PUT_CALL_RATIO = "low_put_call_ratio"
    BLOCK_TRADE = "block_trade"
    SWEEP = "sweep"
    OPENING_POSITION = "opening_position"
    CLOSING_POSITION = "closing_position"
    SMART_MONEY_FLOW = "smart_money_flow"


@dataclass
class VolumeAlert:
    """Volume alert data"""
    symbol: str
    alert_type: VolumeAlertType
    strike: float
    expiration: str
    option_type: str  # 'call' or 'put'
    volume: int
    open_interest: int
    volume_oi_ratio: float
    avg_volume: float
    volume_multiple: float
    premium_value: float
    timestamp: datetime
    confidence: float
    description: str


@dataclass
class OptionsFlowData:
    """Aggregated options flow"""
    symbol: str
    total_call_volume: int
    total_put_volume: int
    total_call_premium: float
    total_put_premium: float
    put_call_ratio: float
    net_premium: float  # calls - puts (bullish if positive)
    avg_iv: float
    unusual_activity_score: float


class OptionsVolumeScanner:
    """
    Scanner for unusual options volume and flow
    Detects smart money, block trades, sweeps, and unusual activity
    """
    
    def __init__(self, 
                volume_threshold: float = 3.0,
                oi_ratio_threshold: float = 1.5,
                block_trade_min: int = 100,
                sweep_threshold: int = 10,
                min_premium: float = 10000):
        
        self.volume_threshold = volume_threshold
        self.oi_ratio_threshold = oi_ratio_threshold
        self.block_trade_min = block_trade_min
        self.sweep_threshold = sweep_threshold
        self.min_premium = min_premium
        
        self.historical_volumes: Dict[str, pd.DataFrame] = {}
        self.alerts: List[VolumeAlert] = []
        self.flow_data: Dict[str, OptionsFlowData] = {}
        
    def load_historical_data(self, symbol: str, data: pd.DataFrame):
        """Load historical volume data for baseline"""
        self.historical_volumes[symbol] = data
    
    def _calculate_avg_volume(self, symbol: str, 
                             strike: float, 
                             expiration: str, 
                             option_type: str,
                             lookback_days: int = 20) -> float:
        """Calculate average volume for comparison"""
        if symbol not in self.historical_volumes:
            return 0
        
        df = self.historical_volumes[symbol]
        
        # Filter for matching options
        mask = (
            (df['strike'] == strike) & 
            (df['expiration'] == expiration) & 
            (df['type'] == option_type)
        )
        
        if mask.sum() == 0:
            # Use overall average for this strike
            mask = (df['strike'] == strike) & (df['type'] == option_type)
        
        if mask.sum() == 0:
            return 100  # Default baseline
        
        return df.loc[mask, 'volume'].mean()
    
    def scan_options_chain(self, 
                          symbol: str,
                          options_data: pd.DataFrame,
                          spot_price: float) -> List[VolumeAlert]:
        """
        Scan options chain for unusual activity
        
        Expected columns: strike, expiration, type (call/put), volume, 
                         open_interest, bid, ask, last, iv
        """
        alerts = []
        
        if options_data.empty:
            return alerts
        
        for _, row in options_data.iterrows():
            strike = row['strike']
            expiration = row['expiration']
            option_type = row['type']
            volume = row.get('volume', 0)
            oi = row.get('open_interest', 1)
            bid = row.get('bid', 0)
            ask = row.get('ask', 0)
            mid_price = (bid + ask) / 2
            
            # Skip if no volume
            if volume == 0:
                continue
            
            # Calculate metrics
            avg_volume = self._calculate_avg_volume(symbol, strike, expiration, option_type)
            volume_multiple = volume / max(avg_volume, 1)
            vol_oi_ratio = volume / max(oi, 1)
            premium_value = volume * mid_price * 100
            
            # Check for unusual volume
            if volume_multiple >= self.volume_threshold:
                alert_type = (VolumeAlertType.UNUSUAL_CALL_VOLUME 
                            if option_type == 'call' 
                            else VolumeAlertType.UNUSUAL_PUT_VOLUME)
                
                confidence = min(0.95, 0.5 + (volume_multiple - self.volume_threshold) * 0.1)
                
                # Determine if opening or closing
                if vol_oi_ratio > 1:
                    position_type = "opening"
                else:
                    position_type = "possibly closing"
                
                # Determine strike position
                moneyness = "ATM"
                if option_type == 'call':
                    if strike > spot_price * 1.05:
                        moneyness = "OTM"
                    elif strike < spot_price * 0.95:
                        moneyness = "ITM"
                else:
                    if strike < spot_price * 0.95:
                        moneyness = "OTM"
                    elif strike > spot_price * 1.05:
                        moneyness = "ITM"
                
                description = (f"{volume_multiple:.1f}x avg volume on {moneyness} "
                             f"{option_type}s, {position_type} position, "
                             f"${premium_value:,.0f} in premium")
                
                alert = VolumeAlert(
                    symbol=symbol,
                    alert_type=alert_type,
                    strike=strike,
                    expiration=expiration,
                    option_type=option_type,
                    volume=volume,
                    open_interest=oi,
                    volume_oi_ratio=vol_oi_ratio,
                    avg_volume=avg_volume,
                    volume_multiple=volume_multiple,
                    premium_value=premium_value,
                    timestamp=datetime.now(),
                    confidence=confidence,
                    description=description
                )
                alerts.append(alert)
            
            # Check for block trades
            if volume >= self.block_trade_min and premium_value >= self.min_premium:
                alert = VolumeAlert(
                    symbol=symbol,
                    alert_type=VolumeAlertType.BLOCK_TRADE,
                    strike=strike,
                    expiration=expiration,
                    option_type=option_type,
                    volume=volume,
                    open_interest=oi,
                    volume_oi_ratio=vol_oi_ratio,
                    avg_volume=avg_volume,
                    volume_multiple=volume_multiple,
                    premium_value=premium_value,
                    timestamp=datetime.now(),
                    confidence=0.8,
                    description=f"Block trade: {volume:,} contracts, ${premium_value:,.0f} premium"
                )
                alerts.append(alert)
        
        return alerts
    
    def analyze_put_call_ratio(self,
                              symbol: str,
                              options_data: pd.DataFrame) -> Optional[VolumeAlert]:
        """Analyze put/call ratio for extreme readings"""
        
        call_volume = options_data[options_data['type'] == 'call']['volume'].sum()
        put_volume = options_data[options_data['type'] == 'put']['volume'].sum()
        
        if call_volume == 0:
            return None
        
        pc_ratio = put_volume / call_volume
        
        # Check for extreme readings
        if pc_ratio > 2.0:  # Very bearish
            return VolumeAlert(
                symbol=symbol,
                alert_type=VolumeAlertType.HIGH_PUT_CALL_RATIO,
                strike=0,
                expiration="",
                option_type="ratio",
                volume=put_volume + call_volume,
                open_interest=0,
                volume_oi_ratio=0,
                avg_volume=0,
                volume_multiple=pc_ratio,
                premium_value=0,
                timestamp=datetime.now(),
                confidence=min(0.9, 0.5 + (pc_ratio - 2.0) * 0.1),
                description=f"High put/call ratio: {pc_ratio:.2f} - Bearish sentiment"
            )
        elif pc_ratio < 0.5:  # Very bullish
            return VolumeAlert(
                symbol=symbol,
                alert_type=VolumeAlertType.LOW_PUT_CALL_RATIO,
                strike=0,
                expiration="",
                option_type="ratio",
                volume=put_volume + call_volume,
                open_interest=0,
                volume_oi_ratio=0,
                avg_volume=0,
                volume_multiple=pc_ratio,
                premium_value=0,
                timestamp=datetime.now(),
                confidence=min(0.9, 0.5 + (0.5 - pc_ratio) * 0.2),
                description=f"Low put/call ratio: {pc_ratio:.2f} - Bullish sentiment"
            )
        
        return None
    
    def aggregate_flow(self, 
                      symbol: str,
                      options_data: pd.DataFrame,
                      spot_price: float) -> OptionsFlowData:
        """Aggregate options flow data"""
        
        calls = options_data[options_data['type'] == 'call']
        puts = options_data[options_data['type'] == 'put']
        
        total_call_volume = calls['volume'].sum()
        total_put_volume = puts['volume'].sum()
        
        # Calculate premium (volume * mid_price * 100)
        if 'bid' in calls.columns and 'ask' in calls.columns:
            call_premiums = calls['volume'] * ((calls['bid'] + calls['ask']) / 2) * 100
            put_premiums = puts['volume'] * ((puts['bid'] + puts['ask']) / 2) * 100
        else:
            call_premiums = calls['volume'] * calls.get('last', 0) * 100
            put_premiums = puts['volume'] * puts.get('last', 0) * 100
        
        total_call_premium = call_premiums.sum()
        total_put_premium = put_premiums.sum()
        
        pc_ratio = total_put_volume / max(total_call_volume, 1)
        net_premium = total_call_premium - total_put_premium
        
        avg_iv = options_data['iv'].mean() if 'iv' in options_data.columns else 0
        
        # Calculate unusual activity score
        avg_volumes = [
            self._calculate_avg_volume(symbol, row['strike'], row['expiration'], row['type'])
            for _, row in options_data.iterrows()
        ]
        
        if avg_volumes and sum(avg_volumes) > 0:
            total_avg = sum(avg_volumes)
            total_current = options_data['volume'].sum()
            unusual_score = total_current / max(total_avg, 1)
        else:
            unusual_score = 1.0
        
        flow = OptionsFlowData(
            symbol=symbol,
            total_call_volume=total_call_volume,
            total_put_volume=total_put_volume,
            total_call_premium=total_call_premium,
            total_put_premium=total_put_premium,
            put_call_ratio=pc_ratio,
            net_premium=net_premium,
            avg_iv=avg_iv,
            unusual_activity_score=unusual_score
        )
        
        self.flow_data[symbol] = flow
        return flow
    
    def detect_smart_money(self,
                          symbol: str,
                          options_data: pd.DataFrame,
                          spot_price: float) -> List[VolumeAlert]:
        """
        Detect smart money activity patterns:
        - Large premium trades
        - Out of the money large positions
        - Consistent directional flow
        """
        alerts = []
        
        for _, row in options_data.iterrows():
            strike = row['strike']
            option_type = row['type']
            volume = row.get('volume', 0)
            oi = row.get('open_interest', 1)
            bid = row.get('bid', 0)
            ask = row.get('ask', 0)
            mid_price = (bid + ask) / 2
            premium = volume * mid_price * 100
            
            # Large premium + OTM = Smart money indicator
            is_otm = (option_type == 'call' and strike > spot_price * 1.05) or \
                     (option_type == 'put' and strike < spot_price * 0.95)
            
            # Check for smart money criteria
            if is_otm and premium >= self.min_premium * 5:  # 5x min premium
                vol_oi_ratio = volume / max(oi, 1)
                
                # New position (volume > OI) in OTM with large premium
                if vol_oi_ratio > 1:
                    direction = "bullish" if option_type == 'call' else "bearish"
                    
                    alert = VolumeAlert(
                        symbol=symbol,
                        alert_type=VolumeAlertType.SMART_MONEY_FLOW,
                        strike=strike,
                        expiration=row['expiration'],
                        option_type=option_type,
                        volume=volume,
                        open_interest=oi,
                        volume_oi_ratio=vol_oi_ratio,
                        avg_volume=0,
                        volume_multiple=0,
                        premium_value=premium,
                        timestamp=datetime.now(),
                        confidence=0.75,
                        description=f"Smart money: ${premium:,.0f} in OTM {option_type}s - {direction}"
                    )
                    alerts.append(alert)
        
        return alerts
    
    def scan_multiple_symbols(self,
                             symbols_data: Dict[str, pd.DataFrame],
                             spot_prices: Dict[str, float]) -> Dict[str, List[VolumeAlert]]:
        """Scan multiple symbols for unusual activity"""
        all_alerts = {}
        
        for symbol, data in symbols_data.items():
            spot = spot_prices.get(symbol, data['strike'].median())
            
            alerts = []
            alerts.extend(self.scan_options_chain(symbol, data, spot))
            
            pc_alert = self.analyze_put_call_ratio(symbol, data)
            if pc_alert:
                alerts.append(pc_alert)
            
            alerts.extend(self.detect_smart_money(symbol, data, spot))
            
            all_alerts[symbol] = alerts
            self.aggregate_flow(symbol, data, spot)
        
        return all_alerts
    
    def get_top_unusual_activity(self, 
                                n: int = 10) -> List[VolumeAlert]:
        """Get top N unusual activity alerts"""
        all_alerts = []
        for symbol_alerts in self.alerts:
            if isinstance(symbol_alerts, list):
                all_alerts.extend(symbol_alerts)
            else:
                all_alerts.append(symbol_alerts)
        
        # Sort by volume multiple and confidence
        sorted_alerts = sorted(
            all_alerts,
            key=lambda x: x.volume_multiple * x.confidence,
            reverse=True
        )
        
        return sorted_alerts[:n]
    
    def get_flow_summary(self) -> pd.DataFrame:
        """Get summary of all tracked flow"""
        if not self.flow_data:
            return pd.DataFrame()
        
        rows = []
        for symbol, flow in self.flow_data.items():
            rows.append({
                'symbol': symbol,
                'call_volume': flow.total_call_volume,
                'put_volume': flow.total_put_volume,
                'call_premium': flow.total_call_premium,
                'put_premium': flow.total_put_premium,
                'put_call_ratio': flow.put_call_ratio,
                'net_premium': flow.net_premium,
                'avg_iv': flow.avg_iv,
                'unusual_score': flow.unusual_activity_score,
                'sentiment': 'Bullish' if flow.net_premium > 0 else 'Bearish'
            })
        
        return pd.DataFrame(rows)
    
    def to_dict(self, alerts: List[VolumeAlert]) -> List[Dict]:
        """Convert alerts to dictionary format"""
        return [
            {
                'symbol': a.symbol,
                'alert_type': a.alert_type.value,
                'strike': a.strike,
                'expiration': a.expiration,
                'option_type': a.option_type,
                'volume': a.volume,
                'open_interest': a.open_interest,
                'volume_oi_ratio': round(a.volume_oi_ratio, 2),
                'volume_multiple': round(a.volume_multiple, 1),
                'premium_value': round(a.premium_value, 2),
                'timestamp': a.timestamp.isoformat(),
                'confidence': round(a.confidence, 2),
                'description': a.description
            }
            for a in alerts
        ]


# Singleton instance
_scanner = None

def get_volume_scanner() -> OptionsVolumeScanner:
    global _scanner
    if _scanner is None:
        _scanner = OptionsVolumeScanner()
    return _scanner
