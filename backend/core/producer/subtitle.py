import json
from config import logger
from moviepy import TextClip
from typing import List


def create_subtitle_video(subtitle_path: str, font_path: str, screen_height: int) -> List[TextClip]:
    """
    Create subtitle clips from JSON subtitle file.

    """
    if not subtitle_path:
        logger.warning("No subtitle file provided.")
        return []
        
    try:
        with open(subtitle_path, 'r', encoding='utf-8') as f:
            subtitles = json.loads(f.read())
            
        if not subtitles:
            logger.warning("Empty subtitles file")
            return []

        # Group subtitles into natural phrases
        phrases = []
        current_phrase = {
            "text": [],
            "start": None,
            "end": None
        }
        
        for i, sub in enumerate(subtitles):
            # Start new phrase if:
            # 1. This is the first subtitle
            # 2. Current word starts after a long pause (>0.3s)
            # 3. Current phrase is getting too long (>40 chars)
            # 4. Current word ends with punctuation
            
            text = sub.get("text")
            start = sub.get("start")
            end = sub.get("end")
            
            if (current_phrase["text"] and  # Only check if we have existing text
                ((start - current_phrase["end"] > 0.3) or  # Long pause
                (len(" ".join(current_phrase["text"])) > 30) or  # Too long
                any(current_phrase["text"][-1].endswith(p) for p in ".!?"))):  # End of sentence
                
                phrases.append(current_phrase)
                current_phrase = {
                    "text": [text],
                    "start": start,
                    "end": end
                }
            else:
                # Initialize or append to current phrase
                if not current_phrase["start"]:
                    current_phrase["start"] = start
                current_phrase["text"].append(text)
                current_phrase["end"] = end
            
            # Handle last phrase
            if i == len(subtitles) - 1 and current_phrase["text"]:
                phrases.append(current_phrase)

        # Create text clips for each phrase
        subtitle_clips = []
        for phrase in phrases:
            text_list = phrase.get("text", [])
            start = phrase.get("start")
            end = phrase.get("end")
            
            # Join all words in the phrase, replace some text
            text_list = " ".join(text_list).replace(" dot fm", ".fm")
            
            clip = (TextClip(
                text=text_list,  
                font=font_path,
                font_size=32,
                color='white',
                stroke_color='black',
                stroke_width=2,
            )
            .with_position(("center", int(screen_height * 0.85)))
            .with_start(start)
            .with_duration(end - start))
            
            subtitle_clips.append(clip)

        return subtitle_clips
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in subtitle file: {e}")
        return []
    except Exception as e:
        logger.error(f"Error creating subtitle clips: {e}")
        return []
