from config import logger
from typing import List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate

from backend.utils.prompt import load_prompt
from backend.models.schema.outputs import ResearchNoteOutput
from backend.core.agent import BaseAgent


class ResearchAssistant(BaseAgent):
    """
    A LLM agent that conducts curation on news content.
    
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
                "name": "Curation Agent",
                "platform": platform,
                "model_name": model_name,
                "base_url": base_url,
                "temperature": temperature,
                "output_format": ResearchNoteOutput
            }
        )
    
    def build_user_prompt(self, web_content: List[str]) -> str:
        """Get the user prompt for the research agent"""

        # build the user prompt 
        scraped_content = "\n\n #####".join(web_content)
        print(scraped_content)
        user_prompt = f"""
            Now, proceed to generate research notes from the following:
            <scraped_content>
                {scraped_content}
            </scraped_content>
        
            Output the research notes strictly in provided JSON schema.
        """
        return user_prompt
        
    async def summarize(self, web_content: List[str], research_outlines: List[str]) -> Dict[str, Any] | None:
        """Main response function that build the prompt and get response from LLM"""
        
        if not web_content or not research_outlines:
            logger.error("Empty web_content or research_outlines provided. ")
            return None
    
        # load the system prompt and user prompt
        research_outlines = "\n    - ".join(research_outlines)
        system_prompt = load_prompt("curate_research").format(research_outlines=research_outlines)
        user_prompt = self.build_user_prompt(web_content)
        
        prompt = ChatPromptTemplate([
            ("system", system_prompt),
            ("user", user_prompt),
        ])
        
        try:
            logger.debug(f"Summarizing research data...")
            response: ResearchNoteOutput = await self._invoke(prompt.format_messages())
            
            return response.model_dump()
        
        except Exception as e:
            logger.error(f"Failed to summarize research content: {e}")
            return None
        
    async def interpret(self, content: str) -> str | None:
        """Read the content and provide a short summary"""
        
        if not content:
            logger.error("Empty content provided. ")
            return None
            
        # load the system prompt and user prompt
        system_prompt = load_prompt("interpret_content")
        user_prompt = self.build_user_prompt(content)
        
        prompt = ChatPromptTemplate([
            ("system", system_prompt),
            ("user", user_prompt),
        ])
        
        try:
            logger.debug(f"Interpreting content...")
            response: str = await self._invoke(prompt.format_messages())
            
            return response
        except Exception as e:
            logger.error(f"Failed to interpret content: {e}")
            return None