from config import logger
from typing import List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, field_validator
from datetime import datetime, timezone
from textwrap import dedent

from backend.models.SQL import RawNewsDB
from .author import Author

class RawNewsItem(BaseModel):
    """Raw news item model before processing"""
    
    id: int | None = Field(default=None, description="Unique identifier of the news item")
    source_name: str = Field(..., description="Name of the source")
    source_id: str = Field(..., description="Item ID in the source")
    source_url: HttpUrl | None = Field(default=None, description="URL of the source")
    timestamp: datetime = Field(..., description="Publication timestamp")
    
    # Author fields
    author: Author = Field(..., description="Author relationship data")
    author_idname: str = Field(..., description="Content author idname")
    
    # Content fields
    title: str = Field(default="", description="Title of the news item")
    text: str = Field(..., description="Main content text")
    media_content: Dict[str, Any] = Field(default_factory=dict, description="Media content")
    
    # Impact score (computed from engagement metrics at aggregation time)
    impact_score: float = Field(default=0.0, ge=0, description="Pre-computed impact score (0-100)")
    
    # Classification fields
    news_category: List[str] = Field(default=["OTHER"], description="The category of the news")
    news_type: List[str] = Field(default=["GLOBAL"], description="The type of the news")
    source_level: str = Field(default="TERTIARY", description="The level of the source")
    sentiment: str = Field(default="NEUTRAL", description="The sentiment of the news")
    entities: List[str] = Field(default=[], description="The entities in the news")
    relevance: float = Field(default=0.0, description="Relevance score to the target audience")

    # Processing status
    is_processed: bool = Field(default=False, description="Whether item has been processed")
   
    model_config = {
        "use_enum_values": True,
        "from_attributes": True
    }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Pydantic News model to dictionary."""
        model_data = self.model_dump(exclude={"author"})
        model_data["source_url"] = str(model_data["source_url"]) if model_data["source_url"] is not None else None

        return model_data
    
    def to_db(self, exclude_id: bool = False) -> RawNewsDB:
        """Convert Pydantic News model to SQLAlchemy RawNewsDB model."""
        
        # Exclude the id field if exclude_id is True
        exclude_fields = {"author"} if not exclude_id else {"author", "id"}
        model_data = self.model_dump(exclude=exclude_fields)
        
        # Convert HttpUrl object to string
        if model_data["source_url"] is not None:
            model_data["source_url"] = str(model_data["source_url"])
        
        return RawNewsDB(**model_data)
    
    @classmethod
    def from_db(cls, db_item: RawNewsDB) -> "RawNewsItem":
        """ Convert SQLAlchemy RawNewsDB model to Pydantic RawNewsItem model."""
        db_data = {
            column.name: getattr(db_item, column.name)  
            for column in db_item.__table__.columns
        }
        try:
            if db_item.author is not None:
                from backend.models.data.author import Author  # Avoid circular import
                db_data['author'] = Author.from_db(db_item.author)
        except Exception as e:
                logger.error(f"Error creating author in News Pydantic: {e}")
            
        return cls.model_validate(db_data)
    
    @field_validator('source_url')
    def validate_url(cls, value):
        """Validate the URL of the news item."""
        try:
            return HttpUrl(value) if value else None
        except ValueError as e:
            logger.error(f"Invalid URL: {value}")
            return None
    
    @field_validator('timestamp')
    def validate_timestamp(cls, value):
        """Validate the timestamp of the news item."""
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc)
        return value
    
    
    @property
    def potential_impact_score(self) -> str:
        """Return the pre-computed impact score as a formatted string."""
        return f"{self.impact_score:.0f}/100"
    
    @property
    def time_text(self) -> str:
        """ Format the time posted of the news item for LLM."""
        delta = datetime.now(timezone.utc) - self.timestamp

        # Less than 5 minutes
        if delta.total_seconds() < 300:
            return "just now"
            
        # Less than an hour
        if delta.total_seconds() < 3600:
            minutes = int(delta.total_seconds() / 60)
            return f"({minutes} minutes ago)"
            
        # Less than a day
        if delta.total_seconds() < 86400:
            hours = int(delta.total_seconds() / 3600)
            return f"({hours} hours ago)"
            
        # Days
        return f"{delta.days} day(s) ago"


    @property
    def composed_content(self) -> str:
        """Compose the full content of the news item for LLM processing."""

        media_text = ""
        # compose the media content
        if self.media_content:
            media_descriptions = "\n".join(
                f"<{key}>{value['description']}</{key}>\n" 
                for key, value in self.media_content.items() if 'description' in value
            )

            if media_descriptions.strip():
                media_text = (f"""
                    <additional_media>
                        The content also includes:  
                        {media_descriptions}
                    </additional_media>
                """)


        return f"""
            Source: {self.source_name.capitalize()}
            Author: {self.author.name} (@{self.author.idname})
            Time posted: {self.time_text}
            ----------------------------------
            <main_content>
            {self.text}
            </main_content>
            {media_text}
        """
    
    def merge_classification(self, data: Dict[str, Any]) -> "RawNewsItem":
        """ Merge classification data to RawNewsItem."""
        try:
            for field in ['title', 'news_category', 'news_type', 'source_level', 
            'sentiment', 'entities', 'relevance', "text"]:
                setattr(self, field, data.get(field, getattr(self, field)))
        except Exception as e:
            logger.error(f"Error merging classification data: {e}")
            pass
        
        return self