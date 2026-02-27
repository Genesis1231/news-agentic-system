from config import logger
from pydantic import BaseModel, Field, field_validator
from typing import List


class YoutubeMeta(BaseModel):
    """Output format for the image description"""
    title: str = Field(..., description="The title of the Youtube video. (50 char max)")
    tags: List[str] = Field(..., description="Tags for the Youtube video. (10-15 tags)")
    
    
class TiktokMeta(BaseModel):
    """Output format for the image description"""
    title: str = Field(..., description="The title of the Tiktok video. (50 char max)")
    tags: List[str] = Field(..., description="Tags for the Tiktok video. (3-5 tags)")