from config import logger
from typing import Dict, Any
import json
from langgraph.types import Command
from langgraph.graph import END

from backend.core.redis import tracker
from backend.services.workflow.state import NewsState, NewsStatus
from backend.services.workflow.agents import ClassificationAgent

class ClassificationNode:
    def __init__(
        self, 
        platform: str = "Anthropic",
        model_name: str | None = "claude-sonnet-4-0",
        temperature: float | None = None,
    ) -> None:
        """Initialize the ClassificationNode."""
        
        self.classification_agent = ClassificationAgent(
            platform=platform, 
            model_name=model_name, 
            temperature=temperature,
        )

    async def __call__(self, state: NewsState) -> Dict[str, Any]:

        # Get the news data and validate it
        raw_data = state["raw_news"]
        raw_id = state["id"]

        # Log the news item in monitor
        await tracker.log(raw_id, f"Curator started classifying the content.")

        # Classify the news item
        classification = await self.classification_agent.classify(raw_data)
        if not classification:
            await tracker.log(raw_id, "Classification failed. Please check logs for more details.")
            await tracker.track({"id": raw_id, "status": "failed"})
            return Command(
                update={"status": NewsStatus.FAILED},
                goto=END
            )
        
        # Update the text if the original text is not in English
        # if classification.get("translation"):
        #     raw_data.text = classification["translation"]
            
        classification["score"] = raw_data.potential_impact_score
        
        # Merge the classification result into the news data
        raw_data = raw_data.merge_classification(classification)
        
        # Log the classification result
        await tracker.log(raw_id, f"Classification: {json.dumps(classification, indent=4)}")
        await tracker.track({
            "id": raw_id,
            "headline": classification["headline"],
            "details": {
                "classification": classification,
            }
        })

        # Check if the classification is relevant, still evaluate if the news is from a key figure
        if classification["relevance"] < 0.7 and not raw_data.author.is_key_figure:
            await tracker.log(raw_id, "Curator rejected the content since it's not newsworthy.")
            await tracker.track({"id": raw_id, "status": "failed"})
            return Command(
                update={"status": NewsStatus.REJECTED},
                goto=END
            )
        
        # Check if the news is negative domestic news
        if classification["sentiment"] == "NEGATIVE" and classification["geolocation"] == ["CHINA"]:
            await tracker.log(raw_id, "Curator rejected the content since it's negative domestic news.")
            await tracker.track({"id": raw_id, "status": "failed"})
            return Command(
                update={"status": NewsStatus.REJECTED},
                goto=END
            )
            
            
        # update the state and goto the next node
        return Command(
            update={
                "raw_news": raw_data,
                "status": NewsStatus.CLASSIFIED,
            },
            goto="node_evaluate"
        )
 