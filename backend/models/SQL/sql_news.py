from typing import List, Dict, Any
from sqlalchemy import Integer, String, Boolean, JSON, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseDB

class NewsDB(BaseDB):
    __tablename__ = 'news_items'
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    raw_id: Mapped[int] = mapped_column(Integer, ForeignKey("raw_news_items.id"), nullable=False, index=True)
        
    # Classification fields
    depth: Mapped[str] = mapped_column(String(16), default="")
    news_category: Mapped[List[str]] = mapped_column(JSON, default=list)
    news_type: Mapped[List[str]] = mapped_column(JSON, default=list)
    
    # Content fields
    title: Mapped[str] = mapped_column(String(1024), default="")
    text: Mapped[str] = mapped_column(String, nullable=False)
    script: Mapped[str] = mapped_column(String, default="")
    
    cover_image: Mapped[str] = mapped_column(String(2048), default="")
    audio_path: Mapped[str] = mapped_column(String(2048), default="")
    video_path: Mapped[Dict[str, str]] = mapped_column(JSON, default=dict)
    
    # Additional metadata
    cited_sources: Mapped[List[str]] = mapped_column(JSON, default=list)
    entities: Mapped[List[str]] = mapped_column(JSON, default=list)
    
    # Processing status
    is_produced: Mapped[bool] = mapped_column(Boolean, default=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
     
    def to_schema(self) -> "NewsItem": #type: ignore
        """ Convert SQLAlchemy NewsDB model to Pydantic NewsItem model."""
        from backend.models.data import NewsItem
        return NewsItem.from_db(self)
    