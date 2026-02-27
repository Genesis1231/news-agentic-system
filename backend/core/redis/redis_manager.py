from redis.asyncio import Redis, ConnectionPool
from config import logger, configuration
from datetime import datetime, timezone
from typing import Dict


class RedisManager:
    """
    Manages Redis operations for content queueing and status tracking.
    
    Attributes:
        pool: Redis connection pool
        client: Redis client instance
        _lifetime: TTL for Redis keys in seconds
        _timeout: Timeout for Redis operations in seconds
    """
    def __init__(self, service: str = "") -> None:
        self._timeout: int = configuration["redis"]["timeout"]
        self._lifetime: int = eval(configuration["redis"]["lifetime"])
        
        self.pool: ConnectionPool = self._get_redis_pool()
        self.client: Redis = Redis(connection_pool=self.pool)

        logger.debug(f"Initialized Redis for {service}.")

    def _get_redis_pool(self) -> ConnectionPool:
        """Get a Redis connection pool."""
 
        return ConnectionPool(
            host=configuration["redis"]["host"],
            port=configuration["redis"]["port"],
            db=configuration["redis"]["database"]["main"],
            max_connections=20,  # Adjust based on your needs
            retry_on_timeout=True,
            socket_timeout=self._timeout,
            socket_connect_timeout=self._timeout,
            decode_responses=True
        )

    async def queue_length(self, queue_name: str) -> int:
        """Get the length of the queue."""
        return await self.client.llen(queue_name)
    
    async def push(self, queue_name: str, content_id: str) -> bool:
        """Push content to Redis using an atomic pipeline operation."""
        
        if not content_id:
            logger.error("Content id cannot be empty.")
            return False
        
        timestamp = datetime.now(timezone.utc).isoformat()
        redis_key = f"{queue_name}:{content_id}"
        content_mapping = {
            "id": str(content_id),  # Ensure string serialization
            "created_at": timestamp
        }
        
        try:
            async with self.client.pipeline() as pipe:
                await pipe.rpush(queue_name, content_id)
                await pipe.hset(redis_key, mapping=content_mapping)
                await pipe.expire(redis_key, self._lifetime)
                await pipe.execute()

            logger.debug(f"Pushed to Redis: {redis_key}")
            return True
        
        except Exception as e:
            logger.error(f"Error pushing to Redis for content {content_id}: {str(e)}")
            return False
        
    async def listen(self, queue_name: str) -> Dict | None:
        """
        Listen to the Redis queue using BLPOP.
        
        Uses a timeout to avoid indefinite blocking,
        and includes logging to trace failures and idle states.
        """

        try:
            # BLPOP will block until an item is available (or timeout occurs)
            if result := await self.client.blpop(queue_name, timeout=self._timeout):
                queue_name, id = result
                redis_key = f"{queue_name}:{id}"
                data = await self.client.hgetall(redis_key)
                return data
            else:
                return None
            
        except Exception as e:
            logger.debug(f"Redis: {str(e)}")
            return None

    async def close(self) -> None:
        """Close the Redis client and disconnect its pool."""
        try:
            await self.client.close()
            await self.pool.disconnect()
            logger.debug("Redis client and pool successfully closed.")
        except Exception as e:
            logger.error(f"Error closing Redis connections: {str(e)}")