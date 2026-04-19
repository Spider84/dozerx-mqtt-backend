"""
Global rate limiter configuration for all routers.

This module provides a centralized rate limiter instance and rate limit
configurations for use across all application routers.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Create global limiter instance for all routers
limiter = Limiter(key_func=get_remote_address)

# Rate limit configurations
RATE_LIMITS = {
    "health": "100/minute",
    "read": "30/minute",
    "write": "10/minute",
    "task_create": "5/minute",  # Very limited for task creation
    "clients_read": "20/minute",
    "clients_write": "10/minute"
}
