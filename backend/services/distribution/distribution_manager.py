import asyncio
import os
from pathlib import Path
from config import logger, configuration
from typing import Dict, Any
import aiofiles
import httpx

from backend.models.data import NewsItem, RawNewsItem
from backend.core.distribution import BaseChannel, ChannelType
from .channels import get_supported_channels

class DistributionManager:
    """
    Distribution manager for handling the distribution of news items to various channels.
    
    Attributes:
        channel_list: Dictionary of supported channels.
        _endpoint: Distribution endpoint URL.
        _default_headers: Default headers for API requests.
    """
    
    def __init__(self) -> None:
        self._endpoint: str = configuration["distribution"]["endpoint"]
        self._default_headers: Dict = self._get_headers()
        self.channel_list: Dict[ChannelType, BaseChannel] = get_supported_channels(
            endpoint=self._endpoint,
            headers=self._default_headers
        )

        logger.debug(f"Distribution Manager initialized with channels: {list(self.channel_list.keys())}")
    
    @staticmethod
    def _get_headers() -> dict[str, str]:
        """Prepare headers with API key authentication."""
        
        return {
            "Authorization": os.environ.get('POSTIZ_TOKEN')
        }
        
    async def distribute(self, news_data: NewsItem, raw_news_data: RawNewsItem) -> None:
        """Distribute news item through all enabled channels"""

        postiz_uploads = await self._upload_media(news_data)
        if not postiz_uploads:
            logger.error("Failed to upload media for distribution.")
            return
        
        # Publish to all enabled channels
        tasks = [
            self._publish_to_channel(
                channel=channel, 
                news_data=news_data, 
                raw_news_data=raw_news_data, 
                postiz_uploads=postiz_uploads
            ) 
            for channel in self.channel_list.values() 
            if channel.enabled
        ]

        await asyncio.gather(*tasks)

    async def _publish_to_channel(
        self, 
        channel: BaseChannel, 
        news_data: NewsItem, 
        raw_news_data: RawNewsItem,
        postiz_uploads: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        """Handle single channel distribution process"""
        try:
            result = await channel.publish(
                news_data=news_data,
                raw_news_data=raw_news_data,
                uploaded_media=postiz_uploads
            )
            if result:
                logger.debug(f"Published the content to {channel.type} channel: {result}")
                return result
        
        except Exception as e:
            logger.error(f"Failed to publish to {channel.type}: {e}")
            return None

    async def _upload_media(self, news_data: NewsItem) -> Dict[str, Any]:
        """Upload media to the distribution endpoint"""
        
        # Get the paths from news_data
        audio_path = news_data.audio_path
        video_portrait = news_data.video_path.get("portrait") if news_data.video_path else None
        video_landscape = news_data.video_path.get("landscape") if news_data.video_path else None
        
        # Results dictionary to track upload results
        results = {}
        upload_tasks = []
        
        # Upload portrait video if it exists
        if video_portrait and Path(video_portrait).exists():
            upload_tasks.append(self._upload_file(video_portrait))
            results["video_portrait"] = None
        
        # Upload landscape video if it exists
        if video_landscape and Path(video_landscape).exists():
            upload_tasks.append(self._upload_file(video_landscape))
            results["video_landscape"] = None
        
        upload_results = await asyncio.gather(*upload_tasks, return_exceptions=True)
        
        # Map results to dictionary
        for i, task in enumerate(upload_tasks):
            if isinstance(upload_results[i], Exception):
                logger.error(f"Upload failed: {upload_results[i]}")
            else:
                logger.debug(f"Successfully uploaded {list(results.keys())[i]} to distribution endpoint")
                results[list(results.keys())[i]] = upload_results[i]
        
        return results
    
    async def _upload_file(self, file_path: str) -> Dict[str, Any] | None:
        """Helper method to upload a single file """
        
        filename = Path(file_path).name
        url = f"{self._endpoint}/upload"
        
        # Read file content
        async with aiofiles.open(file_path, 'rb') as f:
            file_content = await f.read()

        # Upload the file
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=self._default_headers,
                files={'file': (filename, file_content)},
            )
            response.raise_for_status()
            return response.json()
