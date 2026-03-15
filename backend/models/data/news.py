from config import logger
from typing import List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, field_validator

from backend.models.SQL import NewsDB 

class NewsItem(BaseModel):
    """News item model after processing"""
    
    id: int | None = Field(default=None, description="Unique identifier of the news item")
    raw_id: int = Field(..., description="Unique identifier of the raw news item")
    
    #classification
    depth: str = Field(..., description="Depth of the news item")
    news_category: List[str] = Field(..., description="Category of the news item")
    news_type: List[str] = Field(..., description="Type of the news item")
    
    # Content fields
    title: str = Field(default="", description="Title of the news item")
    text: str = Field(default="", description="Main content text")
    script: str = Field(default="", description="Audio script of the news item")
    
    cover_image: str = Field(default="", description="Cover image of the news item")
    audio_path: str = Field(default="", description="Audio path of the news item")
    video_path: Dict[str, str] = Field(default_factory=dict, description="Path to the media content")

    # Additional metadata
    cited_sources: List[HttpUrl] = Field(default_factory=list, description="Cited sources")
    entities: List[str] = Field(default_factory=list, description="Entities in the news item")
    
    # Processing status
    is_produced: bool = Field(default=False, description="Whether item has been produced")
    is_published: bool = Field(default=False, description="Whether item has been published")
  
    model_config = {
        "from_attributes": True
    }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Pydantic News model to dictionary."""
        model_data = self.model_dump()

        # Convert HttpUrl objects in cited_sources to strings
        if model_data.get("cited_sources"):
            model_data["cited_sources"] = [str(url) for url in model_data["cited_sources"]]

        return model_data
    
    def to_db(self, exclude_id: bool = False) -> NewsDB:
        """Convert Pydantic News model to SQLAlchemy NewsDB model."""
        try:
            # Exclude the id field if exclude_id is True
            exclude_fields = [] if not exclude_id else {"id"}
            model_data = self.model_dump(exclude=set(exclude_fields))

            # Convert HttpUrl objects in cited_sources to strings
            if model_data.get("cited_sources"):
                model_data["cited_sources"] = [str(url) for url in model_data["cited_sources"]]
            return NewsDB(**model_data)

        except ValueError as e:
            logger.error(f"Validation error converting NewsItem (id={self.id}) to NewsDB: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error converting NewsItem (id={self.id}) to NewsDB: {str(e)}")
            raise
    
    @classmethod
    def from_db(cls, db_item: NewsDB) -> "NewsItem":
        """Convert SQLAlchemy NewsDB model to Pydantic NewsItem model."""
        try:
            return cls.model_validate(db_item)

        except ValueError as e:
            logger.error(f"Validation error converting NewsDB (id={getattr(db_item, 'id', 'unknown')}) to NewsItem: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error converting NewsDB (id={getattr(db_item, 'id', 'unknown')}) to NewsItem: {str(e)}")
            raise
    
    @field_validator('cited_sources', mode='before')
    def validate_urls(cls, value: List) -> List[HttpUrl]:
        """Validate the URLs in cited_sources."""
        validated_urls = []
        for url in value or []:
            try:
                validated_urls.append(HttpUrl(str(url)))
            except ValueError:
                logger.warning(f"Invalid URL in cited_sources: {url}, skipping...")
                continue

        return validated_urls
    
