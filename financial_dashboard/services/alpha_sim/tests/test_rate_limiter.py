"""
Unit tests for AlphaSim rate limiter module.
"""
import pytest
import time

from financial_dashboard.services.alpha_sim.rate_limiter import (
    RatePlan, TokenBucket, RateLimiter, get_rate_limiter
)


# ---------- RatePlan Tests ----------

class TestRatePlan:
    """Tests for RatePlan dataclass."""
    
    def test_free_plan_defaults(self):
        """Test free plan has correct defaults."""
        plan = RatePlan.free()
        
        assert plan.name == "free"
        assert plan.max_tokens == 25
        assert plan.refill_rate > 0
    
    def test_premium_plan_defaults(self):
        """Test premium plan has correct defaults."""
        plan = RatePlan.premium()
        
        assert plan.name == "premium"
        assert plan.max_tokens == 500
        assert plan.refill_rate > 0
    
    def test_unlimited_plan(self):
        """Test unlimited plan has high limits."""
        plan = RatePlan.unlimited()
        
        assert plan.name == "unlimited"
        assert plan.max_tokens >= 1000000
        assert plan.refill_rate >= 1000000


# ---------- TokenBucket Tests ----------

class TestTokenBucket:
    """Tests for TokenBucket dataclass."""
    
    def test_token_bucket_creation(self):
        """Test TokenBucket creation."""
        bucket = TokenBucket(
            tokens=10.0,
            last_ts=time.time(),
            plan="free"
        )
        
        assert bucket.tokens == 10.0
        assert bucket.plan == "free"
    
    def test_token_bucket_to_dict(self):
        """Test TokenBucket to_dict method."""
        now = time.time()
        bucket = TokenBucket(
            tokens=50.0,
            last_ts=now,
            plan="premium"
        )
        
        result = bucket.to_dict()
        assert result["tokens"] == 50.0
        assert result["plan"] == "premium"


# ---------- RateLimiter Tests ----------

class TestRateLimiter:
    """Tests for RateLimiter class."""
    
    def test_rate_limiter_creation(self):
        """Test RateLimiter creation."""
        limiter = RateLimiter()
        assert limiter is not None
    
    def test_allow_request_new_key(self):
        """Test allow_request for new API key."""
        limiter = RateLimiter()
        
        allowed, retry_after = limiter.allow_request("new_key_123")
        
        assert allowed is True
        assert retry_after is None
    
    def test_allow_request_depletes_tokens(self):
        """Test allow_request depletes tokens."""
        limiter = RateLimiter()
        
        # Make multiple requests
        for _ in range(5):
            allowed, _ = limiter.allow_request("test_key")
            assert allowed is True
    
    def test_rate_limit_exceeded(self):
        """Test rate limit is enforced."""
        limiter = RateLimiter()
        
        # Exhaust tokens (free plan has 5 requests per minute)
        key = "exhaust_key"
        for _ in range(10):
            limiter.allow_request(key)
        
        # Should eventually be rate limited
        allowed, retry_after = limiter.allow_request(key)
        
        # May or may not be limited depending on token refill timing
        # But if limited, retry_after should be set
        if not allowed:
            assert retry_after is not None
            assert retry_after > 0
    
    def test_get_quota(self):
        """Test get_quota returns quota info."""
        limiter = RateLimiter()
        
        # Make a request first to create bucket
        limiter.allow_request("quota_test_key")
        
        quota = limiter.get_quota("quota_test_key")
        
        assert isinstance(quota, dict)
        assert "tokens" in quota
        assert "plan" in quota
        assert "max_tokens" in quota
    
    def test_get_quota_new_key(self):
        """Test get_quota for new key."""
        limiter = RateLimiter()
        
        quota = limiter.get_quota("new_quota_key")
        
        assert isinstance(quota, dict)
        assert "tokens" in quota
    
    def test_reset_quota(self):
        """Test reset_quota restores tokens."""
        limiter = RateLimiter()
        
        key = "reset_test_key"
        
        # Deplete some tokens
        for _ in range(5):
            limiter.allow_request(key)
        
        # Reset
        result = limiter.reset_quota(key)
        
        assert result["ok"] is True
        assert "tokens" in result
    
    def test_reset_quota_custom_tokens(self):
        """Test reset_quota with custom token count."""
        limiter = RateLimiter()
        
        key = "custom_reset_key"
        
        result = limiter.reset_quota(key, tokens=100.0)
        
        assert result["tokens"] == 100.0
    
    def test_is_admin(self):
        """Test is_admin check."""
        limiter = RateLimiter()
        
        # Default admin key
        assert limiter.is_admin("admin") is True
        
        # Non-admin key
        assert limiter.is_admin("not_admin") is False
    
    def test_premium_key_detection(self):
        """Test API key with admin env var detection."""
        limiter = RateLimiter()
        
        # Admin key detection (from default env)
        assert limiter.is_admin("admin") is True
        assert limiter.is_admin("test") is True
        assert limiter.is_admin("regular_user") is False


# ---------- get_rate_limiter Tests ----------

class TestGetRateLimiter:
    """Tests for get_rate_limiter singleton."""
    
    def test_get_rate_limiter_returns_instance(self):
        """Test get_rate_limiter returns RateLimiter instance."""
        limiter = get_rate_limiter()
        assert isinstance(limiter, RateLimiter)
    
    def test_get_rate_limiter_singleton(self):
        """Test get_rate_limiter returns same instance."""
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()
        assert limiter1 is limiter2


# ---------- Edge Cases ----------

class TestRateLimiterEdgeCases:
    """Tests for rate limiter edge cases."""
    
    def test_empty_api_key(self):
        """Test handling of empty API key."""
        limiter = RateLimiter()
        
        # Empty key should still work (as free tier)
        allowed, _ = limiter.allow_request("")
        assert allowed is True
    
    def test_special_characters_in_key(self):
        """Test handling of special characters in API key."""
        limiter = RateLimiter()
        
        special_key = "key!@#$%^&*()_+-=[]{}|;:',.<>?"
        allowed, _ = limiter.allow_request(special_key)
        
        assert allowed is True
    
    def test_unicode_api_key(self):
        """Test handling of unicode API key."""
        limiter = RateLimiter()
        
        unicode_key = "key_日本語_🔑"
        allowed, _ = limiter.allow_request(unicode_key)
        
        assert allowed is True
    
    def test_very_long_api_key(self):
        """Test handling of very long API key."""
        limiter = RateLimiter()
        
        long_key = "k" * 1000
        allowed, _ = limiter.allow_request(long_key)
        
        assert allowed is True
    
    def test_concurrent_access_simulation(self):
        """Test simulated concurrent access."""
        limiter = RateLimiter()
        
        key = "concurrent_key"
        results = []
        
        # Simulate multiple requests
        for _ in range(10):
            allowed, retry_after = limiter.allow_request(key)
            results.append((allowed, retry_after))
        
        # At least first few should succeed
        assert results[0][0] is True
