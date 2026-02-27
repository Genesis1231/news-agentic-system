from datetime import datetime
from sqlalchemy import DateTime, String, Boolean, func, JSON, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column, Mapped
from typing import Dict, Any, List

from .base import BaseDB

class KnowledgeData(BaseDB):
    __tablename__ = "knowledge"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(String(16), nullable=False)  # e.g., 'twitter', 'reddit', etc.
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_query: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    content: Mapped[str] = mapped_column(String(4096), nullable=False) # truncated content
    raw_data: Mapped[Dict] = mapped_column(JSONB) # for social media data
    raw_content: Mapped[str] = mapped_column(String) # for html content
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[List[str]] = mapped_column(JSON, default=list)
    
    def to_schema(self) -> Dict[str, Any]:
        return {
            "source_name": self.source_name,
            "source_url": self.source_url,
            "source_query": self.source_query,
            "relevance_score": self.relevance_score,
            "notes": self.notes,
        }
