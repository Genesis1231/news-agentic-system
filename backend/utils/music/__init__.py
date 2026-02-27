from config import logger, configuration
from pathlib import Path

def get_music(news_category: str) -> Path | None:
    """Load the background music file for a specific news category."""
    
    music_path = Path(__file__).parent / f"{news_category}.mp3"
    
    if not music_path.exists():
        logger.error(f"Background music for category '{news_category}' not found at {music_path}")
        return None
            
    return music_path
