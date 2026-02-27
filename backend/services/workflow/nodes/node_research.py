import json
from config import logger
from typing import Dict, Any
from langgraph.types import Command
from langgraph.graph import END

from backend.services.workflow.state import SubNewsState, NewsStatus
from backend.services.workflow.agents import NewsResearcher
from backend.utils.search import TavilySearch


class ResearchNode:
    def __init__(
        self, 
        platform: str = "Anthropic", 
        model_name: str = "claude-sonnet-4-0",
        temperature: float = 0.5
    ) -> None:
        self.query_agent = NewsResearcher(
            platform=platform, 
            model_name=model_name, 
            temperature=temperature
        )
        self.search_agent = TavilySearch()
        
    async def __call__(self, state: SubNewsState) -> Command:

        # Get the news item
        news_data = state["raw_news"]
        evaluations = state["evaluation"]
        
        if not (research_items := evaluations.get("research_notes") or not any(research_items)):
            return Command(goto="node_writer")
    
        ### if the news is in flash depth, skip the research node
        ### or the news is in brief depth and already has a link, then no need to research
 
        # Generate the research plans
        research_results = await self.query_agent.research(news_data, research_items)
        logger.debug(json.dumps(research_results,indent=2))
        
        if not any(research_results):
            # this is unlikely to happen
            return Command(
                update={
                    "status": NewsStatus.FAILED, 
                    "error": [{"node": "node_research", 
                               "error_message": "Failed to generate research plans"}]
                },
                goto=END
            )
        
        # get the research plans and search it with the search agent
        # still need social media search
        researches = [
            {
                "type": research.get("type"), 
                "query": research.get("query"), 
                "domain_name": research.get("domain_name", "")
            }
            for research in research_results.research_plans
            if research["type"] != "social_search"
        ]

        search_results = await self.search_agent.search_web(researches)
        
        if search_results:
            return Command(
                update={
                    "research": {
                        "outlines": research_results.outlines,
                        "content": search_results
                    },
                },
                goto="node_summarize"
            )
            
        # if the search results are empty
        research_count = state.get("research", {}).get("count", 0)
        if research_count >= 2:
            return Command(
                update={
                    "status": NewsStatus.FAILED,
                    "error": [{"node": "node_research", 
                           "error_message": "Failed to generate research plans"}]
                },
                goto=END
            )

        return Command(
            update={
                "research": {"count": research_count + 1 }
            },
            goto="node_research"
        )