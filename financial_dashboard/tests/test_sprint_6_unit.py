"""
Sprint 6 Unit Tests
Tests for Advanced Analytics & Integrated UX features

Test Coverage:
1. Factor DNA component
2. Portfolio Health Dashboard
3. Volatility Lab
4. Hedge Finder
5. Global Search
6. Theme Toggle
7. Sentiment Analysis
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Sprint 6 components
from components.factor_dna import (
    calculate_factor_attribution,
    create_factor_dna_chart,
    create_factor_dna_table
)
from components.portfolio_health import (
    calculate_portfolio_health,
    create_health_score_gauge,
    create_correlation_heatmap
)
from components.volatility_lab import (
    fetch_vix_data,
    calculate_implied_vol_term_structure,
    detect_volatility_regime,
    forecast_volatility
)
from components.hedge_finder import (
    find_hedge_assets,
    find_options_hedges,
    create_correlation_chart
)
from components.global_search import search_database
from components.theme_toggle import get_theme_css, THEMES
from components.sentiment_analysis import (
    fetch_reddit_sentiment,
    fetch_news_sentiment,
    calculate_composite_sentiment
)


class TestFactorDNA:
    """Test Factor DNA component"""
    
    def test_calculate_factor_attribution(self):
        """Test factor attribution calculation"""
        factor_returns = calculate_factor_attribution(None, None)
        
        assert isinstance(factor_returns, dict)
        assert 'value' in factor_returns
        assert 'growth' in factor_returns
        assert 'momentum' in factor_returns
        assert 'quality' in factor_returns
        assert 'size' in factor_returns
        
        # All factors should have numeric values
        for factor, value in factor_returns.items():
            assert isinstance(value, (int, float))
    
    def test_create_factor_dna_chart(self):
        """Test factor DNA chart creation"""
        factor_returns = calculate_factor_attribution(None, None)
        fig = create_factor_dna_chart(factor_returns)
        
        assert fig is not None
        assert hasattr(fig, 'data')
        assert len(fig.data) > 0
        assert fig.data[0].type == 'bar'
    
    def test_create_factor_dna_table(self):
        """Test factor DNA table creation"""
        factor_returns = calculate_factor_attribution(None, None)
        table = create_factor_dna_table(factor_returns)
        
        assert table is not None
        assert table.type == 'Table'


class TestPortfolioHealth:
    """Test Portfolio Health Dashboard component"""
    
    def test_calculate_portfolio_health(self):
        """Test portfolio health calculation"""
        health_metrics = calculate_portfolio_health(None, None)
        
        assert isinstance(health_metrics, dict)
        assert 'health_score' in health_metrics
        assert 'risk_metrics' in health_metrics
        assert 'diversification' in health_metrics
        assert 'sector_exposure' in health_metrics
        
        # Health score should be 0-100
        assert 0 <= health_metrics['health_score'] <= 100
        
        # Risk metrics should have required fields
        risk = health_metrics['risk_metrics']
        assert 'sharpe_ratio' in risk
        assert 'max_drawdown' in risk
        assert 'volatility' in risk
        assert 'beta' in risk
    
    def test_create_health_score_gauge(self):
        """Test health score gauge creation"""
        fig = create_health_score_gauge(75)
        
        assert fig is not None
        assert hasattr(fig, 'data')
        assert len(fig.data) > 0
        assert fig.data[0].type == 'indicator'
    
    def test_create_correlation_heatmap(self):
        """Test correlation heatmap creation"""
        fig = create_correlation_heatmap(None)
        
        assert fig is not None
        assert hasattr(fig, 'data')
        assert len(fig.data) > 0
        assert fig.data[0].type == 'heatmap'


class TestVolatilityLab:
    """Test Volatility Lab component"""
    
    def test_fetch_vix_data(self):
        """Test VIX data fetching"""
        vix_data = fetch_vix_data()
        
        assert isinstance(vix_data, pd.DataFrame)
        assert 'date' in vix_data.columns
        assert 'vix' in vix_data.columns
        assert len(vix_data) > 0
    
    def test_calculate_implied_vol_term_structure(self):
        """Test implied vol term structure calculation"""
        vol_data = calculate_implied_vol_term_structure('SPY')
        
        assert isinstance(vol_data, pd.DataFrame)
        assert 'days_to_expiration' in vol_data.columns
        assert 'implied_vol' in vol_data.columns
        assert len(vol_data) > 0
    
    def test_detect_volatility_regime(self):
        """Test volatility regime detection"""
        vix_series = pd.Series([15, 18, 20, 22, 16])
        regime, color = detect_volatility_regime(vix_series)
        
        assert regime in ['low', 'normal', 'high', 'crisis']
        assert color.startswith('#')
    
    def test_forecast_volatility(self):
        """Test volatility forecasting"""
        vix_series = pd.Series(np.random.uniform(15, 25, 90))
        forecast = forecast_volatility(vix_series, horizon_days=30)
        
        assert isinstance(forecast, pd.DataFrame)
        assert 'date' in forecast.columns
        assert 'forecast_vix' in forecast.columns
        assert len(forecast) == 30


class TestHedgeFinder:
    """Test Hedge Finder component"""
    
    def test_find_hedge_assets(self):
        """Test finding hedge assets"""
        hedge_assets = find_hedge_assets(None, correlation_threshold=-0.3)
        
        assert isinstance(hedge_assets, list)
        assert len(hedge_assets) > 0
        
        for asset in hedge_assets:
            assert 'ticker' in asset
            assert 'correlation' in asset
            assert 'hedge_ratio' in asset
            assert asset['correlation'] <= -0.3
    
    def test_find_options_hedges(self):
        """Test finding options hedging strategies"""
        strategies = find_options_hedges(None)
        
        assert isinstance(strategies, list)
        assert len(strategies) > 0
        
        for strat in strategies:
            assert 'name' in strat
            assert 'description' in strat
            assert 'cost' in strat
            assert 'protection' in strat
    
    def test_create_correlation_chart(self):
        """Test correlation chart creation"""
        hedge_assets = find_hedge_assets(None)
        fig = create_correlation_chart(hedge_assets)
        
        assert fig is not None
        assert hasattr(fig, 'data')
        assert len(fig.data) > 0


class TestGlobalSearch:
    """Test Global Search component"""
    
    def test_search_database_tickers(self):
        """Test searching for tickers"""
        results = search_database('AAPL')
        
        assert isinstance(results, list)
        assert len(results) > 0
        
        # Check result structure
        result = results[0]
        assert 'type' in result
        assert 'title' in result
        assert 'description' in result
        assert 'href' in result
    
    def test_search_database_strategies(self):
        """Test searching for strategies"""
        results = search_database('condor')
        
        assert isinstance(results, list)
        # Should find Iron Condor strategy
        strategy_results = [r for r in results if r['type'] == 'strategies']
        assert len(strategy_results) > 0
    
    def test_search_database_tabs(self):
        """Test searching for tabs"""
        results = search_database('market')
        
        assert isinstance(results, list)
        tab_results = [r for r in results if r['type'] == 'tabs']
        assert len(tab_results) > 0
    
    def test_search_database_empty(self):
        """Test search with empty query"""
        results = search_database('')
        assert len(results) == 0
        
        results = search_database('x')
        assert len(results) == 0
    
    def test_search_database_limit(self):
        """Test search result limiting"""
        results = search_database('a')  # Should match many items
        assert len(results) <= 10


class TestThemeToggle:
    """Test Theme Toggle component"""
    
    def test_themes_defined(self):
        """Test that both themes are defined"""
        assert 'dark' in THEMES
        assert 'light' in THEMES
        
        for theme_name, theme in THEMES.items():
            assert 'background' in theme
            assert 'surface' in theme
            assert 'primary' in theme
            assert 'text' in theme
    
    def test_get_theme_css_dark(self):
        """Test dark theme CSS generation"""
        css = get_theme_css('dark')
        
        assert isinstance(css, str)
        assert ':root' in css
        assert '--bg-primary' in css
        assert '--color-primary' in css
        assert 'background-color' in css
    
    def test_get_theme_css_light(self):
        """Test light theme CSS generation"""
        css = get_theme_css('light')
        
        assert isinstance(css, str)
        assert ':root' in css
        assert THEMES['light']['background'] in css
    
    def test_get_theme_css_invalid(self):
        """Test CSS generation with invalid theme (should default to dark)"""
        css = get_theme_css('invalid')
        
        assert isinstance(css, str)
        assert THEMES['dark']['background'] in css


class TestSentimentAnalysis:
    """Test Sentiment Analysis component"""
    
    def test_fetch_reddit_sentiment(self):
        """Test Reddit sentiment fetching"""
        sentiment = fetch_reddit_sentiment('TSLA')
        
        assert isinstance(sentiment, dict)
        assert 'positive' in sentiment
        assert 'neutral' in sentiment
        assert 'negative' in sentiment
        assert 'total_mentions' in sentiment
        
        # Percentages should sum to 100
        total = sentiment['positive'] + sentiment['neutral'] + sentiment['negative']
        assert total == 100
    
    def test_fetch_news_sentiment(self):
        """Test news sentiment fetching"""
        news_data = fetch_news_sentiment('TSLA', days=7)
        
        assert isinstance(news_data, dict)
        assert 'articles' in news_data
        assert 'avg_sentiment' in news_data
        assert 'total_articles' in news_data
        
        assert isinstance(news_data['articles'], list)
        assert len(news_data['articles']) > 0
        
        # Check article structure
        article = news_data['articles'][0]
        assert 'title' in article
        assert 'source' in article
        assert 'sentiment_score' in article
    
    def test_calculate_composite_sentiment(self):
        """Test composite sentiment calculation"""
        reddit_data = {
            'positive': 70,
            'neutral': 20,
            'negative': 10
        }
        news_data = {
            'avg_sentiment': 0.5
        }
        
        composite = calculate_composite_sentiment(reddit_data, news_data)
        
        assert isinstance(composite, dict)
        assert 'score' in composite
        assert 'normalized' in composite
        assert 'label' in composite
        
        assert 0 <= composite['normalized'] <= 100
        assert composite['label'] in ['Bullish', 'Neutral', 'Bearish']


class TestIntegration:
    """Integration tests for Sprint 6 components"""
    
    def test_all_components_importable(self):
        """Test that all Sprint 6 components can be imported"""
        try:
            from components import (
                factor_dna,
                portfolio_health,
                volatility_lab,
                hedge_finder,
                global_search,
                theme_toggle,
                sentiment_analysis
            )
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import components: {e}")
    
    def test_component_layouts_creatable(self):
        """Test that all component layouts can be created"""
        from components.factor_dna import create_factor_dna_layout
        from components.portfolio_health import create_portfolio_health_layout
        from components.volatility_lab import create_volatility_lab_layout
        from components.hedge_finder import create_hedge_finder_layout
        from components.sentiment_analysis import create_sentiment_analysis_layout
        
        # All should create without errors
        layout1 = create_factor_dna_layout()
        layout2 = create_portfolio_health_layout()
        layout3 = create_volatility_lab_layout()
        layout4 = create_hedge_finder_layout()
        layout5 = create_sentiment_analysis_layout()
        
        assert layout1 is not None
        assert layout2 is not None
        assert layout3 is not None
        assert layout4 is not None
        assert layout5 is not None


# Test Suite Summary
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
