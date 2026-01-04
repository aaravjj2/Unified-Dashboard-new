from dataclasses import dataclass


@dataclass
class OrderRequest:
    ticker: str
    quantity: int
    side: str


class RiskViolation(Exception):
    pass


class _RiskManager:
    def __init__(self):
        self._limits = {"MAX_POSITION_SIZE": 100}

    def get_risk_limits(self):
        return dict(self._limits)

    def get_portfolio_state(self):
        # Minimal portfolio state for UI
        return {"positions": [], "exposure": 0}


_SINGLETON = None


def get_risk_manager():
    global _SINGLETON
    if _SINGLETON is None:
        _SINGLETON = _RiskManager()
    return _SINGLETON
