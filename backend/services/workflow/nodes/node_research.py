from config import logger
from langgraph.types import Command
from langgraph.graph import END

from backend.core.redis import tracker
from backend.services.workflow.state import SubNewsState, NewsStatus
from backend.services.workflow.agents import NewsResearcher


class ResearchNode:
    def __init__(self) -> None:
        self.researcher = NewsResearcher()

    async def __call__(self, state: SubNewsState) -> Command:

        news_data = state["raw_news"]
        raw_id = str(news_data.id)
        evaluations = state["evaluation"]

        research_topics = evaluations.get("research", [])
        if not research_topics:
            return Command(goto="node_write")

        await tracker.log(raw_id, "Starting ReAct research agent...")

        research_notes = await self.researcher.research(
            news_item=news_data,
            topics=research_topics,
        )

        if not research_notes:
            await tracker.log(raw_id, "Research agent failed — no results.")
            return Command(
                update={
                    "status": NewsStatus.FAILED,
                    "error": [{"node": "node_research",
                               "error_message": "Research agent failed to gather information"}]
                },
                goto=END,
            )

        await tracker.log(raw_id, f"Research complete. ({len(research_notes)} chars)")

        return Command(
            update={
                "status": NewsStatus.RESEARCHED,
                "research": {"research_notes": research_notes},
            },
            goto="node_write",
        )
