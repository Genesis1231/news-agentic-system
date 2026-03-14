import os
import asyncio
from datetime import datetime, timedelta, timezone
from config import logger, configuration
from typing import List, Dict, Any

from apify_client import ApifyClientAsync

from backend.models.data import RawNewsItem, Author
from backend.core.redis import RedisManager, Tracker
from backend.core.reporter import BaseReporter
from backend.core.database import DataInterface
from backend.utils.vision import MediaDownloader
from backend.utils.metrics import potential_impact_score

class TwitterReporter(BaseReporter):
    """
    Twitter Aggregator class to fetch news from multiple Apify twitter scraper tasks.
    
    Args:
        redis (RedisManager): Redis manager for caching.
        database (DataInterface): Database interface for storing and retrieving data.
        tracker (Tracker): Tracker for tracking news items.
        
    Attributes:
        semaphore (asyncio.Semaphore): Semaphore to control concurrency.
        client (ApifyClientAsync): Apify client for making requests.
        downloader (MediaDownloader): Media downloader for downloading media files.
        
        fetched_ids (Set[str]): The set of indexed ids of the fetched news items.
        twitter_accounts (List[str]): The list of twitter accounts to fetch news from.
        
    """

    NUM_DAYS: int = 10  # how many days of tweets to fetch 
    NUM_FETCH_ITEMS: int = 20  # how many tweets to fetch from each account
    CONCURRENCY: int = 20  # how many concurrent processes to process tweets
    BATCH_SIZE: int = 5  # how many accounts to fetch at a time
    
    def __init__(
        self,
        redis: RedisManager,
        database: DataInterface,
        tracker: Tracker
    ) -> None:
        # BaseAggregator init
        super().__init__(
            source_type="twitter",
            redis=redis,
        )
        self.database: DataInterface = database
        
        self.semaphore: asyncio.Semaphore | None = asyncio.Semaphore(self.CONCURRENCY)
        self.client: ApifyClientAsync | None = ApifyClientAsync(os.getenv("APIFY_TOKEN"))
        self.downloader: MediaDownloader = MediaDownloader()
        self.tracker: Tracker = tracker
        
        self.actor_id: str = configuration["apify"]["actor_twitter"]
        self.fetched_ids: set[str] = set()
        self.twitter_accounts: list[str] = []
    
    async def initialize(self) -> None:
        """Initialize the Twitter Aggregator."""
        
        try:
            await self.load_fetched_ids()
        except Exception as e:
            raise Exception(f"Failed to initialize Twitter Aggregator: {e}")
    
    async def load_twitter_accounts(self) -> None:
        """Load the twitter accounts from the database."""
        
        authors = await self.database.load_authors()
        self.twitter_accounts = [
            author.idname for author in authors if author.x_url and author.enabled
        ]
        logger.debug(f"Loaded {len(self.twitter_accounts)} Twitter accounts.")

    async def load_fetched_ids(self) -> None:
        """Get the set of indexed ids of the fetched news items."""

        # Fetch the ids from the last N days (limit=0 to load ALL, not just default 100)
        time_range = (datetime.now(timezone.utc) - timedelta(days=self.NUM_DAYS), None)
        fetched_data = await self.database.load_raw_data(
            time_range=time_range,
            limit=0,
            source_name="twitter"
        )

        if not fetched_data:
            logger.info("No recent twitter posts found.")
            return

        # Collect unprocessed source_ids and bulk-check which already exist in raw_news_items
        unprocessed = [data for data in fetched_data if not data.get("is_processed")]
        unprocessed_source_ids = [data.get("source_id") for data in unprocessed]

        existing_news = set()
        if unprocessed_source_ids:
            existing_items = await self.database.load_raw_news(source_id=unprocessed_source_ids)
            existing_news = {item.source_id for item in existing_items}

        # Build fetched_ids set and handle unprocessed records
        score_updates = []
        preprocess_tasks = []
        for data in fetched_data:
            self.fetched_ids.add(data.get("source_id"))

            if not data.get("is_processed"):
                source_id = data.get("source_id")
                if source_id in existing_news:
                    raw_tweet = data.get("raw_data")
                    if raw_tweet:
                        timestamp = self._parse_tweet_timestamp(raw_tweet)
                        score = self._compute_impact_score(timestamp, raw_tweet)
                        score_updates.append((source_id, score))
                    await self.database.update_raw_data(data.get("id"), {"is_processed": True})
                    continue
                preprocess_tasks.append(self.preprocess_tweet(data.get("raw_data"), data.get("id")))

        # Batch: update impact scores concurrently
        if score_updates:
            await asyncio.gather(*[
                self._update_score_by_source_id(sid, score)
                for sid, score in score_updates
            ])

        # Process unprocessed tweets concurrently
        if preprocess_tasks:
            await asyncio.gather(*preprocess_tasks)

        logger.debug(f"Loaded {len(self.fetched_ids)} recently fetched ids.")
    
    async def fetch(self) -> None:
        """Fetch news data directly from Apify twitter scraper actor."""

        # Reload accounts each cycle to pick up DB changes without restart
        await self.load_twitter_accounts()

        if not self.twitter_accounts:
            logger.error("No twitter accounts to fetch from.")
            return

        try:
            # Fetch tweets
            run_results = await self.fetch_tweets()

            # Fetch all datasets concurrently
            valid_runs = [run for run in run_results if run and "defaultDatasetId" in run]
            datasets = await asyncio.gather(*[
                self.client.dataset(run["defaultDatasetId"]).list_items(limit=10)
                for run in valid_runs
            ])

            # Process all dataset items: separate new tweets from score updates
            fetched_tasks = []
            score_updates = []
            for dataset in datasets:
                for data in dataset.items:
                    tweet_id = data.get("id")
                    if int(tweet_id) < 0 or data.get("isReply"):
                        continue

                    source_id = f'twitter_{tweet_id}'
                    if source_id in self.fetched_ids:
                        # Batch score update instead of awaiting one-by-one
                        timestamp = self._parse_tweet_timestamp(data)
                        score = self._compute_impact_score(timestamp, data)
                        score_updates.append((source_id, score))
                        continue

                    raw_data_id = await self.save_tweet(data)
                    fetched_tasks.append(self.preprocess_tweet(data, raw_data_id))

            logger.debug(f"Fetched {len(fetched_tasks)} new tweets, {len(score_updates)} score updates.")

            # Run score updates and new tweet processing concurrently
            tasks = []
            if score_updates:
                tasks.append(asyncio.gather(*[
                    self._update_score_by_source_id(sid, score)
                    for sid, score in score_updates
                ]))
            if fetched_tasks:
                tasks.append(asyncio.gather(*fetched_tasks))
            if tasks:
                await asyncio.gather(*tasks)

        except Exception as e:
            logger.error(f"Twitter Aggregator: Error fetching news from Twitter: {e}")
    
    async def fetch_tweets(self) -> List[Dict[str, Any]]:
        """Fetch tweets from Apify Twitter scraper actor."""
        
        # Get the start date
        start_date = datetime.now(timezone.utc) - timedelta(days=self.NUM_DAYS)  
        start_date_str = start_date.strftime("%Y-%m-%d_%H:%M:%S_UTC")

        logger.debug(f"Start fetching tweets dated from {start_date_str}")
        
        # Fetch in batches
        run_results = []
        for i in range(0, len(self.twitter_accounts), self.BATCH_SIZE):
            batch = self.twitter_accounts[i:i+self.BATCH_SIZE]
            
            # Create batch of tasks to run concurrently
            batch_tasks = [
                self.client.actor(self.actor_id).call(
                    run_input={
                        "from": account,
                        "maxItems": self.NUM_FETCH_ITEMS,
                        "queryType": "Latest",
                        "since": start_date_str,
                    },
                    logger=None
                )
                for account in batch
            ]
            
            # Wait for all tasks in current batch to complete
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Filter out invalid runs
            filtered_results = [run for run in batch_results if run is not None and not isinstance(run, Exception)]
            
            run_results.extend(filtered_results) 
        
        return run_results     
    
    async def preprocess_tweet(self, tweet: Dict[str, Any], raw_data_id: int | str) -> None:
        """Process the tweets."""
                        
        # add to fetched ids
        self.fetched_ids.add(f"twitter_{tweet.get('id')}")
        
        try:
            async with self.semaphore: #type: ignore
                news_data = await self.process_raw_tweet(tweet)

                # save the news item into database and push to redis
                news_id = await self.database.save_news_item(news_data)
                if news_id:
                    await self.database.update_raw_data(raw_data_id, {"is_processed": True})
                    await self.push_redis(str(news_id))
                    await self.tracker.log(str(news_id), f"News {news_data.source_id} - has been aggregated and preprocessed.")
                                        
        except Exception as e:
            logger.error(f"Error preprocessing tweet ID:{tweet.get('id')}: {e}")

    @staticmethod
    def _parse_tweet_timestamp(tweet: Dict[str, Any]) -> datetime:
        """Parse the tweet timestamp from Apify format."""
        return datetime.strptime(tweet['createdAt'], "%a %b %d %H:%M:%S %z %Y")

    @staticmethod
    def _compute_impact_score(timestamp: datetime, tweet: Dict[str, Any]) -> float:
        """Compute impact score from tweet engagement metrics."""
        return potential_impact_score(
            timestamp=timestamp,
            metrics_likes=tweet.get('likeCount', 0),
            metrics_comments=tweet.get('replyCount', 0),
            metrics_bookmarks=tweet.get('bookmarkCount', 0),
            metrics_reposts=tweet.get('retweetCount', 0) + tweet.get('quoteCount', 0),
            metrics_views=tweet.get('viewCount', 0)
        )

    async def _update_score_by_source_id(self, source_id: str, score: float) -> None:
        """Update impact score for a tweet by source_id."""
        try:
            existing = await self.database.load_raw_news(source_id=source_id)
            if existing:
                await self.database.update_raw_news(existing[0].id, {"impact_score": score})
        except Exception as e:
            logger.error(f"Error updating impact score for {source_id}: {e}")

    async def save_tweet(self, tweet: Dict[str, Any]) -> int | List[int] | None:
        """Save the raw data into database."""
        source_id = f"twitter_{tweet.get('id')}"
        try:
            timestamp = self._parse_tweet_timestamp(tweet)
            author = tweet['author']

            return await self.database.save_raw_data({
                    "source_name": "twitter",
                    "source_id": source_id,
                    "author_idname": author.get("userName"),
                    "timestamp": timestamp,
                    "raw_data": tweet
                })
        except Exception as e:
            logger.error(f"Error saving tweet raw data {source_id}: {e}")
            raise e
            
    
    async def process_raw_tweet(self, tweet: Dict[str, Any]) -> Dict[str, Any] | RawNewsItem | None:
        """Convert a tweet data to RawNewsItem pydantic model."""

        if not tweet:
            raise ValueError(f"Invalid tweet data: {type(tweet)}")

        # Parse timestamp and tweet id
        tweet_id = f"twitter_{tweet['id']}"
        timestamp = self._parse_tweet_timestamp(tweet)

        # author data
        if not (author_data := tweet['author']):
            raise ValueError(f"No author data found for tweet: {tweet_id}")
            
        author_idname = author_data['userName']
        author_name = f"{author_data['name']}({author_idname})"

        # Handle retweets and quotes
        tweet_text = tweet.get('text')
        tweet_media = tweet.get('extendedEntities', {}).get('media', [])
        retweet_data = tweet.get('retweeted_tweet', {})
        quote_data = tweet.get('quoted_tweet', {})

        if retweet_data or quote_data:
            # get the source data
            source_data = quote_data if quote_data else retweet_data
            
            source_timestamp = self._parse_tweet_timestamp(source_data)
            original_author = f"{source_data['author']['name']} ({source_data['author']['userName']})"
            original_text = source_data["text"]
            original_media = source_data.get('extendedEntities', {}).get('media', [])
            

            # format the tweet
            prefix = f"Retweeted from {original_author}'s tweet:"
            if quote_data:
                prefix = f"<main_content>{tweet_text}</main_content> \n {prefix}"
            
            tweet_text = f"""
                {prefix}
                <retweeted_content>{original_text}</retweeted_content> 
            """
            
            #TODO: need to add more media for retweets
            if any(original_media):
                tweet_media.extend(original_media)
        
        # Process media through image descriptor
        media_content = await self.download_media(media=tweet_media, post_id=tweet_id)

        # Compute impact score from raw metrics
        score = self._compute_impact_score(timestamp, tweet)

        # Return RawNewsItem pydantic object
        return RawNewsItem(
                source_name="twitter",
                source_id=tweet_id,
                source_url=tweet.get('url'),
                timestamp=timestamp,
                author_idname=author_idname,
                author=Author(
                    name=author_name,
                    idname=author_idname,
                ),
                text=tweet_text,
                media_content=media_content,
                impact_score=score
            )

    async def update_impact_score(self, source_id: str, tweet: Dict[str, Any]) -> None:
        """Recompute and update impact score for an already-fetched tweet."""
        timestamp = self._parse_tweet_timestamp(tweet)
        score = self._compute_impact_score(timestamp, tweet)
        await self._update_score_by_source_id(source_id, score)

    async def download_media(self, media: list[dict[str, Any]], post_id: str) -> Dict[str, Any]:
        """Download media files from URLs."""
        
        if not media:
            return {}

        media_list: Dict[str, Any] = {}

        photo_urls = [
            item["media_url_https"]
            for item in media
            if item.get("type") == "photo" and "media_url_https" in item
        ]
        if photo_urls:
            image_files = await self.downloader.download_media(photo_urls, post_id)
            media_list["photo"] = {"urls": image_files}

        video_urls = [
            item["media_url_https"]
            for item in media
            if item.get("type") == "video" and "media_url_https" in item
        ]
        if video_urls:
            video_files = await self.downloader.download_media(video_urls, post_id)
            media_list["video"] = {"urls": video_files}

        return media_list

    async def __aenter__(self):
        """Enter the context manager."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        await self.close()

    async def close(self) -> None:
        """Close the context manager and cleanup resources."""     
        try:
            await self.downloader.close()
        except Exception:
            logger.error("Failed to close media downloader.")
        finally:
            self.fetched_ids.clear()
            self.twitter_accounts.clear()
            self.client = None
            self.semaphore = None
