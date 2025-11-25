from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class CashSecuredPutConfig:
    symbol: str = "SPY"
    max_contracts: int = 1
    target_dte: int = 30
    min_delta: float = 0.15
    max_delta: float = 0.25
    min_premium: float = 0.5
    min_volume: int = 100

class CashSecuredPutStrategy:
    def __init__(self, cfg: CashSecuredPutConfig = CashSecuredPutConfig()):
        self.cfg = cfg

    def select_option(self, options_chain: List[Dict[str, Any]], stock_price: float):
        puts = [o for o in options_chain if o.get('type') == 'put']
        puts = [o for o in puts if abs(o.get('dte',0) - self.cfg.target_dte) <= 3]
        filtered = [o for o in puts if o.get('volume',0) >= self.cfg.min_volume and
                    self.cfg.min_delta <= o.get('delta',0) <= self.cfg.max_delta and
                    o.get('mid',0) >= self.cfg.min_premium]
        if not filtered:
            return None
        # prefer highest premium among filtered
        filtered.sort(key=lambda x: x.get('mid',0), reverse=True)
        pick = filtered[0]
        return {
            'action': 'SELL_PUT',
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
