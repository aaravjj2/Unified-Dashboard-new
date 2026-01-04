"""
Machine Learning Strategy Optimization Module

Provides ML-based strategy optimization:
- Reinforcement Learning for parameter optimization
- Market regime detection
- Adaptive strategy selection

Components:
- TradingStrategyEnv: OpenAI Gym environment for RL training
- RLStrategyOptimizer: PPO-based parameter optimizer
- MarketRegimeDetector: HMM-based regime detection
- RegimeAdaptiveSelector: Strategy selection based on regime
"""

from src.ml.rl_optimizer import (
    TradingStrategyEnv,
    RLStrategyOptimizer,
    StrategyConfig,
)
from src.ml.regime_detector import (
    MarketRegimeDetector,
    MarketRegime,
    RegimeAdaptiveStrategySelector,
)

__all__ = [
    "TradingStrategyEnv",
    "RLStrategyOptimizer",
    "StrategyConfig",
    "MarketRegimeDetector",
    "MarketRegime",
    "RegimeAdaptiveStrategySelector",
]
