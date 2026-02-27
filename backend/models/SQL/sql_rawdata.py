from datetime import datetime
from sqlalchemy import DateTime, String, Boolean, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column, Mapped
from typing import Dict, Any

from .base import BaseDB

class RawData(BaseDB):
    __tablename__ = "raw_data"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(String(16), nullable=False)  # e.g., 'twitter', 'reddit', etc.
    source_id: Mapped[str] = mapped_column(String(64), index=True, unique=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    author_idname: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_data: Mapped[Dict] = mapped_column(JSONB, nullable=False)
    
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    
    def to_schema(self) -> Dict[str, Any]:
        """ Convert SQLAlchemy RawData model to Raw Dict."""
        return {
            "id": self.id,
            "source_name": self.source_name,
            "source_id": self.source_id,
            "timestamp": self.timestamp,
            "author_idname": self.author_idname,
            "raw_data": self.raw_data,
            "is_processed": self.is_processed
        }
