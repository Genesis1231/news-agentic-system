from config import logger
from typing import List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, field_validator 

from backend.models.schema.enums import AuthorType
from backend.models.SQL import AuthorDB

class Author(BaseModel):
    """Unified author information across different platforms"""

    id: int | None = Field(default=None, description="The unique identifier in the database")
    idname: str = Field(..., description="The unique identifier of the author, mostly the same with twitter handle")
    name: str = Field(..., description="The full name of the author")
    aliases:  List[str] = Field(default_factory=list, description="A list of aliases for this author")
    type: AuthorType = Field(default=AuthorType.OTHER, description="The type of the author")
    is_key_figure: bool = Field(default=False, description="Whether the author is a key figure")
    affiliations: List[str] = Field(default_factory=list, description="The affiliations for this author")
    
    description: str = Field(default="", description="A brief description of the author")
    profile_image_url: HttpUrl | None = Field(default=None, description="The URL of the author's profile image")
    
    # Social media links
    website_url: HttpUrl | None = Field(default=None, description="The URL of the author's personal website")
    wikipedia_url: HttpUrl | None = Field(default=None, description="The URL of the author's Wikipedia page")
    x_url: HttpUrl | None = Field(default=None, description="The URL of the author's X profile")
    youtube_url: HttpUrl | None = Field(default=None, description="The URL of the author's YouTube channel")
    linkedin_url: HttpUrl | None = Field(default=None, description="The URL of the author's LinkedIn profile")
    instagram_url: HttpUrl | None = Field(default=None, description="The URL of the author's Instagram profile")
    tiktok_url: HttpUrl | None = Field(default=None, description="The URL of the author's TikTok profile")
    weibo_url: HttpUrl | None = Field(default=None, description="The URL of the author's Weibo profile")

    # Additional metadata
    enabled: bool = Field(default=True, description="Whether the author is enabled")
    author_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata for this author")
    
    # # The raw news items associated with this author    
    # raw_news_items: List[RawNewsItem] = Field(default_factory=list, description="Raw news items associated with this author") #type: ignore
    
    model_config = {
        "use_enum_values": True,
        "from_attributes": True,
    }
    
    def to_db(self, exclude_id: bool = False) -> AuthorDB:
        """Convert Pydantic Author model to SQLAlchemy AuthorDB model."""
        
        # Exclude the id field if exclude_id is True
        exclude_fields = ["raw_news_items"] if not exclude_id else ["raw_news_items", "id"]
        model_data = self.model_dump(exclude=exclude_fields)
        
        # Convert HttpUrl objects to strings for all URL fields
        url_fields = [
            "profile_image_url",
            "website_url",
            "wikipedia_url",
            "x_url",
            "youtube_url",
            "linkedin_url",
            "instagram_url",
            "tiktok_url",
            "weibo_url"
        ]
        
        for field in url_fields:
            if model_data[field] is not None:
                model_data[field] = str(model_data[field])

        return AuthorDB(**model_data)
    
    @classmethod
    def from_db(cls, author_db: AuthorDB) -> "Author":
        """Convert SQLAlchemy AuthorDB model to Pydantic Author model."""

        db_data = {
            column.name: getattr(author_db, column.name)  
            for column in author_db.__table__.columns
        }
    
        return cls.model_validate(db_data)
    
    @field_validator("id")
    def validate_id(cls, value, info):
        info_id = info.data.get("id", None)

        # for update, id cannot be modified after creation
        if info_id is not None and value != info_id:
            logger.error("id cannot be modified after creation.")
            return info_id

        return value
    
    @field_validator('profile_image_url', 'wikipedia_url', 'x_url', 'website_url', 
                     'youtube_url', 'linkedin_url', 'instagram_url', 'tiktok_url', 'weibo_url')
    def validate_url(cls, value):
        try:
            return HttpUrl(value) if value else None
        except ValueError as e:
            logger.error(f"Invalid URL: {value}")
            return None
    
    @field_validator("type")
    def validate_type(cls, value):
        if value not in AuthorType.__members__.values():
            logger.error(f"Invalid author type: {value}")
            return AuthorType.OTHER
        return value