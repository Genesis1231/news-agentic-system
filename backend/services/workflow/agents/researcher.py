from config import logger
from typing import List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate

from backend.models.data import RawNewsItem
from backend.utils.prompt import load_prompt
from backend.models.schema.outputs import ResearchEvaluation
from backend.core.agent import BaseAgent


class NewsResearcher(BaseAgent):
    """
    Perplexity-backed research agent that searches the web and synthesizes
    information for news content creation.
    """

    def __init__(
        self,
        platform: str = "Perplexity",
        model_name: str | None = "sonar-pro",
        base_url: str | None = None,
        temperature: float = 0.1
    ) -> None:
        super().__init__(
            config = {
                "name": "Research Agent",
                "platform": platform,
                "model_name": model_name,
                "base_url": base_url,
                "temperature": temperature,
                # No output_format — Perplexity returns free text with citations
            }
        )

    def _build_prompt(
        self,
        news_item: RawNewsItem,
        topics: List[str],
        accumulated_notes: str = ""
    ) -> str:
        """Build the user prompt for Perplexity research."""

        topics_str = "\n    - ".join(topics)
        prompt = f"""
            Research the following topics thoroughly:
            <research_topics>
                - {topics_str}
            </research_topics>

            News context:
            <source_content>
                Media: {news_item.source_name}
                Author: {news_item.author.name} ({news_item.author.idname})
                Time: {news_item.timestamp}
                ----------------------------------
                {news_item.text}
            </source_content>
        """

        if accumulated_notes:
            prompt += f"""
            Previous research findings (avoid repeating, focus on gaps):
            <previous_findings>
                {accumulated_notes}
            </previous_findings>
            """

        prompt += "\n            Provide detailed, well-organized research notes."
        return prompt

    async def research(
        self,
        news_item: RawNewsItem,
        topics: List[str],
        accumulated_notes: str = ""
    ) -> str | None:
        """Research topics via Perplexity and return synthesized findings."""

        if not topics:
            logger.error("Empty topics provided")
            return None

        system_prompt = load_prompt("research_content")
        user_prompt = self._build_prompt(news_item, topics, accumulated_notes)

        prompt = ChatPromptTemplate([
            ("system", system_prompt),
            ("user", user_prompt),
        ])

        try:
            logger.debug(f"Researching {len(topics)} topics via Perplexity...")
            response = await self._invoke(prompt.format_messages())
            return response.content

        except Exception as e:
            logger.error(f"Failed to research topics: {e}")
            return None


class ResearchEvaluator(BaseAgent):
    """
    Evaluates whether accumulated research is sufficient for writing,
    and identifies remaining knowledge gaps.
    """

    def __init__(
        self,
        platform: str = "Google",
        model_name: str | None = "gemini-2.5-flash",
        base_url: str | None = None,
        temperature: float = 0.1
    ) -> None:
        super().__init__(
            config = {
                "name": "Research Evaluator",
                "platform": platform,
                "model_name": model_name,
                "base_url": base_url,
                "temperature": temperature,
                "output_format": ResearchEvaluation,
            }
        )

    async def evaluate(
        self,
        news_item: RawNewsItem,
        original_topics: List[str],
        accumulated_notes: str
    ) -> Dict[str, Any]:
        """Evaluate research completeness and identify gaps."""

        system_prompt = load_prompt("evaluate_research")
        topics_str = "\n    - ".join(original_topics)

        user_prompt = f"""
            Original research topics:
            <research_topics>
                - {topics_str}
            </research_topics>

            News context:
            <source_content>
                {news_item.composed_content}
            </source_content>

            Accumulated research notes:
            <research_notes>
                {accumulated_notes}
            </research_notes>

            Evaluate the research completeness and identify any critical gaps.
            Output strictly in provided JSON schema.
        """

        prompt = ChatPromptTemplate([
            ("system", system_prompt),
            ("user", user_prompt),
        ])

        try:
            logger.debug("Evaluating research completeness...")
            response: ResearchEvaluation = await self._invoke(prompt.format_messages())
            return response.model_dump()

        except Exception as e:
            logger.error(f"Failed to evaluate research: {e}")
            return {
                "sufficient": False,
                "gaps": original_topics,
                "analysis": "Evaluation failed"
            }
