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
            model_name="gpt-5", 
            temperature=temperature
        )
        self.editor_gamma = NewsEditor(
            platform="Mistral", 
            model_name="mistral-medium-latest", 
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
            await tracker.track({"id": raw_id, "status": "failed"})
            return Command(
                update={"status": NewsStatus.FAILED},
                goto=END
            )

        
        # process the evaluation results
    
        evaluation, decision_votes = self._process_evaluation(raw_id, valid_results)
        
        if decision_votes < 2: 
            # If the decision vote is less than 2, reject the news item
            await tracker.log(raw_id, f"News editors voted to reject the content.")
            await tracker.track({"id": raw_id, "status": "failed"})
            return Command(
                update={"status": NewsStatus.REJECTED }, 
                goto=END
            )
        
        # get the coverage nodes for the next moves
        coverage_nodes = [
            f"subgraph_{item.lower()}" 
            for item in evaluation["coverage_depth"]
        ]
    
        # track the evaluation result
        await tracker.track({
            "id": raw_id,
            "details": {
                "evaluation": evaluation
            }
        })
        
        return Command(
            update={
                "status": NewsStatus.EVALUATED,
                "evaluation": evaluation
            }, 
            goto=coverage_nodes
        )

    def _process_evaluation(self, raw_id: str, evaluation_results: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], int]   :
        """Process the evaluation results and return a tuple of evaluation data."""
        
        # Check the evaluation results
        decision_votes = 0
        evaluation = {
            "research": [],
            "editorial_note": [],
            "coverage_depth": set()
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
            
            # Add research items
            if research := result.get("additional_research", []):
                evaluation["research"].extend(research)

            if editorial_note := result.get("editorial_note", ""):
                evaluation["editorial_note"].append(editorial_note)
            
            # Add coverage depth to sets
            if coverage_depth := result.get("coverage_depth", ""):
                evaluation["coverage_depth"].add(coverage_depth)

        # always add flash to the coverage depth    
        # evaluation["coverage_depth"].add('FLASH')
        evaluation["coverage_depth"] = ["FLASH"] # temporary only flash
        
        return evaluation, decision_votes