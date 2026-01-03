"""
Tests for Part 3: Market Forecast Enhancements.

Tests:
- N-BEATS forecaster (blocks, basis functions, full model)
- N-HiTS forecaster (multi-scale blocks, pooling, full model)  
- Enhanced Forecast Engine (ensemble, model selection, confidence intervals)

Run with: python -m pytest financial_dashboard/test_part3_forecasting.py -v
"""

import pytest
import numpy as np
import pandas as pd
import tempfile
import os
from datetime import datetime, timedelta

# Check PyTorch availability
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_time_series():
    """Generate sample time series data."""
    np.random.seed(42)
    n = 200
    dates = pd.date_range('2023-01-01', periods=n, freq='D')
    
    # Trend + seasonality + noise
    t = np.arange(n)
    trend = 100 + 0.1 * t
    seasonality = 10 * np.sin(2 * np.pi * t / 7)  # Weekly
    noise = np.random.normal(0, 2, n)
    
    y = trend + seasonality + noise
    
    return pd.DataFrame({
        'ds': dates,
        'y': y
    })


@pytest.fixture
def short_time_series():
    """Generate short time series for quick tests."""
    np.random.seed(42)
    n = 100
    dates = pd.date_range('2023-01-01', periods=n, freq='D')
    y = np.cumsum(np.random.randn(n)) + 100
    
    return pd.DataFrame({
        'ds': dates,
        'y': y
    })


# ============================================================================
# N-BEATS Tests
# ============================================================================

class TestNBeatsForecaster:
    """Tests for N-BEATS implementation."""
    
    def test_import(self):
        """Test module imports."""
        from financial_dashboard.models.nbeats_forecaster import (
            NBeatsForecaster,
            ForecastResult,
            get_nbeats_availability
        )
        assert NBeatsForecaster is not None
    
    def test_availability_check(self):
        """Test availability checker."""
        from financial_dashboard.models.nbeats_forecaster import get_nbeats_availability
        
        avail = get_nbeats_availability()
        assert 'torch' in avail
        assert 'nbeats_numpy' in avail
        assert avail['nbeats_numpy'] is True  # Numpy fallback always available
    
    def test_forecast_result_dataclass(self):
        """Test ForecastResult dataclass."""
        from financial_dashboard.models.nbeats_forecaster import ForecastResult
        
        dates = pd.date_range('2024-01-01', periods=5)
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        
        result = ForecastResult(
            dates=dates.tolist(),
            values=values,
            model='nbeats'
        )
        
        assert len(result.dates) == 5
        assert len(result.values) == 5
        
        # Test to_dataframe
        df = result.to_dataframe()
        assert 'ds' in df.columns
        assert 'yhat' in df.columns
        assert 'model' in df.columns
        assert df['model'].iloc[0] == 'nbeats'
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_generic_basis(self):
        """Test GenericBasis class."""
        from financial_dashboard.models.nbeats_forecaster import GenericBasis
        
        basis = GenericBasis(backcast_size=60, forecast_size=5, theta_size=32)
        
        theta = torch.randn(4, 32)  # batch=4, theta_size=32
        
        backcast = basis.backcast(theta)
        forecast = basis.forecast(theta)
        
        assert backcast.shape == (4, 60)
        assert forecast.shape == (4, 5)
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_trend_basis(self):
        """Test TrendBasis (polynomial)."""
        from financial_dashboard.models.nbeats_forecaster import TrendBasis
        
        basis = TrendBasis(backcast_size=60, forecast_size=5, degree=3)
        
        theta = torch.randn(4, 4)  # batch=4, degree+1=4
        
        backcast = basis.backcast(theta)
        forecast = basis.forecast(theta)
        
        assert backcast.shape == (4, 60)
        assert forecast.shape == (4, 5)
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_seasonality_basis(self):
        """Test SeasonalityBasis (Fourier)."""
        from financial_dashboard.models.nbeats_forecaster import SeasonalityBasis
        
        basis = SeasonalityBasis(backcast_size=60, forecast_size=5, num_harmonics=5)
        
        theta = torch.randn(4, 10)  # batch=4, 2*num_harmonics=10
        
        backcast = basis.backcast(theta)
        forecast = basis.forecast(theta)
        
        assert backcast.shape == (4, 60)
        assert forecast.shape == (4, 5)
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_nbeats_block(self):
        """Test NBeatsBlock."""
        from financial_dashboard.models.nbeats_forecaster import NBeatsBlock, GenericBasis
        
        basis = GenericBasis(60, 5, 32)
        block = NBeatsBlock(
            input_size=60,
            theta_size=32,
            basis_function=basis,
            num_layers=4,
            layer_size=256
        )
        
        x = torch.randn(4, 60)  # batch=4, input_size=60
        
        backcast, forecast = block(x)
        
        assert backcast.shape == (4, 60)
        assert forecast.shape == (4, 5)
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_nbeats_model(self):
        """Test full NBeats model."""
        from financial_dashboard.models.nbeats_forecaster import NBeats
        
        model = NBeats(
            input_size=60,
            forecast_size=5,
            num_stacks=3,
            num_blocks_per_stack=2,
            interpretable=True
        )
        
        x = torch.randn(4, 60)
        
        residual, forecast = model(x)
        
        assert residual.shape == (4, 60)
        assert forecast.shape == (4, 5)
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_nbeats_model_generic(self):
        """Test NBeats with generic (non-interpretable) stacks."""
        from financial_dashboard.models.nbeats_forecaster import NBeats
        
        model = NBeats(
            input_size=60,
            forecast_size=5,
            num_stacks=2,
            interpretable=False
        )
        
        x = torch.randn(2, 60)
        
        _, forecast = model(x)
        
        assert forecast.shape == (2, 5)
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_nbeats_components(self):
        """Test NBeats component extraction."""
        from financial_dashboard.models.nbeats_forecaster import NBeats
        
        model = NBeats(
            input_size=60,
            forecast_size=5,
            num_stacks=3,
            interpretable=True
        )
        
        x = torch.randn(2, 60)
        
        components = model.forward_with_components(x)
        
        assert 'total' in components
        assert 'residual' in components
        assert components['total'].shape == (2, 5)
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_forecaster_init(self):
        """Test NBeatsForecaster initialization."""
        from financial_dashboard.models.nbeats_forecaster import NBeatsForecaster
        
        forecaster = NBeatsForecaster(
            lookback=60,
            horizon=5,
            interpretable=True
        )
        
        assert forecaster.lookback == 60
        assert forecaster.horizon == 5
        assert forecaster.fitted is False
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_forecaster_fit(self, short_time_series):
        """Test NBeatsForecaster training."""
        from financial_dashboard.models.nbeats_forecaster import NBeatsForecaster
        
        forecaster = NBeatsForecaster(
            lookback=30,
            horizon=5,
            num_stacks=2,
            num_blocks=1,
            layer_size=64
        )
        
        forecaster.fit(
            short_time_series,
            epochs=5,
            batch_size=16,
            verbose=False
        )
        
        assert forecaster.fitted is True
        assert len(forecaster.training_history) > 0
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_forecaster_predict(self, short_time_series):
        """Test NBeatsForecaster prediction."""
        from financial_dashboard.models.nbeats_forecaster import NBeatsForecaster
        
        forecaster = NBeatsForecaster(
            lookback=30,
            horizon=5,
            num_stacks=2,
            num_blocks=1,
            layer_size=64
        )
        
        forecaster.fit(short_time_series, epochs=5, verbose=False)
        
        result = forecaster.predict(short_time_series)
        
        assert isinstance(result, pd.DataFrame)
        assert 'ds' in result.columns
        assert 'yhat' in result.columns
        assert len(result) == 5  # horizon
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_forecaster_model_summary(self):
        """Test model summary method."""
        from financial_dashboard.models.nbeats_forecaster import NBeatsForecaster
        
        forecaster = NBeatsForecaster(lookback=60, horizon=5)
        summary = forecaster.get_model_summary()
        
        assert 'model' in summary
        assert summary['model'] == 'N-BEATS'
        assert 'total_parameters' in summary
        assert summary['total_parameters'] > 0
    
    def test_numpy_fallback(self, short_time_series):
        """Test numpy fallback implementation."""
        from financial_dashboard.models.nbeats_forecaster import NBeatsForecasterNumpy
        
        forecaster = NBeatsForecasterNumpy(lookback=30, horizon=5)
        forecaster.fit(short_time_series)
        
        assert forecaster.fitted is True
        
        result = forecaster.predict(short_time_series)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 5
    
    def test_factory_function(self):
        """Test get_nbeats_forecaster factory."""
        from financial_dashboard.models.nbeats_forecaster import get_nbeats_forecaster
        
        forecaster = get_nbeats_forecaster(lookback=60, horizon=5)
        
        assert forecaster is not None
        assert hasattr(forecaster, 'fit')
        assert hasattr(forecaster, 'predict')


# ============================================================================
# N-HiTS Tests
# ============================================================================

class TestNHiTSForecaster:
    """Tests for N-HiTS implementation."""
    
    def test_import(self):
        """Test module imports."""
        from financial_dashboard.models.nhits_forecaster import (
            NHiTSForecaster,
            NHiTSForecastResult,
            get_nhits_availability
        )
        assert NHiTSForecaster is not None
    
    def test_availability_check(self):
        """Test availability checker."""
        from financial_dashboard.models.nhits_forecaster import get_nhits_availability
        
        avail = get_nhits_availability()
        assert 'torch' in avail
        assert 'nhits_numpy' in avail
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_nhits_block(self):
        """Test NHiTSBlock with pooling."""
        from financial_dashboard.models.nhits_forecaster import NHiTSBlock
        
        block = NHiTSBlock(
            input_size=60,
            output_size=5,
            pooling_kernel=2,
            downsample_ratio=2,
            layer_size=128
        )
        
        x = torch.randn(4, 60)
        
        backcast, forecast = block(x)
        
        assert backcast.shape == (4, 60)
        assert forecast.shape == (4, 5)
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_nhits_block_no_pooling(self):
        """Test NHiTSBlock without pooling."""
        from financial_dashboard.models.nhits_forecaster import NHiTSBlock
        
        block = NHiTSBlock(
            input_size=60,
            output_size=5,
            pooling_kernel=1,
            downsample_ratio=1
        )
        
        x = torch.randn(2, 60)
        
        backcast, forecast = block(x)
        
        assert backcast.shape == (2, 60)
        assert forecast.shape == (2, 5)
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_nhits_model(self):
        """Test full NHiTS model."""
        from financial_dashboard.models.nhits_forecaster import NHiTS
        
        model = NHiTS(
            input_size=60,
            output_size=5,
            num_stacks=3,
            pooling_kernels=[1, 2, 4]
        )
        
        x = torch.randn(4, 60)
        
        residual, forecast = model(x)
        
        assert residual.shape == (4, 60)
        assert forecast.shape == (4, 5)
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_nhits_scales(self):
        """Test NHiTS multi-scale decomposition."""
        from financial_dashboard.models.nhits_forecaster import NHiTS
        
        model = NHiTS(
            input_size=60,
            output_size=5,
            num_stacks=3,
            pooling_kernels=[1, 2, 4]
        )
        
        x = torch.randn(2, 60)
        
        components = model.forward_with_scales(x)
        
        assert 'total' in components
        assert 'scale_1x' in components
        assert 'scale_2x' in components
        assert 'scale_4x' in components
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_nhits_complexity(self):
        """Test model complexity metrics."""
        from financial_dashboard.models.nhits_forecaster import NHiTS
        
        model = NHiTS(input_size=60, output_size=5)
        complexity = model.get_model_complexity()
        
        assert 'total_parameters' in complexity
        assert complexity['total_parameters'] > 0
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_forecaster_init(self):
        """Test NHiTSForecaster initialization."""
        from financial_dashboard.models.nhits_forecaster import NHiTSForecaster
        
        forecaster = NHiTSForecaster(
            lookback=60,
            horizon=5,
            num_stacks=3
        )
        
        assert forecaster.lookback == 60
        assert forecaster.horizon == 5
        assert forecaster.fitted is False
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_forecaster_fit(self, short_time_series):
        """Test NHiTSForecaster training."""
        from financial_dashboard.models.nhits_forecaster import NHiTSForecaster
        
        forecaster = NHiTSForecaster(
            lookback=30,
            horizon=5,
            num_stacks=2,
            layer_size=64
        )
        
        forecaster.fit(
            short_time_series,
            epochs=5,
            batch_size=16,
            verbose=False
        )
        
        assert forecaster.fitted is True
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_forecaster_predict(self, short_time_series):
        """Test NHiTSForecaster prediction."""
        from financial_dashboard.models.nhits_forecaster import NHiTSForecaster
        
        forecaster = NHiTSForecaster(
            lookback=30,
            horizon=5,
            num_stacks=2,
            layer_size=64
        )
        
        forecaster.fit(short_time_series, epochs=5, verbose=False)
        
        result = forecaster.predict(short_time_series)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 5
        assert 'yhat' in result.columns
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_forecaster_model_summary(self):
        """Test model summary."""
        from financial_dashboard.models.nhits_forecaster import NHiTSForecaster
        
        forecaster = NHiTSForecaster(lookback=60, horizon=5)
        summary = forecaster.get_model_summary()
        
        assert summary['model'] == 'N-HiTS'
        assert 'pooling_kernels' in summary
    
    def test_numpy_fallback(self, short_time_series):
        """Test numpy fallback."""
        from financial_dashboard.models.nhits_forecaster import NHiTSForecasterNumpy
        
        forecaster = NHiTSForecasterNumpy(lookback=30, horizon=5)
        forecaster.fit(short_time_series)
        
        result = forecaster.predict(short_time_series)
        
        assert len(result) == 5
    
    def test_factory_function(self):
        """Test get_nhits_forecaster factory."""
        from financial_dashboard.models.nhits_forecaster import get_nhits_forecaster
        
        forecaster = get_nhits_forecaster(lookback=60, horizon=5)
        
        assert forecaster is not None


# ============================================================================
# Enhanced Forecast Engine Tests
# ============================================================================

class TestEnhancedForecastEngine:
    """Tests for Enhanced Forecast Engine."""
    
    def test_import(self):
        """Test module imports."""
        from financial_dashboard.models.enhanced_forecast_engine import (
            EnhancedForecastEngine,
            EnsembleForecast,
            ForecastConfig,
            get_engine_availability
        )
        assert EnhancedForecastEngine is not None
    
    def test_forecast_config(self):
        """Test ForecastConfig dataclass."""
        from financial_dashboard.models.enhanced_forecast_engine import ForecastConfig
        
        config = ForecastConfig(
            horizon=10,
            lookback=90,
            models=['nbeats', 'nhits']
        )
        
        assert config.horizon == 10
        assert config.lookback == 90
        assert 'nbeats' in config.models
    
    def test_ensemble_forecast_dataclass(self):
        """Test EnsembleForecast dataclass."""
        from financial_dashboard.models.enhanced_forecast_engine import EnsembleForecast
        
        dates = pd.date_range('2024-01-01', periods=5).tolist()
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        lower = values - 0.5
        upper = values + 0.5
        
        forecast = EnsembleForecast(
            dates=dates,
            values=values,
            lower_bound=lower,
            upper_bound=upper,
            model_weights={'model1': 0.6, 'model2': 0.4},
            individual_forecasts={'model1': values, 'model2': values + 0.1},
            confidence_level=0.95
        )
        
        df = forecast.to_dataframe()
        
        assert 'yhat' in df.columns
        assert 'yhat_lower' in df.columns
        assert 'yhat_upper' in df.columns
    
    def test_engine_init(self):
        """Test engine initialization."""
        from financial_dashboard.models.enhanced_forecast_engine import EnhancedForecastEngine
        
        engine = EnhancedForecastEngine(
            horizon=5,
            lookback=60,
            models=['ets', 'naive']
        )
        
        assert engine.horizon == 5
        assert engine.fitted is False
    
    def test_get_available_models(self):
        """Test available models check."""
        from financial_dashboard.models.enhanced_forecast_engine import EnhancedForecastEngine
        
        engine = EnhancedForecastEngine()
        models = engine.get_available_models()
        
        assert 'ets' in models  # Always available
        assert 'naive' in models  # Always available
    
    def test_engine_availability(self):
        """Test engine availability function."""
        from financial_dashboard.models.enhanced_forecast_engine import get_engine_availability
        
        avail = get_engine_availability()
        
        assert 'ets' in avail
        assert avail['ets'] is True
        assert avail['naive'] is True
    
    def test_ets_wrapper(self, short_time_series):
        """Test ETS wrapper."""
        from financial_dashboard.models.enhanced_forecast_engine import ETSWrapper
        
        ets = ETSWrapper(horizon=5)
        ets.fit(short_time_series)
        
        result = ets.predict(short_time_series)
        
        assert len(result) == 5
        assert 'yhat' in result.columns
    
    def test_naive_forecaster(self, short_time_series):
        """Test Naive baseline."""
        from financial_dashboard.models.enhanced_forecast_engine import NaiveForecaster
        
        naive = NaiveForecaster(horizon=5)
        naive.fit(short_time_series)
        
        result = naive.predict(short_time_series)
        
        assert len(result) == 5
        # All values should be the last observed value
        last_val = short_time_series['y'].iloc[-1]
        assert all(result['yhat'] == last_val)
    
    def test_engine_fit_statistical(self, sample_time_series):
        """Test engine fit with statistical models only."""
        from financial_dashboard.models.enhanced_forecast_engine import EnhancedForecastEngine
        
        engine = EnhancedForecastEngine(
            horizon=5,
            models=['ets', 'naive']
        )
        
        engine.fit(sample_time_series, val_split=0.2, verbose=False)
        
        assert engine.fitted is True
        assert len(engine.fitted_models) >= 1
        assert len(engine.model_scores) >= 1
    
    def test_engine_predict(self, sample_time_series):
        """Test engine prediction."""
        from financial_dashboard.models.enhanced_forecast_engine import EnhancedForecastEngine
        
        engine = EnhancedForecastEngine(
            horizon=5,
            models=['ets', 'naive']
        )
        
        engine.fit(sample_time_series, verbose=False)
        result = engine.predict(sample_time_series)
        
        assert result is not None
        assert len(result.values) == 5
        assert result.lower_bound is not None
        assert result.upper_bound is not None
    
    def test_engine_model_comparison(self, sample_time_series):
        """Test model comparison output."""
        from financial_dashboard.models.enhanced_forecast_engine import EnhancedForecastEngine
        
        engine = EnhancedForecastEngine(
            horizon=5,
            models=['ets', 'naive']
        )
        
        engine.fit(sample_time_series, verbose=False)
        
        comparison = engine.get_model_comparison()
        
        assert isinstance(comparison, pd.DataFrame)
        assert 'model' in comparison.columns
        assert 'rmse' in comparison.columns
    
    def test_engine_summary(self):
        """Test engine summary."""
        from financial_dashboard.models.enhanced_forecast_engine import EnhancedForecastEngine
        
        engine = EnhancedForecastEngine(horizon=5)
        summary = engine.get_engine_summary()
        
        assert 'horizon' in summary
        assert 'available_models' in summary
        assert 'fitted' in summary
    
    def test_quick_forecast(self, sample_time_series):
        """Test quick_forecast convenience function."""
        from financial_dashboard.models.enhanced_forecast_engine import quick_forecast
        
        result = quick_forecast(
            sample_time_series,
            horizon=5,
            model='ets'
        )
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 5
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_engine_with_neural_models(self, sample_time_series):
        """Test engine with neural models."""
        from financial_dashboard.models.enhanced_forecast_engine import EnhancedForecastEngine
        
        engine = EnhancedForecastEngine(
            horizon=5,
            lookback=30,
            models=['nbeats', 'ets']
        )
        
        engine.fit(
            sample_time_series,
            epochs=3,  # Quick test
            verbose=False
        )
        
        assert 'nbeats' in engine.fitted_models or 'ets' in engine.fitted_models
    
    def test_return_individual_forecasts(self, sample_time_series):
        """Test returning individual model forecasts."""
        from financial_dashboard.models.enhanced_forecast_engine import EnhancedForecastEngine
        
        engine = EnhancedForecastEngine(
            horizon=5,
            models=['ets', 'naive']
        )
        
        engine.fit(sample_time_series, verbose=False)
        result = engine.predict(sample_time_series, return_individual=True)
        
        assert isinstance(result, dict)
        assert 'ensemble' in result
        assert 'individual' in result
        assert 'model_scores' in result


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests across Part 3 components."""
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_nbeats_nhits_comparison(self, sample_time_series):
        """Compare N-BEATS and N-HiTS on same data."""
        from financial_dashboard.models.nbeats_forecaster import NBeatsForecaster
        from financial_dashboard.models.nhits_forecaster import NHiTSForecaster
        
        # Train both
        nbeats = NBeatsForecaster(lookback=30, horizon=5, num_stacks=2, layer_size=64)
        nhits = NHiTSForecaster(lookback=30, horizon=5, num_stacks=2, layer_size=64)
        
        nbeats.fit(sample_time_series, epochs=3, verbose=False)
        nhits.fit(sample_time_series, epochs=3, verbose=False)
        
        # Predict
        nbeats_pred = nbeats.predict(sample_time_series)
        nhits_pred = nhits.predict(sample_time_series)
        
        # Both should produce valid forecasts
        assert len(nbeats_pred) == 5
        assert len(nhits_pred) == 5
        assert not np.isnan(nbeats_pred['yhat']).any()
        assert not np.isnan(nhits_pred['yhat']).any()
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_full_ensemble_pipeline(self, sample_time_series):
        """Test complete ensemble forecasting pipeline."""
        from financial_dashboard.models.enhanced_forecast_engine import EnhancedForecastEngine
        
        engine = EnhancedForecastEngine(
            horizon=5,
            lookback=30,
            models=['nbeats', 'nhits', 'ets'],
            auto_select=True,
            max_models_ensemble=2
        )
        
        # Fit
        engine.fit(sample_time_series, epochs=3, verbose=False)
        
        # Predict
        result = engine.predict(sample_time_series, return_individual=True)
        
        # Validate
        assert 'ensemble' in result
        assert result['ensemble'] is not None
        assert len(result['ensemble'].values) == 5
        
        # Model selection worked
        assert len(engine.best_models) <= 2
    
    def test_all_availability_checks(self):
        """Test all availability check functions."""
        from financial_dashboard.models.nbeats_forecaster import get_nbeats_availability
        from financial_dashboard.models.nhits_forecaster import get_nhits_availability
        from financial_dashboard.models.enhanced_forecast_engine import get_engine_availability
        
        nbeats_avail = get_nbeats_availability()
        nhits_avail = get_nhits_availability()
        engine_avail = get_engine_availability()
        
        # All return dicts
        assert isinstance(nbeats_avail, dict)
        assert isinstance(nhits_avail, dict)
        assert isinstance(engine_avail, dict)
        
        # Common keys
        assert 'torch' in nbeats_avail
        assert 'torch' in nhits_avail
    
    @pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
    def test_uncertainty_estimation(self, sample_time_series):
        """Test MC dropout uncertainty estimation."""
        from financial_dashboard.models.nbeats_forecaster import NBeatsForecaster
        
        forecaster = NBeatsForecaster(
            lookback=30,
            horizon=5,
            num_stacks=2,
            layer_size=64
        )
        
        forecaster.fit(sample_time_series, epochs=5, verbose=False)
        
        # Predict with uncertainty
        result = forecaster.predict(sample_time_series, n_samples=10)
        
        # Should have confidence bounds when n_samples > 0
        # Note: bounds are in the ForecastResult but to_dataframe may include them
        assert 'yhat' in result.columns


# ============================================================================
# Run tests
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
