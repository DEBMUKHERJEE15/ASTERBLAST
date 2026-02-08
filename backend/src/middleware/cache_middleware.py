from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import json
import hashlib
import logging
from typing import Dict, Any
from datetime import datetime

from ..redis_client import get_redis
from ..config import settings

logger = logging.getLogger(__name__)

class CacheMiddleware(BaseHTTPMiddleware):
    """Middleware for caching responses"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.cacheable_methods = ["GET"]
        self.cacheable_paths = [
            "/api/asteroids/feed",
            "/api/asteroids/statistics",
            "/api/asteroids/close-approaches",
            "/api/asteroids/hazardous/top"
        ]
        self.cache_ttl = {
            "/api/asteroids/feed": 300,  # 5 minutes
            "/api/asteroids/statistics": 1800,  # 30 minutes
            "/api/asteroids/close-approaches": 600,  # 10 minutes
            "/api/asteroids/hazardous/top": 300  # 5 minutes
        }
    
    async def dispatch(self, request: Request, call_next):
        # Skip non-GET requests
        if request.method not in self.cacheable_methods:
            return await call_next(request)
        
        # Check if path is cacheable
        path = request.url.path
        is_cacheable = any(path.startswith(p) for p in self.cacheable_paths)
        
        if not is_cacheable or not settings.CACHE_ENABLED:
            return await call_next(request)
        
        # Generate cache key
        cache_key = self._generate_cache_key(request)
        
        # Try to get from cache
        redis = await get_redis()
        cached = await redis.get(cache_key)
        
        if cached:
            # Parse cached response
            cached_data = json.loads(cached)
            
            # Return cached response with headers
            headers = {**cached_data["headers"], "X-Cache": "HIT"}
            return Response(
                content=json.dumps(cached_data["body"]),
                status_code=cached_data["status_code"],
                headers=headers,
                media_type="application/json"
            )
        
        # Call endpoint
        response = await call_next(request)
        
        # Cache successful responses
        if response.status_code == 200:
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
            
            # Get TTL for this path
            ttl = 300  # default
            for cache_path, path_ttl in self.cache_ttl.items():
                if path.startswith(cache_path):
                    ttl = path_ttl
                    break
            
            # Prepare cache data
            cache_data = {
                "body": json.loads(response_body.decode()),
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "cached_at": datetime.now().isoformat(),
                "ttl": ttl
            }
            
            # Store in cache (async, fire and forget)
            import asyncio
            asyncio.create_task(
                redis.setex(cache_key, ttl, json.dumps(cache_data))
            )
            
            # Return response with cache headers
            headers = dict(response.headers)
            headers["X-Cache"] = "MISS"
            headers["X-Cache-TTL"] = str(ttl)
            
            return Response(
                content=json.dumps(cache_data["body"]),
                status_code=response.status_code,
                headers=headers,
                media_type="application/json"
            )
        
        return response
    
    def _generate_cache_key(self, request: Request) -> str:
        """Generate cache key from request"""
        key_parts = [
            request.method,
            request.url.path,
            str(sorted(request.query_params.items()))
        ]
        
        # Include user ID if available for user-specific caching
        user_id = request.headers.get("X-User-ID")
        if user_id:
            key_parts.append(user_id)
        
        key_string = "|".join(key_parts)
        return f"cache:{hashlib.md5(key_string.encode()).hexdigest()}"