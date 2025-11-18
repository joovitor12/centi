"""Google Calendar service for syncing appointments."""

import logging
import os
from datetime import datetime, timedelta
from typing import Optional
import pytz
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config.settings import settings

logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendarService:
    """Service for interacting with Google Calendar API."""

    def __init__(self):
        """Initialize Google Calendar client."""
        self.creds: Optional[Credentials] = None
        self.service = None
        self.calendar_id = settings.GOOGLE_CALENDAR_ID
        self.timezone_str = settings.GOOGLE_CALENDAR_TIMEZONE
        self.timezone = pytz.timezone(settings.GOOGLE_CALENDAR_TIMEZONE)

        # Only initialize if credentials path is provided
        if settings.GOOGLE_CREDENTIALS_PATH:
            self._authenticate()

    def _authenticate(self):
        """Authenticate with Google Calendar API using OAuth 2.0."""
        try:
            credentials_path = settings.GOOGLE_CREDENTIALS_PATH
            token_path = os.path.join(os.path.dirname(credentials_path), "token.json")

            # Load existing token if available
            if os.path.exists(token_path):
                self.creds = Credentials.from_authorized_user_file(token_path, SCOPES)

            # If there are no (valid) credentials available, let the user log in.
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    if not os.path.exists(credentials_path):
                        logger.warning(
                            f"Google Calendar credentials file not found at {credentials_path}. "
                            "Google Calendar integration will be disabled."
                        )
                        return

                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_path, SCOPES
                    )
                    self.creds = flow.run_local_server(port=0)

                # Save the credentials for the next run
                with open(token_path, "w") as token:
                    token.write(self.creds.to_json())

            # Build the service
            self.service = build("calendar", "v3", credentials=self.creds)
            logger.info("Google Calendar service initialized successfully")

        except Exception as e:
            logger.warning(
                f"Failed to initialize Google Calendar service: {e}. "
                "Google Calendar integration will be disabled."
            )
            self.service = None

    def create_event(
        self,
        description: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
    ) -> Optional[str]:
        """Create a calendar event.

        Args:
            description: Event description/summary
            start_time: Event start time as datetime object
            end_time: Event end time as datetime object. If None, defaults to start_time + 1 hour

        Returns:
            Event ID if successful, None otherwise
        """
        if not self.service:
            logger.warning(
                "Google Calendar service not initialized. Skipping event creation."
            )
            return None

        try:
            # Default end_time to 1 hour after start_time if not provided
            if end_time is None:
                end_time = start_time + timedelta(hours=1)

            # Format times in RFC3339 format for Google Calendar API
            # If datetime is naive (no timezone), treat it as local timezone
            # Otherwise, convert to the configured timezone
            if start_time.tzinfo is None:
                # Naive datetime: assume it's in the local timezone
                start_time = self.timezone.localize(start_time)
            else:
                # Timezone-aware: convert to configured timezone
                start_time = start_time.astimezone(self.timezone)

            if end_time.tzinfo is None:
                end_time = self.timezone.localize(end_time)
            else:
                end_time = end_time.astimezone(self.timezone)

            # Format as RFC3339 (ISO8601 with timezone)
            start_time_str = start_time.isoformat()
            end_time_str = end_time.isoformat()

            event = {
                "summary": description,
                "start": {
                    "dateTime": start_time_str,
                    "timeZone": self.timezone_str,
                },
                "end": {
                    "dateTime": end_time_str,
                    "timeZone": self.timezone_str,
                },
            }

            event = (
                self.service.events()
                .insert(calendarId=self.calendar_id, body=event)
                .execute()
            )

            logger.info(
                f"Google Calendar event created: {event.get('htmlLink')} (ID: {event.get('id')})"
            )
            return event.get("id")

        except HttpError as e:
            logger.error(f"Error creating Google Calendar event: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating Google Calendar event: {e}")
            return None
