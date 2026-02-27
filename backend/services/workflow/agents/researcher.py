from config import logger
from typing import List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate

from backend.models.data import RawNewsItem
from backend.utils.prompt import load_prompt
from backend.models.schema.outputs import ResearchOutput

from backend.core.agent import BaseAgent


class NewsResearcher(BaseAgent):
    """
    A LLM agent that conducts research on news content.
    
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
        temperature: float = 0.0
    )-> None:
        super().__init__(
            config = {
                "name": "Research Agent",
                "platform": platform,
                "model_name": model_name,
                "base_url": base_url,
                "temperature": temperature,
                "output_format": ResearchOutput
            }
        )
    
    def build_user_prompt(self, news_item: RawNewsItem, research_items: List[str]) -> str:
        """Get the user prompt for the research agent"""
            
        # build the user prompt 
        research_items = "\n    - ".join(research_items)
        user_prompt = f"""
            Here is the related content:
            <content>
                Media: {news_item.source_name}
                Author: {news_item.author.name}({news_item.author.idname})
                Time: {news_item.timestamp}
                ----------------------------------
                {news_item.text}
            </content>
        
            Now, proceed to generate research plans for the following:
            <research_outlines>
                - {research_items}
            </research_outlines>
        
            Output strictly in provided JSON schema.
        """
        return user_prompt 

        
    async def research(self, news_item: RawNewsItem, research_outlines: List[str]) -> Dict[str, Any] | None:
        """Main response function that build the prompt and get response from LLM"""
        
        if not research_outlines:
            logger.error("Empty research_outlines provided")
            return None
        
        # load the system prompt and user prompt
        system_prompt = load_prompt("research_content") 
        user_prompt = self.build_user_prompt(news_item, research_outlines)
        
        prompt = ChatPromptTemplate([
            ("system", system_prompt),
            ("user", user_prompt),
        ])
        
        try:
            logger.debug(f"Generating research queries...")
            response: ResearchOutput = await self._invoke(prompt.format_messages())
            
            return response.model_dump()
        
        except Exception as e:
            logger.error(f"Failed to create research plans: {e}")
            return None