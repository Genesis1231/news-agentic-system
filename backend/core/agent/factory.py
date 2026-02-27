import os
from config import logger
from langchain_core.language_models import BaseLanguageModel
from typing import Dict, Callable, Any
from functools import lru_cache, partial

class ModelFactory:
    """
    A factory class for creating instances of language models.
    """
    def __init__(self):
        self._initialized: bool = False
    
    def _get_model_factory(self, config: Dict[str, Any]) -> Dict[str, Callable[[], BaseLanguageModel]]:
        """ Get the model factory for creating LLM models. """
       
        return {
        "GROQ" : partial(self.create_groq_model, config),
        "XAI": partial(self.create_xai_model, config),
        "ANTHROPIC": partial(self.create_anthropic_model, config),
        "MISTRAL":  partial(self.create_mistral_model, config),
        "GOOGLE": partial(self.create_google_model, config),
        "DEEPSEEK": partial(self.create_deepseek_model, config),
        "OPENAI" : partial(self.create_openai_model, config),
        "OLLAMA" : partial(self.create_ollama_model, config),
        "PERPLEXITY" : partial(self.create_perplexity_model, config),
    }

    def _fallback_model(self, config: Dict[str, Any]) -> BaseLanguageModel:
        """ Fallback to a different model if the specified model is not available.
        
        Args:
            config: The current model configuration that failed
            
        Returns:
            A fallback model based on the provided configuration
        """
        # Get the agent type (default or vision)
        requires_vision = config.get("requires_vision", False)
        
        # Primary fallback path - always try Ollama first
        primary_fallback = {
            "platform": "Google",
            "model_name": "gemini-2.5-flash"
        }
        
        # Secondary fallback path - try Groq if not coming from Groq
        secondary_fallback = None
        if config.get("platform", "").lower() != "groq":
            secondary_fallback = {
                "platform": "groq",
                "model_name": "meta-llama/llama-4-scout-17b-16e-instruct" if requires_vision else "deepseek-r1-distill-llama-70b"
            }
        
        # First try the primary fallback
        fallback_config = config.copy()  # Preserve original config attributes
        fallback_config.update(primary_fallback)
        
        logger.debug(f"Primary fallback to {fallback_config['platform']} model: {fallback_config['model_name']}")
        
        try:
            return self.get_model(**fallback_config)
        except Exception as e:
            # If primary fallback failed and we have a secondary option, try it
            if secondary_fallback and config.get("platform", "").upper() != "GROQ":
                logger.debug(f"Primary fallback failed: {str(e)}. Trying secondary fallback.")
                fallback_config = config.copy()
                fallback_config.update(secondary_fallback)
                
                logger.debug(f"Secondary fallback to {fallback_config['platform']} model: {fallback_config['model_name']}")
                
                try:
                    return self.get_model(**fallback_config)
                except Exception as e2:
                    logger.error(f"All fallbacks failed. Primary error: {str(e)}, Secondary error: {str(e2)}")
                    raise Exception(f"All fallback models failed. Cannot proceed.")
            else:
                # No secondary fallback or already tried Groq
                logger.error(f"Fallback failed and no alternative available: {str(e)}")
                raise Exception(f"Fallback model failed. Cannot proceed.")
    
    @lru_cache(maxsize=10)
    def get_model(self, **config: Dict[str, Any]) -> BaseLanguageModel:
        """Get an instance of the specified LLM model."""
        
        if platform := config.get("platform"):
            platform = platform.upper()
        else:
            raise ValueError("Platform is required")
        
        factory = self._get_model_factory(config)
        if platform not in factory:
            raise ValueError(f"Unsupported model platform: {platform}")  
        
        return factory[platform]()
    
    def create_groq_model(self, config: Dict[str, Any]) -> BaseLanguageModel:
        
        from langchain_groq import ChatGroq
        
        model_name = config.get("model_name") or "deepseek-r1-distill-llama-70b"
        temperature = config.get("temperature") or 0.8
        
        try:
            return ChatGroq(model_name=model_name, 
                            temperature=temperature, 
                            max_tokens=2048)
            
        except Exception as e:
            logger.error(f"Error: Failed to initialize Groq model: {str(e)}.")
            return self._fallback_model(config)
        
    def create_ollama_model(self, config: Dict[str, Any]) -> BaseLanguageModel:
        
        from langchain_ollama import ChatOllama
        
        base_url = config.get("base_url") or "http://localhost:11434"
        model_name = config.get("model_name") or "llama3.3"
        temperature = config.get("temperature") or 0.6
        
        try:
            model = ChatOllama(
                base_url=base_url,
                model=model_name,
                keep_alive="1h",
                temperature=temperature,
                format="json"
            )
            # model.invoke(" ") #preload the model
            
        except Exception as e:
            raise Exception(f"Error: Failed to initialize Ollama model: {str(e)}")
        
        return model
        
    def create_openai_model(self, config: Dict[str, Any]) -> BaseLanguageModel:
        
        from langchain_openai import ChatOpenAI
        
        model_name = config.get("model_name") or "gpt-4o"
        temperature = config.get("temperature") or 0.8
        
        try:
            return ChatOpenAI(
                model_name=model_name, 
                temperature=temperature,
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI model: {str(e)}")
            return self._fallback_model(config) # fallback to ollama

    def create_mistral_model(self, config: Dict[str, Any]) -> BaseLanguageModel:
        
        from langchain_mistralai.chat_models import ChatMistralAI
        
        model_name = config.get("model_name") or "mistral-large-latest"
        temperature = config.get("temperature") or 0.8
        
        try:
            return ChatMistralAI(
                model_name=model_name, 
                temperature=temperature
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize Mistral model: {str(e)}")
            return self._fallback_model(config) # fallback to ollama

    def create_google_model(self, config: Dict[str, Any]) -> BaseLanguageModel:
        
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        model_name = config.get("model_name") or "gemini-2.5-flash"
        temperature = config.get("temperature") or 0.9
        
        try:
            return ChatGoogleGenerativeAI(
                model=model_name, 
                temperature=temperature,
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize Google model: {str(e)}")
            return self._fallback_model(config) # fallback to ollama
        
    def create_anthropic_model(self, config: Dict[str, Any]) -> BaseLanguageModel:
        
        from langchain_anthropic import ChatAnthropic
        
        model_name = config.get("model_name") or "claude-sonnet-4-0"
        temperature = config.get("temperature") or 0.7
        
        try:
            return ChatAnthropic(
                model_name=model_name, 
                temperature=temperature,
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic model: {str(e)}")
            return self._fallback_model(config) # fallback to ollama

    def create_xai_model(self, config: Dict[str, Any]) -> BaseLanguageModel:
        
        from langchain_xai import ChatXAI
        
        model_name = config.get("model_name") or "grok-4"
        temperature = config.get("temperature") or 0.8
    
        try:
            return ChatXAI(
                model_name=model_name, 
                temperature=temperature,
            )    
            
        except Exception as e:
            logger.error(f"Failed to initialize Grok model: {str(e)}")
            return self._fallback_model(config) # fallback to ollama

    def create_deepseek_model(self, config: Dict[str, Any]) -> BaseLanguageModel:
        
        from langchain_openai import ChatOpenAI
        
        model_name = config.get("model_name") or "deepseek-chat"
        temperature = config.get("temperature") or 1
        
        try:
            api_key = os.getenv("DEEPSEEK_API_KEY")
            return ChatOpenAI(
                api_key=api_key, 
                base_url="https://api.deepseek.com", 
                model_name=model_name, 
                temperature=temperature,
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize DeepSeek model: {str(e)}")
            return self._fallback_model(config) # fallback to ollama

    def create_perplexity_model(self, config: Dict[str, Any]) -> BaseLanguageModel:
        
        from langchain_perplexity import ChatPerplexity
        
        model_name = config.get("model_name") or "sonar-pro"
        temperature = config.get("temperature") or 0.1
        
        try:
            return ChatPerplexity(
                model_name=model_name, 
                temperature=temperature,
            )
        
        except Exception as e:
            logger.error(f"Failed to initialize Perplexity model: {str(e)}")
            return self._fallback_model(config) # fallback to ollama