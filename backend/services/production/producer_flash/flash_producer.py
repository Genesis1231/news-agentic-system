from config import logger
from typing import Dict, Tuple

from .animation import create_particle_video
from backend.core.producer import BaseProducer

class FlashNewsProducer(BaseProducer):
    """
    Audio mixer for combining speech and background music with visual elements.
    Inherits from BaseProducer for core multimedia functionality.
    
    Attributes:
        resolution: Video resolution (width, height)
        fps: Frames per second for video
        bg_music_volume: Background music volume level (0.0-1.0)
        font_path: Path to TTF font file for text overlay
        breathing_time: Padding duration at clip start/end (seconds)
    """
    
    def __init__(
        self,
        resolution: Tuple[int, int] = (720, 1280),
        fps: int = 30,
        bg_music_volume: float = 0.05,
        font_path: str | None = None,
        breathing_time: float = 1.0
    ) -> None:
        """Initialize AudioMixer with configuration settings."""
        
        super().__init__(
            resolution=resolution,
            fps=fps,
            bg_music_volume=bg_music_volume,
            font_path=font_path,
            breathing_time=breathing_time
        )
        
        logger.debug(f"Initialized FlashNewsProducer with resolution({resolution}).")

    def produce(
        self,
        speech_path: str,
        music_path: str,
        subtitle_path: str,
    ) -> Dict[str, str] | None:
        """ Produce a FlashNews video."""
 
        try:
            # Load media clips
            speech_clip = self._load_media(speech_path)
            music_clip = self._load_media(music_path)
            subtitle_clips = self._load_subtitles(subtitle_path)
            
            # Create particle animation
            particle_clip = create_particle_video(speech_path, speech_clip.duration)

            if (not music_clip or 
                not speech_clip or 
                not subtitle_clips or 
                not particle_clip):
                logger.error("Missing required media clips for FlashNews production.")
                return None
            
            # Produce final output using base class method
            return self._produce(
                speech_clip=speech_clip,
                video_clips=particle_clip,
                subtitle_clips=subtitle_clips,
                music_clip=music_clip,
            )
            
        except Exception as e:
            logger.error(f"Error during FlashNews production: {str(e)}")
            return None


