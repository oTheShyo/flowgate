"""
Rate Limiting for flowgate.

Provides per-user and per-tier rate limiting with sliding window algorithm
for controlling API usage and enforcing subscription tier limits.

Key components:
- RateLimiter: Sliding window rate limiter
- RateLimitError: Exception for rate limit violations

Example usage:
    from flowgate.limits import RateLimiter
    from flowgate import UserProfile, TierLevel

    profile = UserProfile.from_tier(TierLevel.PRO, user_id="user_123")
    limiter = RateLimiter()

    # Check if request is allowed
    if await limiter.check_rate_limit(profile):
        # Process request
        result = await agent.run(query)
    else:
        # Rate limit exceeded
        raise RateLimitError("Rate limit exceeded")
"""

from .rate_limiter import RateLimiter, RateLimitState, RateLimitError

__all__ = [
    "RateLimiter",
    "RateLimitState",
    "RateLimitError",
]
