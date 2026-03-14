from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, Boolean, JSON, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseDB

class RawNewsDB(BaseDB):
    __tablename__ = 'raw_news_items'
    
    # Primary key will be news_id
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Source information
    source_name: Mapped[str] = mapped_column(String(16), nullable=False)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    source_url: Mapped[str] = mapped_column(String(2048))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    
    # Author fields
    author_idname: Mapped[str] = mapped_column(
        String(64), ForeignKey("authors.idname"), nullable=False, index=True
    )
    
    # Content fields
    title: Mapped[str] = mapped_column(String(1024))
    text: Mapped[str] = mapped_column(String, nullable=False)
    media_content: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Impact score (computed from engagement metrics at aggregation time)
    impact_score: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Classification fields
    news_category: Mapped[List[str]] = mapped_column(JSON, default=list)
    news_type: Mapped[List[str]] = mapped_column(JSON, default=list)
    sentiment: Mapped[str] = mapped_column(String(16), default="NEUTRAL")
    entities: Mapped[List[str]] = mapped_column(JSON, default=list)
    source_level: Mapped[str] = mapped_column(String(16), default="TERTIARY")
    relevance: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Processing status
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Additional metadata
    raw_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Relationships 
    author: Mapped["AuthorDB"] = relationship( #type: ignore
        "AuthorDB", 
        primaryjoin="RawNewsDB.author_idname == AuthorDB.idname",
        lazy="joined",
        viewonly=True
    ) 
    
    def to_schema(self) -> "RawNewsItem": #type: ignore
        """ Convert SQLAlchemy RawNewsDB model to Pydantic RawNewsItem model."""
        from backend.models.data import RawNewsItem
        return RawNewsItem.from_db(self)

    