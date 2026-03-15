import asyncio
import json
from config import logger, configuration
from typing import Dict, Any
from concurrent.futures import ProcessPoolExecutor

from backend.core.redis import tracker
from backend.models.data import NewsItem
from backend.utils.music import get_music
from backend.utils.TTS import TTSGenerator

from .worker import execute_production_worker


class MultimediaManager:
    """Handles TTS generation (async) and video production (process pool)."""

    def __init__(self, timeout: int = 600) -> None:
        self._timeout: int = timeout
        self._max_workers: int = max((__import__('os').cpu_count() or 4) // 4, 2)
        self.executor = ProcessPoolExecutor(max_workers=self._max_workers)

        voices = configuration["TTS"]["generator"]["voices"]
        self.speech_generators = {
            depth: TTSGenerator(voice=voice_id)
            for depth, voice_id in voices.items()
        }

    async def produce_news(self, news_id: str, news_data: NewsItem) -> Dict[str, Any] | None:
        """Run TTS then video production for a news item."""

        news_depth = news_data.depth.lower()
        await tracker.log(str(news_data.raw_id), "Multimedia production started.")

        # TTS (async ElevenLabs API call)
        generator = self.speech_generators.get(news_depth, self.speech_generators["flash"])
        audio_path, subtitle_path = await generator.generate(news_data.script)

        if not audio_path or not subtitle_path:
            logger.error(f"TTS generation failed for news (ID:{news_id})")
            return None

        # Video composition (sync moviepy in process pool)
        music_path = get_music(news_depth)
        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(
            self.executor,
            execute_production_worker,
            news_depth,
            audio_path,
            subtitle_path,
            music_path,
        )

        try:
            result = await asyncio.wait_for(future, timeout=self._timeout)
            if result:
                result["tts_audio_path"] = audio_path

            await tracker.log(
                str(news_data.raw_id),
                f"{news_depth.capitalize()} production completed: {json.dumps(result, indent=2)}"
            )
            return result

        except asyncio.TimeoutError:
            future.cancel()
            logger.error(f"Production timeout for news (ID:{news_id}) after {self._timeout}s")
            return None

        except Exception as e:
            logger.error(f"Production error for news (ID:{news_id}): {e}")
            return None

    async def shutdown(self) -> None:
        self.executor.shutdown(wait=True, cancel_futures=True)
