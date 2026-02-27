from config import logger
from pathlib import Path

from moviepy import (
    AudioFileClip,
    concatenate_audioclips,
    CompositeVideoClip,
)


def create_looped_music(music_clip: AudioFileClip, target_duration: float) -> AudioFileClip:
    """Create a looped version of the background music to match target duration."""
    
    if music_clip.duration >= target_duration:
        # If music is longer than target, just take the needed portion
        return music_clip.subclipped(0, target_duration)
    
    # Calculate number of loops needed
    n_loops = int(target_duration / music_clip.duration) + 1
    
    clips = [music_clip] * n_loops
    return concatenate_audioclips(clips)

def export_audio(
    audio_clip: AudioFileClip, 
    filename: str, 
    directory: str,
    audio_codec: str = 'libmp3lame', 
    ) -> str | None:
    """Export audio clip to file with high-quality settings."""
    
    try:
        output_path = str(Path(directory) / f"{filename}.mp3")
        audio_clip.write_audiofile(
            output_path,
            fps=48000,
            codec=audio_codec,
            bitrate='128k',
            ffmpeg_params=['-ac', '2']  # Ensure stereo output
        )
        return output_path
    
    except Exception as e:
        logger.error(f"Error exporting audio file: {e}")
        return None

def export_video(
    video_clip: CompositeVideoClip, 
    filename: str, 
    directory: str, 
    fps: int,
    audio_codec: str = 'aac', # Use AAC for iOS compatibility
    video_codec: str = 'libx264' # Use NVIDIA hardware acceleration
    ) -> str | None:
    
    """Export video clip to file with optimized settings for web playback."""
    
    try:
        output_path = str(Path(directory) / f"{filename}.mp4")
        video_clip.write_videofile(
            output_path,
            fps=fps,
            codec=video_codec,
            audio_codec=audio_codec,  
            ffmpeg_params=[
                '-pix_fmt', 'yuv420p',  # Required for compatibility
                '-movflags', '+faststart',  # Enable fast start for web playback
                '-profile:v', 'main',  # High profile for better quality
                '-preset', 'slow',  # Slower preset for better compression
                '-crf', '21',  # Lower CRF for higher quality
                '-level', '4.0',  # Compatibility level
                '-bf', '2',  # 2 consecutive B frames as per YouTube recommendations
                '-b:a', '128k',  # Higher audio bitrate for better quality
                '-ar', '48000',  # 48kHz audio sample rate
                '-ac', '2',  # Stereo audio
                '-threads', '0'  # Use all available CPU threads
            ]
        )
        return output_path
    
    except Exception as e:
        logger.error(f"Error exporting video file: {e}")
        return None

