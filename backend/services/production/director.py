from config import logger
from typing import Set
import asyncio

from backend.core.redis import RedisManager, RedisQueue, tracker
from backend.core.database import DataInterface

from backend.utils.uploaders.r2 import R2Uploader
from .multimedia_manager import MultimediaManager


class ProductionDirector:
    """
    Manages the production of news content.
    Listens on Redis for processed items and produces them concurrently.
    """

    MAX_CONCURRENT = 5

    def __init__(self) -> None:
        self.redis_client: RedisManager = RedisManager(service="Production")
        self.database: DataInterface = DataInterface(service="Production")
        self.multimedia_manager = MultimediaManager()
        self.r2_uploader = R2Uploader()

        self._running: bool = False
        self._active_tasks: Set[asyncio.Task] = set()

    async def start(self) -> None:
        """Start the main production loop."""

        if self._running:
            logger.warning("The Production Director is already running.")
            return

        self._running = True

        while self._running:
            try:
                # Wait for a new item from Redis (blocks until available)
                data = await self.redis_client.listen(RedisQueue.PROCESSED)
                if not data or not (news_id := data.get("id")):
                    continue

                # Backpressure: wait if too many tasks are running
                while len(self._active_tasks) >= self.MAX_CONCURRENT:
                    await asyncio.sleep(1)

                task = asyncio.create_task(self._produce(news_id))
                self._active_tasks.add(task)
                task.add_done_callback(self._active_tasks.discard)

            except asyncio.CancelledError:
                logger.info("Production Director loop cancelled.")
                break
            except Exception as e:
                logger.error(f"Error in the production loop: {e}")

    async def _produce(self, news_id: str) -> None:
        """Produce a single news item end-to-end."""

        try:
            news_data = await self.database.get_single_news(news_id)
            if not news_data:
                logger.error(f"No news data found for ID {news_id}.")
                return

            if news_data.is_produced:
                logger.debug(f"News (ID:{news_id}) is already produced.")
                return

            raw_id = str(news_data.raw_id)
            await tracker.log(raw_id, f"Production started for news (ID:{news_id}).")

            production_result = await self.multimedia_manager.produce_news(news_id, news_data)

            if not production_result:
                await tracker.log(raw_id, f"Production failed for news (ID:{news_id}).")
                return

            # Upload TTS audio (+ companion subtitle JSON) to R2
            audio_url = await self.r2_uploader.upload_audio(production_result["audio_path"])
            if audio_url:
                production_result["audio_path"] = audio_url

            # Update production status and push to publish queue
            production_result["is_produced"] = True
            await self.database.update_news(news_id, production_result)
            await self.redis_client.push(RedisQueue.PRODUCED, news_id)

            # Update stories index on R2
            await self.r2_uploader.update_stories_index(self.database)

            await tracker.log(raw_id, f"Production complete, pushed to publish queue.")

        except Exception as e:
            logger.error(f"Error producing news (ID:{news_id}): {e}")

    async def stop(self) -> None:
        """Stop the production director."""
        self._running = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()

    async def shutdown(self) -> None:
        """Shutdown the production director gracefully."""
        try:
            for task in self._active_tasks:
                if not task.done():
                    task.cancel()

            if self._active_tasks:
                await asyncio.gather(*self._active_tasks, return_exceptions=True)

            await self.multimedia_manager.shutdown()
            await self.database.close()
            await self.redis_client.close()
            logger.debug("Production Director shutdown completed.")
        except Exception as e:
            logger.error(f"Error during Production Director shutdown: {e}")
