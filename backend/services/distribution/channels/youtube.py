from config import logger
from typing import Dict, Any, Tuple
from datetime import datetime, timezone

from backend.core.distribution import BaseChannel, ChannelType
from backend.models.data import NewsItem, RawNewsItem
from backend.services.agents import MetaWriter
from backend.models.schema.meta import YoutubeMeta
from backend.models.schema.enums import NewsDepth

class YoutubeChannel(BaseChannel):
    """YouTube-specific implementation with enhanced validation and error handling."""
    
    def __init__(self, integration_id: str) -> None:
        """ Initialize YouTube channel with integration ID."""
        super().__init__(
            type=ChannelType.YOUTUBE,
            enabled=True
        )
        
        self.meta_writer = MetaWriter(
            platform="Groq",
            output_format=YoutubeMeta
        )
        self._integration_id = integration_id
        
    
    async def format(
        self, 
        news_data: NewsItem,
        raw_news_data: RawNewsItem,
        media_id: str,  
        media_path: str,
        post_type: str,  
        post_time: str 
    ) -> Dict[str, Any]:
        """Transform news data into YouTube API-compatible format with safety checks."""
        
        metadata = await self.meta_writer.generate(news_data, ChannelType.YOUTUBE)
        if not metadata:
            raise ValueError("Failed to generate video metadata.")

        description = self.craft_description(news_data, raw_news_data)
        hashtags = [
            {"label": tag, "value": tag} for tag in metadata.get("tags", [])
        ] + [
            { "label": "Techshorts", "value": "Techshorts"},
            { "label": "BurstFM", "value": "BurstFM"}
        ]
        
        return {
            "type": post_type,              # Required: "draft", "schedule", or "now"
            "shortLink": False,             # Required: Whether to use short links in content
            "date": post_time,              # Required: ISO date format
            "tags": [],               # Required: Array of post tags (for categorization)
            "posts": [{
                "integration": { "id": self._integration_id },
                "value": [{
                    "content": description,   # Required: Video description
                    "image": [{
                        "id": media_id,                 # ID of the uploaded video file
                        "path": media_path              # Path to the video file
                    }]
                }],
                "settings": {             
                    "__type": "youtube", 
                    "title": metadata["title"],         # Required: Video title
                    "type": "public",                   # Required: Privacy status - "public", "private", or "unlisted"
                    # "thumbnail": {                    # Optional: Custom thumbnail for the video
                    # "id": "thumbnail-id",
                    # "path": "/path/to/thumbnail.jpg"
                    # },
                    "tags": hashtags
                }
            }]
        }

    
    async def publish(
        self, 
        news_data: NewsItem,
        raw_news_data: RawNewsItem,
        uploaded_media: Dict[str, Any],
        post_type: str = "now", 
        post_time: str | None = None
    ) -> Dict[str, Any] | None:
        """Distribute news data to YouTube"""
        
        logger.debug(f"Publishing news to YouTube channel with depth {news_data.depth}.")
        
        if not uploaded_media:
            logger.warning("No uploaded media provided. Content will not be published in YouTube.")
            return None

        if post_time is None:
            post_time = datetime.now(timezone.utc).isoformat()
        
        media_id, media_path = self.select_media(uploaded_media, news_data.depth)
        if not media_id or not media_path:
            logger.error("No appropriate video for YouTube. Content will not be published in YouTube.")
            return None
            
        formatted_data = await self.format(
            news_data=news_data,
            raw_news_data=raw_news_data,
            media_id=media_id,
            media_path=media_path,
            post_type=post_type,
            post_time=post_time
        )
        
        return await self._post(formatted_data)

    
    def select_media(self, uploaded_media: Dict[str, Any], depth: str) -> Tuple[str, str]:
        """Select the appropriate media based on the news depth."""
        
        if depth == NewsDepth.FLASH:
            if video := uploaded_media.get("video_portrait"):
                return video.get("id"), video.get("path")
        else:    
            if video := uploaded_media.get("video_landscape"):
                return video.get("id"), video.get("path")
        
        return None, None
    
    def craft_description(self, news_data: NewsItem, raw_news_data: RawNewsItem) -> str:
        """Craft a description for the news item."""    
        
        # Calculate time difference in minutes between creation and source timestamp
        time_duration = datetime.now(timezone.utc) - raw_news_data.timestamp
        minutes_elapsed = int(time_duration.total_seconds() / 60)
        
        # Initialize cited_sources outside the conditional block to fix scope issue
        cited_sources = ""
        if any(news_data.cited_sources):
            cited_sources = "\n".join([str(source) for source in news_data.cited_sources])
        
        return f"""
        {raw_news_data.author.name} posted on {raw_news_data.source_name} {minutes_elapsed} minutes ago.
        
        Source confidence: 100%
        Context confidence: {news_data.confidence:.0%}
        
        Subscribe to @BurstFM NOW to get verified tech news minutes after they happen! 
        
        Source URLs: 
        {raw_news_data.source_url}
        {cited_sources}
        
        """