from config import logger
from typing import Set
import asyncio

from backend.core.redis import RedisManager, RedisQueue, tracker
from backend.core.database import DataInterface
from backend.services.workflow.state import NewsPriority  
from .multimedia_manager import MultimediaManager


class ProductionDirector:
    """
    Manages the production of news content by processing items from a priority queue.
    Handles TTS and video production in a controlled manner due to the synchronous nature
    of moviepy and TTS operations.
    
    Attributes:
        queue: Priority queue for production tasks.
        redis_client: Redis client for listening to news items.
        database: Database client for retrieving news items.
        _running: Flag to indicate if the main processing loop is running.
        production_manager: ProductionManager for handling the actual production process.
 
    """

    def __init__(self, sleep_time: int = 10) -> None:
        """Initialize the Production Director."""
        
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.redis_client: RedisManager = RedisManager(service="Production")
        self.database: DataInterface = DataInterface(service="Production")
        self.multimedia_manager = MultimediaManager()
        
        self._running: bool = False
        self._sleep_time: int = sleep_time
        self._active_tasks: Set[asyncio.Task] = set()


    async def start(self) -> None:
        """Start the main production loop."""

        if self._running:
            logger.warning("The Production Director is already running.")
            return
        
        self._running = True

        while self._running:
            try:
                # Check for new data from Redis (data pushed from node_finalize)
                data = await self.redis_client.listen(RedisQueue.PROCESSED)
                if data and (news_id := data.get("id")):
                    await self._enqueue_news(news_id)
                
                # If there are queued items, process them concurrently.
                if not self.queue.empty():
                    task = asyncio.create_task(self._process_queue_item())
                    self._active_tasks.add(task)
                    task.add_done_callback(self._active_tasks.discard)

                await asyncio.sleep(self._sleep_time)
            
            except asyncio.CancelledError:
                logger.info("Production Director loop cancelled.")
                break
            except Exception as e:
                logger.error(f"Error in the production loop: {e}")

    async def _enqueue_news(self, news_id: str) -> None:
        """Enqueue news items from Redis."""
 
        news_data = await self.database.get_single_news(news_id)
        if not news_data:
            logger.error(f"No news data found for ID {news_id}.")
            return

        if news_data.is_produced:
            logger.debug(f"News (ID:{news_id}) is already produced.")
            return
        
        # Get the priority from the news data
        priority = NewsPriority[news_data.priority.upper()].value
        await self.queue.put((priority, news_id, news_data))
    
        logger.debug(f"Enqueued news (ID:{news_id}) with priority: {priority}.")
 
    async def _process_queue_item(self) -> None:
        """Process a single item from the production queue."""
        
        try:
            priority, news_id, news_data = await self.queue.get()
            production_result = await self.multimedia_manager.produce_news(news_id, news_data)
            
            if production_result:
                # Update production status and push to redis queue
                production_result["is_produced"] = True
                
                # Run database update and Redis push concurrently
                await self.database.update_news(news_id, production_result)
                await self.redis_client.push(RedisQueue.PRODUCED, news_id)

            else:
                logger.error(f"Production failed for news (ID:{news_id or 'Undefined'})")
                # Requeue with lower priority
                if priority < 4:
                    await self.queue.put((priority + 1, news_id, news_data))
                
        except Exception as e:
            logger.error(f"Error producing news (ID:{news_id}): {e}")
        finally:
            self.queue.task_done()


    async def stop(self) -> None:
        """Stop the production director."""
        self._running = False

    async def __aenter__(self):
        """Start the production director using async context management."""

        # unfinished_news = await self.database.load_news(is_produced=False)
        # if unfinished_news:
        #     for news in unfinished_news:
        #         await self._enqueue_news(news.id)
        
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Gracefully shutdown the production director on exit."""
        await self.shutdown()

    async def shutdown(self) -> None:
        """Shutdown the production director gracefully."""
        try:
            # Cancel all active tasks
            for task in self._active_tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for all tasks to complete or be cancelled
            if self._active_tasks:
                await asyncio.gather(*self._active_tasks, return_exceptions=True)
            
            await self.multimedia_manager.shutdown()
            await self.database.close()
            await self.redis_client.close()
            logger.debug("Production Director shutdown completed.")
        except Exception as e:
            logger.error(f"Error during Production Director shutdown: {e}")
