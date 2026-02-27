import os
import asyncio
from config import logger
import httpx
import aiofiles
from pathlib import Path
from dotenv import load_dotenv


class HeyGenProducer:


    def __init__(self, api_key: str):

        self.api_key = api_key
        self.session: httpx.AsyncClient | None = None
        self.upload_url = f"https://upload.heygen.com/v1/asset"
        self.video_url = f"https://api.heygen.com/v2/video/av4/generate"
        self.status_url = f"https://api.heygen.com/v1/video_status.get"

    async def __aenter__(self):
        self.session = httpx.AsyncClient(headers=self.headers, timeout=30.0)
        logger.info("Initialized HeyGen session")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()

    async def upload_asset(self, file_path: str) -> str | None:
        """Uploads an asset to HeyGen.        """
        
        content_type_map = {
            ".jpg": "image/jpeg", 
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".mp3": "audio/mp3", 
            ".wav": "audio/wav",
        }

        ext = Path(file_path).suffix.lower()
        
        content_type = content_type_map.get(ext)
        
        if not content_type:
            logger.error(f"Unsupported file type for upload: {ext}")
            return None

        headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": content_type
        }
        
        try:
            async with aiofiles.open(file_path, "rb") as f:
                file_content = await f.read()

            logger.debug(f"Uploading asset {file_path} to HeyGen...")
            
            response = await self.session.post(self.upload_url, headers=headers, data=file_content)
            response.raise_for_status()
            
            response_data = response.json().get("data", {})
            
            return response_data.get("id")
        
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error uploading asset {file_path}: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Failed to upload asset {file_path}: {e}")
            return None

    async def generate_video(
        self, 
        image_path: str, 
        audio_path: str, 
        voice_id: str,
        title: str = "",
        movement: str = "",
    ) -> str | None:
        """Generates a video from an image and an audio file."""
        
        image_id, audio_id = await asyncio.gather(
            self.upload_asset(image_path),
            self.upload_asset(audio_path)
        )
        
        if not image_id or not audio_id:
            logger.error("Failed to upload one or more assets.")
            return None

        payload = {
            "video_orientation": "portrait",
            "image_key": image_id,
            "video_title": title,
            "voice_id": voice_id,
            "custom_motion_prompt": movement,
            "enhance_custom_motion_prompt": True
        }
        
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "x-api-key": self.api_key
        }

        try:
            response = await self.session.post(self.video_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json().get("data")
            video_id = data.get("video_id")
            logger.info(f"Successfully created video with ID: {video_id}")
            return video_id
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error creating video: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Failed to create video: {e}")
            return None

    async def get_video_status(self, video_id: str) -> dict | None:
        """Retrieves the status of a video."""
        
        try:
            response = await self.session.get(f"{self.status_url}?video_id={video_id}")
            response.raise_for_status()
            
            data = response.json().get("data")
            logger.info(f"Status for video {video_id}: {data.get('status')}")
            return data
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting video status: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Failed to get video status: {e}")
            return None

    async def download_video(self, video_url: str, output_path: str) -> bool:
        """Downloads a video from a URL. """
        try:
            async with self.session.stream("GET", video_url) as r:
                r.raise_for_status()
                async with aiofiles.open(output_path, "wb") as f:
                    async for chunk in r.aiter_bytes():
                        await f.write(chunk)
                logger.info(f"Successfully downloaded video to {output_path}")
                return True
        except Exception as e:
            logger.error(f"Failed to download video: {e}")
            return False


async def main():
    load_dotenv()
    api_key = os.getenv("HEYGEN_API_KEY")

    if not api_key:
        print("Error: HEYGEN_API_KEY not found in environment variables or .env file.")
        return

    # Create dummy files for demonstration
    image_file = "test_image.jpg"
    audio_file = "test_audio.mp3"

    if not os.path.exists(image_file):
        print(f"Creating dummy image file: {image_file}")
        with open(image_file, "w") as f:
            f.write("dummy image data")

    if not os.path.exists(audio_file):
        print(f"Creating dummy audio file: {audio_file}")
        with open(audio_file, "w") as f:
            f.write("dummy audio data")

    async with HeyGenProducer(api_key=api_key) as service:
        video_id = await service.generate_video(
            image_path=image_file,
            audio_path=audio_file,
        )

        if not video_id:
            print("Failed to start video generation.")
            return

        while True:
            await asyncio.sleep(3)
            status_data = await service.get_video_status(video_id)
            if not status_data:
                break

            status = status_data.get("status")
            if status == "completed":
                video_url = status_data.get("video_url")
                if video_url:
                    output_path = f"{video_id}.mp4"
                    download_success = await service.download_video(video_url, output_path)
                    if download_success:
                        print(f"Video downloaded successfully to {output_path}")
                    else:
                        print("Failed to download video.")
                else:
                    print("Video completed, but no URL was provided.")
                break
            elif status == "failed":
                error_message = status_data.get("error", "Unknown error")
                print(f"Video generation failed: {error_message}")
                break


if __name__ == "__main__":
    asyncio.run(main())