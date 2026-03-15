from config import logger
import re
from typing import Dict, Any

from langchain_core.prompts import ChatPromptTemplate

from backend.core.agent import BaseAgent
from backend.models.schema.evaluation import Evaluation
from backend.models.data import RawNewsItem
from backend.utils.prompt import load_prompt


class NewsEditor(BaseAgent):
    """
    A LLM agent that evaluates potential news content.
    
    Args:
        platform (str): The identifier for the selected LLM platform (e.g., "OLLAMA", "GROQ").
        model_name (str): The name of the LLM model (e.g., "llama3.1:70b").
        base_url (str): The base URL for API connections, defaults to localhost for local models.
        temperature (float): The temperature for the LLM model.
        task (str): The task for the agent, either "Evaluation" or "Review".

    """
    
    def __init__(
        self,
        platform: str,
        model_name: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
        task: str = "Evaluation"
    )-> None:
        self._platform = platform
        self._output_format = Evaluation if task.lower() == "evaluation" else None
        
        super().__init__(
            config = {
                "name": f"{task} Agent",
                "platform": platform,
                "model_name": model_name,
                "base_url": base_url,
                "temperature": temperature,
                "output_format": self._output_format
            }
        )

    def build_evaluate_prompt(self, news_item: RawNewsItem) -> str:
        """Build the user prompt for the evaluation agent"""
                
        return f"""
            Now, proceed and output the evaluation strictly in provided JSON schema:
        """
    
    def build_summarize_prompt(self, draft_script: str) -> str:
        """Build the user prompt for the summarize agent"""
        
        summarize_prompt = f"""
            Now, proceed to summarize the draft script:
            <script>
                {draft_script}
            </script>
            
        """
        return summarize_prompt
    
    
    async def evaluate(self, news_item: RawNewsItem) -> Dict[str, Any] | None:
        """Main response function that build the prompt and get response from LLM"""
        
        # load the system prompt and user prompt
        system_prompt = load_prompt("evaluate_content").format(content=news_item.composed_content)
        user_prompt = self.build_evaluate_prompt(news_item)
            
        prompt = ChatPromptTemplate([
            ("system", system_prompt),
            ("user", user_prompt),
        ])
        
        try:
            logger.debug(f"Evaluating content from {news_item.author_idname}")
            response = await self._invoke(prompt.format_messages())

            # serialize the response
            response = response.model_dump()
            response["platform"] = self._platform
            
            return response
            
        except Exception as e:
            logger.error(f"{self._platform} failed to evaluate news content: {e}")
            return None
        
    
    async def summarize(self, script: str) -> str | None:
        """Generate a concise 2-3 sentence summary from the approved script for the news feed."""

        if not script:
            logger.warning("No script to summarize.")
            return None

        system_prompt = load_prompt("summarize_script").format(script=script)
        user_prompt = self.build_summarize_prompt(script)

        prompt = ChatPromptTemplate([
            ("system", system_prompt),
            ("user", user_prompt),
        ])

        try:
            logger.debug("Summarizing script for news feed...")
            response = await self._invoke(prompt.format_messages())
            return re.sub(r"<think>.*?</think>", "", response.content, flags=re.DOTALL).strip()

        except Exception as e:
            logger.error(f"{self._platform} failed to summarize script: {e}")
            return None