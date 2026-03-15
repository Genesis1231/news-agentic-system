from config import logger
from typing import Dict, Any
from langgraph.types import Command
from langgraph.graph import END

from backend.models.data import NewsItem
from backend.services.workflow.state import SubNewsState, NewsStatus
from backend.services.workflow.agents import NewsEditor
from backend.core.database import DataInterface
from backend.core.redis import RedisManager, RedisQueue, tracker


class FinalizeNode:
    def __init__(
        self,
        database: DataInterface,
        redis_client: RedisManager,
    ) -> None:
        """Initialize the FinalizeNode."""
        self.database = database
        self.redis_client = redis_client
        self.editor = NewsEditor(platform="Anthropic", task="Summarize")


    async def __call__(self, state: SubNewsState) -> Dict[str, Any] | Command:

        # Get the data from the state
        raw_news = state["raw_news"]
        raw_id = raw_news.id
        depth = state["depth"]
        script = state.get("draft")
        

        if not raw_id:
            logger.error("Finalize called with no raw_id.")
            return Command(update={"status": NewsStatus.FAILED}, goto=END)

        # Generate a concise feed summary from the approved script
        summary = await self.editor.summarize(script)
        if not summary:
            logger.warning(f"News (ID:{raw_id}) summary generation failed, using truncated text.")
            summary = raw_news.composed_content[:200] if raw_news.composed_content else ""

        await tracker.log(str(raw_id), f"News (ID:{raw_id}) {depth} script sent to production queue.")

        processed_data = NewsItem(
            raw_id=raw_id,
            title=raw_news.title,
            script=script,
            text=summary,
            depth=depth,
            news_category=raw_news.news_category,
            news_type=raw_news.news_type,
            entities=raw_news.entities,
        )

        try:
            # save processed news
            data_id = await self.database.save_news_item(processed_data)
            if not data_id:
                return Command(update={"status": NewsStatus.FAILED}, goto=END)

            # update raw news as processed
            await self.database.update_raw_news(raw_id, {"is_processed": True})
            await self.redis_client.push(RedisQueue.PROCESSED, str(data_id))

        except Exception as e:
            logger.error(f"Error saving processed news: {e}")
            return Command(update={"status": NewsStatus.FAILED}, goto=END)

        return { "output": [processed_data] }
            