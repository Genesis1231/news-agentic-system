from typing import TypeVar
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, DateTime
from sqlalchemy.sql import func
from datetime import datetime

# Type variables for generic operations
ModelType = TypeVar("ModelType", bound=DeclarativeBase)

class BaseDB(DeclarativeBase):
    """Base class for all database models."""
    __abstract__ = True
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())