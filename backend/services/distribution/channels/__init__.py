from config import logger
import httpx
from typing import Dict

from backend.core.distribution import BaseChannel, ChannelType
from .youtube import YoutubeChannel
from .tiktok import TiktokChannel


def get_supported_channels(endpoint: str, headers: Dict[str, str])-> Dict[ChannelType, BaseChannel] | None:
    
    try:
        with httpx.Client() as client:
            response = client.get(f"{endpoint}/integrations", headers=headers)
            response.raise_for_status()
            channels = response.json()
        
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP {endpoint} error during file upload: {e.response}")
        return None
    
    except Exception as e:
        logger.error(f"Error getting distribution channels: {e}")
        return None

           
    # Define a mapping between enum values and their corresponding channel classes
    channel_mapping = {
        ChannelType.YOUTUBE: YoutubeChannel,
        ChannelType.TIKTOK: TiktokChannel,
        # Add more channels here as they become available
    }
    
    channel_list = {}
    for channel in channels:
        if channel["disabled"]:
            continue
            
        try:
            # Convert string identifier to ChannelType enum
            channel_type = ChannelType(channel["identifier"])
            
            if channel_type in channel_mapping:
                channel_class = channel_mapping[channel_type](
                    integration_id=channel["id"]
                )
                if channel_class.enabled:
                    channel_list[channel_type] = channel_class

        except Exception as e:
            raise Exception(f"Error setting up channel {channel['identifier']}: {e}")

    
    return channel_list
