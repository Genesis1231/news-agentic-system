from typing import  Any, Dict, List
from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from langchain_core.language_models import BaseLanguageModel

from .factory import ModelFactory
from config import logger


class BaseAgent:
    """Base agent class with common LLM functionality and retry mechanisms.
    
    Attributes:
        model_config (Dict[str, Any]): Configuration for the LLM model
        llm (BaseLanguageModel): The initialized language model instance
        _initialized (bool): Whether the agent has been initialized
    """
    
    def __init__(self, config: Dict[str, Any]) -> None:
        self.model_config: Dict[str, Any] = config
        self._initialized: bool = False
        
        self.llm: BaseLanguageModel | None = None
        self.name: str = config.pop("name", "Default Agent")
        self.tools: List[Any] = config.pop("tools", [])
        self.output_format: str = config.pop("output_format", "")
        
        #initialize the agent
        self._initialize_agent(config)

    def _initialize_agent(self, config: Dict[str, Any]) -> None:
        """Initialize the agent's LLM model and bind tools or structured output"""
        
        model_factory = ModelFactory()
        self.llm = model_factory.get_model(**config)
        
        # bind tools if provided or bind structured output
        if self.tools:
            self.llm = self.llm.bind_tools(self.tools)
            logger.debug(f"Initialized {self.name} with tools: {self.model_config['platform']} {self.model_config['model_name']}")
        elif self.output_format:
            self.llm = self.llm.with_structured_output(self.output_format, method="function_calling")
            logger.debug(f"Initialized {self.name} with structured output: {self.model_config['platform']} {self.model_config['model_name']}")
        else:
            logger.warning(f"Initialized {self.name} without tools or structured output.")
        
        self._initialized = True
    
    async def _fallback(self) -> None:
        """Switch to a fallback model using the factory's fallback logic"""
        
        # Mark the configuration appropriately for fallback handling
        self.model_config["requires_vision"] = (self.name.lower() == "descriptor")
        
        # Use the factory to get a fallback model
        model_factory = ModelFactory()
        try:
            # The factory will handle fallback logic and return an appropriate model
            self.llm = model_factory._fallback_model(self.model_config)
            
            # Restore tool bindings or structured output format
            if self.tools:
                self.llm = self.llm.bind_tools(self.tools)
            elif self.output_format:
                self.llm = self.llm.with_structured_output(self.output_format, method="function_calling")
                
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize fallback model: {str(e)}")
            self._initialized = False
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((Exception,)),
    )
    async def _invoke(self, messages: Any) -> Any:
        """Invoke the LLM with retry logic"""
        
        if not self._initialized:
            logger.warning(f"{self.name} not initialized. Initializing now.")
            self._initialize_agent(**self.model_config)
            
        try:
            return await self.llm.ainvoke(messages)
        
        except ValidationError as e:
            logger.error(f"{self.name}: {self.model_config['platform']} Output validation error: {e} - Try again.")
            raise
        except Exception as e:
            logger.error(f"{self.name}: {self.model_config['platform']} Failed to invoke LLM. Error: {e} ")
            await self._fallback()
            raise  # This will trigger the retry decorator
        
