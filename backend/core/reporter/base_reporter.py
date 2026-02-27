from config import logger
from backend.core.redis import RedisManager, RedisQueue

class BaseReporter:
    """
    Base class for all aggregators.
    
    Attributes:
        source_type (str): The type of source to aggregate from.
        redis (RedisManager): The Redis manager instance.
    """
    
    def __init__(self, redis: RedisManager, source_type: str = ""):
        self.redis_client: RedisManager = redis
        self.source_type: str = source_type
        
        logger.debug(f"Initialized {source_type} reporter.")

    async def push_redis(self, content_id: str) -> None:
        """Push content to Redis with proper error handling.   """

        if not content_id:
            logger.error("Invalid content_id provided.")
            return
        
        success = await self.redis_client.push(RedisQueue.RAW, content_id)
        
        if not success:
            logger.error(f"Failed to push content to Redis: {content_id}")
