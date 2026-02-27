import asyncio
import argparse
from backend.utils.TTS import TTSGenerator
from backend.services.workflow import FlowOrchestrator
from backend.core.database import DataInterface

from moviepy import AudioFileClip

from dotenv import load_dotenv


load_dotenv()

async def run_test(test_id: int):

    orchestrator = FlowOrchestrator()
    result = await orchestrator.immediate(test_id)
    print(result)
    
    # speaker = TTSGenerator("aD6riP1btT197c6dACmy")
    # file_path, subtitle_path = await speaker.generate(result)
    
    # print(file_path, subtitle_path)
    # audio = AudioFileClip(file_path)
    # audio.audiopreview()

async def test_update():
    db = DataInterface("test")
    
    data = await db.get_single_rawnews(10)
    data.is_processed = True

    # Debug logging
    # Convert to dict and check
    # dict_data = data.to_db(output_dict=True)
    
    result = await db.update_raw_news(10, data)
    print(result)


# Execute the async function

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run test node with specified ID')
    parser.add_argument('-id', '--id', type=int, required=True, help='ID to run test with')
    args = parser.parse_args()
    
    asyncio.run(run_test(args.id))