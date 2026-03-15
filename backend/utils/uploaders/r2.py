import os
import json
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Set

import boto3
from botocore.exceptions import ClientError

from config import logger, configuration


class R2Uploader:
    """Cloudflare R2 uploader for audio files and stories index."""

    def __init__(self) -> None:
        account_id = os.environ["R2_ACCOUNT_ID"]
        self._client = boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
            region_name="auto",
        )
        self._bucket = os.environ["R2_BUCKET_NAME"]

        r2_config = configuration.get("r2", {})
        self._public_url = r2_config.get("public_url", "").rstrip("/")
        self._stories_limit = r2_config.get("stories_limit", 50)
        self._cleanup_enabled = r2_config.get("cleanup_old_files", True)

    async def upload_audio(self, local_path: str) -> Optional[str]:
        """Upload an audio file and its companion subtitle JSON to R2.

        Subtitle is expected at the same path with .json extension.
        Returns the public URL of the audio file (subtitle URL is derived by replacing .mp3 → .json).
        """
        path = Path(local_path)
        if not path.exists():
            logger.error(f"Audio file not found: {local_path}")
            return None

        date_str = datetime.now().strftime("%Y-%m-%d")
        r2_key = f"audio/{date_str}/{path.name}"

        try:
            await asyncio.to_thread(
                self._client.upload_file,
                str(path),
                self._bucket,
                r2_key,
                ExtraArgs={"ContentType": "audio/mpeg"},
            )
            public_url = f"{self._public_url}/{r2_key}"
            logger.debug(f"Uploaded audio to R2: {public_url}")

            # Upload companion subtitle JSON if it exists
            subtitle_path = path.with_suffix(".json")
            if subtitle_path.exists():
                sub_key = f"audio/{date_str}/{subtitle_path.name}"
                await asyncio.to_thread(
                    self._client.upload_file,
                    str(subtitle_path),
                    self._bucket,
                    sub_key,
                    ExtraArgs={"ContentType": "application/json"},
                )
                logger.debug(f"Uploaded subtitle to R2: {self._public_url}/{sub_key}")

            return public_url

        except ClientError as e:
            logger.error(f"R2 upload failed for {local_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error uploading to R2: {e}")
            return None

    async def update_stories_index(self, database) -> bool:
        """Query produced news from DB and upload stories.json to R2."""
        try:
            news_items = await database.load_news(is_produced=True)

            news_items.sort(
                key=lambda x: getattr(x, "created_at", datetime.min),
                reverse=True,
            )
            news_items = news_items[: self._stories_limit]

            stories = []
            for item in news_items:
                audio_url = item.audio_path or ""
                subtitle_url = audio_url.rsplit(".", 1)[0] + ".json" if audio_url else ""
                stories.append({
                    "id": item.id,
                    "title": item.title,
                    "text": item.text or "",
                    "category": item.news_category or [],
                    "entities": item.entities or [],
                    "depth": item.depth,
                    "audio_url": audio_url,
                    "subtitle_url": subtitle_url,
                    "cover_image": item.cover_image or "",
                    "published_at": (
                        item.created_at.isoformat()
                        if hasattr(item, "created_at") and item.created_at
                        else None
                    ),
                })

            payload = {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "stories": stories,
            }

            body = json.dumps(payload, ensure_ascii=False, indent=2)

            await asyncio.to_thread(
                self._client.put_object,
                Bucket=self._bucket,
                Key="stories.json",
                Body=body.encode("utf-8"),
                ContentType="application/json",
            )
            logger.debug(f"Updated stories.json with {len(stories)} items.")

            # Clean up orphaned audio files no longer in the index
            if self._cleanup_enabled:
                active_keys = set()
                for story in stories:
                    if url := story.get("audio_url", ""):
                        # Extract R2 key from public URL
                        key = url.replace(f"{self._public_url}/", "")
                        active_keys.add(key)
                    if url := story.get("subtitle_url", ""):
                        key = url.replace(f"{self._public_url}/", "")
                        active_keys.add(key)
                await self._cleanup_old_files(active_keys)

            return True

        except Exception as e:
            logger.error(f"Failed to update stories.json: {e}")
            return False

    async def _cleanup_old_files(self, active_keys: Set[str]) -> None:
        """Delete audio/subtitle files from R2 that are not in the active stories index."""
        try:
            # List all objects under audio/
            response = await asyncio.to_thread(
                self._client.list_objects_v2,
                Bucket=self._bucket,
                Prefix="audio/",
            )

            contents = response.get("Contents", [])
            if not contents:
                return

            orphaned = [
                {"Key": obj["Key"]}
                for obj in contents
                if obj["Key"] not in active_keys
            ]

            if not orphaned:
                return

            # S3 delete_objects supports max 1000 keys per request
            for i in range(0, len(orphaned), 1000):
                batch = orphaned[i:i + 1000]
                await asyncio.to_thread(
                    self._client.delete_objects,
                    Bucket=self._bucket,
                    Delete={"Objects": batch, "Quiet": True},
                )

            logger.debug(f"R2 cleanup: deleted {len(orphaned)} orphaned files.")

        except Exception as e:
            logger.error(f"R2 cleanup failed: {e}")
