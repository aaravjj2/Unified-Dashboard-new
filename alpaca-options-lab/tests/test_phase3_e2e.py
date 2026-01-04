"""
End-to-End Test Suite for Alpaca Options Lab

Comprehensive tests covering all Phase 3 production components:
- Live Trading Orchestrator
- ML Strategy Optimization
- API Backend
- WebSocket Communication
- Security & Authentication
"""
from __future__ import annotations

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_alpaca_client():
    """Mock Alpaca trading client"""
    client = MagicMock()
    client.get_account.return_value = MagicMock(
        buying_power=100000.0,
        portfolio_value=150000.0,
        cash=50000.0,
    )
    client.get_all_positions.return_value = []
    client.get_orders.return_value = []
    return client


@pytest.fixture
def sample_market_data():
    """Sample market data for testing"""
    return {
        "SPY": {
            "bid": 475.50,
            "ask": 475.55,
            "last": 475.52,
            "volume": 1000000,
        },
        "QQQ": {
            "bid": 405.20,
            "ask": 405.25,
            "last": 405.22,
            "volume": 500000,
        },
    }


# =============================================================================
# LIVE TRADING TESTS
# =============================================================================

class TestLiveTradingOrchestrator:
    """Tests for the live trading orchestrator"""
    
    @pytest.mark.asyncio
    async def test_pre_market_checklist(self, mock_alpaca_client):
        """Test pre-market checklist validation"""
        from src.live_trading.orchestrator import PreMarketChecklist
        
        checklist = PreMarketChecklist()
        
        # Mock successful checks
        checklist.market_data_connected = True
        checklist.broker_connected = True
        checklist.positions_reconciled = True
        checklist.risk_limits_set = True
        checklist.capital_allocated = True
        checklist.strategies_loaded = True
        checklist.kill_switch_tested = True
        checklist.alerts_configured = True
        checklist.logs_initialized = True
        
        assert checklist.is_ready()
        assert checklist.completion_percentage() == 100.0
        
    @pytest.mark.asyncio
    async def test_pre_market_checklist_incomplete(self):
        """Test incomplete pre-market checklist"""
        from src.live_trading.orchestrator import PreMarketChecklist
        
        checklist = PreMarketChecklist()
        checklist.market_data_connected = True
        checklist.broker_connected = True
        # Other items default to False
        
        assert not checklist.is_ready()
        assert checklist.completion_percentage() < 100.0
        
    @pytest.mark.asyncio
    async def test_capital_ramp_up_schedule(self):
        """Test capital ramp-up schedule logic"""
        from src.live_trading.capital_manager import CapitalRampUpManager
        
        manager = CapitalRampUpManager(
            initial_capital=100000,
            max_capital=500000,
        )
        
        # Check initial stage
        current = manager.get_current_allocation()
        assert current["current_stage"] == 0
        assert current["current_pct"] == 10  # 10% at stage 0
        
    @pytest.mark.asyncio
    async def test_kill_switch_activation(self):
        """Test kill switch emergency stop"""
        from src.live_trading.kill_switch import KillSwitch
        
        kill_switch = KillSwitch()
        
        # Mock broker client
        mock_broker = AsyncMock()
        mock_broker.cancel_all_orders = AsyncMock()
        mock_broker.close_all_positions = AsyncMock()
        
        # Activate kill switch
        await kill_switch.activate(
            reason="Test activation",
            broker_client=mock_broker,
        )
        
        assert kill_switch.is_active
        mock_broker.cancel_all_orders.assert_called_once()


# =============================================================================
# ML COMPONENT TESTS
# =============================================================================

class TestRLStrategyOptimizer:
    """Tests for RL-based strategy optimization"""
    
    def test_trading_environment_creation(self):
        """Test Gym environment creation"""
        from src.ml.rl_optimizer import TradingStrategyEnv
        
        env = TradingStrategyEnv(
            initial_capital=100000,
            max_positions=10,
        )
        
        # Check observation space
        assert env.observation_space is not None
        assert len(env.observation_space.shape) == 1
        
        # Check action space
        assert env.action_space is not None
        
    def test_environment_reset(self):
        """Test environment reset"""
        from src.ml.rl_optimizer import TradingStrategyEnv
        
        env = TradingStrategyEnv()
        obs, info = env.reset()
        
        assert obs is not None
        assert isinstance(info, dict)
        
    def test_environment_step(self):
        """Test environment step"""
        from src.ml.rl_optimizer import TradingStrategyEnv
        
        env = TradingStrategyEnv()
        env.reset()
        
        # Take a random action
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        
        assert obs is not None
        assert isinstance(reward, (int, float))
        assert isinstance(terminated, bool)
        assert isinstance(truncated, bool)


class TestMarketRegimeDetector:
    """Tests for market regime detection"""
    
    def test_regime_detection(self):
        """Test HMM-based regime detection"""
        from src.ml.regime_detector import MarketRegimeDetector, MarketRegime
        
        detector = MarketRegimeDetector(n_regimes=5)
        
        # Generate mock data
        np.random.seed(42)
        returns = np.random.randn(100) * 0.02
        volatility = np.abs(returns).cumsum() / np.arange(1, 101)
        
        # Fit model
        detector.fit(returns, volatility)
        
        # Predict regime
        regime = detector.predict_regime(returns[-1], volatility[-1])
        assert isinstance(regime, MarketRegime)
        
    def test_strategy_selection(self):
        """Test regime-adaptive strategy selection"""
        from src.ml.regime_detector import RegimeAdaptiveStrategySelector, MarketRegime
        
        selector = RegimeAdaptiveStrategySelector()
        
        # Test each regime
        for regime in MarketRegime:
            strategies = selector.get_recommended_strategies(regime)
            assert isinstance(strategies, list)
            assert len(strategies) > 0


# =============================================================================
# API BACKEND TESTS
# =============================================================================

class TestAPIEndpoints:
    """Tests for FastAPI endpoints"""
    
    @pytest.fixture
    def test_client(self):
        """Create test client"""
        from fastapi.testclient import TestClient
        from src.api.main import app
        return TestClient(app)
        
    def test_health_endpoint(self, test_client):
        """Test health check endpoint"""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        
    def test_portfolio_endpoint(self, test_client):
        """Test portfolio endpoint"""
        response = test_client.get("/api/v1/portfolio")
        # May fail without auth - that's expected
        assert response.status_code in [200, 401]
        
    def test_risk_limits_endpoint(self, test_client):
        """Test risk limits endpoint"""
        response = test_client.get("/api/v1/risk/limits")
        assert response.status_code in [200, 401]


class TestWebSocketManager:
    """Tests for WebSocket real-time updates"""
    
    @pytest.mark.asyncio
    async def test_client_connection(self):
        """Test WebSocket client connection"""
        from src.api.websocket import WebSocketManager
        
        manager = WebSocketManager()
        
        # Connect a client
        await manager.connect("test_sid_1", "user_1")
        
        assert "test_sid_1" in manager.clients
        assert manager.clients["test_sid_1"].user_id == "user_1"
        
    @pytest.mark.asyncio
    async def test_channel_subscription(self):
        """Test channel subscription"""
        from src.api.websocket import WebSocketManager
        
        manager = WebSocketManager()
        await manager.connect("test_sid_1", "user_1")
        
        # Subscribe to channels
        await manager.subscribe("test_sid_1", ["portfolio", "positions"])
        
        assert "portfolio" in manager.clients["test_sid_1"].subscriptions
        assert "positions" in manager.clients["test_sid_1"].subscriptions
        assert "test_sid_1" in manager.channel_subscribers["portfolio"]
        
    @pytest.mark.asyncio
    async def test_broadcast_to_channel(self):
        """Test broadcasting to channel"""
        from src.api.websocket import WebSocketManager
        
        manager = WebSocketManager()
        await manager.connect("test_sid_1", "user_1")
        await manager.subscribe("test_sid_1", ["portfolio"])
        
        # Broadcast (won't actually send without Socket.IO)
        await manager.broadcast_to_channel(
            "portfolio",
            "portfolio_update",
            {"total_value": 100000},
        )


# =============================================================================
# SENTIMENT ENGINE TESTS
# =============================================================================

class TestNewsSentimentEngine:
    """Tests for news sentiment analysis"""
    
    def test_rule_based_sentiment(self):
        """Test rule-based sentiment analysis"""
        from src.sentiment import FinBERTSentimentAnalyzer, Sentiment
        
        analyzer = FinBERTSentimentAnalyzer()
        
        # Test bullish text
        sentiment, score, confidence = analyzer._analyze_rule_based(
            "Strong earnings beat expectations, stock surges"
        )
        assert sentiment in [Sentiment.BULLISH, Sentiment.VERY_BULLISH]
        assert score > 0
        
        # Test bearish text
        sentiment, score, confidence = analyzer._analyze_rule_based(
            "Stock plunges on weak guidance, analysts downgrade"
        )
        assert sentiment in [Sentiment.BEARISH, Sentiment.VERY_BEARISH]
        assert score < 0
        
    @pytest.mark.asyncio
    async def test_sentiment_signal_generation(self):
        """Test sentiment signal generation"""
        from src.sentiment import NewsSentimentEngine
        
        engine = NewsSentimentEngine()
        
        # Add some sentiment data
        engine.symbol_sentiment["SPY"] = [0.3, 0.4, 0.35, 0.5, 0.45]
        
        # Generate signal
        signal = engine.get_sentiment_signal("SPY")
        
        # With 5 bullish scores, should generate a signal
        assert signal is not None
        assert signal.direction == "bullish"


class TestEarningsCalendar:
    """Tests for earnings calendar"""
    
    @pytest.mark.asyncio
    async def test_fetch_earnings(self):
        """Test fetching earnings calendar"""
        from src.sentiment.earnings import EarningsCalendar
        
        calendar = EarningsCalendar()
        events = await calendar.fetch_earnings_calendar(
            symbols=["AAPL", "MSFT"],
        )
        
        assert isinstance(events, list)
        
    def test_earnings_detection(self):
        """Test earnings within period detection"""
        from src.sentiment.earnings import EarningsCalendar
        from datetime import date, timedelta
        
        calendar = EarningsCalendar()
        
        # Add mock earnings
        from src.sentiment.earnings import EarningsEvent, EventTiming
        calendar.earnings["AAPL"] = [
            EarningsEvent(
                symbol="AAPL",
                event_date=date.today() + timedelta(days=5),
                timing=EventTiming.POST_MARKET,
                fiscal_quarter="Q1",
                fiscal_year=2024,
            )
        ]
        
        assert calendar.has_earnings_within("AAPL", 10)
        assert not calendar.has_earnings_within("AAPL", 3)


# =============================================================================
# MARKET MAKING TESTS
# =============================================================================

class TestMarketMakingEngine:
    """Tests for market making engine"""
    
    def test_spread_calculation(self):
        """Test spread calculation"""
        from src.market_making import SpreadCalculator, Instrument
        
        calculator = SpreadCalculator()
        instrument = Instrument(
            symbol="SPY240119C00480000",
            underlying="SPY",
            strike=480.0,
            expiry="2024-01-19",
            option_type="call",
            bid=5.0,
            ask=5.10,
            mid=5.05,
        )
        
        bid_spread, ask_spread = calculator.calculate_spread(
            instrument=instrument,
            inventory=0,
            max_inventory=100,
            market_volatility=0.20,
        )
        
        assert bid_spread > 0
        assert ask_spread > 0
        
    def test_inventory_limits(self):
        """Test inventory limit checking"""
        from src.market_making import InventoryManager
        
        manager = InventoryManager({
            "max_position_size": 50,
            "max_delta_exposure": 500,
        })
        
        # Check within limits
        allowed, reason = manager.check_limits("TEST", "bid", 10)
        assert allowed
        
        # Check exceeding limits
        allowed, reason = manager.check_limits("TEST", "bid", 100)
        assert not allowed
        assert "max position size" in reason.lower()


# =============================================================================
# SECURITY TESTS
# =============================================================================

class TestAuthentication:
    """Tests for authentication"""
    
    def test_password_hashing(self):
        """Test password hashing and verification"""
        from src.security import PasswordHasher
        
        hasher = PasswordHasher()
        password = "test_password_123"
        
        hashed = hasher.hash_password(password)
        
        assert hashed != password
        assert hasher.verify_password(password, hashed)
        assert not hasher.verify_password("wrong_password", hashed)
        
    def test_jwt_token_creation(self):
        """Test JWT token creation and verification"""
        from src.security import JWTManager
        
        manager = JWTManager("test-secret-key")
        
        # Create token
        token = manager.create_access_token(
            user_id="user_123",
            role="trader",
        )
        
        assert token is not None
        assert len(token) > 0
        
        # Verify token
        valid, payload, error = manager.verify_token(token)
        
        assert valid
        assert payload["sub"] == "user_123"
        assert payload["role"] == "trader"
        
    def test_api_key_management(self):
        """Test API key generation and verification"""
        from src.security import APIKeyManager
        
        manager = APIKeyManager()
        
        # Generate key
        raw_key, api_key = manager.generate_api_key(
            user_id="user_123",
            name="Test Key",
            permissions=["read", "trade"],
        )
        
        assert raw_key is not None
        assert api_key.user_id == "user_123"
        
        # Verify key
        valid, key_obj, error = manager.verify_api_key(raw_key)
        
        assert valid
        assert key_obj.name == "Test Key"
        
    def test_rate_limiting(self):
        """Test rate limiting"""
        from src.security import RateLimiter
        
        limiter = RateLimiter()
        
        # First requests should be allowed
        for i in range(5):
            allowed, remaining, reset = limiter.check_rate_limit(
                "test_client",
                limit=5,
                window_seconds=60,
            )
            assert allowed
            
        # Next request should be blocked
        allowed, remaining, reset = limiter.check_rate_limit(
            "test_client",
            limit=5,
            window_seconds=60,
        )
        assert not allowed
        assert remaining == 0


class TestUserAuthentication:
    """Tests for full authentication flow"""
    
    def test_user_registration_and_login(self):
        """Test user registration and login flow"""
        from src.security import AuthenticationService, UserRole
        
        service = AuthenticationService("test-secret")
        
        # Register user
        user = service.register_user(
            email="test@example.com",
            username="testuser",
            password="secure_password_123",
        )
        
        assert user.email == "test@example.com"
        
        # Login
        success, tokens, error = service.authenticate(
            email="test@example.com",
            password="secure_password_123",
        )
        
        assert success
        assert tokens["access_token"] is not None
        assert tokens["refresh_token"] is not None
        
    def test_failed_login_lockout(self):
        """Test account lockout after failed attempts"""
        from src.security import AuthenticationService
        
        service = AuthenticationService("test-secret")
        service.max_failed_attempts = 3
        
        # Register user
        service.register_user(
            email="locktest@example.com",
            username="locktest",
            password="password123",
        )
        
        # Fail login multiple times
        for _ in range(3):
            success, _, _ = service.authenticate(
                email="locktest@example.com",
                password="wrong_password",
            )
            assert not success
            
        # Account should be locked
        success, _, error = service.authenticate(
            email="locktest@example.com",
            password="password123",  # Even correct password
        )
        
        assert not success
        assert "locked" in error.lower()


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for full system flow"""
    
    @pytest.mark.asyncio
    async def test_trading_flow(self):
        """Test complete trading flow"""
        # This would test the full flow from strategy signal
        # through order placement to position management
        pass
        
    @pytest.mark.asyncio
    async def test_ml_to_trading_integration(self):
        """Test ML components feeding into trading"""
        # Test regime detection affecting strategy selection
        from src.ml.regime_detector import MarketRegimeDetector, RegimeAdaptiveStrategySelector, MarketRegime
        
        detector = MarketRegimeDetector()
        selector = RegimeAdaptiveStrategySelector()
        
        # For each regime, get strategies
        for regime in MarketRegime:
            strategies = selector.get_recommended_strategies(regime)
            assert len(strategies) > 0


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
