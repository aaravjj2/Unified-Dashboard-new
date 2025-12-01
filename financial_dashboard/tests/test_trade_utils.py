"""
Unit tests for utils/trade_utils.py

Tests position sizing, slippage estimation, and trade scheduling functions.
"""
import pytest
import math
from utils import trade_utils


class TestPositionSizing:
    """Test compute_position_size function."""
    
    def test_volatility_method_normal_case(self, mock_prediction, mock_volatility, mock_portfolio_value):
        """Test volatility-based position sizing with normal inputs."""
        result = trade_utils.compute_position_size(
            prediction=mock_prediction,
            volatility=mock_volatility,
            max_notional=mock_portfolio_value,
            adv=5_000_000,  # $5M ADV
            method='volatility'
        )
        
        assert result is not None
        assert 'position_size_dollars' in result
        assert 'position_pct' in result
        assert 'method_used' in result
        assert result['method_used'] == 'volatility'
        assert result['position_size_dollars'] > 0
        assert 0 < result['position_pct'] <= 100.0  # Function returns 0-100, not 0-1.0
    
    def test_zero_volatility_uses_default(self, mock_prediction, mock_portfolio_value):
        """Test that zero volatility triggers default value."""
        result = trade_utils.compute_position_size(
            prediction=mock_prediction,
            volatility=0.0,  # Zero volatility
            max_notional=mock_portfolio_value,
            adv=5_000_000,
            method='volatility'
        )
        
        assert 'default_volatility' in result.get('constraints', [])
        assert result['position_size_dollars'] > 0
    
    def test_negative_volatility_uses_default(self, mock_prediction, mock_portfolio_value):
        """Test that negative volatility triggers default value."""
        result = trade_utils.compute_position_size(
            prediction=mock_prediction,
            volatility=-0.10,  # Negative volatility (invalid)
            max_notional=mock_portfolio_value,
            adv=5_000_000,
            method='volatility'
        )
        
        assert 'default_volatility' in result.get('constraints', [])
        assert result['position_size_dollars'] > 0
    
    def test_kelly_method_with_params(self, mock_prediction, mock_volatility, mock_portfolio_value):
        """Test Kelly criterion with all required parameters."""
        result = trade_utils.compute_position_size(
            prediction=mock_prediction,
            volatility=mock_volatility,
            max_notional=mock_portfolio_value,
            adv=5_000_000,
            method='kelly',
            win_rate=0.60,
            avg_win=0.12,
            avg_loss=0.08
        )
        
        assert result['position_size_dollars'] > 0
        assert result['method_used'] in ['kelly', 'volatility']
    
    def test_kelly_method_missing_params_fallback(self, mock_prediction, mock_volatility, mock_portfolio_value):
        """Test Kelly method falls back to volatility when params missing."""
        result = trade_utils.compute_position_size(
            prediction=mock_prediction,
            volatility=mock_volatility,
            max_notional=mock_portfolio_value,
            adv=5_000_000,
            method='kelly',
            # Missing win_rate, avg_win, avg_loss
        )
        
        assert 'kelly_params_missing' in result.get('constraints', [])
        assert result['method_used'] == 'volatility'
    
    def test_position_size_respects_max_cap(self, mock_prediction, mock_portfolio_value):
        """Test that position size is capped at MAX_POSITION_PCT."""
        result = trade_utils.compute_position_size(
            prediction=mock_prediction,
            volatility=0.05,  # Very low volatility -> would size very large
            max_notional=mock_portfolio_value,
            adv=50_000_000,
            method='volatility'
        )
        
        max_allowed = mock_portfolio_value * trade_utils.MAX_POSITION_PCT
        assert result['position_size_dollars'] <= max_allowed
    
    def test_position_size_respects_min_cap(self, mock_prediction, mock_portfolio_value):
        """Test that position size is capped at MIN_POSITION_PCT."""
        result = trade_utils.compute_position_size(
            prediction=mock_prediction,
            volatility=2.0,  # Very high volatility -> would size very small
            max_notional=mock_portfolio_value,
            adv=50_000_000,
            method='volatility'
        )
        
        min_allowed = mock_portfolio_value * trade_utils.MIN_POSITION_PCT
        assert result['position_size_dollars'] >= min_allowed
    
    def test_low_adv_triggers_constraint(self, mock_prediction, mock_volatility, mock_portfolio_value):
        """Test that low ADV triggers liquidity constraint."""
        # Use ADV that's actually limiting: 50K ADV means max $5K position,
        # which is less than the 10% max_position constraint ($10K)
        result = trade_utils.compute_position_size(
            prediction=mock_prediction,
            volatility=mock_volatility,
            max_notional=mock_portfolio_value,  # 100K
            adv=50_000,  # Low ADV - 10% = only $5K allowed
            method='volatility'
        )
        
        # Function adds 'liquidity_limit_10pct_adv' when position is capped by 10% of ADV
        # With 50K ADV, max position is 5K which is less than portfolio's 10K max
        constraints = result.get('constraints', [])
        assert any('liquidity' in c.lower() or 'adv' in c.lower() for c in constraints),         f"Expected liquidity constraint but got: {constraints}"


class TestSlippageEstimation:
    """Test estimate_slippage function."""
    
    def test_slippage_normal_case(self):
        """Test slippage estimation with normal inputs."""
        result = trade_utils.estimate_slippage(
            position_size=10_000,  # Correct parameter name
            adv=5_000_000,
            spread_pct=0.001,
            is_buy=True  # Correct parameter name (not urgency)
        )
        
        assert result is not None
        assert 'slippage_bps' in result or 'slippage_pct' in result
        assert 'slippage_dollars' in result
        assert result['slippage_dollars'] >= 0
    
    def test_slippage_increases_with_order_size(self):
        """Test that slippage increases with larger orders."""
        small_order = trade_utils.estimate_slippage(
            position_size=1_000,
            adv=5_000_000,
            spread_pct=0.001,
            is_buy=True
        )
        
        large_order = trade_utils.estimate_slippage(
            position_size=100_000,
            adv=5_000_000,
            spread_pct=0.001,
            is_buy=True
        )
        
        # Use slippage_pct for comparison
        assert large_order.get('slippage_pct', 0) > small_order.get('slippage_pct', 0)
    
    def test_slippage_buy_vs_sell(self):
        """Test slippage for buy vs sell orders."""
        buy_order = trade_utils.estimate_slippage(
            position_size=10_000,
            adv=5_000_000,
            spread_pct=0.001,
            is_buy=True
        )
        
        sell_order = trade_utils.estimate_slippage(
            position_size=10_000,
            adv=5_000_000,
            spread_pct=0.001,
            is_buy=False
        )
        
        # Both should have positive slippage
        assert buy_order['slippage_dollars'] >= 0
        assert sell_order['slippage_dollars'] >= 0
    
    def test_slippage_increases_with_wide_spread(self):
        """Test that wider spreads increase slippage."""
        tight_spread = trade_utils.estimate_slippage(
            position_size=10_000,
            adv=5_000_000,
            spread_pct=0.0005,
            is_buy=True
        )
        
        wide_spread = trade_utils.estimate_slippage(
            position_size=10_000,
            adv=5_000_000,
            spread_pct=0.005,
            is_buy=True
        )
        
        assert wide_spread.get('slippage_pct', 0) > tight_spread.get('slippage_pct', 0)
    
    def test_zero_order_size(self):
        """Test handling of zero order size."""
        result = trade_utils.estimate_slippage(
            position_size=0,
            adv=5_000_000,
            spread_pct=0.001,
            is_buy=True
        )
        
        assert result['slippage_dollars'] == 0
    
    def test_negative_order_size_handled(self):
        """Test that negative order size is handled gracefully."""
        result = trade_utils.estimate_slippage(
            position_size=-10_000,
            adv=5_000_000,
            spread_pct=0.001,
            is_buy=True
        )
        
        # Function should handle gracefully (may treat as absolute value or return 0)
        assert result is not None


class TestLiquidityFlag:
    """Test compute_liquidity_flag function."""
    
    def test_ok_liquidity(self):
        """Test OK liquidity classification."""
        result = trade_utils.compute_liquidity_flag(
            adv=10_000_000,  # High ADV
            spread_pct=0.001  # Tight spread
        )
        
        assert result['flag'] == 'OK'
    
    def test_warn_liquidity_low_adv(self):
        """Test WARN classification for low ADV."""
        result = trade_utils.compute_liquidity_flag(
            adv=600_000,  # Between WARN and CRITICAL
            spread_pct=0.001
        )
        
        assert result['flag'] == 'WARN'
    
    def test_warn_liquidity_wide_spread(self):
        """Test WARN classification for wide spread."""
        result = trade_utils.compute_liquidity_flag(
            adv=10_000_000,
            spread_pct=0.003  # Between OK and WARN
        )
        
        assert result['flag'] == 'WARN'
    
    def test_critical_liquidity(self):
        """Test CRITICAL classification."""
        result = trade_utils.compute_liquidity_flag(
            adv=100_000,  # Very low ADV
            spread_pct=0.01  # Very wide spread
        )
        
        assert result['flag'] == 'CRITICAL'
    
    def test_zero_adv(self):
        """Test handling of zero ADV."""
        result = trade_utils.compute_liquidity_flag(
            adv=0,
            spread_pct=0.001
        )
        
        assert result['flag'] == 'CRITICAL'
    
    def test_result_contains_reasons(self):
        """Test that result contains reasons for classification."""
        result = trade_utils.compute_liquidity_flag(
            adv=100_000,
            spread_pct=0.01
        )
        
        assert 'reasons' in result
        assert len(result['reasons']) > 0


class TestTradeSchedule:
    """Test generate_trade_schedule function."""
    
    def test_schedule_normal_case(self):
        """Test trade schedule generation."""
        result = trade_utils.generate_trade_schedule(
            position_size=10000,  # $10K position
            price=100.0,  # $100 per share
            num_days=5,
            strategy='TWAP'
        )
        
        assert result is not None
        assert 'schedule' in result
        assert 'total_shares' in result
        assert result['total_shares'] == 100  # 10000 / 100 = 100 shares
        assert len(result['schedule']) > 0
    
    def test_schedule_single_day(self):
        """Test schedule with single day."""
        result = trade_utils.generate_trade_schedule(
            position_size=10000,
            price=100.0,
            num_days=1,
            strategy='TWAP'
        )
        
        assert result['total_shares'] == 100
        assert len(result['schedule']) >= 1  # At least one session
    
    def test_schedule_shares_sum_to_total(self):
        """Test that scheduled shares sum to total."""
        for position in [10000, 25000, 50000]:
            price = 100.0
            result = trade_utils.generate_trade_schedule(
                position_size=position,
                price=price,
                num_days=3,
                strategy='TWAP'
            )
            
            expected_shares = int(position / price)
            scheduled_total = sum([s['shares'] for s in result['schedule']])
            # Allow small rounding differences
            assert abs(scheduled_total - expected_shares) <= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
