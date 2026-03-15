import json
from config import logger, configuration
from typing import Dict, Any

from backend.core.redis import tracker
from backend.models.data import NewsItem
from backend.utils.TTS import TTSGenerator


class MultimediaManager:
    """Handles TTS generation (script to speech + subtitles)."""

    def __init__(self) -> None:
        voices = configuration["TTS"]["generator"]["voices"]
        self.speech_generators = {
            depth: TTSGenerator(voice=voice_id)
            for depth, voice_id in voices.items()
        }

    async def produce_news(self, news_id: str, news_data: NewsItem) -> Dict[str, Any] | None:
        """Generate TTS audio and subtitles for a news item."""

        news_depth = news_data.depth.lower()
        await tracker.log(str(news_data.raw_id), "Multimedia production started.")

        # TTS (async ElevenLabs API call)
        generator = self.speech_generators.get(news_depth, self.speech_generators["flash"])
        result = await generator.generate(news_data.script)

        if not result or not result[0]:
            logger.error(f"TTS generation failed for news (ID:{news_id})")
            return None

        audio_path, _ = result

        await tracker.log(
            str(news_data.raw_id),
            f"{news_depth.capitalize()} production completed: {audio_path}"
        )
        return {"audio_path": str(audio_path)}

    async def shutdown(self) -> None:
        pass
