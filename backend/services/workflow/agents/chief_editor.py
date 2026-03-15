from config import logger
from typing import Dict, Any, List

from langchain_core.prompts import ChatPromptTemplate

from backend.core.agent import BaseAgent
from backend.models.schema.review import Review
from backend.models.data import RawNewsItem
from backend.utils.prompt import load_prompt


class ChiefEditor(BaseAgent):
    """
    A LLM agent that evaluates potential news content.
    
    Attributes:
        platform (str): The identifier for the selected LLM platform (e.g., "OLLAMA", "GROQ").
        model_name (str): The name of the LLM model (e.g., "llama3.1:70b").
        base_url (str): The base URL for API connections, defaults to localhost for local models.
        temperature (float): The temperature for the LLM model.
    """
    
    def __init__(
        self,
        platform: str,
        model_name: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
    )-> None:

        super().__init__(
            config = {
                "name": "Chief Editor",
                "platform": platform,
                "model_name": model_name,
                "base_url": base_url,
                "temperature": temperature,
                "output_format": Review
            }
        )
    
    def build_revision_prompt(self) -> str:
        """Build the user prompt for the revision agent"""
        
        review_prompt = f"""
            
            Output strictly in provided JSON format schema:
        """
        return review_prompt
    
    async def review(
        self, 
        news_item: RawNewsItem, 
        draft: str, 
    ) -> Dict[str, Any] | None:
        """Main response function that build the prompt and get response from LLM"""
        
        if not draft:
            logger.warning("No draft to review. ")
            return None
        
        # load the system prompt and user prompt
        system_prompt = load_prompt("finalize_review").format(
            content=news_item.composed_content,
            draft=draft
        )
        user_prompt = self.build_revision_prompt()
        
        prompt = ChatPromptTemplate([
            ("system", system_prompt),
            ("user", user_prompt),
        ])
        
        try:
            logger.debug(f"Reviewing the script...")
            response = await self._invoke(prompt.format_messages())

            # serialize the response
            return response.model_dump()
            
        except Exception as e:
            logger.error(f"Chief Editor failed to finalize news script revision: {e}")
            return None