from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class CoveredCallConfig:
    symbol: str = "SPY"
    max_contracts: int = 1
    target_dte: int = 30
    min_delta: float = 0.25
    max_delta: float = 0.35
    min_premium: float = 0.5
    min_volume: int = 100


class CoveredCallStrategy:
    def __init__(self, cfg: CoveredCallConfig = CoveredCallConfig()):
        self.cfg = cfg

    def select_option(self, options_chain: List[Dict[str, Any]], stock_price: float):
        """Return single option leg to SELL (call) or None if no suitable option found."""
        # Filter by call options, DTE and liquidity
        candidates = [o for o in options_chain if o.get('type') == 'call']
        # Prefer options with DTE close to target_dte
        candidates = [o for o in candidates if abs(o.get('dte', 0) - self.cfg.target_dte) <= 3]
        # filter by volume and delta and premium
        filtered = [o for o in candidates if o.get('volume',0) >= self.cfg.min_volume and
                    self.cfg.min_delta <= o.get('delta',0) <= self.cfg.max_delta and
                    o.get('mid',0) >= self.cfg.min_premium]
        # choose the option with delta closest to the midpoint
        if not filtered:
            return None
        midpoint = (self.cfg.min_delta + self.cfg.max_delta)/2
        filtered.sort(key=lambda x: abs(x.get('delta',0) - midpoint))
        pick = filtered[0]
        return {
            'action': 'SELL_CALL',
            'symbol': self.cfg.symbol,
            'expiration': pick['expiration'],
            'strike': pick['strike'],
            'quantity': 1,
            'premium': pick.get('mid')
        }

    def run(self, options_chain: List[Dict[str, Any]], stock_price: float):
        leg = self.select_option(options_chain, stock_price)
        if leg:
            return [leg]
        return []
