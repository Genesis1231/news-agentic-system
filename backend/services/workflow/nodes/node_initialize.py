from config import logger
from typing import Dict, Any
from langgraph.types import Command
from langgraph.graph import END

from backend.core.redis import tracker
from backend.services.workflow.state import NewsState, NewsStatus
from backend.models.data import RawNewsItem 
from backend.utils.vision import ImageDescriptor
from backend.utils.vision import VideoAnalyzer
from backend.core.database import DataInterface

class InitializationNode:
    def __init__(self, database: DataInterface) -> None:
        """Initialize the InitializationNode."""
        
        self.database = database
        self.image_descriptor = ImageDescriptor()
        self.video_analyzer= VideoAnalyzer()

    async def __call__(self, state: NewsState) -> Dict[str, Any]:

        raw_id = state.get("id")

        await tracker.log(raw_id, f"Initializing creative workflow.")
        await tracker.track({
            "id": raw_id, 
            "status": "processing"
        })
        
        # Get the news data and validate it
        raw_data: RawNewsItem = await self.database.get_single_rawnews(raw_id)
        if not raw_data or raw_data.is_processed:
            logger.debug(f"News (ID:{raw_id}) is not available or already processed.")
            return Command(
                update={"status": NewsStatus.FAILED},
                goto=END
            )

        # Interpret the media content
        if media := raw_data.media_content:
            context = raw_data.composed_content
            images = media.get("photo", {})
            videos = media.get("video", {})

            try:
                image_urls = images.get("urls")
                if image_urls and not images.get("description"):
                    photo_description = await self.image_descriptor.describe(
                        urls=image_urls, 
                        context=context,
                    )
                    
                    media['photo']['description'] = photo_description or "This is a photo."

                video_urls = videos.get("urls")
                if video_urls and not videos.get("description"):

                    if isinstance(video_urls, list):
                        # for testing phase.
                        logger.debug(f"Currently only one video is allowed.")
                        video_urls = video_urls[0] 

                    #video_tasks = [self.video_descriptor.describe(url, context) for url in video_urls]
                    #video_description = await asyncio.gather(*video_tasks)
                
                    video_description = await self.video_analyzer.analyze(video_urls, context)
                     
                    media['video']['description'] = video_description or "This is a video."

                # update the media content in the database
                raw_data.media_content = media
                await self.database.update_raw_news(raw_id, raw_data)
                
                # track the media content
                await tracker.track({
                    "id": raw_id, 
                    "details": {
                        "media": media
                    }
                })
                
            except Exception as e:
                logger.error(f"Error interpreting media content: {e}")
                return Command(
                    update={"status": NewsStatus.FAILED},
                    goto=END
                )

        # update the state and goto the next node
        return Command(
            update={"raw_news": raw_data },
            goto="node_classify"
        )
