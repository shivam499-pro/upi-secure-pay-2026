"""
UPI SECURE PAY - Redis Client
Async Redis for caching fraud results and rate limiting
"""

import redis.asyncio as aioredis
import json
from typing import Optional

# Global Redis client
redis_client: Optional[aioredis.Redis] = None


async def init_redis(redis_url: str = "redis://localhost:6379"):
    """
    Initialize Redis connection.
    
    Args:
        redis_url: Redis connection URL
    
    Returns:
        Redis client instance
    """
    global redis_client
    try:
        redis_client = await aioredis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        await redis_client.ping()
        print("✅ Redis connected")
        return redis_client
    except Exception as e:
        print(f"⚠️ Redis connection failed: {e}")
        print("   Continuing without Redis caching")
        redis_client = None
        return None


async def get_redis() -> Optional[aioredis.Redis]:
    """
    Get the Redis client instance.
    
    Returns:
        Redis client or None if not connected
    """
    return redis_client


async def cache_fraud_result(transaction_id: str, result: dict, ttl: int = 86400):
    """
    Cache fraud detection result.
    
    Args:
        transaction_id: Transaction ID
        result: Fraud detection result dict
        ttl: Time to live in seconds (default: 1 hour)
    """
    if redis_client:
        try:
            await redis_client.setex(f"fraud:{transaction_id}", ttl, json.dumps(result))
        except Exception as e:
            print(f"Redis cache error: {e}")


async def get_cached_fraud_result(transaction_id: str) -> Optional[dict]:
    """
    Get cached fraud detection result.
    
    Args:
        transaction_id: Transaction ID
    
    Returns:
        Cached result dict or None
    """
    if not redis_client:
        return None
    try:
        data = await redis_client.get(f"fraud:{transaction_id}")
        return json.loads(data) if data else None
    except Exception as e:
        print(f"Redis get error: {e}")
        return None


async def store_rate_limit_token(key: str, ttl: int = 60) -> Optional[int]:
    """
    Store rate limit token and return count.
    
    Args:
        key: Rate limit key
        ttl: Time to live in seconds (default: 60)
    
    Returns:
        Current count or None if Redis not available
    """
    if not redis_client:
        return None
    try:
        count = await redis_client.incr(f"ratelimit:{key}")
        if count == 1:
            await redis_client.expire(f"ratelimit:{key}", ttl)
        return count
    except Exception as e:
        print(f"Redis rate limit error: {e}")
        return None


async def close_redis():
    """
    Close Redis connection.
    """
    global redis_client
    if redis_client:
        try:
            await redis_client.close()
            redis_client = None
            print("✅ Redis disconnected")
        except Exception as e:
            print(f"Redis close error: {e}")
