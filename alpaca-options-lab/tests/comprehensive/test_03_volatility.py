"""
Alpaca Options Lab - Comprehensive Volatility Tests
Test File 3 of 10: Volatility Lab Components
~50 tests covering IV, Surface, Skew, Term Structure
"""
import pytest
from datetime import datetime, date, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
import sys
sys.path.insert(0, '.')


class TestIVEngine:
    """Tests for IV Engine - 15 tests"""
    
    def test_iv_engine_import(self):
        from src.volatility.iv_engine import IVEngine
        assert IVEngine is not None
    
    def test_iv_model_enum(self):
        from src.volatility.iv_engine import IVModel
        assert IVModel is not None
    
    def test_iv_result_class(self):
        from src.volatility.iv_engine import IVResult
        assert IVResult is not None
    
    def test_iv_engine_creation(self):
        from src.volatility.iv_engine import IVEngine
        engine = IVEngine()
        assert engine is not None
    
    def test_iv_engine_with_rate(self):
        from src.volatility.iv_engine import IVEngine
        engine = IVEngine(risk_free_rate=0.05)
        assert engine is not None
    
    def test_iv_calculation(self):
        from src.volatility.iv_engine import IVEngine, IVModel
        engine = IVEngine(risk_free_rate=0.05)
        result = engine.calculate_iv(
            market_price=10.0,
            spot=100.0,
            strike=100.0,
            time_to_expiry=30/365,
            is_call=True,
            model=IVModel.NEWTON_RAPHSON
        )
        assert result.iv > 0
    
    def test_iv_result_has_iv(self):
        from src.volatility.iv_engine import IVEngine, IVModel
        engine = IVEngine()
        result = engine.calculate_iv(
            market_price=5.0,
            spot=100.0,
            strike=100.0,
            time_to_expiry=30/365,
            is_call=True
        )
        assert hasattr(result, 'iv')
    
    def test_iv_result_has_iterations(self):
        from src.volatility.iv_engine import IVEngine
        engine = IVEngine()
        result = engine.calculate_iv(
            market_price=5.0,
            spot=100.0,
            strike=100.0,
            time_to_expiry=30/365,
            is_call=True
        )
        assert hasattr(result, 'iterations') or hasattr(result, 'converged')
    
    def test_all_greeks(self):
        from src.volatility.iv_engine import IVEngine
        engine = IVEngine()
        greeks = engine.all_greeks(
            spot=100.0,
            strike=100.0,
            time_to_expiry=30/365,
            volatility=0.25,
            is_call=True
        )
        assert "delta" in greeks
        assert "gamma" in greeks
    
    def test_greeks_has_theta(self):
        from src.volatility.iv_engine import IVEngine
        engine = IVEngine()
        greeks = engine.all_greeks(
            spot=100.0,
            strike=100.0,
            time_to_expiry=30/365,
            volatility=0.25,
            is_call=True
        )
        assert "theta" in greeks
    
    def test_greeks_has_vega(self):
        from src.volatility.iv_engine import IVEngine
        engine = IVEngine()
        greeks = engine.all_greeks(
            spot=100.0,
            strike=100.0,
            time_to_expiry=30/365,
            volatility=0.25,
            is_call=True
        )
        assert "vega" in greeks
    
    def test_greeks_has_rho(self):
        from src.volatility.iv_engine import IVEngine
        engine = IVEngine()
        greeks = engine.all_greeks(
            spot=100.0,
            strike=100.0,
            time_to_expiry=30/365,
            volatility=0.25,
            is_call=True
        )
        assert "rho" in greeks
    
    def test_iv_model_newton_raphson(self):
        from src.volatility.iv_engine import IVModel
        assert hasattr(IVModel, 'NEWTON_RAPHSON')
    
    def test_iv_model_bisection(self):
        from src.volatility.iv_engine import IVModel
        assert hasattr(IVModel, 'BISECTION')
    
    def test_iv_engine_put_option(self):
        from src.volatility.iv_engine import IVEngine
        engine = IVEngine()
        result = engine.calculate_iv(
            market_price=5.0,
            spot=100.0,
            strike=100.0,
            time_to_expiry=30/365,
            is_call=False  # PUT
        )
        assert result.iv > 0


class TestVolatilitySurface:
    """Tests for Volatility Surface - 15 tests"""
    
    def test_surface_import(self):
        from src.volatility.surface import VolatilitySurface
        assert VolatilitySurface is not None
    
    def test_surface_config_import(self):
        from src.volatility.surface import SurfaceConfig
        assert SurfaceConfig is not None
    
    def test_surface_creation(self):
        from src.volatility.surface import VolatilitySurface, SurfaceConfig
        surface = VolatilitySurface(symbol="SPY", spot_price=450.0, config=SurfaceConfig())
        assert surface is not None
    
    def test_surface_has_symbol(self):
        from src.volatility.surface import VolatilitySurface, SurfaceConfig
        surface = VolatilitySurface(symbol="SPY", spot_price=450.0, config=SurfaceConfig())
        assert surface.symbol == "SPY"
    
    def test_surface_has_spot_price(self):
        from src.volatility.surface import VolatilitySurface, SurfaceConfig
        surface = VolatilitySurface(symbol="SPY", spot_price=450.0, config=SurfaceConfig())
        assert surface.spot_price == 450.0
    
    def test_surface_point_class(self):
        from src.volatility.surface import SurfacePoint
        assert SurfacePoint is not None
    
    def test_interpolation_method_enum(self):
        from src.volatility.surface import InterpolationMethod
        assert InterpolationMethod is not None
    
    def test_surface_has_add_point(self):
        from src.volatility.surface import VolatilitySurface, SurfaceConfig
        surface = VolatilitySurface(symbol="SPY", spot_price=450.0, config=SurfaceConfig())
        assert hasattr(surface, 'add_point')
    
    def test_surface_has_get_iv(self):
        from src.volatility.surface import VolatilitySurface, SurfaceConfig
        surface = VolatilitySurface(symbol="SPY", spot_price=450.0, config=SurfaceConfig())
        assert hasattr(surface, 'get_iv') or hasattr(surface, 'interpolate')
    
    def test_surface_config_defaults(self):
        from src.volatility.surface import SurfaceConfig
        config = SurfaceConfig()
        assert config is not None
    
    def test_surface_has_points(self):
        from src.volatility.surface import VolatilitySurface, SurfaceConfig
        surface = VolatilitySurface(symbol="SPY", spot_price=450.0, config=SurfaceConfig())
        assert hasattr(surface, '_points') or hasattr(surface, 'points')
    
    def test_surface_has_build(self):
        from src.volatility.surface import VolatilitySurface, SurfaceConfig
        surface = VolatilitySurface(symbol="SPY", spot_price=450.0, config=SurfaceConfig())
        assert hasattr(surface, 'build') or hasattr(surface, 'fit')
    
    def test_interpolation_methods_count(self):
        from src.volatility.surface import InterpolationMethod
        assert len(list(InterpolationMethod)) >= 2
    
    def test_surface_config_has_method(self):
        from src.volatility.surface import SurfaceConfig
        config = SurfaceConfig()
        assert hasattr(config, 'interpolation_method') or hasattr(config, 'method')
    
    def test_surface_file_size(self):
        import os
        path = 'src/volatility/surface.py'
        assert os.path.exists(path)
        with open(path) as f:
            lines = len(f.readlines())
        assert lines > 200


class TestTermStructure:
    """Tests for Term Structure - 10 tests"""
    
    def test_term_structure_import(self):
        from src.volatility.term_structure import TermStructure
        assert TermStructure is not None
    
    def test_term_structure_creation(self):
        from src.volatility.term_structure import TermStructure
        term = TermStructure(symbol="SPY", spot_price=450.0)
        assert term is not None
    
    def test_term_structure_point_class(self):
        from src.volatility.term_structure import TermStructurePoint
        assert TermStructurePoint is not None
    
    def test_term_structure_analysis_class(self):
        from src.volatility.term_structure import TermStructureAnalysis
        assert TermStructureAnalysis is not None
    
    def test_contango_backwardation_enum(self):
        from src.volatility.term_structure import ContangoBackwardation
        assert ContangoBackwardation is not None
    
    def test_term_structure_add_point(self):
        from src.volatility.term_structure import TermStructure
        term = TermStructure(symbol="SPY", spot_price=450.0)
        future_expiry = date.today() + timedelta(days=30)
        term.add_point(expiry=future_expiry, iv=0.15)
        assert len(term._points) > 0
    
    def test_term_structure_has_analyze(self):
        from src.volatility.term_structure import TermStructure
        term = TermStructure(symbol="SPY", spot_price=450.0)
        assert hasattr(term, 'analyze')
    
    def test_term_structure_multiple_points(self):
        from src.volatility.term_structure import TermStructure
        term = TermStructure(symbol="SPY", spot_price=450.0)
        for i in range(1, 5):
            term.add_point(expiry=date.today() + timedelta(days=30*i), iv=0.15 + i*0.01)
        assert len(term._points) == 4
    
    def test_term_structure_has_symbol(self):
        from src.volatility.term_structure import TermStructure
        term = TermStructure(symbol="SPY", spot_price=450.0)
        assert term.symbol == "SPY"
    
    def test_term_structure_file_size(self):
        import os
        path = 'src/volatility/term_structure.py'
        assert os.path.exists(path)
        with open(path) as f:
            lines = len(f.readlines())
        assert lines > 100


class TestVolatilitySkew:
    """Tests for Volatility Skew - 10 tests"""
    
    def test_skew_import(self):
        from src.volatility.skew import VolatilitySkew
        assert VolatilitySkew is not None
    
    def test_skew_creation(self):
        from src.volatility.skew import VolatilitySkew
        future_expiry = date.today() + timedelta(days=30)
        skew = VolatilitySkew(symbol="SPY", expiry=future_expiry, spot_price=450.0)
        assert skew is not None
    
    def test_skew_type_enum(self):
        from src.volatility.skew import SkewType
        assert SkewType is not None
    
    def test_skew_point_class(self):
        from src.volatility.skew import SkewPoint
        assert SkewPoint is not None
    
    def test_skew_metrics_class(self):
        from src.volatility.skew import SkewMetrics
        assert SkewMetrics is not None
    
    def test_skew_add_point(self):
        from src.volatility.skew import VolatilitySkew
        future_expiry = date.today() + timedelta(days=30)
        skew = VolatilitySkew(symbol="SPY", expiry=future_expiry, spot_price=450.0)
        skew.add_point(strike=440.0, iv=0.18)
        skew.add_point(strike=450.0, iv=0.15)
        assert len(skew._points) == 2
    
    def test_skew_has_analyze(self):
        from src.volatility.skew import VolatilitySkew
        future_expiry = date.today() + timedelta(days=30)
        skew = VolatilitySkew(symbol="SPY", expiry=future_expiry, spot_price=450.0)
        assert hasattr(skew, 'analyze')
    
    def test_skew_has_symbol(self):
        from src.volatility.skew import VolatilitySkew
        future_expiry = date.today() + timedelta(days=30)
        skew = VolatilitySkew(symbol="SPY", expiry=future_expiry, spot_price=450.0)
        assert skew.symbol == "SPY"
    
    def test_skew_has_expiry(self):
        from src.volatility.skew import VolatilitySkew
        future_expiry = date.today() + timedelta(days=30)
        skew = VolatilitySkew(symbol="SPY", expiry=future_expiry, spot_price=450.0)
        assert skew.expiry == future_expiry
    
    def test_skew_file_size(self):
        import os
        path = 'src/volatility/skew.py'
        assert os.path.exists(path)
        with open(path) as f:
            lines = len(f.readlines())
        assert lines > 100


class TestVolatilityStrategies:
    """Tests for Volatility Trading Strategies - 5 tests"""
    
    def test_vol_strategies_import(self):
        from src.volatility.strategies import VolStrategy
        assert VolStrategy is not None
    
    def test_vol_trade_signal(self):
        from src.volatility.strategies import VolTradeSignal
        assert VolTradeSignal is not None
    
    def test_calendar_spread_finder(self):
        from src.volatility.strategies import CalendarSpreadFinder
        assert CalendarSpreadFinder is not None
    
    def test_vol_arbitrage(self):
        from src.volatility.strategies import VolArbitrage
        assert VolArbitrage is not None
    
    def test_skew_trade(self):
        from src.volatility.strategies import SkewTrade
        assert SkewTrade is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
