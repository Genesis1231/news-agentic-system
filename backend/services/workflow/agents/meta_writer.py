from pydantic import BaseModel
from config import logger
from typing import List, Dict, Any
from datetime import datetime, timezone
from langchain_core.prompts import ChatPromptTemplate

from backend.utils.prompt import load_prompt
from backend.models.data import NewsItem
from backend.core.agent import BaseAgent


class MetaWriter(BaseAgent):
    """
    An agent that writes meta information on different platforms.
    
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
        output_format: BaseModel | None = None
    )-> None:
        super().__init__(
            config = {
                "name": "MetaWriter Agent",
                "platform": platform,
                "model_name": model_name,
                "base_url": base_url,
                "temperature": temperature,
                "output_format": output_format
            }
        )
        

    def build_meta_prompt(self, news_item: NewsItem) -> str:
        """Get the user prompt for the meta writer agent"""
        
        user_prompt = f"""
            Now proceed to generate meta information for the following content:
            <news_content>
                {news_item.script}
            </news_content>
            
            Output strictly in provided JSON format schema:
        """
        return user_prompt
    
    async def generate(
        self,
        news_item: NewsItem, 
        media_name: str
    ) -> Dict[str, Any] | None:
        """Main response function that build the prompt and get response from LLM"""
        
        # load the system prompt and user prompt
        system_prompt = load_prompt(f"create_meta").format(
            media_name=media_name.title(),
            current_year=datetime.now(timezone.utc).year
        )
        user_prompt = self.build_meta_prompt(news_item)
        
        prompt = ChatPromptTemplate([
            ("system", system_prompt),
            ("user", user_prompt),
        ])
        
        try:
            logger.debug(f"Generating meta for {media_name}...")
            response = await self._invoke(prompt.format_messages())
            
            return response.model_dump()
        
        except Exception as e:
            logger.error(f"Failed to create meta for {media_name}: {e}")
            return None

