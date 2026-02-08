import redis.asyncio as redis
import logging
from typing import Optional
from .config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None

async def init_redis():
    """Initialize Redis connection"""
    global _redis_client
    try:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            retry_on_timeout=True,
            max_connections=settings.REDIS_POOL_SIZE
        )
        
        # Test connection
        await _redis_client.ping()
        logger.info("Redis connected successfully")
        
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise

async def get_redis() -> redis.Redis:
    """Get Redis client instance"""
    global _redis_client
    if _redis_client is None:
        await init_redis()
    return _redis_client

async def close_redis():
    """Close Redis connection"""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis connection closed")

# Cache helper functions
async def get_from_cache(key: str) -> Optional[str]:
    """Get value from cache"""
    try:
        redis_client = await get_redis()
        return await redis_client.get(key)
    except Exception as e:
        logger.error(f"Failed to get from cache: {e}")
        return None

async def set_to_cache(key: str, value: str, ttl: int = None):
    """Set value in cache with TTL"""
    try:
        redis_client = await get_redis()
        ttl = ttl or settings.REDIS_CACHE_TTL
        await redis_client.setex(key, ttl, value)
    except Exception as e:
        logger.error(f"Failed to set to cache: {e}")

async def delete_from_cache(key: str):
    """Delete value from cache"""
    try:
        redis_client = await get_redis()
        await redis_client.delete(key)
    except Exception as e:
        logger.error(f"Failed to delete from cache: {e}")

async def clear_cache(pattern: str = "*"):
    """Clear cache by pattern"""
    try:
        redis_client = await get_redis()
        keys = []
        async for key in redis_client.scan_iter(match=pattern):
            keys.append(key)
        
        if keys:
            await redis_client.delete(*keys)
            logger.info(f"Cleared {len(keys)} cache keys matching {pattern}")
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")

async def cache_stats() -> dict:
    """Get cache statistics"""
    try:
        redis_client = await get_redis()
        info = await redis_client.info("stats")
        
        return {
            "total_keys": await redis_client.dbsize(),
            "hit_rate": float(info.get("keyspace_hits", 0)) / 
                       max(1, float(info.get("keyspace_hits", 0)) + 
                           float(info.get("keyspace_misses", 0))) * 100,
            "memory_used": info.get("used_memory_human", "0B"),
            "connected_clients": info.get("connected_clients", 0),
            "commands_processed": info.get("total_commands_processed", 0)
        }
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        return {}