from config import logger
from typing import Dict, Any
from langgraph.types import Command
from langgraph.graph import END

from backend.models.data import NewsItem
from backend.services.workflow.state import SubNewsState, NewsStatus
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


    async def __call__(self, state: SubNewsState) -> Dict[str, Any]:

        # Get the data from the state
        raw_news = state["raw_news"]
        raw_id = raw_news.id
        depth = state["depth"]
        script = state.get("draft")
        
        await tracker.log(str(raw_id), f"News (ID:{raw_id}) {depth} script sent to production queue.")
        return { "output": [raw_news] }
    
        # processed_data = NewsItem(
        #     raw_id=raw_id,
        #     script=script,
        #     depth=depth,
        #     geolocation=raw_news.geolocation,
        #     news_category=raw_news.news_category,
        #     entities=raw_news.entities,
        # )
        
        # try:
        #     # save processed news
        #     data_id = await self.database.save_news_item(processed_data)
        #     if not data_id:
        #         return Command(update={"status": NewsStatus.FAILED}, goto=END)
            
        #     # update raw news
        #     await self.database.update_raw_news(raw_id, raw_news)         
        #     await self.redis_client.push(RedisQueue.PROCESSED, data_id)
        
        # except Exception as e:
        #     logger.error(f"Error saving processed news: {e}")
        #     return Command(update={"status": NewsStatus.FAILED}, goto=END)
        
        
        
        # return { "output": [processed_data] }
            