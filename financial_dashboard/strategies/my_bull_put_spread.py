from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class BullPutSpreadConfig:
    symbol: str = "SPY"
    max_contracts: int = 1
    target_dte: int = 30
    short_delta: float = 0.20
    long_delta: float = 0.10
    min_premium: float = 0.3
    min_volume: int = 100

class BullPutSpreadStrategy:
    def __init__(self, cfg: BullPutSpreadConfig = BullPutSpreadConfig()):
        self.cfg = cfg

    def select_legs(self, options_chain: List[Dict[str, Any]], stock_price: float):
        puts = [o for o in options_chain if o.get('type') == 'put']
        puts = [o for o in puts if abs(o.get('dte',0) - self.cfg.target_dte) <= 3]
        # find short put around short_delta
        short_candidates = [o for o in puts if o.get('volume',0) >= self.cfg.min_volume and abs(o.get('delta',0) - self.cfg.short_delta) <= 0.05]
        long_candidates = [o for o in puts if o.get('volume',0) >= self.cfg.min_volume and abs(o.get('delta',0) - self.cfg.long_delta) <= 0.05]
        if not short_candidates or not long_candidates:
            return None
        # pick closest deltas
        short_candidates.sort(key=lambda x: abs(x.get('delta',0) - self.cfg.short_delta))
        long_candidates.sort(key=lambda x: abs(x.get('delta',0) - self.cfg.long_delta))
        short_put = short_candidates[0]
        long_put = long_candidates[0]
        # ensure long strike < short strike
        if long_put['strike'] >= short_put['strike']:
            # try to find a long put with strike lower than short
            lowers = [p for p in long_candidates if p['strike'] < short_put['strike']]
            if not lowers:
                return None
            long_put = lowers[0]
        # premium check (net credit >= min_premium)
        net_credit = short_put.get('mid',0) - long_put.get('mid',0)
        if net_credit < self.cfg.min_premium:
            return None
        return [
            {
                'action': 'SELL_PUT', 'symbol': self.cfg.symbol, 'expiration': short_put['expiration'], 'strike': short_put['strike'], 'quantity': 1, 'premium': short_put.get('mid')
            },
            {
                'action': 'BUY_PUT', 'symbol': self.cfg.symbol, 'expiration': long_put['expiration'], 'strike': long_put['strike'], 'quantity': 1, 'premium': long_put.get('mid')
            }
        ]

    def run(self, options_chain: List[Dict[str, Any]], stock_price: float):
        legs = self.select_legs(options_chain, stock_price)
        if legs:
            return legs
        return []
