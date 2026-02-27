import os
from config import logger, configuration
import asyncio
import httpx
from enum import StrEnum
from typing import Dict, Any, ClassVar

from backend.models.data import NewsItem


class ChannelType(StrEnum):
    """Supported publishing channels."""
    BURST = "burst" # burst specific channels
    TWITTER = "twitter"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    SPOTIFY = "spotify"


class BaseChannel:
    """Base class for all channel implementations.
    
    This class provides the base infrastructure for all distribution channels
    such as social media platforms and internal services.
    """
    
    # Class constants
    DEFAULT_TIMEOUT: ClassVar[int] = 30
    DEFAULT_RETRIES: ClassVar[int] = 3
    
    def __init__(
        self, 
        type: ChannelType,
        enabled: bool = True
    ) -> None:
        self._type: ChannelType = type
        self._enabled: bool = enabled
        self._default_headers: Dict[str, str] = self._get_headers()
        self._endpoint = configuration["distribution"]["endpoint"]


    @property
    def type(self) -> ChannelType:
        return self._type
    
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    @staticmethod
    def _get_headers() -> dict[str, str]:
        """Prepare headers with API key authentication."""
        
        token = os.environ.get('POSTIZ_TOKEN')
        if not token:
            raise ValueError("POSTIZ_TOKEN environment variable not set.")
            
        return {
            "Authorization": f"{token}",
        }
        
    async def _post(
        self, 
        payload: Dict[str, Any], 
    ) -> Dict[str, Any] | None:
        """Helper method to POST data with a retry mechanism.
        
        Args:
            payload: Data to send as JSON
            
        Returns:
            JSON response as dictionary or None if request failed
        """
        
        if not payload:
            raise ValueError(f"{self._type}: Payload is empty, cannot make POST request.")
        
        url = f"{self._endpoint}/posts"
        async with httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT) as client:
            for attempt in range(1, self.DEFAULT_RETRIES + 1):
                try:
                    response = await client.post(url, json=payload, headers=self._default_headers)
                    response.raise_for_status()
                    return response.json()
                
                except httpx.HTTPStatusError as e:
                    logger.error(f"Attempt {attempt}/{self.DEFAULT_RETRIES}: HTTP error {e.response.status_code} : {e}")
                
                except Exception as e:
                    logger.error(f"Attempt {attempt}/{self.DEFAULT_RETRIES}: Exception during POST to {url}: {e}")
                
                # wait before next attempt
                if attempt < self.DEFAULT_RETRIES:
                    await asyncio.sleep(attempt*2)
                
        raise Exception(f"Failed to post to {self._type} after {self.DEFAULT_RETRIES} attempts.")