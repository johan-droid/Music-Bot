"""Redis cache utilities with SQLite fallback for zero-cost deployment."""

import logging
import os
from typing import Optional
from config import config

logger = logging.getLogger(__name__)

# Global Redis client
redis_client = None
sqlite_cache = None

# Cache mode: "redis" or "sqlite"
CACHE_MODE = "sqlite"  # Default to zero-cost SQLite


async def init_redis():
    """Initialize Redis connection if configured, otherwise use SQLite."""
    global redis_client, sqlite_cache, CACHE_MODE
    
    # Try Redis first if configured
    if config.REDIS_HOST and config.REDIS_HOST != "redis":
        try:
            import redis.asyncio as aioredis
            redis_client = aioredis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                password=config.REDIS_PASSWORD if config.REDIS_PASSWORD else None,
                decode_responses=True,
            )
            
            # Test connection
            await redis_client.ping()
            CACHE_MODE = "redis"
            logger.info("Redis cache connected")
            return
        except Exception as e:
            logger.warning(f"Redis connection failed, falling back to SQLite: {e}")
    
    # Use SQLite fallback
    from bot.utils.sqlite_cache import init_sqlite_cache, sqlite_cache as _sqlite
    sqlite_path = os.getenv("SQLITE_CACHE_PATH", "./data/cache.db")
    init_sqlite_cache(sqlite_path)
    sqlite_cache = _sqlite
    CACHE_MODE = "sqlite"
    logger.info("Using SQLite cache (zero-cost mode)")


class Cache:
    """Unified cache interface - uses Redis if available, else SQLite."""
    
    def __init__(self):
        self.mode = "sqlite"
    
    async def init(self):
        """Initialize with appropriate backend."""
        global CACHE_MODE
        self.mode = CACHE_MODE
    
    def _get_backend(self):
        """Get current backend client."""
        if self.mode == "redis" and redis_client:
            return redis_client
        return sqlite_cache
    
    # Admin cache
    async def cache_admins(self, chat_id: int, admin_ids: list, ttl: int = 60):
        """Cache admin list for a chat."""
        key = f"admins:{chat_id}"
        
        if self.mode == "redis" and redis_client:
            await redis_client.delete(key)
            if admin_ids:
                await redis_client.sadd(key, *admin_ids)
            await redis_client.expire(key, ttl)
        else:
            import json
            await sqlite_cache.set(key, json.dumps(admin_ids), ex=ttl)
    
    async def is_admin(self, chat_id: int, user_id: int) -> bool:
        """Check if user is admin (from cache)."""
        key = f"admins:{chat_id}"
        
        if self.mode == "redis" and redis_client:
            is_member = await redis_client.sismember(key, user_id)
            return bool(is_member)
        else:
            import json
            data = await sqlite_cache.get(key)
            if data:
                admin_ids = json.loads(data)
                return user_id in admin_ids
            return False
    
    async def get_cached_admins(self, chat_id: int) -> list:
        """Get cached admin list."""
        key = f"admins:{chat_id}"
        
        if self.mode == "redis" and redis_client:
            members = await redis_client.smembers(key)
            return [int(m) for m in members]
        else:
            import json
            data = await sqlite_cache.get(key)
            if data:
                return json.loads(data)
            return []
    
    async def invalidate_admins(self, chat_id: int):
        """Invalidate admin cache for a chat."""
        key = f"admins:{chat_id}"
        
        if self.mode == "redis" and redis_client:
            await redis_client.delete(key)
        else:
            await sqlite_cache.delete(key)
    
    # Bot admin status
    async def set_bot_admin(self, chat_id: int, is_admin: bool, ttl: int = 120):
        """Cache bot admin status."""
        key = f"bot_admin:{chat_id}"
        
        if self.mode == "redis" and redis_client:
            await redis_client.set(key, "1" if is_admin else "0", ex=ttl)
        else:
            await sqlite_cache.set(key, "1" if is_admin else "0", ex=ttl)
    
    async def is_bot_admin_cached(self, chat_id: int) -> bool:
        """Check cached bot admin status."""
        key = f"bot_admin:{chat_id}"
        
        if self.mode == "redis" and redis_client:
            val = await redis_client.get(key)
            return val == "1"
        else:
            val = await sqlite_cache.get(key)
            return val == "1"
    
    # Cooldown
    async def check_cooldown(self, user_id: int, command: str, cooldown: int = 3) -> bool:
        """Check if user is on cooldown for a command."""
        key = f"cooldown:{user_id}:{command}"
        
        if self.mode == "redis" and redis_client:
            exists = await redis_client.exists(key)
            if exists:
                return False
            await redis_client.set(key, "1", ex=cooldown)
            return True
        else:
            val = await sqlite_cache.get(key)
            if val:
                return False
            await sqlite_cache.set(key, "1", ex=cooldown)
            return True
    
    # Maintenance mode
    async def is_maintenance(self) -> bool:
        """Check if bot is in maintenance mode."""
        key = "maintenance"
        
        if self.mode == "redis" and redis_client:
            val = await redis_client.get(key)
            return val == "1"
        else:
            val = await sqlite_cache.get(key)
            return val == "1"
    
    async def set_maintenance(self, enabled: bool):
        """Set maintenance mode."""
        key = "maintenance"
        
        if self.mode == "redis" and redis_client:
            if enabled:
                await redis_client.set(key, "1")
            else:
                await redis_client.delete(key)
        else:
            if enabled:
                await sqlite_cache.set(key, "1")
            else:
                await sqlite_cache.delete(key)
    
    # Gban cache
    async def cache_gban(self, user_id: int, is_banned: bool, ttl: int = 300):
        """Cache gban status."""
        key = f"gban_cache:{user_id}"
        
        if self.mode == "redis" and redis_client:
            await redis_client.set(key, "1" if is_banned else "0", ex=ttl)
        else:
            await sqlite_cache.set(key, "1" if is_banned else "0", ex=ttl)
    
    async def is_gbanned_cached(self, user_id: int) -> bool:
        """Check cached gban status."""
        key = f"gban_cache:{user_id}"
        
        if self.mode == "redis" and redis_client:
            val = await redis_client.get(key)
            return val == "1"
        else:
            val = await sqlite_cache.get(key)
            return val == "1"
    
    # Queue operations (delegate to appropriate backend)
    async def lpush(self, key: str, *values: str):
        """List push left."""
        if self.mode == "redis" and redis_client:
            await redis_client.lpush(key, *values)
        else:
            await sqlite_cache.lpush(key, *values)
    
    async def rpush(self, key: str, *values: str):
        """List push right."""
        if self.mode == "redis" and redis_client:
            await redis_client.rpush(key, *values)
        else:
            await sqlite_cache.rpush(key, *values)
    
    async def lpop(self, key: str):
        """List pop left."""
        if self.mode == "redis" and redis_client:
            return await redis_client.lpop(key)
        else:
            return await sqlite_cache.lpop(key)
    
    async def lindex(self, key: str, index: int):
        """List get index."""
        if self.mode == "redis" and redis_client:
            return await redis_client.lindex(key, index)
        else:
            return await sqlite_cache.lindex(key, index)
    
    async def llen(self, key: str) -> int:
        """List length."""
        if self.mode == "redis" and redis_client:
            return await redis_client.llen(key)
        else:
            return await sqlite_cache.llen(key)
    
    async def lrange(self, key: str, start: int, end: int) -> list:
        """List range."""
        if self.mode == "redis" and redis_client:
            return await redis_client.lrange(key, start, end)
        else:
            return await sqlite_cache.lrange(key, start, end)
    
    async def delete(self, key: str):
        """Delete key."""
        if self.mode == "redis" and redis_client:
            await redis_client.delete(key)
        else:
            await sqlite_cache.delete(key)


# Global cache instance
cache = Cache()

async def init_cache():
    """Initialize cache helper."""
    await cache.init()
