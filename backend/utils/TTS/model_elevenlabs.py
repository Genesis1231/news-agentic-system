from datetime import datetime
import base64 
from config import logger
from pathlib import Path
import uuid
import aiofiles
from typing import Dict, Any, List, Tuple
import json

from elevenlabs.client import AsyncElevenLabs
from elevenlabs import VoiceSettings
    
class ElevenLabsClient:
    def __init__(self, model_name: str, voice: str) -> None:
        self.client: AsyncElevenLabs = AsyncElevenLabs()
        self.model_name: str = model_name
        self.voice: str = voice 
        self.voice_settings: VoiceSettings = VoiceSettings(
            stability=0.5,
            similarity_boost=0.8,
            style=0.0,
            use_speaker_boost=True
        )
    
    async def _get_audio_stream(self, text: str):
        """ Get audio stream from text using ElevenLabs """
        
        try:
            response = await self.client.text_to_speech.convert_with_timestamps(
                model_id=self.model_name,
                text=text,
                voice_id=self.voice,
                optimize_streaming_latency=1,
                voice_settings=self.voice_settings,
            )
            
            if not response:
                logger.error("Empty response from ElevenLabs")
                return None
            
            audio_stream = response.audio_base_64
            timestamp_data = response.alignment
                           
            # Ensure audio_stream is bytes
            if not isinstance(audio_stream, bytes):
                audio_stream = base64.b64decode(audio_stream)
                
            logger.debug(f"Successfully generated audio stream of size: {len(audio_stream)} bytes")
            return audio_stream, timestamp_data
            
        except Exception as e:
            logger.error(f"Failed to get audio stream: {str(e)}")
            return None
        
    async def generate(self, text: str, media_folder: str) -> Tuple[str, str]:
        """ Generate mp3 from text using ElevenLabs """

        file_time = datetime.now().strftime("%Y%m%d")
        filename = f"{uuid.uuid4().hex[:8]}"
        audio_path = Path(media_folder) / file_time / f"{filename}.mp3"
        subtitle_path = Path(media_folder) / file_time / f"{filename}.json"
        
        # Create directory if not exists
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        text = self._format_tts(text) # format the script for TTS

        try:
            result = await self._get_audio_stream(text)
            if result is None:
                logger.error("Failed to get audio stream from ElevenLabs")
                return None
            
            audio_stream, timestamps = result

            # Write audio to file
            async with aiofiles.open(audio_path, 'wb') as f:
                await f.write(audio_stream)
            
            # Convert timestamps to subtitles
            subtitles = self.convert_subtitles(timestamps)
            if not subtitles:
                logger.warning("No subtitles generated from timestamps.")
                return audio_path, ""
            
            # Write subtitles to file
            subtitle_json = json.dumps(subtitles, indent=2)
            async with aiofiles.open(subtitle_path, 'w') as f:
                await f.write(subtitle_json)
               
            return str(audio_path), str(subtitle_path)
            
        except IOError as e:
            logger.error(f"Failed to write files: {e}")
            return None
        
        except Exception as e:
            logger.error(f"Error during text to speech synthesis: {str(e)}")
            return None

    def convert_subtitles(self, alignment: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert ElevenLabs alignment data to moviepy-compatible subtitle format."""
        
        if not alignment or not isinstance(alignment, Dict):
            logger.error("Invalid alignment data received")
            return []
        
        try:
            characters = alignment['characters']
            start_times = alignment['character_start_times_seconds']
            end_times = alignment['character_end_times_seconds']
            
            # Initialize variables
            words = []
            current_word = []
            word_start_time = None
            
            # Define characters that should be part of words
            WORD_CHARS = {"'", "-", ".", "!", "?", ",", ":", ";"}
            WHITESPACE = {" ", "\n", "\t"}
            
            # Combine characters into words with timing
            for char, start, end in zip(characters, start_times, end_times):
                if char in WHITESPACE:
                    if current_word:
                        words.append({
                            'text': ''.join(current_word),
                            'start': word_start_time,
                            'end': end,
                        })
                        current_word = []
                elif char.isalnum() or char in WORD_CHARS:
                    if not current_word:
                        word_start_time = start
                    current_word.append(char)
            
            # Add the last word if exists
            if current_word:
                words.append({
                    'text': ''.join(current_word),
                    'start': word_start_time,
                    'end': end_times[-1],
                })
            
            return words
            
        except KeyError as e:
            logger.error(f"Missing required key in alignment data: {e}")
            return []
        except Exception as e:
            logger.error(f"Error converting subtitles: {e}")
            return []
    
    def _format_tts(self, script: str) -> str:
        """format the script by replacing text patterns for speech synthesis"""
        
        replacements = {
            ".fm": " dot fm",
            "**": "<emphasis level='high'>",
            " – ": ", ",
        }

        for old, new in replacements.items():
            script = script.replace(old, new)
        
        return script + "\n\n"