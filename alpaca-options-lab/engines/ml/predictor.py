from dataclasses import dataclass
from typing import List, Dict
import time


@dataclass
class PricePrediction:
    signal_strength: float
    direction: object
    timestamps: List[int]
    price_path: List[float]
    current_price: float
    target_price: float
    regime: object
    confidence: float
    change_pct: float


@dataclass
class VolatilityPrediction:
    current_iv: float
    forecast_iv: float
    iv_rank: float
    vol_regime: str


class DummyEnum:
    def __init__(self, value):
        self.value = value


class _PricePredictor:
    def predict(self, ticker: str, current_price: float = 100.0, horizon_days: int = 7) -> PricePrediction:
        # deterministic example prediction
        timestamps = [int(time.time()) + 86400 * i for i in range(horizon_days)]
        price_path = [current_price * (1 + 0.002 * i) for i in range(horizon_days)]
        return PricePrediction(
            signal_strength=75.0,
            direction=DummyEnum("BULLISH"),
            timestamps=timestamps,
            price_path=price_path,
            current_price=current_price,
            target_price=price_path[-1],
            regime=DummyEnum("BULL"),
            confidence=68.0,
            change_pct= (price_path[-1] - current_price) / current_price * 100
        )

    def to_dict(self, pred: PricePrediction) -> Dict:
        return {
            "signal_strength": pred.signal_strength,
            "direction": pred.direction.value,
            "timestamps": pred.timestamps,
            "price_path": pred.price_path,
            "current_price": pred.current_price,
            "target_price": pred.target_price,
            "regime": pred.regime.value,
            "confidence": pred.confidence,
            "change_pct": pred.change_pct,
        }


class _VolPredictor:
    def predict(self, ticker: str, horizon_days: int = 7) -> VolatilityPrediction:
        return VolatilityPrediction(current_iv=18.5, forecast_iv=20.2, iv_rank=60.0, vol_regime="STABLE")

    def to_dict(self, pred: VolatilityPrediction) -> Dict:
        return {
            "current_iv": pred.current_iv,
            "forecast_iv": pred.forecast_iv,
            "iv_rank": pred.iv_rank,
            "vol_regime": pred.vol_regime,
        }


class _HintGenerator:
    def generate_hint(self, price_pred: PricePrediction, vol_pred: VolatilityPrediction) -> Dict:
        direction = price_pred.direction.value if hasattr(price_pred.direction, 'value') else str(price_pred.direction)
        return {
            "recommended_strategy": "Long Call" if direction == "BULLISH" else "Long Put",
            "description": f"Confidence {price_pred.confidence:.0f}%",
            "icon": "📈" if direction == "BULLISH" else "📉",
            "color": "#4caf50" if direction == "BULLISH" else "#f44336",
            "confidence": price_pred.confidence,
            "price_direction": direction,
            "vol_regime": vol_pred.vol_regime
        }


def get_price_predictor():
    return _PricePredictor()


def get_vol_predictor():
    return _VolPredictor()


def get_hint_generator():
    return _HintGenerator()
