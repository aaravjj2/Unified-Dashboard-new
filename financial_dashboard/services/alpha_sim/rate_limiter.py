"""
AlphaSim Rate Limiter - Token bucket implementation for per-apikey rate limiting.
"""
import os
import time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class RatePlan:
    """Rate limit plan configuration."""
    name: str
    max_tokens: int
    refill_rate: float  # tokens per second
    
    @classmethod
    def free(cls) -> "RatePlan":
        """Free tier: 25 requests/day."""
        return cls(name="free", max_tokens=25, refill_rate=25 / 86400)
    
    @classmethod
    def premium(cls) -> "RatePlan":
        """Premium tier: 500 requests/day."""
        return cls(name="premium", max_tokens=500, refill_rate=500 / 86400)
    
    @classmethod
    def unlimited(cls) -> "RatePlan":
        """Unlimited tier for admins/internal use."""
        return cls(name="unlimited", max_tokens=1000000, refill_rate=1000000)


@dataclass
class TokenBucket:
    """Token bucket state for an API key."""
    tokens: float
    last_ts: float
    plan: str
    
    def to_dict(self) -> dict:
        return {
            "tokens": self.tokens,
            "last_ts": self.last_ts,
            "plan": self.plan
        }


class RateLimiter:
    """
    In-memory token bucket rate limiter.
    For production, replace with Redis-backed implementation.
    """
    
    def __init__(self):
        self._buckets: Dict[str, TokenBucket] = {}
        self._plans: Dict[str, RatePlan] = {
            "free": RatePlan.free(),
            "premium": RatePlan.premium(),
            "unlimited": RatePlan.unlimited(),
        }
        self._admin_keys = set(
            k.strip() for k in os.getenv("ALPHA_SIM_ADMIN_KEYS", "admin,test").split(",")
            if k.strip()
        )
    
    def _get_plan(self, apikey: str) -> RatePlan:
        """Get rate plan for an API key."""
        if apikey in self._admin_keys:
            return self._plans["unlimited"]
        return self._plans.get("free", RatePlan.free())
    
    def _get_or_create_bucket(self, apikey: str) -> TokenBucket:
        """Get or create token bucket for an API key."""
        if apikey not in self._buckets:
            plan = self._get_plan(apikey)
            self._buckets[apikey] = TokenBucket(
                tokens=plan.max_tokens,
                last_ts=time.time(),
                plan=plan.name
            )
        return self._buckets[apikey]
    
    def _refill_bucket(self, bucket: TokenBucket) -> TokenBucket:
        """Refill tokens based on elapsed time."""
        plan = self._plans.get(bucket.plan, RatePlan.free())
        now = time.time()
        elapsed = now - bucket.last_ts
        refill = elapsed * plan.refill_rate
        bucket.tokens = min(plan.max_tokens, bucket.tokens + refill)
        bucket.last_ts = now
        return bucket
    
    def allow_request(self, apikey: str, cost: float = 1.0) -> Tuple[bool, Optional[int]]:
        """
        Check if request is allowed and consume tokens.
        
        Returns:
            (allowed, retry_after_seconds)
            - If allowed: (True, None)
            - If denied: (False, seconds_until_enough_tokens)
        """
        bucket = self._get_or_create_bucket(apikey)
        bucket = self._refill_bucket(bucket)
        
        if bucket.tokens >= cost:
            bucket.tokens -= cost
            return (True, None)
        else:
            # Calculate time until enough tokens
            plan = self._plans.get(bucket.plan, RatePlan.free())
            if plan.refill_rate > 0:
                needed = cost - bucket.tokens
                retry_after = int(needed / plan.refill_rate) + 1
            else:
                retry_after = 3600  # Default 1 hour
            return (False, retry_after)
    
    def get_quota(self, apikey: str) -> dict:
        """Get current quota info for an API key."""
        bucket = self._get_or_create_bucket(apikey)
        bucket = self._refill_bucket(bucket)
        plan = self._plans.get(bucket.plan, RatePlan.free())
        
        return {
            "tokens": round(bucket.tokens, 2),
            "max_tokens": plan.max_tokens,
            "plan": bucket.plan,
            "last_ts": bucket.last_ts
        }
    
    def reset_quota(self, apikey: str, tokens: Optional[float] = None) -> dict:
        """Reset quota for an API key (admin action)."""
        bucket = self._get_or_create_bucket(apikey)
        plan = self._plans.get(bucket.plan, RatePlan.free())
        
        bucket.tokens = tokens if tokens is not None else plan.max_tokens
        bucket.last_ts = time.time()
        
        return {"ok": True, "tokens": bucket.tokens}
    
    def is_admin(self, apikey: str) -> bool:
        """Check if API key is an admin key."""
        return apikey in self._admin_keys


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
