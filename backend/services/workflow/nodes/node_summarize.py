from config import logger
from langgraph.types import Command
from langgraph.graph import END
import json

from backend.services.workflow.state import SubNewsState, NewsStatus
from backend.services.workflow.agents import ResearchAssistant

class SummarizationNode:
    def __init__(
        self, 
        platform: str = "Deepseek", 
        model_name: str | None = None,
        temperature: float = 0.3
    ) -> None:
        self._platform = platform
        self.agent = ResearchAssistant(
            platform=platform, 
            model_name=model_name, 
            temperature=temperature
        )

    async def __call__(self, state: SubNewsState) -> Command:
        
        # Get the news item
        research_data = state["research"]
        research_outlines = research_data["outlines"]
        research_content = research_data["content"]

        # Curate the research data
        curation_result = await self.agent.curate(research_content, research_outlines)
        print(json.dumps(curation_result, indent=2))
        
        if not curation_result or not curation_result.get("notes"):
            # unlikely to happen since the agent retries, 
            # but just in case the agent failed, end this workflow.
            logger.error("Failed to summarize research.")
            return Command(
                update={ "status": NewsStatus.FAILED },
                goto=END
            )
        
        # Add the curation result to the research data
        research_data["research_notes"] = curation_result
        return Command(
            update={
                "status": NewsStatus.RESEARCHED, 
                "research": research_data
            }, 
            goto="node_write"
        )

    