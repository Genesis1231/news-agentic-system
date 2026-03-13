from config import logger
import asyncio
import streamlit as st
import pandas as pd
import random
import json
from redis import Redis
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from backend.core.database import DataInterface
from backend.models.SQL import RawNewsDB, NewsDB
from .styles import STAGES


@st.cache_data(ttl=3)
def fetch_news_data(_database: DataInterface, limit: int = 1000) -> pd.DataFrame:
    """Fetch news data from PostgreSQL.

    Args:
        _database: DataInterface instance (underscore prefix for Streamlit cache).
        limit: Maximum number of recent items to fetch.

    Returns:
        DataFrame containing news items sorted by timestamp (newest first).
    """
    default_columns = ['id', 'timestamp', 'status', 'headline', 'author', 'url',
                       'source', 'details', 'log']
    try:
        df = asyncio.run(_fetch_from_postgres(_database, limit))
        if df.empty:
            return pd.DataFrame(columns=default_columns)
        return df.reindex(columns=default_columns, fill_value=None)
    except Exception as e:
        logger.error(f"Error fetching news from PostgreSQL: {e}")
        return pd.DataFrame(columns=default_columns)


async def _fetch_from_postgres(database: DataInterface, limit: int) -> pd.DataFrame:
    """Async helper to query PostgreSQL and build the dashboard DataFrame."""

    # 1. Query raw_news_items ordered by timestamp desc
    raw_items = await database.database_manager.query(
        RawNewsDB, order_by="timestamp", desc=True, limit=limit
    )

    if not raw_items:
        return pd.DataFrame()

    # 2. Collect raw IDs and query matching news_items
    raw_ids = [raw.id for raw in raw_items]
    news_items = await database.database_manager.query(
        NewsDB, filters={"raw_id": raw_ids}, limit=5000
    )

    # 3. Group news_items by raw_id
    news_by_raw = defaultdict(list)
    for item in news_items:
        news_by_raw[item.raw_id].append(item)

    # 4. Build rows
    rows = [_build_row(raw, news_by_raw.get(raw.id, [])) for raw in raw_items]

    return pd.DataFrame(rows)


def _build_row(raw, news_items) -> dict:
    """Build a single dashboard row from a RawNewsItem and its associated NewsItems."""

    # Author name from the eager-loaded relationship
    author_name = raw.author.name if raw.author else raw.author_idname

    # Headline: use title, fallback to author+source
    headline = raw.title if raw.title else f"{author_name} posted on {raw.source_name}."

    return {
        "id": raw.id,
        "timestamp": pd.to_datetime(raw.timestamp, utc=True, errors='coerce'),
        "status": _derive_status(raw, news_items),
        "headline": headline,
        "author": author_name,
        "url": str(raw.source_url) if raw.source_url else None,
        "source": raw.source_name,
        "details": _build_details(raw, news_items),
        "log": [],  # Logs fetched on-demand from Redis in detail view
    }


def _derive_status(raw, news_items) -> str:
    """Derive dashboard status from raw_news_item and its news_items."""

    if not raw.is_processed:
        return "aggregated"

    if not news_items:
        return "processing"

    if any(ni.is_published for ni in news_items):
        return "published"

    if any(ni.is_produced for ni in news_items):
        return "production"

    return "processing"


def _build_details(raw, news_items) -> dict:
    """Reconstruct the details dict from structured PostgreSQL fields."""

    details = {
        "content": raw.text,
        "media": raw.media_content or {},
        "classification": {
            "news_category": raw.news_category or [],
            "news_type": raw.news_type or [],
            "source_level": raw.source_level or "N/A",
            "sentiment": raw.sentiment or "N/A",
            "relevance": raw.relevance or 0.0,
            "entities": raw.entities or [],
            "score": raw.potential_impact_score,
        },
    }

    if news_items:
        # Build evaluation with coverage depths
        depths = [ni.depth for ni in news_items if ni.depth]
        details["evaluation"] = {"coverage_depth": depths if depths else ["FLASH"]}

        # Per-depth fields
        for ni in news_items:
            depth = ni.depth.lower() if ni.depth else "flash"

            # Script
            if ni.script:
                details[f"{depth}_script"] = ni.script

            # Production status
            production = {}
            if ni.text:
                production["text"] = ni.text
            if ni.audio_path:
                production["audio"] = ni.audio_path
            if ni.video_path:
                production["video"] = ni.video_path
            if production:
                details[f"{depth}_production"] = production

            # Processing stage derivation
            if ni.is_published:
                details[f"{depth}_processing_stage"] = "finalization"
            elif ni.is_produced:
                details[f"{depth}_processing_stage"] = "finalization"
            elif ni.script:
                details[f"{depth}_processing_stage"] = "approval"
            else:
                details[f"{depth}_processing_stage"] = "pending"

    return details


def fetch_news_logs(redis_client: Redis, news_id) -> list:
    """Fetch logs for a specific news item from Redis tracking hash.

    Called on-demand from the detail page, not on every list load.

    Args:
        redis_client: Connected Redis client (decode_responses=True, DB 15).
        news_id: The raw news item ID.

    Returns:
        List of log strings, or a default message if unavailable.
    """
    try:
        log_data = redis_client.hget(f"tracking:item:{news_id}", "log")
        if log_data:
            return json.loads(log_data)
    except Exception as e:
        logger.error(f"Error fetching logs for item {news_id}: {e}")

    return ["No logs available yet."]


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
