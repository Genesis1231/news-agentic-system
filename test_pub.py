
import multiprocessing
import asyncio
from backend.utils.vision.video import VideoAnalyzer

# multiprocessing.set_start_method("spawn", force=True)

from dotenv import load_dotenv
load_dotenv()

async def run_test():
    video_analyzer = VideoAnalyzer()
    result = await video_analyzer.analyze("tests/test_video.mp4")
    print(result)
        
# Execute the async function
asyncio.run(run_test())