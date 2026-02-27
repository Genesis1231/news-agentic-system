from config import logger
from typing import Set
import asyncio

from backend.core.redis import RedisManager, RedisQueue
from backend.core.database import DataInterface
from .distribution_manager import DistributionManager


class Publisher:
    """
    Manages the distribution of produced content by listening to Redis for signals and
    using DistributionManager to publish content to various channels.
    
    Attributes:
        redis_client: Redis client for listening to production signals.
        database: Database client for retrieving news items.
        distribution_manager: Manager for handling the distribution to various channels.
        
        _active_tasks: Set of active distribution tasks.
        _running: Flag to indicate if the main processing loop is running.
        _sleep_time: Time to sleep between processing loops.

    """

    def __init__(self, sleep_time: int = 5) -> None:
        """Initialize the Publisher."""
        self.redis_client: RedisManager = RedisManager(service="Publisher")
        self.database: DataInterface = DataInterface(service="Publisher")
        self.distribution_manager = DistributionManager()
        
        self._running: bool = False
        self._sleep_time: int = sleep_time
        self._active_tasks: Set[asyncio.Task] = set()

    async def start(self) -> None:
        """Start the main distribution loop."""

        if self._running:
            logger.warning("The Publisher is already running.")
            return
        
        self._running = True

        while self._running:
            try:
                # Check for new data from Redis
                data = await self.redis_client.listen(RedisQueue.PRODUCED)
                if data and (news_id := data.get("id")):
                    # Create task for distribution and track it
                    task = asyncio.create_task(self._distribute_news(news_id))
                    
                    self._active_tasks.add(task)
                    task.add_done_callback(self._active_tasks.discard)
                    
                await asyncio.sleep(self._sleep_time)

            except Exception as e:
                logger.error(f"Error in the publisher loop: {e}")

    async def _distribute_news(self, news_id: str) -> None:
        """Process a produced news item and distribute it."""
            
        try:
            # Retrieve the news data from the database
            news_data = await self.database.get_single_news(news_id)
            if not news_data:
                logger.error(f"No news data found for ID {news_id}.")
                return

            # Retrieve the raw news data from the database
            raw_news_data = await self.database.get_single_rawnews(news_data.raw_id)
            if not raw_news_data:
                logger.error(f"No raw news data found for ID {news_id}.")
                return
            
            # Distribute the news data
            result = await self.distribution_manager.distribute(news_data, raw_news_data)
            if not result:
                return
            
            # Update status only on successful distribution
            await self.database.update_news(news_id, {"is_published": True})
            logger.debug(f"Successfully published news ID: {news_id}")
            
        except asyncio.CancelledError:
            logger.warning(f"Distribution task for news ID {news_id} was cancelled")

        except Exception as e:
            logger.error(f"Error distributing news ID {news_id}: {e}")


    async def stop(self) -> None:
        """Stop the publisher."""
        self._running = False

    async def __aenter__(self):
        """Start the publisher using async context management."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Gracefully shutdown the publisher on exit."""
        await self.shutdown()

    async def shutdown(self) -> None:
        """Shutdown the publisher gracefully."""
        try: 
            # Wait for all active tasks to complete naturally
            if self._active_tasks:
                logger.debug(f"Waiting for {len(self._active_tasks)} active distribution tasks to complete")
                await asyncio.gather(*self._active_tasks, return_exceptions=True)
            
            # Close connections
            await self.database.close()
            await self.redis_client.close()
            
            logger.debug("Publisher shutdown completed.")
        except Exception as e:
            logger.error(f"Error during Publisher shutdown: {e}")
