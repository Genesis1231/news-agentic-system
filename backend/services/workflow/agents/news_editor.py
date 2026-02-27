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
    
    def build_review_prompt(self, draft_script: str) -> str:
        """Build the user prompt for the review agent"""
        
        review_prompt = f"""
            Now, proceed to review the draft script:
            <script>
                {draft_script}
            </script>
            
        """
        return review_prompt
    
    
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
        
    
    async def review(
        self, 
        news_item: RawNewsItem, 
        draft: str,
        depth: str
    ) -> Dict[str, Any] | None:
        """Main response function that build the prompt and get response from LLM"""
        
        if not draft:
            logger.warning("No draft to review. ")
            return None
        
        # load the system prompt and user prompt
        system_prompt = load_prompt("review_script").format(content=news_item.composed_content)
        user_prompt = self.build_review_prompt(draft)
        
        prompt = ChatPromptTemplate([
            ("system", system_prompt),
            ("user", user_prompt),
        ])
        
        try:
            logger.debug(f"Reviewing news script...")
            response = await self._invoke(prompt.format_messages())
            
            return re.sub(r"<think>.*?</think>", "", response.content, flags=re.DOTALL)
            
        except Exception as e:
            logger.error(f"{self._platform} failed to evaluate news content: {e}")
            return None