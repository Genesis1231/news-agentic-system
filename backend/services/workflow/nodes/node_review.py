from config import logger
from typing import Dict, Any
from langgraph.types import Command
from langgraph.graph import END
import json

from backend.core.redis import tracker
from backend.services.workflow.state import SubNewsState, NewsStatus
from backend.services.workflow.agents import ChiefEditor

class ReviewNode:
    def __init__(
        self,
        platform: str = "OpenAI", 
        model_name: str | None = "gpt-5.4",
        temperature: float | None = 0.6,
    ) -> None:
        """Initialize the ReviewNode."""
        self.agent = ChiefEditor(
            platform=platform, 
            model_name=model_name, 
            temperature=temperature,
        )

    async def __call__(self, state: SubNewsState) -> Dict[str, Any] | Command:

        # Get the data from the state
        raw_data = state["raw_news"]
        raw_id = raw_data.id
        depth = state["depth"]
        script = state["draft"]
        notes = state.get("research", {}).get("research_notes", "")

        # track the processing
        await tracker.log(str(raw_id), f"Chief editor is reviewing the {depth} script.")
        
        final_review = await self.agent.review(
            news_item=raw_data, 
            draft=script, 
            research_notes=notes,
            depth=depth
        )
        
        # If no final review is generated, return an error.
        if not final_review:
            await tracker.log(str(raw_id), f"Failed to approve {depth} script. Please check the logs.")
            return Command(
                update={ "status": NewsStatus.FAILED },
                goto=END
            )
        
        # log the final review
        await tracker.log(str(raw_id), f"Chief editor: {json.dumps(final_review, indent=4)}")
        
        # Format the final output from the reviews
        approved = self.approve_script(final_review, depth)
            
        if not approved:
            count = state.get("revision", {}).get("count", 0)
            if count >= 2:
                # TODO: send to human editor
                await tracker.log(str(raw_id), f"Revised {count} times for {depth} script. Send to human editor.")
                # return Command(
                #     update={ "status": NewsStatus.FAILED },
                #     goto=END
                # )
                return Command(
                    update={ "status": NewsStatus.REVIEWED, "raw_news": raw_data},
                    goto="node_finalize"
                )
            # Update the revision notes and count
            revisions = {
                "notes": final_review.get("revision_notes"),
                "count": count + 1,
            }
            
            await tracker.log(str(raw_id), f"{depth} script need revision, send back to the writer.")
            return Command(
                update={ "revision": revisions },
                goto="node_write"
            )
            
        # If all scripts are approved, goto the final output.
        await tracker.log(str(raw_id), f"Chief editor has approved {depth} script.")
        
        # Update the confidence of the news
        # raw_data.confidence = (88 + (final_review.get("source_integrity") + 
        #                        final_review.get("technical_precision"))/2)/100
                                     

        return Command(
            update={ "status": NewsStatus.REVIEWED, "raw_news": raw_data},
            goto="node_finalize"
        )
    
    def approve_script(self, final_review: Dict[str, Any], script_depth: str) -> bool:
        """Get the decision based on the final review and script depth."""
        
        if not script_depth or not final_review:
            logger.error(f"Invalid final review: {final_review} or script depth: {script_depth}")
            return False
            
        source_integrity = final_review.get("source_integrity", 0)
        storytelling = final_review.get("storytelling", 0)
        hook_effectiveness = final_review.get("hook_effectiveness", 0)
        value_density = final_review.get("value_density", 0)
        engagement_potential = final_review.get("engagement_potential", 0)

        if script_depth.upper() == "FLASH":
            return (
                source_integrity >= 7 and
                storytelling >= 7 and
                hook_effectiveness >= 8
            )

        if script_depth.upper() == "DEEP":
            return (
                source_integrity >= 7 and
                storytelling >= 7 and
                value_density >= 7 and
                hook_effectiveness >= 7 and
                engagement_potential >= 7
            )

        return False
