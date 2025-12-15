"""
Tests for rate limiter
"""

import pytest
import asyncio
from rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_allows_within_limit():
    """Test that requests within limit are allowed"""
    limiter = RateLimiter(max_requests=5, window_seconds=60)
    
    for i in range(5):
        is_allowed, remaining = await limiter.check_rate_limit("test_ip")
        assert is_allowed is True
        assert remaining >= 0


@pytest.mark.asyncio
async def test_rate_limiter_blocks_over_limit():
    """Test that requests over limit are blocked"""
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    
    # Use up the limit
    for i in range(3):
        is_allowed, remaining = await limiter.check_rate_limit("test_ip")
        assert is_allowed is True
    
    # Next request should be blocked
    is_allowed, remaining = await limiter.check_rate_limit("test_ip")
    assert is_allowed is False
    assert remaining == 0


@pytest.mark.asyncio
async def test_rate_limiter_different_ips():
    """Test that different IPs have separate limits"""
    limiter = RateLimiter(max_requests=2, window_seconds=60)
    
    # IP 1
    is_allowed, _ = await limiter.check_rate_limit("ip1")
    assert is_allowed is True
    is_allowed, _ = await limiter.check_rate_limit("ip1")
    assert is_allowed is True
    is_allowed, _ = await limiter.check_rate_limit("ip1")
    assert is_allowed is False  # Over limit
    
    # IP 2 should still be allowed
    is_allowed, _ = await limiter.check_rate_limit("ip2")
    assert is_allowed is True
    is_allowed, _ = await limiter.check_rate_limit("ip2")
    assert is_allowed is True


@pytest.mark.asyncio
async def test_rate_limiter_cleanup():
    """Test cleanup of old entries"""
    limiter = RateLimiter(max_requests=5, window_seconds=1)
    
    # Add some requests
    await limiter.check_rate_limit("test_ip")
    await limiter.check_rate_limit("test_ip")
    
    # Wait for window to expire
    await asyncio.sleep(1.1)
    
    # Cleanup should remove old entries
    await limiter.cleanup_old_entries()
    
    # Should be able to make new requests
    is_allowed, remaining = await limiter.check_rate_limit("test_ip")
    assert is_allowed is True
