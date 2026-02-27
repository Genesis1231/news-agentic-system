from config import logger
from typing import Dict
import asyncio
from functools import lru_cache
from pathlib import Path

from .producer_flash.flash_producer import FlashNewsProducer
from backend.core.producer import BaseProducer

PRODUCER_MAP = {
    "flash": FlashNewsProducer,
}

@lru_cache(maxsize=8)
def select_producer(depth: str) -> BaseProducer | None:
    """LRU cached producer instances."""
    
    producer = PRODUCER_MAP.get(depth)
    if not producer:
        return None
    
    return producer()

# Module-level function for process pool
def execute_production_worker(
    depth: str,
    audio_path: str,
    subtitle_path: str,
    music_path: str,
) -> Dict[str, str] | None:
    """Synchronous worker function for process pool (must be module-level)"""
    
    # # Defensive check against async code
    # if asyncio.get_event_loop().is_running():
    #     raise RuntimeError("Async context detected in worker process")

    # check if all files exist in the file system
    if not Path(audio_path).exists():
        logger.error(f"Missing audio file: {audio_path}")
        raise FileNotFoundError("Missing audio file")
    
    if not Path(subtitle_path).exists():
        logger.error(f"Missing subtitle file: {subtitle_path}")
        raise FileNotFoundError("Missing subtitle file")
    
    if not Path(music_path).exists():
        logger.error(f"Missing music file: {music_path}")
        raise FileNotFoundError("Missing music file")
    
    try:
        if not (producer := select_producer(depth)):
            logger.error(f"Invalid depth: {depth}, could not load a producer.")
            return None
            
        return producer.produce(
            speech_path=str(audio_path),
            music_path=str(music_path),
            subtitle_path=str(subtitle_path)
        )
        
    except Exception as e:
        logger.error(f"Production worker failed: {e}")
        return None