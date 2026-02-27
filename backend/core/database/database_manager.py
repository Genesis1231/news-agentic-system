import asyncio
from config import logger
from datetime import datetime
from config import configuration, logger
from typing import Type, List, Any, Dict, Tuple
import json
import random

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker, AsyncEngine
from sqlalchemy import select, insert, update, delete, and_, Select
from sqlalchemy.exc import IntegrityError, OperationalError
from contextlib import asynccontextmanager
from pydantic import BaseModel

from backend.models.SQL.base import ModelType

class DatabaseManager:
    """
    Database manager class that provides a unified interface for database operations.
    """
    def __init__(self):
        self._retry_attempts: int = 3
        self._max_batch_size: int = 50
        self.engine: AsyncEngine = self.initialize_engine()
        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False
        )
        self._is_shutdown: bool = False
        
    def initialize_engine(self):
        """Initialize the database engine."""
        
        DB_config = configuration.get("database")
        db_url = f"postgresql+asyncpg://{DB_config.get('username')}:{DB_config.get('password')}@{DB_config.get('host')}:{DB_config.get('port')}/{DB_config.get('database')}"
        
        try:
            # TODO: Move this to a config file
            return create_async_engine(
                url=db_url,
            pool_size=20,
            max_overflow=30,
            pool_timeout=20,
            pool_pre_ping=True,
            pool_recycle=1800,
            pool_use_lifo=True,
                json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
                json_deserializer=json.loads
            )
        except Exception as e:
            logger.error(f"Error initializing database engine: {e}")
            raise
        
    @asynccontextmanager
    async def session(self):
        """Provide transactional operations with retry mechanism."""
        
        for attempt in range(self._retry_attempts):
            session: AsyncSession = self.session_factory()
            try:
                yield session
                await session.commit()
                break  # Success - exit the retry loop
                
            except IntegrityError as e:
                await session.rollback()
                logger.error(f"Integrity error occurred: {str(e)}")
                break
            
            except (OperationalError, asyncio.TimeoutError) as e:
                await session.rollback()
                if attempt == self._retry_attempts - 1:
                    logger.error(f"Final retry attempt failed: {str(e)}")
                
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(
                    f"Operation failed (attempt {attempt + 1}/{self._retry_attempts}), "
                    f"retrying in {wait_time:.2f}s: {str(e)}"
                )
                await asyncio.sleep(wait_time)
            finally:
                await session.close()


    async def create(
        self,
        model: Type[ModelType],
        input_data: Dict | BaseModel | List[Dict] | List[BaseModel]
    ) -> List[Dict] | List[BaseModel]:
        """
        Unified create function that handles single or multiple records.
        Silently ignores duplicate records.
        """

        successful_objs: List[ModelType] = []  # Store successfully processed objects

        async with self.session() as session:
            # Ensure input_data is a list
            if not isinstance(input_data, list):
                input_data = [input_data]
                
            db_objs = [
                model(**input_data_item) if isinstance(input_data_item, Dict)
                else input_data_item.to_db()
                for input_data_item in input_data
            ]
            
            # Process in batches for performance
            for i in range(0, len(db_objs), self._max_batch_size):
                batch_data = db_objs[i: i + self._max_batch_size]
                try:
                    session.add_all(batch_data)
                    await session.flush()
                    # Refresh all objects in the batch concurrently
                    refresh_results = await asyncio.gather(
                        *(session.refresh(obj) for obj in batch_data),
                        return_exceptions=True
                    )
                    for idx, res in enumerate(refresh_results):
                        if isinstance(res, Exception):
                            logger.warning(f"Error refreshing object at index {i + idx}: {res}")
                        else:
                            successful_objs.append(batch_data[idx])
                            
                except IntegrityError as e:
                    logger.warning(f"Skipping duplicate records in batch due to IntegrityError: {str(e)}")
                    await session.rollback()
                    continue
                            
                except Exception as e:
                    logger.error(f"Unhandled error occurred in batch: {str(e)}")
                    await session.rollback()
                    continue
            
            # Final commit after processing all batches
            await session.commit()
            return [obj.to_schema() for obj in successful_objs]

    async def get(self, model: Type[ModelType], id: int) -> BaseModel | None:
        """Get a single record by ID."""
        return await self.query(model, id=id)

    async def query(
        self,
        model: Type[ModelType],
        id: int | None = None,
        filters: Dict = {},
        skip: int = 0,
        limit: int = 100,
        order_by: str | None = None,
        desc: bool = True,
        time_range: Tuple[datetime, datetime | None] | None = None,
    ) -> BaseModel | List[BaseModel] | Dict | List[Dict] | None:
        """
        Unified query method that handles all types of database queries.
        
        Args:
            model: The SQLAlchemy model class
            id: single record lookup
            filters: Dictionary of field-value pairs for filtering
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            time_range: Tuple of (start_time, end_time) for time-based filtering
            order_by: Field name to sort by
            desc: Sort in descending order if True
        Returns:
            Single record if ID is provided, otherwise list of records
        """
        async with self.session() as session:
            # Start building the query
            statement: Select = select(model)
            conditions = []
            
            # Add ID filter if provided
            if id is not None:
                conditions.append(model.id == id)
            
            # Add custom filters
            if filters:
                for key, value in filters.items():
                    if not hasattr(model, key):
                        logger.warning(f"Filter field '{key}' does not exist in model {model.__name__}")
                        continue
                        
                    if value is None:
                        conditions.append(getattr(model, key).is_(None))
                    elif isinstance(value, (list, tuple)):
                        if value:  # Only add condition if list is not empty
                            conditions.append(getattr(model, key).in_(value))
                    else:
                        conditions.append(getattr(model, key) == value)
            
            # Add time range filter if provided
            if time_range:
                start_time, end_time = time_range
                
                # If end_time is None, set it to the current time
                if end_time is None:
                    end_time = datetime.now()
                    
                # if the model has a timestamp field, add a between condition
                if hasattr(model, 'timestamp'):
                    conditions.append(model.timestamp.between(start_time, end_time))
                else:
                    logger.warning(f"Model {model.__name__} does not have a 'timestamp' field.")
            
            # Combine all conditions
            if conditions:
                statement = statement.where(and_(*conditions))
            
            # Add pagination
            if skip:
                statement = statement.offset(skip)
            if limit:
                statement = statement.limit(limit)
            
            # Add sorting logic
            if order_by:
                if desc:
                    statement = statement.order_by(getattr(model, order_by).desc())
                else:
                    statement = statement.order_by(getattr(model, order_by))
            
            # Execute query
            results = await session.execute(statement)
            
            # Return appropriate type based on query
            if id is not None:
                # For single record lookup
                result = results.scalar_one_or_none()
                if result is None:
                    logger.warning(f"No record found when querying ID {id} in {model.__tablename__}")
                    return None
                return result.to_schema()
            
            # For multiple records
            all_results = results.scalars().all()
            if not all_results:
                logger.warning(f"No records found when querying {model.__tablename__}")
            
            return [result.to_schema() for result in all_results]
        
    async def update(
        self,
        model: Type[ModelType],
        id: int,
        input_data: Dict[str, Any] | BaseModel
    ) -> BaseModel | Dict[str, Any] | None:
        """Update a database record."""
          
        async with self.session() as session:
            if isinstance(input_data, BaseModel):
                update_data = input_data.to_dict()
            else:
                update_data = input_data
            
            statement = (
                update(model)
                .where(model.id == id)
                .values(**update_data)
            )
            
            result = await session.execute(statement)
            
            if result.rowcount == 0:
                logger.warning(f"No record found when updating ID {id} in {model.__tablename__}")
                return None
            
            return await self.get(model, id)


    async def delete(
        self,
        model: Type[ModelType],
        id: int
    ) -> None:
        """Delete a record."""
        async with self.session() as session:
            statement = delete(model).where(model.id == id)
            result = await session.execute(statement)
            
            if result.rowcount == 0:
                logger.warning(f"No record found when deleting ID {id} in {model.__tablename__}")
                 

    async def health_check(self) -> bool:
        """Check database connection health."""
        try:
            async with self.session() as session:
                await session.execute(select(1))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return False

    async def shutdown(self) -> None:
        """Close the database connection."""
        if self._is_shutdown:
            return
        
        try:
            await self.engine.dispose()
            self._is_shutdown = True
            logger.debug("Database engine shutdown successfully.")
        except Exception as e:
            logger.error(f"Error while closing database connection: {str(e)}")


    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()