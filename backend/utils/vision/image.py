import io
from datetime import datetime
from config import logger
import asyncio
from typing import List
import base64
import httpx
import aiofiles
from PIL import Image, ImageOps

from langchain_core.messages import HumanMessage
from backend.utils.prompt import load_prompt

from backend.core.agent import BaseAgent

class ImageDescriptor(BaseAgent):
    """
    A class that processes and describes images using various vision models.
    It can handle image URLs or local file paths, and automatically optimizes
    images to reduce payload size for LLMs.
    
    Args:
        platform (str): The platform to use for the vision model.
        model_name (str): The name of the vision model to use.
        base_url (str): The base URL of the vision model.
        temperature (float): The temperature to use for the vision model.
    
    Class Attributes:
        URL_UNSUPPORTED_MODELS (Set[str]): The set of models that do not support image URLs.
        MAX_IMAGE_DIMENSIONS (Tuple[int, int]): The maximum dimensions of the image for optimization.
        
    """
    
    # Models that do not support web urls 
    # Deepseek API does not support image input, only claude sonnet support image input
    URL_UNSUPPORTED_MODELS = {"ollama"} # Using set for faster lookup
    MAX_IMAGE_DIMENSIONS = (1024, 1024)
    
    def __init__(
        self,
        platform: str = "Google",
        model_name: str | None = "gemini-2.5-flash", # Gemini recognizes famous people
        base_url: str | None = None,
        temperature: float = 0.1,
    ) -> None:
        """Initialize the ImageDescriptor and a shared httpx client."""
        config = {
            "name": "Image Descriptor",
            "platform": platform,
            "model_name": model_name,
            "base_url": base_url,
            "temperature": temperature,
        }
        super().__init__(config=config)

    def _optimize_image_sync(self, image_bytes: bytes, image_quality: int = 85) -> bytes:
        """
        Synchronous helper to downscale and recompress an image.
        Always returns JPEG bytes.
        """
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:

                # If the file size is < 500k, skip optimization and just return the original bytes.
                if len(image_bytes) < 300 * 1024:
                    return image_bytes
                
                img = ImageOps.exif_transpose(img)
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")

                resample = getattr(Image, "Resampling", Image).LANCZOS
                img.thumbnail(self.MAX_IMAGE_DIMENSIONS, resample)

                buffer = io.BytesIO()
                img.save(
                    buffer,
                    format="JPEG",
                    quality=image_quality,
                    optimize=True,
                    progressive=True,
                )
                optimized_bytes = buffer.getvalue()

                logger.debug(f"Image optimized to {len(optimized_bytes) / 1024:.1f} KB.")
                return optimized_bytes
                
        except Exception as e:
            logger.warning(f"Image optimization failed: {e}; returning original bytes")
            return image_bytes
            
    async def _optimize_image(self, image_bytes: bytes, image_quality: int = 85) -> bytes:
        """Asynchronously offloads image optimization to a separate thread."""
        return await asyncio.to_thread(
            self._optimize_image_sync, image_bytes, image_quality
        )

    async def convert_url(self, image_url: str) -> str | None:
        """Download an image from a URL and convert it to a base64 data URI."""

        try:
            async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
                response = await client.get(image_url)
                response.raise_for_status()
                
            content_bytes = response.content
            content_type = response.headers.get("content-type", "image/jpeg")

            if "image/svg" in content_type:
                image_b64 = base64.b64encode(content_bytes).decode("utf-8")
                return f"data:image/svg+xml;base64,{image_b64}"

            optimized_bytes = await self._optimize_image(content_bytes)
            image_b64 = base64.b64encode(optimized_bytes).decode("utf-8")

            return f"data:image/jpeg;base64,{image_b64}"

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch image from URL {image_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading image {image_url}: {e}")
            return None

    async def convert_file(self, image_path: str) -> str | None:
        """Read a local image file and convert it to a base64 data URI."""
        try:
            async with aiofiles.open(image_path, 'rb') as img_file:
                file_bytes = await img_file.read()

                # Optimize the image bytes and convert to a base64 data URI.
                optimized_bytes = await self._optimize_image(file_bytes)
                image_b64 = base64.b64encode(optimized_bytes).decode("utf-8")

            return f"data:image/jpeg;base64,{image_b64}"

        except FileNotFoundError:
            logger.error(f"Image file {image_path} not found.")
            return None
        except Exception as e:
            logger.error(f"Failed to read image file {image_path}: {e}")
            return None

    async def describe(
        self,
        urls: str | List[str],
        context: str = "",
    ) -> str:
        """
        Describe images using the configured vision model.
        
        Args:
            urls (str | List[str]): The image URLs to describe.
            context (str): The context to use for the description.
            
        Returns:
            str: The description of the images.
        """
        
        if not urls:
            logger.error(f"No image urls provided.")
            return ""
        
        # Ensure image_urls is always a list
        if isinstance(urls, str):
            urls = [urls]
            
        prompt = load_prompt("describe_image").format(context=context)
        content = [{"type": "text", "text": prompt}]
        
        # Convert urls to base64 data URI if needed
        convert_urls = self.model_config.get("platform") in self.URL_UNSUPPORTED_MODELS
        processed_urls = []
        for url in urls:
            if not url.startswith(("http://", "https://")):
                processed_urls.append(await self.convert_file(url))
            elif convert_urls:
                processed_urls.append(await self.convert_url(url))
            else:
                processed_urls.append(url)

        
        for processed in processed_urls:
            if processed is not None:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": processed}
                })
        
        # If no image URL found, return an empty string
        if len(content) == 1:
            logger.error(f"No valid images provided, image description failed.")
            return ""
        
        try:
            logger.debug(f"Analyzing images ({len(urls)}) ... ")
            response = await self._invoke([HumanMessage(content=content)])
            return response.content

        except Exception as e:
            logger.error(f"Failed to describe image: {urls} {str(e)}")
            return ""
    
