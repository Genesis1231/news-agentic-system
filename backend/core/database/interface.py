from config import logger
from typing import Any, Dict, List, Mapping, Sequence, Tuple, Type, cast
from datetime import datetime
from pydantic import BaseModel

from backend.models.SQL.base import ModelType
from backend.models.SQL import RawNewsDB, RawData, AuthorDB, NewsDB
from backend.models.data import RawNewsItem, Author, NewsItem
from .database_manager import DatabaseManager

class DataInterface:
    """Interface for data access and manipulation."""
    def __init__(self, service: str = "") -> None:
        """ Initialize DataInterface with service name. """
        self.database_manager: DatabaseManager = DatabaseManager()
        logger.debug(f"Data Interface layer initialized for {service}.")

    async def save_data(
        self,
        data: BaseModel | Sequence[BaseModel] | Mapping[str, Any] | Sequence[Mapping[str, Any]],
        model: Type[ModelType]
    ) -> int | List[int] | None:
        """Save data to database, support single and multiple records."""

        if not data:
            logger.error(f"No data provided when saving {model.__name__} to database.")
            return None

        try:
            normalized_data: Dict[str, Any] | BaseModel | List[Dict[str, Any]] | List[BaseModel]

            if isinstance(data, BaseModel):
                normalized_data = data
            elif isinstance(data, Mapping):
                normalized_data = dict(data)
            elif isinstance(data, Sequence) and not isinstance(data, (str, bytes)):
                if all(isinstance(item, BaseModel) for item in data):
                    normalized_data = [cast(BaseModel, item) for item in data]
                else:
                    normalized_data = [dict(cast(Mapping[str, Any], item)) for item in data]
            else:
                logger.error(f"Unsupported data type for saving {model.__name__}.")
                return None

            result = await self.database_manager.create(model, normalized_data)

            if not result:
                return None

            # extract ids from the result
            data_ids = [
                cast(int, getattr(item, "id") if isinstance(item, BaseModel) else item["id"])
                for item in result
            ]

            if isinstance(data, Sequence) and not isinstance(data, (str, bytes, BaseModel, Mapping)):
                return data_ids
            return data_ids[0]

        except Exception as e:
            logger.error(f"Error saving {model.__name__} to database: {e}")
            return None

    async def save_raw_news(self, content_data: RawNewsItem | List[RawNewsItem]) -> int | List[int] | None:
        """Save raw news to database."""
        return await self.save_data(content_data, RawNewsDB)

    async def save_raw_data(self, raw_data: Dict[str, Any] | List[Dict[str, Any]]) -> int | List[int] | None:
        """Save raw data to database."""
        return await self.save_data(raw_data, RawData)
    
    async def save_news_item(self, news_item: NewsItem | List[NewsItem]) -> int | List[int] | None:
        """Save news item to database."""
        return await self.save_data(news_item, NewsDB)

    async def load_authors(self, **kwargs) -> List[Author]:
        """ Load authors from database."""
        
        try:        
            result = await self.database_manager.query(AuthorDB, filters=kwargs)
            return cast(List[Author], result or [])
        except Exception as e:
            logger.error(f"Error loading authors from database: {e}")
            return []
    
    
    async def load_raw_data(
        self,
        time_range: Tuple[datetime, datetime] | None = None,
        limit: int = 100,
        **kwargs
    ) -> List[RawData]:
        """ Load raw data from database."""

        try:
            result = await self.database_manager.query(
                RawData,
                time_range=time_range,
                limit=limit,
                filters=kwargs
            )
            return cast(List[RawData], result or [])
        except Exception as e:
            logger.error(f"Error loading raw data from database: {e}")
            return []
        
    async def load_raw_news(self, **kwargs) -> List[RawNewsDB]:
        """ Load raw news from database."""
        try:        
            result = await self.database_manager.query(RawNewsDB, filters=kwargs)
            return cast(List[RawNewsDB], result or [])
        except Exception as e:
            logger.error(f"Error loading raw news from database: {e}")
            return []
    
    async def load_news(self, **kwargs) -> List[NewsDB]:
        """ Load news from database."""
        try:        
            result = await self.database_manager.query(NewsDB, filters=kwargs)
            return cast(List[NewsDB], result or [])
        except Exception as e:
            logger.error(f"Error loading news from database: {e}")
            return []
    
    async def get_single_data(self, model: Type[ModelType], data_id: int | str) -> BaseModel | None:
        """Get single data from database."""
        if isinstance(data_id, str):
            data_id = int(data_id.strip())
            
        try:
            return await self.database_manager.get(model, data_id)
        except Exception as e:
            logger.error(f"Error retrieving data {data_id}: {e}")
            return None
    
    async def get_single_rawnews(self, raw_id: int | str) -> RawNewsItem | None:
        """Retrieve a single raw news item from database."""
        result = await self.get_single_data(RawNewsDB, raw_id)
        return cast(RawNewsItem | None, result)
        
    async def get_single_news(self, news_id: int | str) -> NewsItem | None:
        """Retrieve a single news item from database."""
        result = await self.get_single_data(NewsDB, news_id)
        return cast(NewsItem | None, result)
    
    async def update_data(
        self, 
        model: Type[ModelType], 
        data_id: int | str, 
        updates: Dict[str, Any] | BaseModel
    ) -> BaseModel | Dict[str, Any] | None:
        """Update a data item in the database."""
        
        if isinstance(data_id, str):
            data_id = int(data_id.strip())

        try:
            return await self.database_manager.update(model, data_id, updates)
        except Exception as e:
            logger.error(f"Error updating data {data_id}: {e}")
            return None
        
    async def update_news(self, news_id: int | str, updates: Dict[str, Any] | NewsItem) -> BaseModel | Dict[str, Any] | None:
        """Update a news item in the database."""
        return await self.update_data(NewsDB, news_id, updates)
    
    async def update_raw_news(self, news_id: int | str, updates: Dict[str, Any] | RawNewsItem) -> BaseModel | Dict[str, Any] | None:
        """Update a raw news item in the database."""
        return await self.update_data(RawNewsDB, news_id, updates)
    
    async def update_raw_data(self, data_id: int | str, updates: Dict[str, Any]) -> BaseModel | Dict[str, Any] | None:
        """Update a raw data item in the database."""
        return await self.update_data(RawData, data_id, updates)
            
    async def close(self) -> None:
        """Close the database connection."""
        await self.database_manager.shutdown()
