# Options Service Strategy Engine

## Overview
This directory contains a pluggable strategy engine for options trading strategies. All strategies inherit from the `BaseStrategy` ABC and implement standardized interfaces for signal generation and backtesting.

## Architecture

### BaseStrategy (Abstract Base Class)
All strategies must implement:
- `generate_signals(historical_df)` - Generate trading signals from historical data
- `backtest(historical_df)` - Run backtest and return performance metrics
- `to_dict()` - Serialize strategy configuration
- `from_dict(config)` - Deserialize strategy from configuration

### Implemented Strategies

#### CoveredCallScreener
Screens stocks for covered call opportunities based on volatility and returns.

**Scoring Formula**: `mean_daily_return * -volatility`
- Favors stable growth (positive returns with low volatility)
- Higher scores indicate better covered call candidates

**Parameters**:
- `ticker` (str): Stock symbol to analyze
- `lookback_days` (int, optional): Days of historical data

**Output Signal Structure**:
```python
{
    "ticker": "AAPL",
    "score": 0.002345,
    "recommended_strike": 175.50,  # ~10% above current price
    "recommendation_date": "2025-01-15"
}
```

## Usage

### Basic Usage
```python
from financial_dashboard.services.options_service.strategies import CoveredCallScreener
import pandas as pd

# Create strategy
screener = CoveredCallScreener(
    name="my_covered_call_screen",
    params={"ticker": "AAPL", "lookback_days": 30}
)

# Generate signals
historical_df = pd.DataFrame({
    'Date': [...],
    'Open': [...],
    'Close': [...],
    # ... other OHLCV data
})

signals = screener.generate_signals(historical_df)
print(signals)  # [{"ticker": "AAPL", "score": 0.0023, ...}]
```

### Backtesting with MLflow
```python
# Run backtest with MLflow tracking
results = screener.backtest(historical_df)
print(results)
# {
#     "sharpe_ratio": 1.5,
#     "total_return": 0.25,
#     "max_drawdown": 0.15,
#     "num_trades": 12
# }
```

### Serialization
```python
# Save strategy configuration
config = screener.to_dict()
# {"name": "my_strategy", "params": {"ticker": "AAPL", ...}}

# Restore from configuration
restored = CoveredCallScreener.from_dict(config)
```

## Testing

### Run All Tests
```bash
cd /mnt/c/Aarav/fin_env/unified-dashboard
python -m pytest tests/test_strategies_base.py tests/test_covered_call_screener.py tests/test_strategy_mlflow_logging.py -v
```

### Test Coverage
- **BaseStrategy ABC Tests**: 8 tests
  - Abstract class enforcement
  - Subclass requirements
  - Serialization interface
  
- **CoveredCallScreener Tests**: 8 tests
  - Instantiation
  - Signal generation
  - Deterministic behavior
  - Mocked client injection
  - Scoring algorithm
  
- **MLflow Integration Tests**: 7 tests
  - Experiment initialization
  - Metric logging
  - Parameter logging
  - Return value structure

**Total**: 23 tests, 100% passing

### Test Logs
- Failing tests (pre-implementation): `tests/logs/strategies_tests_failure.log`
- Passing tests (post-implementation): `tests/logs/strategies_tests_success.log`

## Adding New Strategies

1. **Create Strategy Class**
```python
from .base_strategy import BaseStrategy
import pandas as pd
from typing import List, Dict, Any

class MyStrategy(BaseStrategy):
    def generate_signals(self, historical_df: pd.DataFrame) -> List[Dict[str, Any]]:
        # Your signal generation logic
        return [{"ticker": "...", "score": 0.5, ...}]
    
    def backtest(self, historical_df: pd.DataFrame) -> Dict[str, Any]:
        # Your backtest logic with MLflow logging
        from financial_dashboard.utils.mlflow_helpers import initialize_mlflow_experiment
        import mlflow
        
        initialize_mlflow_experiment("My Strategy Validation")
        with mlflow.start_run():
            mlflow.log_param("strategy_name", self.name)
            # ... backtest logic ...
            mlflow.log_metric("sharpe_ratio", sharpe)
            return {"sharpe_ratio": sharpe, ...}
```

2. **Register in __init__.py**
```python
from .my_strategy import MyStrategy

__all__ = ['BaseStrategy', 'CoveredCallScreener', 'MyStrategy']
```

3. **Write Tests**
Follow TDD pattern:
- Write failing tests first
- Implement strategy to make tests pass
- Verify 100% pass rate

## MLflow Integration

All strategies automatically integrate with MLflow for experiment tracking:

- **Experiment Initialization**: `initialize_mlflow_experiment(name)`
- **Parameter Logging**: `mlflow.log_param(key, value)`
- **Metric Logging**: `mlflow.log_metric(key, value)`

**Note**: MLflow tracking requires `MLFLOW_TRACKING_URI` environment variable for production use. Tests mock MLflow to avoid this dependency.

## Dependencies
- pandas
- numpy  
- mlflow
- financial_dashboard.utils.mlflow_helpers

## Development Notes

### TDD Approach
This module was built using strict Test-Driven Development:
1. ✅ Write failing tests first
2. ✅ Implement code to pass tests
3. ✅ Achieve 100% test coverage
4. ✅ Document and deliver

### Design Decisions
- **Dependency Injection**: Strategies accept `price_client` parameter for testability
- **Simplified Interface**: No position management in base class (focused on signal generation)
- **Deterministic Testing**: Sample data designed for reproducible test results
- **Mock-Friendly**: All external dependencies (MLflow, HTTP clients) properly mocked in tests
