from config import logger
from typing import List
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langchain.agents import create_agent

from backend.models.data import RawNewsItem
from backend.utils.prompt import load_prompt
from backend.utils.tools.research_tools import ALL_RESEARCH_TOOLS


class NewsResearcher:
    """ReAct research agent that uses domain-scoped search tools
    to gather comprehensive research for news content creation.

    Uses Claude Sonnet as the reasoning model and Perplexity-backed
    tools for domain-targeted web searches.
    """

    RECURSION_LIMIT = 35  # ~17 tool calls max

    def __init__(
        self,
        model_name: str = "claude-sonnet-4-6",
        temperature: float = 0.3,
    ) -> None:
        self.system_prompt = load_prompt("research_agent")
        
        self.agent = create_agent(
            model=ChatAnthropic( 
                model_name=model_name,
                temperature=temperature,
                timeout=600,
                max_tokens_to_sample=8192,
            ), #type: ignore
            tools=ALL_RESEARCH_TOOLS,
            system_prompt=self.system_prompt,
        )

    def _build_user_message(self, news_item: RawNewsItem, topics: List[str]) -> str:
        """Build the user message with news context and research topics."""
        topics_str = "\n    - ".join(topics)
        return f"""
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

            Use your search tools to gather comprehensive information, then provide well-organized research notes.
        """

    async def research(
        self,
        news_item: RawNewsItem,
        topics: List[str],
    ) -> str | None:
        """Run the ReAct agent to research topics.

        Returns research notes as a string, or None on failure.
        """
        if not topics:
            logger.error("Empty topics provided")
            return None

        user_message = self._build_user_message(news_item, topics)

        try:
            logger.debug(f"Starting research agent with {len(topics)} topics...")
            result = await self.agent.ainvoke(
                {"messages": [HumanMessage(content=user_message)]},
                config={"recursion_limit": self.RECURSION_LIMIT},
            )
            final_message = result["messages"][-1]
            return final_message.content

        except Exception as e:
            logger.error(f"Research agent failed: {e}")
            return None
