from config import logger, configuration
from typing import Dict, Callable, Tuple

class TTSGenerator:
    """
    The Speaker class is responsible for initializing and managing the text-to-speech models.
    It provides methods to create different speaker models and speak the given text.

    Attributes:
        model_name (str): The selected speaker model name.
        model_factory (dict): A dictionary mapping model names to their corresponding creation methods.
        model: The initialized speaker model instance.
    """
    
    def __init__(self, voice: str | None = None):
        self.config: Dict = configuration["TTS"]
        self._platform: str = self.config["generator"]["platform"].upper()
        self._model_name: str = self.config["generator"]["model"]
        self._media_folder: str = self.config["media_folder"]
        self._language: str = self.config["generator"]["language"]
        self._voice: str = voice or self.config["generator"]["voice"]
        self.model = self._initialize_model()
        
        logger.debug(f"TTS Generator: {self._platform} is ready.")


    def _initialize_model(self):
        model_factory = self._get_model_factory()
        model = model_factory.get(self._platform)
        if model is None:
            raise ValueError(f"Error: Model {self._platform} is not supported.")
        
        return model()
        
    def _get_model_factory(self) -> Dict[str, Callable]:
        return {
            # "COQUI" : self._create_coqui_model,
            "ELEVENLABS" : self._create_elevenlabs_model,
        }
    
    # def _create_coqui_model(self):
    #     from .model_coqui import CoquiSpeaker
        
    #     try:
    #         return CoquiSpeaker(language=self._language)
    #     except Exception as e:
    #         raise Exception(f"Error: Failed to initialize Coqui TTS model {str(e)} ")

    def _create_elevenlabs_model(self):
        from .model_elevenlabs import ElevenLabsClient
        
        try:
            return ElevenLabsClient(
                model_name=self._model_name,
                voice=self._voice
            )
        except Exception as e:
            raise Exception(f"Error: Failed to initialize ElevenLabs model {str(e)} ")

    async def generate(self, text: str) -> Tuple[str, str]:
        """ Generate audio from text and save it to the media folder """
        
        if not text:
            logger.error("Failed to generate audio. Text is empty.")
            return None, None
        
        return await self.model.generate(text, self._media_folder)
    
        
        