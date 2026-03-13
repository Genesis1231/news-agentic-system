from config import logger, configuration
from redis.asyncio import Redis, ConnectionPool
from typing import Dict, List, Any
from datetime import datetime, timezone
import json


class Tracker:
    def __init__(self):
        # Initialize Redis connection
        self.redis_pool = self._get_redis_pool()
        self.redis_client = Redis(connection_pool=self.redis_pool)
        
        self.tracking_time = 3600 * 24 * 7 # keep tracking data for 7 days
        self.key_prefix = "tracking:item"  # Key prefix for individual items
        self.timeline_key = "tracking:timeline"  # Timeline sorted set
    
    def _get_redis_pool(self) -> ConnectionPool:
        """Get a Redis connection pool."""
        return ConnectionPool(
            host=configuration["redis"]["host"],
            port=configuration["redis"]["port"],
            db=configuration["redis"]["database"]["monitor"],  
            max_connections=10,
            retry_on_timeout=True,  
            socket_timeout=5,
            socket_connect_timeout=5,
            decode_responses=True
        )

    def _serialize_field(self, value: Any) -> Any:
        """Serialize a field value for Redis storage."""
        if isinstance(value, (Dict, List)):
            try:
                return json.dumps(value, indent=4, ensure_ascii=False)
            except Exception as e:
                logger.error(f"Could not JSON serialize complex type {type(value)}: {e}.")
                return "[]" if isinstance(value, List) else "{}"
                
        elif isinstance(value, bool):
            return str(value).lower()  # 'true' or 'false'
        elif value is None:
            return ""  # Store None as empty string
        return str(value) 

    def _merge_details(self, current_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
        """ Merge the details of the current data with the new data """

        # Optimize by only processing the 'details' key specially and handling other keys directly
        result = current_data.copy()
        
        # Special handling for 'details' key
        if "details" in new_data:
            try:
                current_details = current_data.get("details", {})
                if isinstance(current_details, str):
                    current_details = json.loads(current_details)
                
                new_details = new_data["details"]
                if isinstance(current_details, Dict) and isinstance(new_details, Dict):
                    result["details"] = {**current_details, **new_details}
                else:
                    result["details"] = new_details
            except Exception as e:
                logger.error(f"Could not merge details: {e}")
                result["details"] = new_data["details"]
            
            # Remove details from new_data to avoid processing it again
            new_data_remaining = {k: v for k, v in new_data.items() if k != "details"}
        else:
            new_data_remaining = new_data
            
        # Update all other keys directly
        result.update(new_data_remaining)
        
        return result

    async def track(self, data: Dict[str, Any]) -> None:
        """
        Smart tracking function that creates or updates an item in Redis.
        
        Based on the 'id' field:
        - If the item doesn't exist in Redis, creates it with all provided fields
        - If the item exists, intelligently merges the changes (especially for nested dicts)
        
        Always updates the timestamp and score in the timeline sorted set.
        """
 
        if not (item_id:=data.get("id")):
            logger.error(f"Cannot track data without 'id' field: {data}")
            return
        
        # Set up keys and timestamp
        item_key = f"{self.key_prefix}:{item_id}"
        timestamp = datetime.now(timezone.utc)
        
        try:
            # Check if the item exists and get its current data
            current_item = await self.redis_client.hgetall(item_key)
            
            # Make a copy of the new data
            data_to_store = data.copy()
            
            # Add timestamp field if not present, not needed for now
            # if "timestamp" not in data_to_store:
            #     data_to_store["timestamp"] = timestamp.isoformat()
            
            # If the item exists, merge the data intelligently
            if current_item:
                data_to_store = self._merge_details(current_item, data_to_store)
            
            # Prepare data by serializing complex types
            serialized_data = {k: self._serialize_field(v) for k, v in data_to_store.items()}
            
            # Use a pipeline for all Redis operations
            async with self.redis_client.pipeline(transaction=True) as pipe:
                # Set/update fields in the item's hash
                await pipe.hset(item_key, mapping=serialized_data)
                await pipe.expire(item_key, self.tracking_time)
                
                # Update item in timeline with current timestamp as score
                await pipe.zadd(self.timeline_key, {item_key: timestamp.timestamp()})
                await pipe.expire(self.timeline_key, self.tracking_time)
                
                # Execute all commands
                await pipe.execute()
                
                operation = "Updated" if current_item else "Created"
                logger.debug(f"{operation} item: {item_key} with {len(serialized_data)} fields.")
                
        except Exception as e:
            logger.error(f"Error tracking data for key {item_key}: {str(e)}")    
 
    async def log(self, id: str, message: str) -> None:
        """Add a message to the Redis log"""
        
        if not id or not message:
            logger.error(f"Cannot track data without 'id' or 'message' field")
            return
        
        # Set up keys and timestamp
        item_key = f"{self.key_prefix}:{id}"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            # Format log entry
            log_entry = f"{timestamp} - {message}"

            # Get existing logs and append new log entry
            current_logs = await self.redis_client.hget(item_key, "log")
            if current_logs is not None:
                try:
                    logs = json.loads(current_logs)
                    logs.append(log_entry)
                except Exception:
                    logs = [log_entry]  # Start fresh if logs are corrupted
            else:
                logs = [log_entry]
            
            # Use pipeline for atomic operations
            async with self.redis_client.pipeline(transaction=True) as pipe:
                await pipe.hset(item_key, "log", json.dumps(logs, indent=4, ensure_ascii=False))
                await pipe.expire(item_key, self.tracking_time)
                await pipe.execute()
                
        except Exception as e:
            logger.error(f"Error logging message for key {item_key}: {str(e)}")


    async def close(self) -> None:
        """Gracefully shutdown Redis connection pool"""
        try:
            await self.redis_client.close()
            await self.redis_pool.disconnect()
            logger.debug("Redis tracker shutdown successfully.")
        except Exception as e:
            logger.error(f"Error during tracker shutdown: {str(e)}")
