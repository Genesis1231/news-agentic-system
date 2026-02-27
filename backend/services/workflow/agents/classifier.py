from config import logger
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any

from backend.models.schema.classification import Classification
from backend.models.data import RawNewsItem
from backend.utils.prompt import load_prompt

from backend.core.agent import BaseAgent


class ClassificationAgent(BaseAgent):
    """
    A LLM agent that classifies news content.
    
    Args:
        platform (str): The identifier for the selected LLM platform (e.g., "OLLAMA", "GROQ").
        model_name (str): The name of the LLM model (e.g., "llama3.1:70b").
        base_url (str): The base URL for API connections, defaults to localhost for local models. 
        temperature (float): The temperature for the LLM model.
        
    Returns:
        Dict[str, Any]: The classification result.
    """
    
    def __init__(
        self,
        platform: str = "ollama",
        model_name: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
    )-> None:
        super().__init__(
            config = {
                "name": "Classification Agent",
                "platform": platform,
                "model_name": model_name,
                "base_url": base_url,
                "temperature": temperature,
                "output_format": Classification
            }
        )
    
    def build_user_prompt(self, news_item: RawNewsItem) -> str:
        """Get the user prompt for the classification agent"""

        return f"""
            Now, proceed to classify the following content:
            
            <content>
                {news_item.composed_content}
            </content>
        
        Output strictly in provided JSON schema:
        """
    
    
    async def classify(self, news_item: RawNewsItem) -> Dict[str, Any] | None:
        """Main response function that build the prompt and get response from LLM"""
        
        # load the system prompt and user prompt
        system_prompt = load_prompt("classify_content")
        user_prompt = self.build_user_prompt(news_item)
        
        prompt = ChatPromptTemplate([
            ("system", system_prompt),
            ("user", user_prompt),
        ])
        
        try:
            logger.debug(f"Classifying potential news from {news_item.author_idname}")
            response = await self._invoke(prompt.format_messages())
            return response.model_dump()

        except Exception as e:
            logger.error(f"Failed to classify news content: {e}")
            return None
