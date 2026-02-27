from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy import String, Boolean, ARRAY, Integer, Enum, DateTime, JSON
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy.sql import func

from backend.models.schema.enums import AuthorType
from .base import BaseDB

class AuthorDB(BaseDB):
    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    idname: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    aliases: Mapped[List[str]] = mapped_column(ARRAY(String(64)), default=list)
    type: Mapped[AuthorType] = mapped_column(
        Enum(AuthorType, native_enum=True), 
        default=AuthorType.OTHER,
        nullable=False
    )
    is_key_figure: Mapped[bool] = mapped_column(Boolean, default=False)
    affiliations: Mapped[List[str]] = mapped_column(ARRAY(String(64)), default=list)
    
    description: Mapped[str] = mapped_column(String(4096), default="")
    profile_image_url: Mapped[str | None] = mapped_column(String(1024))
    
    # Social media links, must be None if not present
    website_url: Mapped[str | None] = mapped_column(String(256))
    wikipedia_url: Mapped[str | None] = mapped_column(String(256))
    x_url: Mapped[str | None] = mapped_column(String(256))
    youtube_url: Mapped[str | None] = mapped_column(String(256))
    linkedin_url: Mapped[str | None] = mapped_column(String(256))
    instagram_url: Mapped[str | None] = mapped_column(String(256))
    tiktok_url: Mapped[str | None] = mapped_column(String(256))
    weibo_url: Mapped[str | None] = mapped_column(String(256))
    
    # Additional metadata
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    author_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # # Relationships 
    # raw_news_items: Mapped[List["RawNewsDB"]] = relationship(
    #     "RawNewsDB", 
    #     primaryjoin="AuthorDB.idname == RawNewsDB.author_idname",
    #     viewonly=True
    # ) #type: ignore
    
    def to_schema(self) -> "Author": #type: ignore
        """ Convert SQLAlchemy AuthorDB model to Pydantic Author model."""
        from backend.models.data import Author
        try:
            return Author.from_db(self)
        except Exception as e:
            raise Exception(f"Error converting AuthorDB to Author: {e}")
    