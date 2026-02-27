from config import logger
from typing import Dict, Any
from langgraph.types import Command
from langgraph.graph import END

from backend.services.workflow.state import SubNewsState, NewsStatus
from backend.services.workflow.agents import NewsEditor

class PlanNode:
    def __init__(
        self, 
        platform: str = "Groq", 
        model_name: str | None = "deepseek-r1-distill-llama-70b",
        temperature: float | None = None,
        task: str = "Review"
    ) -> None:
        """Initialize the ReviewNode."""
        self.agent = NewsEditor(
            platform=platform, 
            model_name=model_name, 
            temperature=temperature,
            task=task
        )

    async def __call__(self, state: SubNewsState) -> Dict[str, Any]:

        # Get the data from the state
        news_data = state["raw_news"]
        depth = state["depth"]
        draft = state["draft"]
        
        review = await self.agent.review(
            news_item=news_data, 
            draft=draft, 
            depth=depth
        )
        
        logger.debug(f"Generated review: {review}")
        
        if not review:
            logger.error("Failed to generate review.")
            return Command(
                update={ "status": NewsStatus.FAILED },
                goto=END
            )
        
        
        
        # update the state
        return { "status": NewsStatus.REVIEWED, "review": review or "" }
 