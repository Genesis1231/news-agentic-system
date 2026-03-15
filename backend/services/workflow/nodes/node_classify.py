from config import logger
from typing import Dict, Any
import json
from langgraph.types import Command
from langgraph.graph import END

from backend.core.redis import tracker
from backend.core.database import DataInterface
from backend.services.workflow.state import NewsState, NewsStatus
from backend.services.workflow.agents import ClassificationAgent
from backend.utils.vector.embeddings import EmbeddingEngine
from backend.utils.dedup import check_duplicate

class ClassificationNode:
    def __init__(
        self,
        database: DataInterface,
        platform: str = "Google",
        model_name: str | None = "gemini-2.5-flash",
        temperature: float | None = None,
    ) -> None:
        """Initialize the ClassificationNode."""

        self.database = database
        self.classification_agent = ClassificationAgent(
            platform=platform,
            model_name=model_name,
            temperature=temperature,
        )
        self.embedding_engine = EmbeddingEngine()
        self.embedding_engine.init_model()

    async def __call__(self, state: NewsState) -> Command:

        # Get the news data and validate it
        raw_data = state["raw_news"]
        raw_id = state["id"]

        # Log the news item in monitor
        await tracker.log(raw_id, f"Curator started classifying the content.")

        # Classify the news item
        classification = await self.classification_agent.classify(raw_data)
        if not classification:
            await tracker.log(raw_id, "Classification failed. Please check logs for more details.")
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

        # Generate embedding for dedup
        embed_text = f"{raw_data.headline} | {', '.join(raw_data.entities)}"
        embedding = await self.embedding_engine.embed_one(embed_text)

        if embedding:
            # Check for duplicates before persisting
            match = await check_duplicate(self.database, raw_data, embedding)
            if match:
                raw_data.raw_metadata = {"duplicate_of": match.id}
                raw_data.embedding = embedding
                await self.database.update_raw_news(raw_id, raw_data)
                match_headline = match.headline or match.title
                await tracker.log(raw_id, f"Duplicate of #{match.id} ({match_headline}). Skipping.")
                return Command(
                    update={"status": NewsStatus.DUPLICATE},
                    goto=END,
                )

            # Store embedding for future comparisons
            raw_data.embedding = embedding

        # Persist classification to database so dashboard can display it
        await self.database.update_raw_news(raw_id, raw_data)

        # Log the classification result
        await tracker.log(raw_id, f"Classification: {json.dumps(classification, indent=4)}")

        # Check if the classification is relevant, still evaluate if the news is from a key figure
        if classification["relevance"] < 0.7 and not raw_data.author.is_key_figure:
            await tracker.log(raw_id, "Curator rejected the content since it's not newsworthy.")
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
 