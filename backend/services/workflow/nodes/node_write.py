from config import logger
from typing import Dict, Any
import json
from langgraph.types import Command
from langgraph.graph import END

from backend.services.workflow.state import SubNewsState, NewsStatus
from backend.services.workflow.agents import NewsWriter
from backend.core.redis import tracker

class WritingNode:
    def __init__(
        self, 
        platform: str = "Anthropic", 
        model_name: str | None = "claude-opus-4-6",
        temperature: float | None = 1.0,
    ) -> None:
        """Initialize the WriterNode."""
        self.agent = NewsWriter(
            platform=platform, 
            model_name=model_name, 
            temperature=temperature,
        )

    async def __call__(self, state: SubNewsState) -> Dict[str, Any] | Command:

        # Get the data from the state
        raw_data = state["raw_news"]
        raw_id = str(raw_data.id)
        depth = state["depth"]
        
        # see if there are any revisions
        revision = state.get("revision", {})
        research_notes = state.get("research", {}).get("research_notes", "")
        
        # if there are any revisions, revise the script
        if revision:
            original_script = state.get("draft")
            revision_notes = revision.get("notes")
            
            # log revision in monitor
            await tracker.log(str(raw_id), f"News writer is revising the {depth} script.")
            
            script = await self.agent.revise(
                news_item=raw_data, 
                original_script=original_script, 
                revision_notes=revision_notes,
                research_notes=research_notes,
                depth=depth
            )
        else:
            editorial_notes = state["evaluation"].get("editorial_notes", [])
            
            # log writing in monitor
            await tracker.log(str(raw_id), f"News writer is crafting the {depth} script.")
            
            script = await self.agent.write(
                news_item=raw_data, 
                research_notes=research_notes, 
                editorial_notes=editorial_notes,
                depth=depth
            )

        # if the script is not generated, return an error
        if not script or not (draft_script := script.get("script", "")):
            await tracker.log(str(raw_id), f"Failed to generate {depth} script, please check logs for more details.")
            return Command(
                update={ "status": NewsStatus.FAILED },
                goto=END
            )

        # log the draft script
        await tracker.log(str(raw_id), f"Draft script: \n {json.dumps(script, indent=4)}")
                    
        return { "status": NewsStatus.COMPOSED, "draft": draft_script }
 
