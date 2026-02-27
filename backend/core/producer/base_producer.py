from config import logger, configuration
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
import uuid
import requests
from io import BytesIO

from moviepy import (
    AudioFileClip, 
    VideoFileClip,
    TextClip,
    ColorClip,
    CompositeVideoClip,
    CompositeAudioClip,
    concatenate_videoclips,
    concatenate_audioclips,
    AudioClip,
    VideoClip
)

from .subtitle import create_subtitle_video
from .utils import export_audio, export_video, create_looped_music

class BaseProducer:
    """
    Enhanced base class for multimedia production with subtitle support,
    flexible media loading, and composite video/audio mixing.
    
    Attributes:
        resolution: Output video dimensions (width, height)
        fps: Frames per second for video exports
        bg_music_volume: Background music volume level (0.0-1.0)
        font_path: Path to font file for text overlays
        breathing_time: Padding duration at clip start/end (seconds)
        output_dir: Directory for output files
    """
    
    def __init__(
        self,
        resolution: Tuple[int, int] = (1080, 1920),
        fps: int = 30,
        bg_music_volume: float = 0.05,
        font_path: str | None = None,
        breathing_time: float = 1.0
    ) -> None:
        self.resolution: Tuple[int, int] = resolution
        self.fps: int = fps
        self.bg_music_volume: float = bg_music_volume
        self.font_path: str | None = font_path or self.get_font()
        self.breathing_time: float = breathing_time
        self.output_dir: str = self.get_output_dir()


    def get_font(self) -> str:
        """ Get font path """
        return str(Path(__file__).parent / "fonts" / "Roboto-Bold.ttf")
    
    def get_output_dir(self) -> str:
        """ Get output directory from configuration """
        
        directory = configuration["directory"]["output"]
        folder_name = f"{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:6]}"
        output_dir = Path(__file__).parents[3] / directory / folder_name
        
        # Create the output directory if it doesn't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        return str(output_dir)
        
    def _load_media(self, source: str) -> VideoClip | AudioClip | None:
        """ Load media from URL or local file path. """
        logger.debug(f"Loading media from: {source}")
        
        # Validate file extension
        valid_video_extensions = ('.mp4', '.mov')
        valid_audio_extensions = ('.mp3', '.wav')
        
        try:
            # Handle remote files
            if source.startswith(('http://', 'https://')):
                response = requests.get(source, timeout=30)
                response.raise_for_status()
                content = BytesIO(response.content)
                
                if source.endswith(valid_video_extensions):
                    return VideoFileClip(content)
                elif source.endswith(valid_audio_extensions):
                    return AudioFileClip(content)
            
            # Handle local files
            else:
                if source.endswith(valid_video_extensions):
                    return VideoFileClip(source)
                elif source.endswith(valid_audio_extensions):
                    return AudioFileClip(source)
            
            logger.error(f"Unsupported file format. Must be one of: {valid_video_extensions + valid_audio_extensions}")
            return None
        
        except requests.RequestException as e:
            logger.error(f"Failed to download media: {e}")
            return None
        except Exception as e:
            logger.error(f"Media loading failed: {e}")
            return None

    def _load_subtitles(self, subtitle_path: str) -> List[TextClip]:
        """Generate subtitle TextClips from file."""
        return create_subtitle_video(
            subtitle_path=subtitle_path,
            font_path=self.font_path,
            screen_height=self.resolution[1]
        )

    def _create_base_layer(self, duration: float) -> ColorClip:
        """Create background layer with breathing space."""
        return ColorClip(
            size=self.resolution,
            color=(0, 0, 0),
            duration=duration
        )
        
    def _mix_audio_layers(
        self,
        duration: float,
        speech_clip: AudioClip,
        music_clip: AudioClip | None = None,
    ) -> CompositeAudioClip:
        """Combine audio components with volume adjustments."""
        
        audio_clips = [speech_clip]
        
        if music_clip:
            #adjust the volume of the background music
            music_clip = music_clip.with_volume_scaled(self.bg_music_volume)
            
            #loop the background music if it's shorter than the speech
            music_clip = create_looped_music(music_clip, duration)
            audio_clips.insert(0, music_clip)
        
        
        audio_clips = CompositeAudioClip(audio_clips)
        audio_breathing = AudioClip(lambda t: 0, duration=self.breathing_time)
        return concatenate_audioclips([audio_breathing, audio_clips])

    def _composite_video_layers(
        self,
        base_layer: ColorClip,
        video_clips: List[VideoClip],
        subtitle_clips: List[TextClip]
    ) -> CompositeVideoClip:
        """Build final video composition with proper layering."""
        
        video_layers = CompositeVideoClip([base_layer] + video_clips + subtitle_clips)
        
        # Add breathing space at the start and end of the video
        breathing_video = self._create_base_layer(self.breathing_time)
        return concatenate_videoclips([breathing_video, video_layers, breathing_video])

    def _produce(
        self,
        speech_clip: AudioClip,
        video_clips: List[VideoClip] | VideoClip,
        subtitle_clips: List[TextClip] | None = None,
        music_clip: AudioClip | None = None,
        output_name: str = "news"
    ) -> Dict[str, str] | None:
        """
        Main production pipeline that combines media components.
        
        Args:
            speech_clip: Primary narration audio track
            subtitle_path: Path to subtitle file
            music_clip: Background music track (optional)
            video_clips: List of VideoClips to composite (optional)
            output_name: Base name for output files (optional)
            
        Returns:
            Dictionary with paths to exported files
        """
        
        # Create subtitle layer
        if not subtitle_clips:
            logger.warning("No subtitles will be included in the video.")
        
        if not music_clip:
            logger.warning("No background music will be included in the video.")
        
        if isinstance(video_clips, VideoClip):
            video_clips = [video_clips]
        
        try:
            duration = speech_clip.duration 
            
            # Mix audio components
            final_audio = self._mix_audio_layers(duration, speech_clip, music_clip)
            
            # Create base composition
            base_layer = self._create_base_layer(duration)
            
            final_video = self._composite_video_layers(
                base_layer, 
                video_clips,
                subtitle_clips
            ).with_audio(final_audio)

            audio_path = export_audio(final_audio, output_name, self.output_dir)
            video_path = export_video(final_video, output_name, self.output_dir, self.fps)

            if not audio_path or not video_path:
                logger.error("Failed to export audio or video.")
                return None
            
            # Export results
            return {
                "audio_path": audio_path,
                "video_path": {
                    "portrait": video_path
                }
            }
            
        except Exception as e:
            logger.error(f"Production failed: {e}")
            return None
        finally:
            for clip in [speech_clip, music_clip, *video_clips]:
                self._safe_close_clip(clip)

    def _safe_close_clip(self, clip: VideoClip | AudioClip) -> None:
        """Safely close a clip."""
        try:
            clip.close()
        except Exception as e:
            logger.warning(f"Error closing clip: {e}")

