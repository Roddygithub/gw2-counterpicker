"""
Rate limiting middleware for GW2 CounterPicker
Prevents abuse by limiting requests per IP address
"""

from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import HTTPException, Request
import asyncio


class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum number of requests allowed in the time window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def check_rate_limit(self, client_ip: str) -> Tuple[bool, int]:
        """
        Check if client has exceeded rate limit
        
        Args:
            client_ip: Client IP address
            
        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        async with self._lock:
            now = datetime.now()
            cutoff = now - timedelta(seconds=self.window_seconds)
            
            # Clean old requests
            self.requests[client_ip] = [
                req_time for req_time in self.requests[client_ip]
                if req_time > cutoff
            ]
            
            # Check if limit exceeded
            current_count = len(self.requests[client_ip])
            
            if current_count >= self.max_requests:
                return False, 0
            
            # Add current request
            self.requests[client_ip].append(now)
            remaining = self.max_requests - current_count - 1
            
            return True, remaining
    
    async def cleanup_old_entries(self):
        """Periodic cleanup of old entries to prevent memory leak"""
        async with self._lock:
            now = datetime.now()
            cutoff = now - timedelta(seconds=self.window_seconds * 2)
            
            # Remove IPs with no recent requests
            ips_to_remove = []
            for ip, requests in self.requests.items():
                if not requests or all(req_time < cutoff for req_time in requests):
                    ips_to_remove.append(ip)
            
            for ip in ips_to_remove:
                del self.requests[ip]


# Global rate limiter instance
upload_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)


async def check_upload_rate_limit(request: Request):
    """
    Middleware to check rate limit for upload endpoints
    
    Args:
        request: FastAPI request object
        
    Raises:
        HTTPException: If rate limit exceeded
    """
    client_ip = request.client.host if request.client else "unknown"
    
    is_allowed, remaining = await upload_rate_limiter.check_rate_limit(client_ip)
    
    if not is_allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum {upload_rate_limiter.max_requests} uploads per minute. Please wait before trying again."
        )
    
    return remaining
