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

    def update_event(
        self,
        event_id: str,
        description: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> bool:
        """Update an existing calendar event.

        Args:
            event_id: Google Calendar event ID
            description: New event description/summary (optional)
            start_time: New event start time (optional)
            end_time: New event end time (optional)

        Returns:
            True if successful, False otherwise
        """
        if not self.service:
            logger.warning(
                "Google Calendar service not initialized. Skipping event update."
            )
            return False

        try:
            # First, get the existing event
            event = (
                self.service.events()
                .get(calendarId=self.calendar_id, eventId=event_id)
                .execute()
            )

            # Update fields if provided
            if description:
                event["summary"] = description

            if start_time is not None:
                # Format timezone-aware datetime
                if start_time.tzinfo is None:
                    start_time = self.timezone.localize(start_time)
                else:
                    start_time = start_time.astimezone(self.timezone)
                event["start"] = {
                    "dateTime": start_time.isoformat(),
                    "timeZone": self.timezone_str,
                }

            if end_time is not None:
                # Format timezone-aware datetime
                if end_time.tzinfo is None:
                    end_time = self.timezone.localize(end_time)
                else:
                    end_time = end_time.astimezone(self.timezone)
                event["end"] = {
                    "dateTime": end_time.isoformat(),
                    "timeZone": self.timezone_str,
                }

            # Update the event
            updated_event = (
                self.service.events()
                .update(calendarId=self.calendar_id, eventId=event_id, body=event)
                .execute()
            )

            logger.info(f"Google Calendar event updated: {event_id}")
            return True

        except HttpError as e:
            logger.error(f"Error updating Google Calendar event {event_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error updating Google Calendar event: {e}")
            return False

    def delete_event(self, event_id: str) -> bool:
        """Delete a calendar event.

        Args:
            event_id: Google Calendar event ID

        Returns:
            True if successful, False otherwise
        """
        if not self.service:
            logger.warning(
                "Google Calendar service not initialized. Skipping event deletion."
            )
            return False

        try:
            self.service.events().delete(
                calendarId=self.calendar_id, eventId=event_id
            ).execute()

            logger.info(f"Google Calendar event deleted: {event_id}")
            return True

        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(
                    f"Google Calendar event {event_id} not found (may have been already deleted)"
                )
                return True  # Consider it successful if already deleted
            logger.error(f"Error deleting Google Calendar event {event_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting Google Calendar event: {e}")
            return False

    # ============================================================
    # Recurring Events Methods
    # ============================================================

    def _generate_rrule(
        self,
        recurrence_pattern: str,
        recurrence_interval: int = 1,
        recurrence_byday: Optional[str] = None,
        recurrence_bymonthday: Optional[int] = None,
        end_date: Optional[datetime] = None,
        max_occurrences: Optional[int] = None,
    ) -> str:
        """Generate RRULE string for Google Calendar API.

        Args:
            recurrence_pattern: Pattern type ("daily", "weekly", "monthly", "yearly")
            recurrence_interval: Interval (e.g., every 2 weeks = 2)
            recurrence_byday: Days of week for weekly (e.g., "MO,WE,FR" or "MO")
            recurrence_bymonthday: Day of month for monthly (e.g., 15)
            end_date: When recurrence should stop
            max_occurrences: Maximum number of occurrences

        Returns:
            RRULE string (e.g., "FREQ=WEEKLY;BYDAY=MO;INTERVAL=1")
        """
        pattern_upper = recurrence_pattern.upper()

        # Validate pattern
        if pattern_upper not in ["DAILY", "WEEKLY", "MONTHLY", "YEARLY"]:
            raise ValueError(f"Invalid recurrence_pattern: {recurrence_pattern}")

        # Build RRULE parts
        rrule_parts = [f"FREQ={pattern_upper}"]

        # Add interval if not 1
        if recurrence_interval > 1:
            rrule_parts.append(f"INTERVAL={recurrence_interval}")

        # Add BYDAY for weekly patterns
        if pattern_upper == "WEEKLY" and recurrence_byday:
            rrule_parts.append(f"BYDAY={recurrence_byday}")
        # Note: If no byday specified for weekly, it will be handled by caller

        # Add BYMONTHDAY for monthly patterns
        if pattern_upper == "MONTHLY" and recurrence_bymonthday:
            rrule_parts.append(f"BYMONTHDAY={recurrence_bymonthday}")

        # Add end condition
        if max_occurrences:
            rrule_parts.append(f"COUNT={max_occurrences}")
        elif end_date:
            # Format end_date as UTC in format YYYYMMDDTHHMMSSZ
            if end_date.tzinfo is None:
                end_date = self.timezone.localize(end_date)
            else:
                end_date = end_date.astimezone(self.timezone)
            # Convert to UTC
            end_date_utc = end_date.astimezone(pytz.UTC)
            until_str = end_date_utc.strftime("%Y%m%dT%H%M%SZ")
            rrule_parts.append(f"UNTIL={until_str}")

        return ";".join(rrule_parts)

    def create_recurring_event(
        self,
        description: str,
        start_time: datetime,
        recurrence_pattern: str,
        recurrence_interval: int = 1,
        recurrence_byday: Optional[str] = None,
        recurrence_bymonthday: Optional[int] = None,
        end_time: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        max_occurrences: Optional[int] = None,
    ) -> Optional[str]:
        """Create a recurring event with RRULE.

        Args:
            description: Event description/summary
            start_time: Event start time as datetime object
            recurrence_pattern: Pattern type ("daily", "weekly", "monthly", "yearly")
            recurrence_interval: Interval (e.g., every 2 weeks = 2)
            recurrence_byday: Days of week for weekly (e.g., "MO,WE,FR" or "MO")
            recurrence_bymonthday: Day of month for monthly (e.g., 15)
            end_time: Event end time (optional, defaults to start_time + 1 hour)
            end_date: When recurrence should stop (optional)
            max_occurrences: Maximum number of occurrences (optional)

        Returns:
            Event ID if successful, None otherwise
        """
        if not self.service:
            logger.warning(
                "Google Calendar service not initialized. Skipping recurring event creation."
            )
            return None

        try:
            # Default end_time to 1 hour after start_time if not provided
            if end_time is None:
                end_time = start_time + timedelta(hours=1)

            # Format times in RFC3339 format for Google Calendar API
            if start_time.tzinfo is None:
                start_time = self.timezone.localize(start_time)
            else:
                start_time = start_time.astimezone(self.timezone)

            if end_time.tzinfo is None:
                end_time = self.timezone.localize(end_time)
            else:
                end_time = end_time.astimezone(self.timezone)

            # If weekly pattern and no byday specified, extract day from start_time
            if recurrence_pattern.lower() == "weekly" and not recurrence_byday:
                # Get weekday (Monday = 0, Sunday = 6) and map to RRULE format
                weekday = start_time.weekday()
                weekday_map = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
                recurrence_byday = weekday_map[weekday]

            # Generate RRULE
            rrule = self._generate_rrule(
                recurrence_pattern=recurrence_pattern,
                recurrence_interval=recurrence_interval,
                recurrence_byday=recurrence_byday,
                recurrence_bymonthday=recurrence_bymonthday,
                end_date=end_date,
                max_occurrences=max_occurrences,
            )

            # Format as RFC3339
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
                "recurrence": [f"RRULE:{rrule}"],
            }

            event = (
                self.service.events()
                .insert(calendarId=self.calendar_id, body=event)
                .execute()
            )

            logger.info(
                f"Google Calendar recurring event created: {event.get('htmlLink')} (ID: {event.get('id')}, RRULE: {rrule})"
            )
            return event.get("id")

        except HttpError as e:
            logger.error(f"Error creating Google Calendar recurring event: {e}")
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error creating Google Calendar recurring event: {e}"
            )
            return None

    def update_recurring_event(
        self,
        event_id: str,
        description: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        recurrence_pattern: Optional[str] = None,
        recurrence_interval: Optional[int] = None,
        recurrence_byday: Optional[str] = None,
        recurrence_bymonthday: Optional[int] = None,
        end_date: Optional[datetime] = None,
    ) -> bool:
        """Update a recurring event.

        Note: If recurrence rules change significantly, this method will attempt to update.
        For major changes, you may need to delete and recreate the event.

        Args:
            event_id: Google Calendar recurring event ID
            description: New event description (optional)
            start_time: New start time (optional)
            end_time: New end time (optional)
            recurrence_pattern: New pattern type (optional)
            recurrence_interval: New interval (optional)
            recurrence_byday: New days of week (optional)
            recurrence_bymonthday: New day of month (optional)
            end_date: New end date (optional)

        Returns:
            True if successful, False otherwise
        """
        if not self.service:
            logger.warning(
                "Google Calendar service not initialized. Skipping recurring event update."
            )
            return False

        try:
            # Get the existing event
            event = (
                self.service.events()
                .get(calendarId=self.calendar_id, eventId=event_id)
                .execute()
            )

            # Update basic fields
            if description:
                event["summary"] = description

            if start_time is not None:
                if start_time.tzinfo is None:
                    start_time = self.timezone.localize(start_time)
                else:
                    start_time = start_time.astimezone(self.timezone)
                event["start"] = {
                    "dateTime": start_time.isoformat(),
                    "timeZone": self.timezone_str,
                }

            if end_time is not None:
                if end_time.tzinfo is None:
                    end_time = self.timezone.localize(end_time)
                else:
                    end_time = end_time.astimezone(self.timezone)
                event["end"] = {
                    "dateTime": end_time.isoformat(),
                    "timeZone": self.timezone_str,
                }

            # Update recurrence rules if provided
            if any(
                [
                    recurrence_pattern,
                    recurrence_interval is not None,
                    recurrence_byday,
                    recurrence_bymonthday is not None,
                    end_date,
                ]
            ):
                # Generate new RRULE
                if recurrence_pattern:
                    # If weekly and no byday, extract from start_time
                    if recurrence_pattern.lower() == "weekly" and not recurrence_byday:
                        if start_time:
                            weekday_map = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
                            weekday = start_time.weekday()
                            recurrence_byday = weekday_map[weekday]
                        else:
                            # Use existing start time from event
                            existing_start = datetime.fromisoformat(
                                event["start"]["dateTime"]
                            )
                            weekday_map = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
                            weekday = existing_start.weekday()
                            recurrence_byday = weekday_map[weekday]

                    rrule = self._generate_rrule(
                        recurrence_pattern=recurrence_pattern,
                        recurrence_interval=recurrence_interval or 1,
                        recurrence_byday=recurrence_byday,
                        recurrence_bymonthday=recurrence_bymonthday,
                        end_date=end_date,
                        max_occurrences=None,  # Don't update count on update
                    )
                    event["recurrence"] = [f"RRULE:{rrule}"]

            # Update the event
            updated_event = (
                self.service.events()
                .update(calendarId=self.calendar_id, eventId=event_id, body=event)
                .execute()
            )

            logger.info(f"Google Calendar recurring event updated: {event_id}")
            return True

        except HttpError as e:
            logger.error(
                f"Error updating Google Calendar recurring event {event_id}: {e}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error updating Google Calendar recurring event: {e}"
            )
            return False

    def delete_recurring_event(self, event_id: str) -> bool:
        """Delete a recurring event (removes all future occurrences).

        Args:
            event_id: Google Calendar recurring event ID

        Returns:
            True if successful, False otherwise
        """
        # Reuse the existing delete_event method which works for recurring events too
        return self.delete_event(event_id)
