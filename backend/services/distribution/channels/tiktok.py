from config import logger, configuration
from typing import Dict, Any
from datetime import datetime, timezone

from backend.core.distribution import BaseChannel, ChannelType
from backend.models.data import NewsItem
from backend.services.agents import MetaWriter
from backend.models.schema.meta import TiktokMeta

class TiktokChannel(BaseChannel):
    """TikTok-specific implementation with enhanced validation and error handling."""
    
    def __init__(
        self,
        integration_id: str,
    ) -> None:
        super().__init__(
            type=ChannelType.TIKTOK,
            enabled=False
        )
        
        self.meta_writer = MetaWriter(
            platform="Groq",
            output_format=TiktokMeta
        )
        self._endpoint = configuration["distribution"]["endpoint"]
        self._integration_id = integration_id
    
    async def format(
        self, 
        news_data: NewsItem,
        media_id: str,  
        media_path: str,
        post_type: str,  
        post_time: str 
    ) -> Dict[str, Any] | None:
        """Transform news data into postiz-compatible format with safety checks."""
        
        metadata = await self.meta_writer.generate(news_data, ChannelType.TIKTOK)
        if not metadata:
            logger.error("Failed to generate metadata for TikTok")
            return None
            
        hashtags = [
            {tag : tag} for tag in metadata.get("hashtags", [])
        ]
        
        return {
            "type": post_type,
            "date": post_time,
            "posts": [{ 
                "integration": {"id": self._integration_id },
                "value": [{
                    "content": "this is a test post",
                    "images": [{
                        "id": media_id,
                        "path": media_path
                        }]             
                }],
                "settings": {
                    "__type": "tiktok",
                    "title": metadata.get("title", ""),
                    "tags": hashtags
                }
            }]
        }
    
    async def publish(
        self, 
        news_data: NewsItem,
        media_id: str,
        media_path: str,
        post_type: str = "now", 
        post_time: str | None = None
    ) -> Dict[str, Any] | None:
        """Publish tiktok news data through postiz API"""
        
        if not self.enabled:
            logger.debug(f"Channel tiktok is DISABLED, skipping publish.")
            return None
        
        if not media_id or not media_path:
            logger.error("Invalid Media ID or path.")
            return None

        if post_time is None:
            post_time = datetime.now(timezone.utc).isoformat()
                
        formatted_data = await self.format(
            news_data=news_data,
            media_id=media_id,
            media_path=media_path,
            post_type=post_type,
            post_time=post_time
        )
        
        # Post the tiktok content to postiz
        response = await self._post(formatted_data)
        if not response:
            logger.error(f"Tiktok distribution failed for news ID: {news_data['id']}!")
            return None
        
        return response
