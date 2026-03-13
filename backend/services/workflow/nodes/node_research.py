from config import logger
from typing import Dict, Any
from langgraph.types import Command
from langgraph.graph import END

from backend.core.redis import tracker
from backend.services.workflow.state import SubNewsState, NewsStatus
from backend.services.workflow.agents import NewsResearcher, ResearchEvaluator


class ResearchNode:
    def __init__(self, max_rounds: int = 10) -> None:
        self.max_rounds = max_rounds
        self.researcher = NewsResearcher()
        self.evaluator = ResearchEvaluator()

    async def __call__(self, state: SubNewsState) -> Command:

        news_data = state["raw_news"]
        raw_id = str(news_data.id)
        evaluations = state["evaluation"]

        research_topics = evaluations.get("research", [])
        if not research_topics:
            return Command(goto="node_write")

        await tracker.log(raw_id, "Starting deep research...")

        accumulated_notes = []
        remaining_topics = research_topics

        for round_num in range(self.max_rounds):
            await tracker.log(
                raw_id,
                f"Research round {round_num + 1}/{self.max_rounds}: "
                f"researching {len(remaining_topics)} topics"
            )

            # Research current topics via Perplexity
            notes = await self.researcher.research(
                news_item=news_data,
                topics=remaining_topics,
                accumulated_notes="\n\n".join(accumulated_notes)
            )

            if not notes:
                logger.warning(f"Round {round_num + 1}: empty research response")
                continue

            accumulated_notes.append(notes)

            # Evaluate completeness
            evaluation = await self.evaluator.evaluate(
                news_item=news_data,
                original_topics=research_topics,
                accumulated_notes="\n\n".join(accumulated_notes)
            )

            if evaluation.get("sufficient") or not evaluation.get("gaps"):
                await tracker.log(
                    raw_id,
                    f"Research sufficient after {round_num + 1} rounds. "
                    f"{evaluation.get('analysis', '')}"
                )
                break

            # Narrow focus to identified gaps
            remaining_topics = evaluation["gaps"]
            await tracker.log(raw_id, f"Gaps identified: {remaining_topics}")

        if not accumulated_notes:
            await tracker.log(raw_id, "Research failed — no results after all rounds.")
            return Command(
                update={
                    "status": NewsStatus.FAILED,
                    "error": [{"node": "node_research",
                               "error_message": "Failed to gather research"}]
                },
                goto=END
            )

        research_notes = "\n\n".join(accumulated_notes)
        await tracker.log(raw_id, f"Research complete. {len(accumulated_notes)} rounds of notes collected.")

        return Command(
            update={
                "status": NewsStatus.RESEARCHED,
                "research": {"research_notes": research_notes}
            },
            goto="node_write"
        )
