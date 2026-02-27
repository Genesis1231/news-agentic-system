from config import logger
import streamlit as st
import pandas as pd
import random
import json
from redis import Redis
from datetime import datetime, timedelta, timezone

from .styles import STAGES


@st.cache_data(ttl=3)  # Cache data for 3 seconds
def fetch_news_data(
    _redis_client: Redis,   
    timeline_key: str = "tracking:timeline",
    limit: int = 1000
) -> pd.DataFrame:
    """Fetch news data from Redis, retrieving keys from the timeline sorted set.

    Retrieves news items stored as individual hashes with the following key pattern:
    - Timeline sorted set: 'tracking:timeline'
    - Item keys: 'tracking:item:{id}'

    Args:
        _redis_client: Connected Redis client instance (assumed decode_responses=True).
        limit: Maximum number of recent items to fetch.

    Returns:
        DataFrame containing news items sorted by last update time (newest first).
    """
    
    # Define default columns
    default_columns = ['id', 'timestamp', 'status', 'headline', 'author', 'url',
                       'source', 'details', 'log']
    
    # Get item keys from timeline sorted set
    item_keys = _redis_client.zrevrange(timeline_key, 0, limit - 1)
    if not item_keys:
        logger.warning(f"No news item keys found in Redis timeline: {timeline_key}")
        return pd.DataFrame(columns=default_columns)

    news_data = []
    for key in item_keys:
        try:
            item_data = _redis_client.hgetall(key)
            if not item_data:
                logger.warning(f"No data found for key {key}, deleted from timeline.")
                # Remove expired key from timeline to prevent future warnings
                _redis_client.zrem(timeline_key, key)
                continue
                
            if not item_data.get('headline'):
                item_data['headline'] = f'{item_data.get("author")} posted on {item_data.get("source")}.'
            
            # Convert timestamp to datetime
            timestamp = item_data.get('timestamp')
            item_data['timestamp'] = pd.to_datetime(timestamp, utc=True, errors='coerce')
            
            # Deserialize details and log
            if details := item_data.get('details', {}):
                try:
                    item_data['details'] = json.loads(details)
                except json.JSONDecodeError as e:
                    logger.error(f"Could not deserialize 'details' for key {key}: {e}")
            
            if logs := item_data.get('log', []):
                try:
                    item_data['log'] = json.loads(logs)
                except json.JSONDecodeError as e:
                    logger.error(f"Could not deserialize 'log' for key {key}: {e}")
            
            news_data.append(item_data)
            
        except Exception as e:
            logger.error(f"Error processing news item from key {key}: {str(e)}")

    if not news_data:
        logger.error("No valid news items processed from Redis")
        return pd.DataFrame(columns=default_columns)

    return pd.DataFrame(news_data).reindex(columns=default_columns, fill_value=None)


def filter_news_dataframe(
    df: pd.DataFrame, 
    search_query: str = "", 
    status_filter: str = "All",
    source_filter: str = "All",
    sort_by: str = "Timestamp"
) -> pd.DataFrame:
    """Filter and sort the news DataFrame based on UI controls.

    Args:
        df: The input DataFrame of news items.
        search_query: Text query to search in headlines.
        status_filter: Filter by status ('All' or specific status).
        source_filter: Filter by source ('All' or specific source).
        sort_by: Column to sort by ('Timestamp', 'Priority').

    Returns:
        Filtered and sorted DataFrame.
    """
    if df.empty:
        return df

    # Apply search filter (case-insensitive)
    if search_query:
        df = df[df['headline'].str.contains(search_query, case=False, na=False)]

    # Apply status filter
    if status_filter and status_filter != "All":
        if isinstance(status_filter, list):
            if status_filter:  # Only filter if list is not empty
                df = df[df['status'].isin(status_filter)]
        else:
            df = df[df['status'] == status_filter]

    # Apply source filter
    if source_filter and source_filter != "All":
        if isinstance(source_filter, list):
            if source_filter:
                df = df[df['source'].isin(source_filter)]
        else:
            df = df[df['source'] == source_filter]

    # Apply sorting
    if 'timestamp' in df.columns:
        # Ensure timestamp is datetime before sorting
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            
        # Handle different sorting options
        if sort_by == "Newest First":
            df = df.sort_values('timestamp', ascending=False, na_position='last')  # Newest first
        elif sort_by == "Oldest First":
            df = df.sort_values('timestamp', ascending=True, na_position='last')   # Oldest first
    
    return df



def generate_sample_news(count: int = 30) -> pd.DataFrame:
    """Generate sample news items for demo and testing"""
    
    now = datetime.now(timezone.utc)
    news_items = []
    
    # List of potential headlines
    headlines = [
        "Global Leaders Meet to Address Climate Change",
        "Tech Giant Unveils Revolutionary AI System",
        "Major Scientific Breakthrough in Renewable Energy",
        "Stock Markets See Unexpected Rise Amid Economic Concerns",
        "Health Researchers Announce Promising Vaccine Development",
        "Political Tensions Rise in Key Strategic Region",
        "Sports Team Wins Championship in Dramatic Upset",
        "Entertainment Industry Faces New Digital Challenges",
        "Educational Reform Bill Passes with Bipartisan Support",
        "Space Exploration Mission Discovers New Planetary Features"
    ]
    
    # News sources
    sources = ["Twitter", "CNN", "BBC", "Reuters", "AP News"]
    
    for i in range(count):
        # Create random timestamps within last 24 hours
        hours_ago = random.randint(0, 24)
        timestamp = now - timedelta(hours=hours_ago, 
                                  minutes=random.randint(0, 59))
        
        # Determine status based on time (older news more likely to be further along)
        progress = min(4, int(hours_ago / 5))  # 0-4 corresponding to stages
        if random.random() < 0.1:  # 10% chance of error at any stage
            status = "failed"
        else:
            status = STAGES[progress]
        
        # Create the news item with a unique ID
        news_id = f"news_{str(random.randint(10, 500))}"
        headline = random.choice(headlines)
        source = random.choice(sources)
        
        # Track stages this news has passed through
        stages_passed = STAGES[:progress+1]
        if status == "failed":
            stages_passed = STAGES[:STAGES.index(status)+1]
        
        # Generate stage timestamps
        stage_times = {}
        for j, stage in enumerate(stages_passed):
            stage_time = timestamp + timedelta(minutes=j*random.randint(10, 30))
            if stage_time > now:
                stage_time = now - timedelta(minutes=random.randint(1, 10))
            stage_times[stage] = stage_time.isoformat()
        
        # Create news item dictionary with all required fields
        news_item = {
            "id": news_id,  # Add the ID to the main news item
            "headline": headline,
            "source": source,
            "status": status,
            "timestamp": timestamp,
        }
     
        # Add complete news item to list
        news_items.append(news_item)
    
    # Create DataFrame
    return pd.DataFrame(news_items)