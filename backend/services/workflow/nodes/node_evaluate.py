import asyncio
from config import logger
from typing import Tuple, List, Dict, Any
import json
from langgraph.types import Command
from langgraph.graph import END

from backend.core.redis import tracker
from backend.services.workflow.state import NewsState, NewsStatus
from backend.services.workflow.agents import NewsEditor

class NewsEvaluationNode:
    def __init__(
        self, 
        platform: str = "OpenAI", 
        model_name: str | None = None,
        temperature: float = 0.3
    ) -> None:
        self.editor_alpha = NewsEditor(
            platform="DeepSeek", 
            model_name="deepseek-chat", 
            temperature=temperature
        )
        self.editor_beta = NewsEditor(
            platform="OpenAI", 
            model_name="gpt-5.4", 
            temperature=temperature
        )
        self.editor_gamma = NewsEditor(
            platform="XAI", 
            model_name="grok-4", 
            temperature=temperature
        )
        
    async def __call__(self, state: NewsState) -> Command:
        
        # no need to validate, previous node already did that
        raw_id = state.get("id")
        raw_data = state["raw_news"]
        
        # log evaluation
        await tracker.log(raw_id, f"News editors are evaluating the content.")
        
        # Evaluate the news item with 3 editors
        evaluation_results = await asyncio.gather(
            *[editor.evaluate(raw_data) for editor in 
              [self.editor_alpha, self.editor_beta, self.editor_gamma]],
            return_exceptions=True
        )

        # Check the evaluation results
        valid_results = []
        for result in evaluation_results:
            if isinstance(result, Exception):
                logger.error(f"An evaluator failed with an exception.", exc_info=result)
            else:
                valid_results.append(result)
                await tracker.log(raw_id, json.dumps(result, indent=4))
        
        if not valid_results:
            await tracker.log(raw_id, "All news editors failed to evaluate the content.")
            return Command(
                update={"status": NewsStatus.FAILED},
                goto=END
            )

        
        # process the evaluation results
    
        evaluation, decision_votes = self._process_evaluation(raw_id, valid_results)
        
        if decision_votes < 2: 
            # If the decision vote is less than 2, reject the news item
            await tracker.log(raw_id, f"News editors voted to reject the content.")
            return Command(
                update={"status": NewsStatus.REJECTED }, 
                goto=END
            )

        # Always go to flash first; graph handles conditional deep dive after
        return Command(
            update={
                "status": NewsStatus.EVALUATED,
                "evaluation": evaluation
            },
            goto="subgraph_flash"
        )

    def _process_evaluation(self, raw_id: str, evaluation_results: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], int]:
        """Process the evaluation results and return a tuple of evaluation data."""

        decision_votes = 0
        deep_dive_votes = 0
        evaluation: Dict[str, Any] = {
            "research": [],
            "editorial_notes": [],
            "deep_dive": False,
        }

        for result in evaluation_results:
            if not result:
                continue

            # Count the decision votes
            decision = result.get("final_decision", "")
            if isinstance(decision, str) and decision.upper() == "YES":
                decision_votes += 1
            else:
                continue

            # Count deep dive votes
            if result.get("deep_dive"):
                deep_dive_votes += 1

            # Add research items
            if research := result.get("additional_research", []):
                evaluation["research"].extend(research)

            if notes := result.get("editorial_notes", []):
                if isinstance(notes, str):
                    notes = [notes]
                evaluation["editorial_notes"].extend(notes)

        # Majority vote: deep dive if 2+ editors recommend it
        evaluation["deep_dive"] = deep_dive_votes >= 2

        return evaluation, decision_votes