import asyncio
from datetime import datetime, timezone, timedelta
from config import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.core.database import DataInterface
from backend.core.redis import RedisManager, Tracker
from .twitter import TwitterReporter
from .weibor import WeiboReporter


class AggregatorScheduler:
    """
    Aggregator Scheduler for managing Media scraping.
    
    Attributes:
        redis_client (RedisManager): The Redis cache manager.
        database (DataInterface): The database client.
        tracker (Tracker): The tracker for tracking news items.
        _is_shutdown (bool): Whether the scheduler is shutdown.
        
        twitter_reporter (TwitterReporter): The Twitter scraper class.
        weibo_reporter (WeiboReporter): The Weibo scraper class.
        scheduler (AsyncIOScheduler): The scheduler.
    
    """
    
    def __init__(self):
        self.redis_client: RedisManager = RedisManager("Scheduler")
        self.database: DataInterface = DataInterface("Scheduler")
        self.tracker: Tracker = Tracker()
        
        # Pass redis client to aggregators
        self.twitter_reporter: TwitterReporter = TwitterReporter(
            redis=self.redis_client,
            database=self.database,
            tracker=self.tracker,
        )
        self.weibo_reporter: WeiboReporter = WeiboReporter(
            redis=self.redis_client,
            database=self.database,
            tracker=self.tracker,
        )

        self.scheduler = AsyncIOScheduler()
        self._is_shutdown = False
        
    def _get_current_interval(self) -> int:
        """Determine the appropriate interval based on current time."""
        
        # temporary intervals, peak can be 5 minutes or less
        PEAK_INTERVAL = 30
        OFF_PEAK_INTERVAL = 30
        
        # Get the current PST time, the news is more tracked on PST time
        current_time = datetime.now(timezone.utc) + timedelta(hours=-8)
        current_hour_pst = current_time.hour

        if 2 <= current_hour_pst <= 8:
            return OFF_PEAK_INTERVAL
        return PEAK_INTERVAL

    async def _reschedule_job(self, job_id: str) -> None:
        """Reschedule a job with updated interval."""

        job = self.scheduler.get_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        current_interval = job.trigger.interval.total_seconds() // 60
        new_interval = self._get_current_interval()
        
        if current_interval == new_interval:
            # Only update if interval has changed
            return
        
        try:            
            self.scheduler.reschedule_job(
                job_id,
                trigger='interval',
                minutes=new_interval,
                misfire_grace_time=300
            )
            logger.debug(f"Rescheduled {job_id} with new interval: {new_interval} minutes")
            
        except Exception as e:
            logger.error(f"Error rescheduling {job_id}: {str(e)}")

    async def start(self) -> None:
        # Schedule different scraping frequencies
        # TODO: Add RSS scraping, initialize database here
        
        await asyncio.gather(
            self.twitter_reporter.initialize(),
            self.weibo_reporter.initialize()
        )

        try:
            initial_interval = self._get_current_interval()

            # Twitter reporter
            self.scheduler.add_job(
                func=self.twitter_reporter.fetch,
                trigger='interval',
                minutes=initial_interval,
                id='twitter_reporter',
                max_instances=1,
                replace_existing=True,
                misfire_grace_time=300,
                next_run_time=datetime.now()
            )
            
            # Weibo reporter 
            # self.scheduler.add_job(
            #     func=self.weibo_reporter.fetch,
            #     trigger='interval',
            #     minutes=initial_interval,
            #     id='weibo_reporter',
            #     max_instances=1,
            #     replace_existing=True,
            #     misfire_grace_time=300,
            #     next_run_time=datetime.now()
            # )

            # Add a job to check and update intervals every hour for peak time
            # self.scheduler.add_job(
            #     func=self._reschedule_job,
            #     args=['twitter_reporter'],
            #     trigger='cron',
            #     hour='*',  # Every hour
            #     id='interval_updater'
            # )

            # self.scheduler.add_job(
            #     func=self.scrape_rss,
            #     trigger='interval',
            #     minutes=10,  # Lower frequency for RSS
            #     id='rss_scraper'
            # )
                    
            self.scheduler.start()
            logger.debug("Aggregator Scheduler started.")
            
        except Exception as e:
            raise Exception(f"Error setting up aggregator scheduler: {str(e)}")

    async def __aenter__(self):
        """ Enter context manager """
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """ Exit context manager """
        await self.shutdown()
        
    async def shutdown(self) -> None:
        """Gracefully shutdown the scheduler. Safe to call multiple times."""
        if self._is_shutdown:
            return

        try:
            # First stop accepting new jobs
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
            
            # Then close connections
            await self.database.close()
            await self.redis_client.close()
            await self.tracker.close()
            await self.twitter_reporter.close()
            await self.weibo_reporter.close()
            
            self._is_shutdown = True
            logger.debug("Aggregator Scheduler shutdown successfully.")
            
        except Exception as e:
            logger.error(f"Error during Aggregator Scheduler shutdown: {str(e)}")

