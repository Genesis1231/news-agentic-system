import asyncio
import http.client
import httplib2
import json
import logging
import random
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


class YoutubeUploader:
    """A class to handle YouTube video uploads with authentication and metadata handling."""
    
    # API constants
    YOUTUBE_API_SERVICE_NAME = "youtube"
    YOUTUBE_API_VERSION = "v3"
    SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]
    VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")
    
    # HTTP constants
    RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
    RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
                            http.client.IncompleteRead, http.client.ImproperConnectionState,
                            http.client.CannotSendRequest, http.client.CannotSendHeader,
                            http.client.ResponseNotReady, http.client.BadStatusLine)
    
    def __init__(
        self, 
        client_secrets_file: str | Path = None,
        oauth2_storage_file: str | Path = None,
        force_token_refresh_days: int = 7,
        max_retries: int = 10,
    ):
        """
        Initialize the YouTube uploader with configuration.
        
        Args:
            client_secrets_file: Path to client secrets JSON file (or use YOUTUBE_CLIENT_SECRETS_FILE env var)
            oauth2_storage_file: Path to OAuth2 token storage file (or use YOUTUBE_OAUTH2_STORAGE_FILE env var)
            force_token_refresh_days: Days before token refresh is forced (or use YOUTUBE_TOKEN_REFRESH_DAYS env var)
            max_retries: Maximum retry attempts for upload operations (or use YOUTUBE_MAX_RETRIES env var)
        """
        self.logger = logging.getLogger(__name__)
        
        # Set httplib2 retries
        httplib2.RETRIES = 1
        
        # Get configuration from parameters or environment variables
        self.client_secrets_file = Path(client_secrets_file).resolve()  
        self.oauth2_storage_file = Path(oauth2_storage_file).resolve()  
        self.force_token_refresh_days = force_token_refresh_days 
        self.max_retries = max_retries 
            
        self._youtube = None
        self._check_required_files()
    
    def _check_required_files(self) -> None:
        """Check if required files exist."""
        if self.client_secrets_file is None or not self.client_secrets_file.exists():
            raise FileNotFoundError(f"Required file {self.client_secrets_file} does not exist.")
    
    async def _refresh_token_with_retry(self, creds: Credentials) -> bool:
        """
        Attempt to refresh the token with retries.
        
        Args:
            creds: The credentials object to refresh
            
        Returns:
            bool: True if refresh was successful, False otherwise
        """
        retry_count = 0
        max_retries = 3
        while retry_count < max_retries:
            try:
                creds.refresh(Request())
                self.logger.info(f"Refresh successful: new expiry={creds.expiry}")
                return True
            except HttpError as e:
                self.logger.error(f"HttpError refreshing token (attempt {retry_count+1}): status={e.resp.status}, content={e.content}")
            except RefreshError as e:
                self.logger.error(f"RefreshError refreshing token (attempt {retry_count+1}): {e}")
            except Exception as e:
                self.logger.error(f"Unexpected error refreshing token (attempt {retry_count+1}): {e}")
            retry_count += 1
            await asyncio.sleep(2 ** retry_count)
        return False
    
    async def authenticate(self, force_refresh: bool = False) -> Any:
        """
        Get an authenticated YouTube service object.
        
        Args:
            force_refresh: Force token refresh regardless of expiry status
            
        Returns:
            The authenticated YouTube service object
        """
        creds = None
        
        if self.oauth2_storage_file and self.oauth2_storage_file.exists():
            try:
                with open(self.oauth2_storage_file, 'r') as token:
                    creds_data = json.load(token)
                creds = Credentials.from_authorized_user_info(creds_data, self.SCOPES)
                
                current_time = datetime.now(timezone.utc)
                should_refresh = False
                
                if not creds.refresh_token:
                    self.logger.info("No refresh token available, forcing new authentication.")
                    should_refresh = True
                elif creds.expiry:
                    expiry_aware = creds.expiry.replace(tzinfo=timezone.utc)
                    time_to_expiry = expiry_aware - current_time
                    
                    # Custom expiry check
                    is_expired = current_time >= expiry_aware
                    should_refresh = (is_expired or 
                                     time_to_expiry.total_seconds() < 300 or  # Refresh if less than 5 minutes remaining
                                     time_to_expiry.days <= -self.force_token_refresh_days or
                                     force_refresh)
                else:
                    self.logger.info("No expiry set in credentials, forcing refresh.")
                    should_refresh = True

                if should_refresh and creds and creds.refresh_token:
                    self.logger.info("Attempting to refresh token.")
                    success = await self._refresh_token_with_retry(creds)
                    if success:
                        with open(self.oauth2_storage_file, 'w') as token:
                            json.dump(json.loads(creds.to_json()), token)
                    else:
                        self.logger.warning("Token refresh failed after retries, forcing new authentication.")
                        if self.oauth2_storage_file.exists():
                            self.oauth2_storage_file.unlink()
                        creds = None
                        
            except (ValueError, json.JSONDecodeError) as e:
                self.logger.error(f"Invalid or corrupted credentials file ({e}), initiating new authentication.")
                if self.oauth2_storage_file.exists():
                    self.oauth2_storage_file.unlink()
                creds = None

        if not creds or not creds.valid:
            self.logger.info("No valid credentials found, initiating manual authentication.")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.client_secrets_file), self.SCOPES, redirect_uri="urn:ietf:wg:oauth:2.0:oob")
            
            authorization_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true'
            )
            
            print(f"Please visit this URL on a device with a browser to authorize the application:")
            print(authorization_url)
            code = input("Enter the authorization code: ").strip()
            
            try:
                flow.fetch_token(code=code)
                creds = flow.credentials
                if not creds.expiry:
                    self.logger.warning("No expiry set after initial authentication, setting manually.")
                    creds.expiry = datetime.now(timezone.utc) + timedelta(seconds=3600)  # Keep offset-naive for library
            except Exception as e:
                self.logger.error(f"Failed to fetch token with code: {e}")
                raise

            with open(self.oauth2_storage_file, 'w') as token:
                json.dump(json.loads(creds.to_json()), token)

        if creds and not creds.valid and creds.refresh_token:
            self.logger.info("Credentials invalid but refresh token available, attempting final refresh.")
            success = await self._refresh_token_with_retry(creds)
            if success:
                with open(self.oauth2_storage_file, 'w') as token:
                    json.dump(json.loads(creds.to_json()), token)
            else:
                self.logger.error("Final refresh attempt failed. Please re-authenticate manually.")
                if self.oauth2_storage_file.exists():
                    self.oauth2_storage_file.unlink()
                raise AuthenticationError("Authentication failed after refresh attempts")

        self._youtube = build(self.YOUTUBE_API_SERVICE_NAME, self.YOUTUBE_API_VERSION, credentials=creds)
        return self._youtube
    
    async def upload_video(
        self,
        video_file: Union[str, Path],
        title: str,
        description: str = "",
        privacy_status: str = "private",
        category: str = "22",
        keywords: str = "",
        language: str = "en",
        playlist_id: str = None,
        thumbnail: Union[str, Path] = None,
        license: str = "youtube",
        made_for_kids: bool = False,
        public_stats_viewable: bool = False,
        publish_at: str = None,
        location: Tuple[float, float] = None,
        targeting: Dict[str, Any] = None,
        default_audio_language: str = None,
    ) -> Dict[str, Any]:
        """
        Upload a video to YouTube with specified metadata.
        
        Args:
            video_file: Path to the video file
            title: Video title
            description: Video description
            privacy_status: One of 'public', 'private', 'unlisted'
            category: Numeric video category
            keywords: Comma-separated keywords
            language: Video language code
            playlist_id: ID of playlist to add video to
            thumbnail: Path to thumbnail image
            license: License type ('youtube' or 'creativeCommon')
            made_for_kids: Whether the video is made for kids
            public_stats_viewable: Whether video statistics are public
            publish_at: ISO 8601 timestamp for scheduled publishing
            location: Tuple of (latitude, longitude)
            targeting: Dictionary with targeting options (ageGroup, gender, geo)
            default_audio_language: Default audio language
            
        Returns:
            Dict containing response information including video ID
        """
        if not self._youtube:
            await self.authenticate()
            
        video_path = Path(video_file)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
            
        if privacy_status not in self.VALID_PRIVACY_STATUSES:
            raise ValueError(f"Invalid privacy status. Must be one of {self.VALID_PRIVACY_STATUSES}")
            
        # Prepare tags
        tags = None
        if keywords:
            tags = keywords.split(",")

        # Prepare body
        body: Dict[str, Any] = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": category,
                "defaultLanguage": language,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": made_for_kids,
                "license": license,
                "publicStatsViewable": public_stats_viewable,
            }
        }
        
        # Add optional fields
        if default_audio_language:
            body["snippet"]["defaultAudioLanguage"] = default_audio_language
            
        if location and len(location) == 2:
            body["snippet"]["recordingDetails"] = {
                "location": {
                    "latitude": location[0],
                    "longitude": location[1]
                }
            }
            
        if publish_at:
            body["status"]["publishAt"] = publish_at
            
        if targeting:
            body["status"]["targeting"] = {}
            if "ageGroup" in targeting:
                body["status"]["targeting"]["ageGroup"] = targeting["ageGroup"]
            if "gender" in targeting:
                body["status"]["targeting"]["genders"] = [targeting["gender"]]
            if "geo" in targeting and isinstance(targeting["geo"], str):
                body["status"]["targeting"]["countries"] = targeting["geo"].split(',')

        # Create upload request
        insert_request = self._youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
        )

        # Execute upload with retry logic
        response = await self._resumable_upload(insert_request)
        
        # Add thumbnail if specified
        if thumbnail and response and 'id' in response:
            await self._upload_thumbnail(response['id'], thumbnail)
        
        # Add to playlist if specified
        if playlist_id and response and 'id' in response:
            await self._add_video_to_playlist(response['id'], playlist_id)
            
        return response

    async def _add_video_to_playlist(self, video_id: str, playlist_id: str) -> Dict[str, Any]:
        """
        Add the uploaded video to a specified playlist.
        
        Args:
            video_id: ID of the uploaded video
            playlist_id: ID of the playlist to add the video to
            
        Returns:
            API response
        """
        try:
            add_video_request = self._youtube.playlistItems().insert(
                part="snippet",
                body={
                    'snippet': {
                        'playlistId': playlist_id,
                        'resourceId': {
                            'kind': 'youtube#video',
                            'videoId': video_id
                        }
                    }
                }
            )
            response = add_video_request.execute()
            self.logger.info(f"Video {video_id} added to playlist {playlist_id}")
            return response
        except HttpError as e:
            self.logger.error(f"Failed to add video to playlist: {e}")
            return {}

    async def _upload_thumbnail(self, video_id: str, thumbnail_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """
        Upload a thumbnail for the video.
        
        Args:
            video_id: ID of the uploaded video
            thumbnail_path: Path to the thumbnail image
            
        Returns:
            API response or None if failed
        """
        thumb_path = Path(thumbnail_path)
        if not thumb_path.exists():
            self.logger.error(f"Thumbnail file not found: {thumb_path}")
            return None
            
        try:
            request = self._youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(thumb_path))
            )
            response = request.execute()
            self.logger.info(f"Thumbnail uploaded for video {video_id}")
            return response
        except HttpError as e:
            self.logger.error(f"An error occurred while uploading the thumbnail: {e}")
            return None

    async def _resumable_upload(self, insert_request: Any) -> Optional[Dict[str, Any]]:
        """
        Implement resumable upload with exponential backoff strategy.
        
        Args:
            insert_request: The video insert request object
            
        Returns:
            API response or None if failed
        """
        response = None
        error = None
        retry = 0
        
        while response is None:
            try:
                self.logger.info("Uploading file...")
                status, response = insert_request.next_chunk()
                
                if response is not None:
                    if 'id' in response:
                        self.logger.info(f"Video id '{response['id']}' was successfully uploaded.")
                        return response
                    else:
                        raise Exception(f"The upload failed with an unexpected response: {response}")
                        
            except HttpError as e:
                if e.resp.status in self.RETRIABLE_STATUS_CODES:
                    error = f"A retriable HTTP error {e.resp.status} occurred:\n{e.content}"
                else:
                    raise
                    
            except self.RETRIABLE_EXCEPTIONS as e:
                error = f"A retriable error occurred: {e}"

            if error is not None:
                self.logger.error(error)
                retry += 1
                
                if retry > self.max_retries:
                    self.logger.error("No longer attempting to retry.")
                    return None
                    
                max_sleep = 2 ** retry
                sleep_seconds = random.random() * max_sleep
                self.logger.info(f"Sleeping {sleep_seconds:.1f} seconds and then retrying...")
                await asyncio.sleep(sleep_seconds)
                error = None

        return None


class AuthenticationError(Exception):
    """Exception raised for authentication failures."""
    pass