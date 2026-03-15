import os
from config import logger, configuration
import psutil
import asyncio
import json
from typing import Dict, Any
from concurrent.futures import ProcessPoolExecutor
from backend.core.redis import tracker
from backend.models.data import NewsItem
from backend.utils.music import get_music
from backend.utils.TTS import TTSGenerator

from .worker import execute_production_worker


class MultimediaManager:
    """
    Handles the actual production process of news content, including video and audio generation.
    Manages resource-intensive tasks using process pool executor.
    
    Attributes:
        executor (ProcessPoolExecutor): Executor for running tasks.
        timeout (int): Timeout for executor tasks.
    """
    
    def __init__(
        self, 
        max_workers: int = (os.cpu_count() // 8) or 2, # use quarter of the available cores
        timeout: int = 600 # 10 minutes
    ) -> None:  
        self.executor: ProcessPoolExecutor = ProcessPoolExecutor(max_workers=max_workers)
        voices = configuration["TTS"]["generator"]["voices"]
        self.speech_generators = {
            depth: TTSGenerator(voice=voice_id)
            for depth, voice_id in voices.items()
        }
        self._timeout: int = timeout
        self._max_workers: int = max_workers
        
    async def produce_news(self, news_id: str, news_data: NewsItem) -> Dict[str, Any] | None:
        """Main production method that handles the production pipeline."""

        if not news_id or not news_data:
            raise ValueError("Invalid news data or news_id.")
            
        # Add resource check before execution
        if len(self.executor._processes) >= self._max_workers:
            logger.warning(f"Process pool at capacity ({self._max_workers} workers)")
            await asyncio.sleep(self._timeout/2)  # Backpressure mechanism
            return None
        
        # log start
        news_depth = news_data.depth.lower()
        await tracker.log(str(news_data.raw_id), f"Multimedia manager has started the production.")
        
        # Get music path
        music_path = get_music(news_depth)
        
        # Generate audio and subtitle first (voice selected by depth)
        generator = self.speech_generators.get(news_depth, self.speech_generators["flash"])
        audio_path, subtitle_path = await generator.generate(news_data.script)
        
        loop = asyncio.get_running_loop()
        # Submit the task to the executor and get a Future object
        future = loop.run_in_executor(
            self.executor,
            execute_production_worker,
            news_depth,
            audio_path,
            subtitle_path,
            music_path,
        )
        
        try:
            # Wait for the future to complete with a timeout
            result = await asyncio.wait_for(future, timeout=self._timeout)

            # Attach raw TTS audio path for R2 upload (synced with subtitles)
            if result:
                result["tts_audio_path"] = audio_path

            # track the production result
            await tracker.log(str(news_data.raw_id), f"{news_depth.capitalize()} news production completed: {json.dumps(result, indent=2)}")

            return result
        
        except asyncio.TimeoutError:
            # Just cancel this specific future instead of resetting the whole executor
            future.cancel()
            logger.error(f"Production timeout for {news_depth} after {self._timeout} seconds")
            
            return None
        
        except Exception as e:
            logger.error(f"Production error for news_id {news_id}: {e}")
            return None

    async def shutdown(self):
        """Safe shutdown with proper process termination"""
        try:
            if hasattr(self, 'executor'):
                self.executor.shutdown(wait=True, cancel_futures=True)
                self.cleanup_process()
        except Exception as e:
            logger.error(f"Shutdown failed: {e}")
            raise
    
    def cleanup_process(self) -> None:
        """ Cleanup child processes """
        current_proc = psutil.Process()
        for child in current_proc.children(recursive=True):
            try:
                child.kill()
            except psutil.NoSuchProcess:
                continue