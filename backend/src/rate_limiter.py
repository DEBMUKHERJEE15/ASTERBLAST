from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import FastAPI, Request
import logging
from typing import Callable
from .config import settings

logger = logging.getLogger(__name__)

# Create rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute", 
                   f"{settings.RATE_LIMIT_PER_HOUR}/hour"],
    storage_uri=settings.REDIS_URL
)

def setup_rate_limiting(app: FastAPI):
    """Setup rate limiting for the application"""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    
    # Custom rate limits for specific endpoints
    custom_limits = {
        "/api/auth/login": ["10/minute", "100/hour"],
        "/api/auth/register": ["5/minute", "50/hour"],
        "/api/asteroids/feed": ["30/minute", "500/hour"],
        "/api/asteroids/batch": ["20/minute", "300/hour"],
        "/api/asteroids/search": ["15/minute", "200/hour"],
        "/api/alerts": ["10/minute", "100/hour"],
        "/api/chat": ["30/minute", "1000/hour"]
    }
    
    return custom_limits

async def rate_limit_key_func(request: Request) -> str:
    """Custom rate limit key function"""
    # Use user ID if authenticated, otherwise IP address
    user_id = request.headers.get("X-User-ID")
    if user_id:
        return f"user:{user_id}"
    
    # Get API key if provided
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"api:{api_key}"
    
    # Default to IP address
    return get_remote_address(request)

def create_rate_limit_decorator(limits: str):
    """Create rate limit decorator with custom key"""
    return limiter.limit(limits, key_func=rate_limit_key_func)

# Predefined rate limit decorators
login_rate_limit = create_rate_limit_decorator("10/minute")
register_rate_limit = create_rate_limit_decorator("5/minute")
feed_rate_limit = create_rate_limit_decorator("30/minute")
asteroid_rate_limit = create_rate_limit_decorator("20/minute")
search_rate_limit = create_rate_limit_decorator("15/minute")
alert_rate_limit = create_rate_limit_decorator("10/minute")
chat_rate_limit = create_rate_limit_decorator("30/minute")