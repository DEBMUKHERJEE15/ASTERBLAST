from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
import logging
import psutil
import os
from datetime import datetime

from ..redis_client import get_redis, cache_stats
from ..neo_fetcher import get_nasa_fetcher
from ..auth import get_current_user

router = APIRouter(prefix="/monitoring", tags=["monitoring"])
logger = logging.getLogger(__name__)

@router.get("/health")
async def health_check():
    """Comprehensive health check endpoint"""
    try:
        # Check Redis
        redis = await get_redis()
        redis_ok = await redis.ping()
        
        # Check NASA fetcher
        fetcher = await get_nasa_fetcher()
        nasa_ok = fetcher.initialized
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        health_status = {
            "status": "healthy" if redis_ok and nasa_ok else "degraded",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "redis": "healthy" if redis_ok else "unhealthy",
                "nasa_fetcher": "healthy" if nasa_ok else "unhealthy",
                "api": "healthy"
            },
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_percent": disk.percent,
                "disk_free_gb": round(disk.free / (1024**3), 2)
            },
            "process": {
                "pid": os.getpid(),
                "uptime_seconds": psutil.Process().create_time(),
                "threads": psutil.Process().num_threads(),
                "memory_mb": round(psutil.Process().memory_info().rss / (1024**2), 2)
            }
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/cache/stats")
async def get_cache_statistics(
    current_user = Depends(get_current_user)
):
    """Get Redis cache statistics"""
    try:
        stats = await cache_stats()
        
        # Get additional cache info
        redis = await get_redis()
        info = await redis.info()
        
        return {
            **stats,
            "redis_info": {
                "version": info.get("redis_version"),
                "mode": info.get("redis_mode"),
                "os": info.get("os"),
                "uptime_days": int(info.get("uptime_in_seconds", 0)) // 86400,
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
                "used_memory_peak_human": info.get("used_memory_peak_human"),
                "total_commands_processed": info.get("total_commands_processed"),
                "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec")
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/nasa/status")
async def nasa_api_status(
    current_user = Depends(get_current_user)
):
    """Check NASA API status and rate limiting"""
    try:
        fetcher = await get_nasa_fetcher()
        
        # Try a simple request
        test_data = await fetcher.fetch_feed(
            datetime.now().strftime("%Y-%m-%d"),
            datetime.now().strftime("%Y-%m-%d")
        )
        
        return {
            "status": "connected",
            "requests_this_hour": len(fetcher.request_times),
            "rate_limit": fetcher.rate_limit_per_hour,
            "remaining_requests": fetcher.rate_limit_per_hour - len(fetcher.request_times),
            "test_request_successful": bool(test_data.get("asteroids")),
            "last_request_time": fetcher.request_times[-1] if fetcher.request_times else None,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"NASA API status check failed: {e}")
        return {
            "status": "disconnected",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/performance")
async def performance_metrics(
    current_user = Depends(get_current_user)
):
    """Get performance metrics"""
    try:
        import time
        start_time = time.time()
        
        # Test Redis performance
        redis = await get_redis()
        redis_start = time.time()
        await redis.ping()
        redis_time = time.time() - redis_start
        
        # Test database performance (if available)
        # This would require a database query
        
        return {
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
            "redis_ping_ms": round(redis_time * 1000, 2),
            "timestamp": datetime.now().isoformat(),
            "load_averages": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
            "network_connections": len(psutil.net_connections()),
            "open_files": len(psutil.Process().open_files())
        }
        
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs/recent")
async def get_recent_logs(
    lines: int = 100,
    current_user = Depends(get_current_user)
):
    """Get recent application logs"""
    try:
        log_file = "cosmic_watch.log"
        if not os.path.exists(log_file):
            return {"logs": [], "file": log_file, "exists": False}
        
        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        return {
            "logs": recent_lines,
            "total_lines": len(all_lines),
            "file": log_file,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to read logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))