from config import logger
import asyncio
import base64
import aiofiles
import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse, unquote

from langchain_core.messages import HumanMessage
from backend.utils.prompt import load_prompt
from backend.core.agent import BaseAgent

class VideoAnalyzer(BaseAgent):
    """
    A class that processes and describes videos using various vision models.
    It can handle video URLs or local file paths, and automatically optimizes
    videos to reduce payload size for LLMs.
    
    Args:
        platform (str): The platform to use for the vision model.
        model_name (str): The name of the vision model to use.
        base_url (str): The base URL of the vision model.
        temperature (float): The temperature to use for the vision model.
    """
    
    def __init__(
        self,
        platform: str = "Google",
        model_name: str | None = "gemini-2.5-flash",  
        base_url: str | None = None,
        temperature: float = 0.1,
    ) -> None:
        """Initialize the VideoAnalyzer."""
        config = {
            "name": "Video Analyzer",
            "platform": platform,
            "model_name": model_name,
            "base_url": base_url,
            "temperature": temperature,
        }
        super().__init__(config=config)

    def _optimize_video_sync(self, input_path: str, max_dimension: int = 480) -> str:
        """
        Create ultra-compressed video for cheap analysis.
        This is a synchronous helper.
        """
        
        output_path = f"optimized_{Path(input_path).stem}.mp4"
        
        try:
            duration_cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                           '-of', 'default=noprint_wrappers=1:nokey=1', input_path]
            
            duration = float(subprocess.check_output(duration_cmd).decode().strip())
            logger.debug(f"Video duration: {duration} seconds")
            
            # Optimize the fps for the video length
            optimized_fps = 1 if duration < 60 else 0.5

            scale_filter = f"scale='min({max_dimension},iw)':'min({max_dimension},ih)':force_original_aspect_ratio=decrease"
            
            ffmpeg_cmd = [
                'ffmpeg', '-i', input_path, '-y',
                '-vf', f'{scale_filter},fps={optimized_fps}',
                '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '35',
                '-an',
                '-movflags', '+faststart',
                output_path
            ]
            
            subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)
            
            original_tokens = int(duration * 258)
            optimized_tokens = int(duration * 66 * 0.5)
            if original_tokens > 0:
                savings = ((original_tokens - optimized_tokens) / original_tokens) * 100
                logger.debug(f"💰 Video optimization savings: {savings:.1f}%")

            return output_path
        
        except subprocess.CalledProcessError as e:
            logger.error(f"Video optimization FFmpeg failed: {e.stderr}")
            return ""
        except Exception as e:
            logger.error(f"Error optimizing video size: {e}")
            return ""

    async def _optimize_video(self, input_path: str) -> str:
        """Asynchronously offloads video optimization to a separate thread."""
        return await asyncio.to_thread(self._optimize_video_sync, input_path)

    async def convert_url(self, video_url: str) -> str | None:
        """Only YouTube videos are supported."""
        if "youtube" in video_url:
            return video_url
        else:
            return None

    async def convert_file(self, video_path: str) -> str | None:
        """Process a local video file for analysis."""
        
        optimized_video = await self._optimize_video(video_path)
        try:
            async with aiofiles.open(optimized_video, "rb") as f:
                encoded_video = base64.b64encode(await f.read()).decode("utf-8")
        
        except FileNotFoundError:
            logger.error(f"Video file {video_path} not found.")
            return None
        except Exception as e:
            logger.error(f"Error encoding video file {video_path}: {e}")
            return None
        finally:
            if os.path.exists(optimized_video):
                os.remove(optimized_video) # Clean up optimized video file

        return encoded_video

    async def analyze(
        self,
        url: str,
        context: str = "",
    ) -> str:
        """
        Analyze videos using the configured vision model.
        
        Args:
            url (str): The video URL or local path to analyze.
            context (str): The context to use for the description.

        """
        if not url or not isinstance(url, str):
            logger.error(f"No video urls provided.")
            return ""
            
        prompt = load_prompt("describe_video").format(context=context)
        content = [{"type": "text", "text": prompt}]
        
        if url.startswith(("http://", "https://")):
            # Handle YouTube URLs which don't have file extensions
            if "youtube.com" in url or "youtu.be" in url:
                content.append({
                    "file_uri": url, 
                })
            else:
                logger.error(f"Video URL analysis is not supported: {url}")
                return ""
        else:
            # Handle local files
            extension = extract_video_extension(url)
            if not extension or extension not in ["mp4", "mov", "avi", "mkv", "wmv", "mpg", "mpeg", "3gpp"]:
                logger.error(f"Unsupported video format for local file: {extension}")
                return ""
            
            encoded_video = await self.convert_file(url)
            if not encoded_video:
                logger.error(f"Failed to analyze local video file: {url}")
                return ""
            
            content.append({
                "type": "media", 
                "data": encoded_video, 
                "mime_type": f"video/{extension}"
            })
    
        try:
            logger.debug(f"Analyzing video: {url}")
            response = await self._invoke([HumanMessage(content=content)])
            return response.content

        except Exception as e:
            logger.error(f"Failed to describe video: {url} {str(e)}")
            return ""
    
def extract_video_extension(url: str) -> str:
    """
    Robustly extract a file extension from a URL path while:
      - decoding percent-encodings (e.g., %3F, %2E),
      - ignoring query strings & fragments,
      - stripping RFC 3986 path parameters (semicolon ';' segments),
      - handling trailing slashes / empty last segments,
      - and being resilient to multiple dots in filenames.

    Returns the lowercase extension without the leading dot,
    or "" if no valid extension is present.
    """
    # Parse once
    parsed = urlparse(url)

    # Decode path (handles %3F, %2E, etc.)
    path = unquote(parsed.path or "")

    # Take final segment only
    last = path.rsplit("/", 1)[-1]

    # Drop any path parameters after ';'
    # e.g., "video.mp4;download" -> "video.mp4"
    if ";" in last:
        last = last.split(";", 1)[0]

    # Empty or ends with slash? No filename -> no extension
    if not last or last.endswith("/"):
        return ""

    # Require at least one dot that is not the first char (avoid ".hidden")
    if "." not in last or last.startswith("."):
        return ""

    # Split on the last dot
    ext = last.rsplit(".", 1)[-1].lower()
    return ext