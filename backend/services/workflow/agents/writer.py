from config import logger
from typing import List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate

from backend.utils.prompt import load_prompt
from backend.models.schema.outputs import ScriptOutput
from backend.models.schema.enums import NewsDepth
from backend.models.data import RawNewsItem
from backend.core.agent import BaseAgent


class NewsWriter(BaseAgent):
    """
    A LLM agent that conducts writing on news content.
    
    Attributes:
        platform (str): The identifier for the selected LLM platform (e.g., "OLLAMA", "GROQ").
        model_name (str): The name of the LLM model (e.g., "llama3.1:70b").
        base_url (str): The base URL for API connections, defaults to localhost for local models.
        temperature (float): The temperature for the LLM model.
    """
    
    def __init__(
        self,
        platform: str = "XAI",
        model_name: str | None = "grok-4",
        base_url: str | None = None,
        temperature: float | None = None,
    )-> None:
        super().__init__(
            config = {
                "name": "Writing Agent",
                "platform": platform,
                "model_name": model_name,
                "base_url": base_url,
                "temperature": temperature,
                "output_format": ScriptOutput
            }
        )
        
    def build_content(
        self, 
        news_item: RawNewsItem, 
        research_notes: str | None = None, 
        editorial_notes: List[str] | None = None
    ) -> str:
        """Get the content for the research agent"""
        
        # build the content 
        content = f"""
            <source_content>
                {news_item.composed_content}
            </source_content>
        """

        if editorial_notes:
            editorial_notes = "\n".join(editorial_notes)
            content += f"""
                Draw inspiration from these editorial suggestions and adapt them creatively in the writing process:
                <editorial_suggestions>
                    {editorial_notes}
                </editorial_suggestions>
            """

        if research_notes:
            content += f"""
                Here are the research notes that could assist the writing process:
                <research_notes>
                    {research_notes}
                </research_notes>
            """
        return content

    def build_draft_prompt(self, editorial_notes: List[str]) -> str:
        """Get the user prompt for the research agent"""
                
        # build the user prompt 
        user_prompt = f"""
        
            Now craft the news script in provided JSON schema.
        """
        return user_prompt
    
    
    def build_revise_prompt(self, original_script: str, revision_notes: List[str]) -> str:
        """Get the user prompt for the research agent"""
        
        revision_notes = "\n".join(revision_notes)
                
        # build the user prompt 
        user_prompt = f"""
            Here is the previous draft script:
            <draft_script>
                {original_script}
            </draft_script>
            
            Here are the revision suggestions to improve the script:
            <revision_notes>
                {revision_notes}
            </revision_notes>
            
            Now craft a revised script in provided JSON schema.
        """
        return user_prompt
    
    async def write(
        self,
        news_item: RawNewsItem, 
        research_notes: str,
        editorial_notes: List[str],
        depth: str
    ) -> Dict[str, Any] | None:
        """Main response function that build the prompt and get response from LLM"""
        
        # load the system prompt and user prompt
        content = self.build_content(news_item, research_notes, editorial_notes)
        system_prompt = load_prompt(f"create_news_{depth.lower()}").format(content=content)
        user_prompt = self.build_draft_prompt(editorial_notes)
        
        prompt = ChatPromptTemplate([
            ("system", system_prompt),
            ("user", user_prompt),
        ])
        
        try:
            logger.debug(f"Generating script...")
            response = await self._invoke(prompt.format_messages())
            
            return response.model_dump()
        
        except Exception as e:
            logger.error(f"Failed to create script: {e}")
            return None


    async def revise(
        self,
        depth: str,
        news_item: RawNewsItem,
        research_notes: str,
        original_script: str,
        revision_notes: List[str]
    ) -> Dict[str, Any] | None:
        """Main response function that build the prompt and get response from LLM"""
        
        # load the system prompt and user prompt
        content = self.build_content(news_item, research_notes)
        system_prompt = load_prompt(f"create_news_{depth.lower()}").format(content=content)
        user_prompt = self.build_revise_prompt(original_script, revision_notes)
        
        prompt = ChatPromptTemplate([
            ("system", system_prompt),
            ("user", user_prompt),
        ])
        
        try:
            logger.debug(f"Revising script...")
            response = await self._invoke(prompt.format_messages())
            
            return response.model_dump()
        
        except Exception as e:
            logger.error(f"Failed to create script: {e}")
            return None