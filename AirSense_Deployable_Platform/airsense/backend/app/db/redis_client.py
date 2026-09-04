import redis.asyncio as aioredis
import json
from typing import Any, Optional
from app.core.config import settings
from functools import wraps
import hashlib

_redis: Optional[aioredis.Redis] = None

async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
        )
    return _redis

async def cache_get(key: str) -> Optional[Any]:
    r = await get_redis()
    val = await r.get(key)
    return json.loads(val) if val else None

async def cache_set(key: str, value: Any, ttl: int = 300):
    r = await get_redis()
    await r.setex(key, ttl, json.dumps(value, default=str))

async def cache_delete(key: str):
    r = await get_redis()
    await r.delete(key)

async def cache_delete_pattern(pattern: str):
    r = await get_redis()
    keys = await r.keys(pattern)
    if keys:
        await r.delete(*keys)

async def increment_counter(key: str, expire: int = 86400) -> int:
    r = await get_redis()
    pipe = r.pipeline()
    await pipe.incr(key)
    await pipe.expire(key, expire)
    results = await pipe.execute()
    return results[0]

def cached(ttl: int = 300, prefix: str = "airsense"):
    """Decorator for caching async functions."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key_data = f"{prefix}:{func.__name__}:{args}:{sorted(kwargs.items())}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()
            
            cached_val = await cache_get(cache_key)
            if cached_val is not None:
                return cached_val
            
            result = await func(*args, **kwargs)
            await cache_set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator
