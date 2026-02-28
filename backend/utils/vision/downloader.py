import asyncio
from config import logger, configuration
from aiohttp import ClientSession, ClientTimeout, ClientError
import aiofiles
from tqdm import tqdm
import uuid
from pathlib import Path
from urllib.parse import urlparse
import mimetypes
from typing import List, Dict


class MediaDownloader:
    """
    A class that downloads media files from URLs.
    This class is designed to download media files from URLs and save them to a specified folder.

    Args:
        timeout (int): The timeout for the request.
        retries (int): The number of retries for the request.
    """

    def __init__(self, timeout: int = 300, retries: int = 3):
        """Initialize the MediaDownloader."""

        self.session = ClientSession(
            timeout=ClientTimeout(total=timeout, connect=10),
            trust_env=True,  # respect https_proxy / http_proxy env vars
        )
        self.retries = retries

    def get_headers(self) -> dict[str, str]:
        """Get the headers for the request."""

        return {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            "Sec-Ch-Ua": '"Not(A:Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Referer": "https://www.google.com/",
        }
    
    async def download_media(self, url: str | List[str], media_id: str) -> List[str] | str :
        """Download a media file or a list of media files from URLs."""
        
        if isinstance(url, list):
            # Download a list of media files from URLs.
            tasks = [self._download_single(u, media_id, i) for i, u in enumerate(url)]
            results = await asyncio.gather(*tasks)
            return [r for r in results if r is not None]

        elif isinstance(url, str):
            return await self._download_single(url, media_id, 0)
        else:
            logger.error(f"Invalid URL type: {type(url)}")
            return ""

    async def _download_single(self, url: str, media_id: str, position: int = 0) -> str | None:
        """Download a single media file from a URL with retries."""

        # Create the destination folder for the media file.
        directory = configuration["directory"]["download"]
        destination_folder = Path(__file__).parents[3] / directory 
        destination_folder.mkdir(parents=True, exist_ok=True)

        # Download the media file with retries.
        for attempt in range(self.retries):
            try:

                async with self.session.get(url, headers=self.get_headers()) as response:
                    response.raise_for_status()

                    total_size = int(response.headers.get("content-length", 0))
                    if total_size == 0:
                        logger.warning(f"No content length found for {url}")
                        return url
                    
                    # If the file size is > 100MB, return the original url
                    # We don't want to download files that are too large.
                    if total_size > 1024 * 1024 * 100:
                        logger.warning(f"File size is too large: {total_size/1024/1024:.1f} MB, return original url.")
                        return url
                    
                    content_type = response.headers.get("Content-Type")
                    file_extension = mimetypes.guess_extension(content_type, strict=False) if content_type else None
                    
                    if not file_extension:
                        file_extension = Path(urlparse(url).path).suffix or ".jpg"
                    
                    # Media id in the filename to avoid duplicate filenames.
                    # Put all the media into the same folder make it easier for browsing.
                    filename = destination_folder / f"{str(media_id)}_{str(uuid.uuid4())[:8]}{file_extension}"

                    async with aiofiles.open(filename, "wb") as f:
                        with tqdm(
                            total=total_size if total_size > 0 else None,
                            unit="B",
                            unit_scale=True,
                            desc=f"Downloading {filename.name}",
                            position=position,
                            leave=False,
                        ) as pbar:
                            chunk_size = 8192
                            while True:
                                chunk = await response.content.read(chunk_size)
                                if not chunk:
                                    break
                                await f.write(chunk)
                                pbar.update(len(chunk))

                    logger.debug(f"Downloaded media {url} (size: {filename.stat().st_size / 1024:.1f} KB)")
                    return str(filename)

            except (ClientError, asyncio.TimeoutError) as e:
                logger.warning(f"Attempt {attempt + 1}/{self.retries} for {url} failed: {e}")
                if attempt + 1 < self.retries:
                    await asyncio.sleep(2 ** attempt)  # exponential backoff: 1s, 2s, 4s
                else:
                    logger.error(f"All {self.retries} retries failed for {url}, returning original url")

            except Exception as e:
                logger.error(f"Unexpected error downloading {url}: {e}")
                break
        
        return url

    
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager and close the client session."""
        await self.close()

    async def close(self):
        """Closes the client session."""
        if self.session and not self.session.closed:
            await self.session.close()
