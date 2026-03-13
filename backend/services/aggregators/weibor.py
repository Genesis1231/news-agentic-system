import asyncio
from datetime import datetime, timedelta, timezone
from config import logger
from typing import List, Dict, Any, Set
from concurrent.futures import ThreadPoolExecutor

from backend.models.data import RawNewsItem, Author
from backend.core.redis import RedisManager, Tracker
from backend.core.reporter import BaseReporter
from backend.core.database import DataInterface
from backend.utils.vision import MediaDownloader
from backend.utils.metrics import potential_impact_score

from backend.utils.weibo_crawler.weibo import Weibo


class WeiboReporter(BaseReporter):
    """
    Weibo Aggregator class to fetch news from Weibo.
        
    Args:
        redis (RedisManager): Redis manager for caching.
        database (DataInterface): Database interface for storing and retrieving data.
        tracker (Tracker): Tracker for tracking news items.

    Attributes:
        database (DataInterface): Database interface for storing and retrieving data.
        semaphore (asyncio.Semaphore): Semaphore to control concurrency.
        descriptor (ImageDescriptor): Image descriptor for processing images.
        downloader (MediaDownloader): Media downloader for downloading media files.
        _executor (ThreadPoolExecutor): Dedicated bounded executor for running weibo crawler.
        
        fetched_ids (Set[str]): The set of indexed ids of the fetched news items.
        weibo_config (Dict[str, Any]): The configuration for the weibo crawler.
            
    """

    NUM_HOURS: int = 1  # how many hours of weibo posts to fetch 
    CONCURRENCY: int = 20  # how many concurrent processes to process posts  
    COOKIE: str = "_T_WM=9a2c57426f56de8a2ff5b9b451ffce61; SCF=AvrPd2G2oewaaWDgCGMvPy_H3jImUGBPQp9gQGpdXxbBqitNd-g-pPWdybaS0D_rYU0pbmL5kQeT3A0cphtNag8.; SUB=_2A25F3ftcDeRhGedI7VEV8ibOwzuIHXVmk3KUrDV6PUJbktANLWnukW1NVuDCemg9L146_03PhhtDnNZOTbFj3eiR; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9W53PuyMw6XXBcT2U8V_-DM_5JpX5KMhUgL.Fo2cSoeXeonE1hM2dJLoI7U39g9JMJH4; SSOLoginState=1759087372; ALF=1761679372"
    
    def __init__(
        self, 
        redis: RedisManager, 
        database: DataInterface,
        tracker: Tracker
    ) -> None:
        # BaseReporter init
        super().__init__(
            source_type="weibo",
            redis=redis,
        )
        self.database: DataInterface = database
        self.tracker: Tracker = tracker

        self.semaphore: asyncio.Semaphore = asyncio.Semaphore(self.CONCURRENCY)
        self.downloader: MediaDownloader = MediaDownloader()
        self._executor: ThreadPoolExecutor = ThreadPoolExecutor() # Dedicated bounded executor
        
        self.weibo_accounts: Dict[str, str] = {}
        self.weibo_config = self._create_weibo_config()
        self.fetched_ids: Set[str] = set()

    
    def _create_weibo_config(self) -> Dict[str, Any]:
        """Create configuration for weibo crawler."""

        return {
            "user_id_list": [],  # Will be populated with account IDs
            "only_crawl_original": 1,
            "remove_html_tag": 1,
            "since_date": "",
            "start_page": 1,
            "page_weibo_count": 10,
            "write_mode": [],  # No file writing
            "original_pic_download": 0,
            "retweet_pic_download": 0,
            "original_video_download": 0,
            "retweet_video_download": 0,
            "original_live_photo_download": 0,
            "retweet_live_photo_download": 0,
            "download_comment": 0,
            "comment_max_download_count": 0,
            "download_repost": 0,
            "repost_max_download_count": 0,
            "user_id_as_folder_name": 0,
            "cookie": self.COOKIE,  # Weibo cookie for authentication
        }

    async def initialize(self) -> None:
        """Initialize the Weibo Aggregator."""
        
        try:
            await asyncio.gather(
                self.load_weibo_accounts(),
                self.load_fetched_ids()
            )
            self.weibo_config["user_id_list"] = list(self.weibo_accounts.keys())
            
        except Exception as e:
            raise Exception(f"Failed to initialize Weibo Aggregator: {e}")

    async def load_weibo_accounts(self) -> None:
        """Load the weibo accounts from the database."""
        
        authors = await self.database.load_authors()
        for author in authors:
            if author.enabled and author.weibo_url:
                self.weibo_accounts[str(author.weibo_url).split('/')[-1]] = author.idname
        
        logger.debug(f"Loaded {len(self.weibo_accounts)} Weibo accounts.")

    async def load_fetched_ids(self) -> None:
        """Get the set of indexed ids of the fetched news items."""
        
        # Fetch the ids from the last N days
        time_range = (datetime.now(timezone.utc) - timedelta(days=1), None)
        fetched_data = await self.database.load_raw_data(time_range=time_range, source_name="weibo")
        
        if not fetched_data:
            logger.info("No recent weibo posts found in database.")
            return

        for data in fetched_data:
            self.fetched_ids.add(data.get("source_id"))
            
            # process the posts that are not processed previously
            if not data.get("is_processed"):
                await self.preprocess_weibo(data.get("raw_data"), data.get("id"))
        
        logger.debug(f"Loaded {len(self.fetched_ids)} recently fetched ids.")
    
    async def fetch(self) -> None:
        """Fetch news data from Weibo using the Weibo crawler directly."""

        if not self.weibo_accounts:
            logger.error("No weibo accounts to fetch from.")
            return

        try:
            # Fetch weibo posts in batches
            fetched_tasks = []
            posts = await self.fetch_weibo()
            
            # Process each post
            for post in posts:
                post_id = post.get("id")
                if (not post_id 
                    or f'weibo_{post_id}' in self.fetched_ids 
                    or not post.get("text")):  # Skip posts without content 
                    continue
                
                # save raw data and preprocess the post
                post["idname"] = self.weibo_accounts.get(str(post.get("user_id", "")), "")
                raw_data_id = await self.save_raw_weibo(post)
                if raw_data_id:
                    fetched_tasks.append(self.preprocess_weibo(post, raw_data_id))

            logger.debug(f"Fetched {len(fetched_tasks)} weibo posts.")

            # Process fetched posts
            if fetched_tasks:
                await asyncio.gather(*fetched_tasks)
                                    
        except Exception as e:
            logger.error(f"Weibo Aggregator: Error fetching news from Weibo: {e}")
    
    async def fetch_weibo(self) -> List[Dict[str, Any]]:
        """Fetch weibo posts using the Weibo crawler."""
        
        # Calculate date range
        # Use China Standard Time (UTC+8)
        end_date = datetime.now(timezone(timedelta(hours=8)))
        start_date = end_date - timedelta(hours=self.NUM_HOURS)
        
        try:
            # Create weibo config with current batch of user IDs
            config = self.weibo_config.copy()
            config["since_date"] = start_date.strftime("%Y-%m-%dT%H:%M:%S")

            # Run weibo crawler in a thread to avoid blocking
            loop = asyncio.get_running_loop()
            posts = await asyncio.wait_for(
                loop.run_in_executor(self._executor, self._run_weibo_collector, config),
                timeout=300 # 5 minutes
            )
            
            return posts 
            
        except Exception as e:
            logger.error(f"Error fetching weibo posts: {e}")
            return []
    
    def _run_weibo_collector(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run weibo crawler directly and collect posts from wb.weibo."""
        try:
            # Create Weibo instance with our config
            wb = Weibo(config)
            wb.start()
            return wb.weibo
            
        except Exception as e:
            logger.error(f"Error running weibo crawler: {e}")
            return []

    async def save_raw_weibo(self, post: Dict[str, Any]) -> int | None:
        """Save the raw data into database."""
        try:
            timestamp = self._parse_timestamp(post.get("created_at", ""))
            
            source_id = f"weibo_{str(post['id'])}"
            idname = str(post.get("idname", ""))
            
            return await self.database.save_raw_data({
                "source_name": "weibo",
                "source_id": source_id,
                "author_idname": idname,
                "timestamp": timestamp,
                "raw_data": post
            })
            
        except Exception as e:
            logger.error(f"Error saving weibo post raw data: {e}")
            return None
                
    async def preprocess_weibo(self, post: Dict[str, Any], raw_data_id: int | str) -> None:
        """Process the weibo posts."""
        
        # add to fetched ids
        self.fetched_ids.add(f"weibo_{post.get('id')}")
        
        try:
            async with self.semaphore:
                news_data = await self.process_raw_weibo(post)

                # save the news item into database and push to redis
                news_id = await self.database.save_news_item(news_data)
                if news_id:
                    await self.database.update_raw_data(raw_data_id, {"is_processed": True})
                    await self.push_redis(news_id)
                    await self.tracker.log(news_id, f"News {news_data.source_id} - has been aggregated and preprocessed.")
                                        
        except Exception as e:
            logger.error(f"Error preprocessing weibo post ID:{post.get('id')}: {e}")

            
    async def process_raw_weibo(self, post: Dict[str, Any]) -> RawNewsItem:
        """Convert a weibo post data to RawNewsItem pydantic model."""

        if not post or not (pid := post.get("id")):
            raise ValueError(f"Invalid weibo post data: {type(post)}")
        
        # Parse timestamp and post id
        post_id = f"weibo_{str(pid)}"
        timestamp = self._parse_timestamp(post.get("created_at", ""))
        source_url = f"https://m.weibo.cn/detail/{str(pid)}"
        user_id = str(post.get("idname", "")) # get the idname 
        author_name = post.get("screen_name", user_id)  # Weibo class uses "screen_name"

        # Post content
        post_content = post.get("text", "")  # Weibo class uses "text"
        
        # TODO: handle retweeted posts
        # retweet_content = post.get("retweet", "")
        # if retweet_content:
        #     post_content = f"{post_content}\n\nRetweet: {retweet_content}"

        # Process media
        post_images = post.get("pics")
        live_photos = post.get("live_photo_url", "")
        post_media = {
            "images": [url.strip() for url in post_images.split(",") if url.strip()],
            "video": post.get("video_url", ""),
            "live_photos": [url.strip() for url in live_photos.split(",") if url.strip()]
        }

        media_content = await self.download_media(post_media, post_id)
        # media_content = await self.interpret_media(
        #     post_media=post_media, 
        #     context=post_content
        # )
        
        # Compute impact score from raw metrics
        score = potential_impact_score(
            timestamp=timestamp,
            metrics_likes=int(post.get("attitudes_count", 0)),
            metrics_comments=int(post.get("comments_count", 0)),
            metrics_bookmarks=0,
            metrics_reposts=int(post.get("reposts_count", 0)),
            metrics_views=0
        )

        # Return RawNewsItem pydantic object
        return RawNewsItem(
            source_name="weibo",
            source_id=post_id,
            source_url=source_url,
            timestamp=timestamp,
            author_idname=user_id,
            author=Author(
                name=author_name,
                idname=user_id,
            ),
            text=post_content,
            media_content=media_content,
            impact_score=score
        )

    def _parse_timestamp(self, value: str | None) -> datetime:
        """Parse weibo timestamp formats into UTC datetime with robustness."""
        if not value:
            return datetime.now(timezone.utc)
        
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%a %b %d %H:%M:%S %z %Y"):
            try:
                dt = datetime.strptime(value, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))  # treat as Beijing local
                return dt.astimezone(timezone.utc)  # normalize to UTC
            except Exception:
                continue
        return datetime.now(timezone.utc)

    async def download_media(self, post_media: Dict[str, Any], post_id: str) -> Dict[str, Any]:
        """
        Process the media urls and return the media data.
        Extract images and videos from weibo post.
        """
        
 
        media_list = {}
        
        try:
            # Process images
            image_urls = post_media.get("images", [])
            live_urls = post_media.get("live_photos", [])
            video_url = post_media.get("video", "")
            
            if image_urls or live_urls:
                # Download the images first
                image_urls.extend(live_urls)
                image_files = await self.downloader.download_media(image_urls, post_id)

                media_list['photo'] = {
                    'urls': image_files,
                }

            if video_url:
                video_file = await self.downloader.download_media(video_url, post_id)
    
                media_list['video'] = {
                    'urls': [video_file],
                }
        except Exception as e:
            logger.error(f"Error downloading media: {e}")
            return {}
        
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
        await self.downloader.close()
        self._executor.shutdown(wait=True)
        
        # Reset state attributes
        self.fetched_ids.clear()
        self.weibo_accounts.clear()
        
        # Reset references
        self.semaphore = None