from enum import Enum
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Any


class StrategyType(Enum):
    IRON_CONDOR = "iron_condor"
    COVERED_CALL = "covered_call"
    CASH_SECURED_PUT = "cash_secured_put"
    LONG_CALL = "long_call"
    LONG_PUT = "long_put"


@dataclass
class BacktestConfig:
    start_date: date
    end_date: date
    initial_capital: float = 100000.0
    strategy: StrategyType = StrategyType.IRON_CONDOR
    symbol: str = "SPY"
    position_size_pct: float = 0.1
    days_to_expiration: int = 30
    profit_target_pct: float = 0.5
    stop_loss_pct: float = 2.0


class _Result:
    def __init__(self, dates: List[date]):
        self.dates = dates
        self.equity_curve = [100000 + i * 10 for i in range(len(dates))]
        self.drawdown_series = [0 for _ in dates]
        self.total_return_pct = 10.0
        self.sharpe_ratio = 1.2
        self.max_drawdown_pct = 2.5
        self.win_rate = 0.55
        self.profit_factor = 1.4
        self.total_trades = 10
        self.winning_trades = 6
        self.losing_trades = 4
        self.avg_win = 150.0
        self.avg_loss = -100.0
        self.best_trade = 500.0
        self.worst_trade = -300.0
        self.avg_days_in_trade = 12
        self.trades = []


class BacktestRunner:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def run(self, config: BacktestConfig) -> Any:
        # Simple deterministic mock backtest result for UI display
        days = (config.end_date - config.start_date).days or 1
        dates = [config.start_date + timedelta(days=i) for i in range(days + 1)]
        return _Result(dates)
