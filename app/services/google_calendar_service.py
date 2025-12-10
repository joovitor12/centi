"""Google Calendar service for syncing appointments."""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import pytz
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config.settings import settings

logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
COMBINED_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.modify",
]


class GoogleCalendarService:
    """Service for interacting with Google Calendar API."""

    def __init__(self):
        """Initialize Google Calendar client."""
        self.creds: Optional[Credentials] = None
        self.service = None
        self.calendar_id = settings.GOOGLE_CALENDAR_ID
        self.timezone_str = settings.GOOGLE_CALENDAR_TIMEZONE
        self.timezone = pytz.timezone(settings.GOOGLE_CALENDAR_TIMEZONE)

        # Initialize authentication if token/credentials are provided (via env var, path, or JSON)
        if (
            settings.GOOGLE_TOKEN_PATH
            or settings.GOOGLE_TOKEN_JSON
            or settings.GOOGLE_CREDENTIALS_PATH
            or settings.GOOGLE_CREDENTIALS_JSON
        ):
            self._authenticate()

    def _authenticate(self):
        """Authenticate with Google Calendar API using OAuth 2.0.
        
        Priority order:
        1. GOOGLE_TOKEN_JSON (environment variable with JSON string)
        2. GOOGLE_TOKEN_PATH (file path)
        3. GOOGLE_CREDENTIALS_JSON (environment variable with JSON string) - for cloud deployments
        4. GOOGLE_CREDENTIALS_PATH (file path) - with interactive OAuth flow
        """
        try:
            # Debug: Log which authentication method will be used
            logger.info(
                f"Authentication check: GOOGLE_TOKEN_JSON={'set' if settings.GOOGLE_TOKEN_JSON else 'not set'}, "
                f"GOOGLE_TOKEN_PATH={'set' if settings.GOOGLE_TOKEN_PATH else 'not set'}, "
                f"GOOGLE_CREDENTIALS_JSON={'set' if settings.GOOGLE_CREDENTIALS_JSON else 'not set'}, "
                f"GOOGLE_CREDENTIALS_PATH={'set' if settings.GOOGLE_CREDENTIALS_PATH else 'not set'}"
            )
            
            # Priority 1: Use token from environment variable (JSON string)
            if settings.GOOGLE_TOKEN_JSON:
                try:
                    token_data = json.loads(settings.GOOGLE_TOKEN_JSON)
                    self.creds = Credentials.from_authorized_user_info(
                        token_data, COMBINED_SCOPES
                    )
                    if self.creds and self.creds.valid:
                        self.service = build("calendar", "v3", credentials=self.creds)
                        logger.info(
                            "Google Calendar service initialized successfully using token from GOOGLE_TOKEN_JSON"
                        )
                        return
                    elif self.creds and self.creds.expired and self.creds.refresh_token:
                        try:
                            self.creds.refresh(Request())
                            self.service = build("calendar", "v3", credentials=self.creds)
                            logger.info(
                                "Google Calendar service initialized successfully after refreshing token from GOOGLE_TOKEN_JSON"
                            )
                            return
                        except Exception as e:
                            logger.warning(
                                f"Failed to refresh token from GOOGLE_TOKEN_JSON: {e}"
                            )
                except json.JSONDecodeError as e:
                    logger.warning(
                        f"Invalid JSON in GOOGLE_TOKEN_JSON: {e}. Falling back to other methods."
                    )

            # Priority 2: Use direct token path if provided (for org installations)
            if settings.GOOGLE_TOKEN_PATH:
                if os.path.exists(settings.GOOGLE_TOKEN_PATH):
                    self.creds = Credentials.from_authorized_user_file(
                        settings.GOOGLE_TOKEN_PATH, COMBINED_SCOPES
                    )
                    if self.creds and self.creds.valid:
                        self.service = build("calendar", "v3", credentials=self.creds)
                        logger.info(
                            f"Google Calendar service initialized successfully using token from {settings.GOOGLE_TOKEN_PATH}"
                        )
                        return
                    elif self.creds and self.creds.expired and self.creds.refresh_token:
                        try:
                            self.creds.refresh(Request())
                            self.service = build("calendar", "v3", credentials=self.creds)
                            logger.info(
                                f"Google Calendar service initialized successfully after refreshing token from {settings.GOOGLE_TOKEN_PATH}"
                            )
                            return
                        except Exception as e:
                            logger.warning(
                                f"Failed to refresh token from {settings.GOOGLE_TOKEN_PATH}: {e}"
                            )
                else:
                    logger.warning(
                        f"Token file not found at {settings.GOOGLE_TOKEN_PATH}. "
                        "Falling back to OAuth flow."
                    )

            # Priority 3: Use credentials from environment variable (JSON string) - for cloud deployments
            if settings.GOOGLE_CREDENTIALS_JSON:
                try:
                    credentials_data = json.loads(settings.GOOGLE_CREDENTIALS_JSON)
                    # For cloud deployments, we expect a token JSON, not OAuth credentials
                    # If it's a token, use it directly
                    if "token" in credentials_data or "refresh_token" in credentials_data:
                        self.creds = Credentials.from_authorized_user_info(
                            credentials_data, COMBINED_SCOPES
                        )
                        if self.creds and self.creds.valid:
                            self.service = build("calendar", "v3", credentials=self.creds)
                            logger.info(
                                "Google Calendar service initialized successfully using credentials from GOOGLE_CREDENTIALS_JSON"
                            )
                            return
                        elif self.creds and self.creds.expired and self.creds.refresh_token:
                            try:
                                self.creds.refresh(Request())
                                self.service = build("calendar", "v3", credentials=self.creds)
                                logger.info(
                                    "Google Calendar service initialized successfully after refreshing credentials from GOOGLE_CREDENTIALS_JSON"
                                )
                                return
                            except Exception as e:
                                logger.warning(
                                    f"Failed to refresh credentials from GOOGLE_CREDENTIALS_JSON: {e}"
                                )
                    else:
                        logger.warning(
                            "GOOGLE_CREDENTIALS_JSON should contain a token JSON, not OAuth credentials. "
                            "Use GOOGLE_TOKEN_JSON instead."
                        )
                except json.JSONDecodeError as e:
                    logger.warning(
                        f"Invalid JSON in GOOGLE_CREDENTIALS_JSON: {e}. Falling back to other methods."
                    )

            # Priority 4: Use existing token.json (generated automatically)
            # Priority 5: Start OAuth flow (only works locally)
            credentials_path = settings.GOOGLE_CREDENTIALS_PATH
            if not credentials_path:
                logger.warning(
                    "No Google credentials configured (GOOGLE_TOKEN_JSON, GOOGLE_TOKEN_PATH, "
                    "GOOGLE_CREDENTIALS_JSON, or GOOGLE_CREDENTIALS_PATH). "
                    "Google Calendar integration will be disabled."
                )
                return

            token_path = os.path.join(os.path.dirname(credentials_path), "token.json")

            # Load existing token if available
            if os.path.exists(token_path):
                self.creds = Credentials.from_authorized_user_file(
                    token_path, COMBINED_SCOPES
                )

            # If there are no (valid) credentials available, disable the service
            # OAuth flow is now handled by FastAPI endpoints (/auth/google)
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    try:
                        self.creds.refresh(Request())
                        self.service = build("calendar", "v3", credentials=self.creds)
                        logger.info(
                            "Google Calendar service initialized successfully after refreshing token"
                        )
                        return
                    except Exception as e:
                        logger.warning(
                            f"Failed to refresh token: {e}. "
                            "Google Calendar integration will be disabled."
                        )
                        return
                else:
                    # No valid credentials available - disable service
                    # Users should use the OAuth endpoint at /auth/google to authenticate
                    logger.warning(
                        f"No valid Google Calendar credentials found. "
                        "Google Calendar integration will be disabled. "
                        "To authenticate, use the OAuth endpoint at /auth/google"
                    )
                    return

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
        summary: Optional[str] = None,
        attendees: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Create a calendar event.

        Args:
            description: Event description (body text)
            start_time: Event start time as datetime object
            end_time: Event end time as datetime object. If None, defaults to start_time + 1 hour
            summary: Event title/summary. If None, uses description
            attendees: List of email addresses to invite as attendees

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

            # Use summary if provided, otherwise use description as summary
            event_summary = summary or description

            event = {
                "summary": event_summary,
                "description": description,
                "start": {
                    "dateTime": start_time_str,
                    "timeZone": self.timezone_str,
                },
                "end": {
                    "dateTime": end_time_str,
                    "timeZone": self.timezone_str,
                },
            }

            # Add attendees if provided
            if attendees:
                # Remove duplicates and filter out the calendar owner to avoid self-invitation
                unique_attendees = []
                calendar_owner = self.calendar_id.lower()
                for email in attendees:
                    email_lower = email.lower()
                    if (
                        email_lower != calendar_owner
                        and email_lower not in unique_attendees
                    ):
                        unique_attendees.append(email)

                if unique_attendees:
                    event["attendees"] = [
                        {"email": email} for email in unique_attendees
                    ]
                    # Send invitations
                    event["guestsCanModify"] = False
                    event["guestsCanInviteOthers"] = False

            # Add Google Meet conference
            event["conferenceData"] = {
                "createRequest": {
                    "requestId": str(uuid.uuid4()),
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                },
            }

            # Create event with conference (conferenceDataVersion=1 is required)
            event = (
                self.service.events()
                .insert(
                    calendarId=self.calendar_id,
                    body=event,
                    sendUpdates="all",
                    conferenceDataVersion=1,
                )
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
            self.service.events().update(
                calendarId=self.calendar_id, eventId=event_id, body=event
            ).execute()

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
                        max_occurrences=None,
                    )
                    event["recurrence"] = [f"RRULE:{rrule}"]

            # Update the event
            self.service.events().update(
                calendarId=self.calendar_id, eventId=event_id, body=event
            ).execute()

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

    def freebusy_query(
        self,
        participant_emails: List[str],
        start_date: datetime,
        end_date: datetime,
        duration_minutes: int = 30,
        timezone_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Query freebusy information for multiple participants.

        Uses Google Calendar Freebusy API to check availability of multiple calendars.
        Requires that calendars are public or shared with the service account owner.

        Args:
            participant_emails: List of email addresses to check availability for
            start_date: Start of time range to query
            end_date: End of time range to query
            duration_minutes: Minimum duration for free slots (not used in query, but for reference)
            timezone_str: Optional timezone string (e.g., "America/Sao_Paulo", "US/Pacific").
                        If None, uses self.timezone_str from settings

        Returns:
            Dictionary with structure:
            {
                "calendars": {
                    "email@example.com": {
                        "busy": [
                            {"start": "2025-11-20T10:00:00Z", "end": "2025-11-20T11:00:00Z"}
                        ]
                    }
                },
                "unavailable": ["email2@example.com"]  # Emails whose calendars couldn't be accessed
            }
        """
        if not self.service:
            logger.warning("Google Calendar service not initialized")
            return {"calendars": {}, "unavailable": participant_emails}

        try:
            # Use provided timezone or fallback to default
            tz = pytz.timezone(timezone_str) if timezone_str else self.timezone

            # Ensure datetimes are timezone-aware
            if start_date.tzinfo is None:
                start_date = tz.localize(start_date)
            else:
                start_date = start_date.astimezone(tz)

            if end_date.tzinfo is None:
                end_date = tz.localize(end_date)
            else:
                end_date = end_date.astimezone(tz)

            # Format as RFC3339 for API
            time_min = start_date.isoformat()
            time_max = end_date.isoformat()

            # Prepare items (each email is a calendar to check)
            items = [{"id": email} for email in participant_emails]

            # Call freebusy API
            body = {
                "timeMin": time_min,
                "timeMax": time_max,
                "items": items,
            }

            freebusy_response = self.service.freebusy().query(body=body).execute()

            calendars_result = freebusy_response.get("calendars", {})
            unavailable = []

            # Check which calendars were successfully queried
            for email in participant_emails:
                if email not in calendars_result:
                    unavailable.append(email)
                elif "errors" in calendars_result[email]:
                    # Calendar exists but has errors (e.g., permission denied)
                    unavailable.append(email)
                    logger.warning(
                        f"Error accessing calendar for {email}: {calendars_result[email].get('errors')}"
                    )

            result = {
                "calendars": {
                    email: calendars_result[email]
                    for email in participant_emails
                    if email not in unavailable
                },
                "unavailable": unavailable,
            }

            logger.info(
                f"Freebusy query completed: {len(participant_emails) - len(unavailable)}/{len(participant_emails)} calendars accessible"
            )

            return result

        except HttpError as e:
            logger.error(f"Error querying freebusy: {e}")
            return {"calendars": {}, "unavailable": participant_emails}
        except Exception as e:
            logger.error(f"Unexpected error in freebusy_query: {e}")
            return {"calendars": {}, "unavailable": participant_emails}

    @staticmethod
    def get_availability_slots(
        user_token: Dict[str, Any],
        participant_emails: List[str],
        start_date: datetime,
        end_date: datetime,
        duration_minutes: int = 30,
        timezone_str: Optional[str] = None,
        supabase_service = None,
        user_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get availability slots for a user using their own token.
        
        This method creates a temporary service instance using the user's token
        to query freebusy information. Used for multi-user scenarios where
        each user has their own OAuth token.
        
        Args:
            user_token: User's OAuth token JSON (dict)
            participant_emails: List of email addresses to check availability for
            start_date: Start of time range to query
            end_date: End of time range to query
            duration_minutes: Minimum duration for free slots
            timezone_str: Optional timezone string (e.g., "America/Sao_Paulo")
            supabase_service: Optional SupabaseService instance to save refreshed token
            user_email: Optional user email to save refreshed token (required if supabase_service is provided)
            
        Returns:
            Dictionary with structure:
            {
                "calendars": {
                    "email@example.com": {
                        "busy": [
                            {"start": "2025-11-20T10:00:00Z", "end": "2025-11-20T11:00:00Z"}
                        ]
                    }
                },
                "unavailable": ["email2@example.com"]
            }
        """
        try:
            # Create credentials from user token
            # Scope for freebusy is calendar.freebusy
            freebusy_scopes = ["https://www.googleapis.com/auth/calendar.freebusy"]
            creds = Credentials.from_authorized_user_info(user_token, freebusy_scopes)
            
            # Refresh token if expired and save updated token back to database
            token_was_refreshed = False
            if creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    token_was_refreshed = True
                    logger.info("Token refreshed successfully for calendar freebusy query")
                    
                    # Save refreshed token back to database if supabase_service is provided
                    if supabase_service and user_email:
                        try:
                            # Convert credentials back to dict format for storage
                            refreshed_token_dict = {
                                "token": creds.token,
                                "refresh_token": creds.refresh_token,
                                "token_uri": creds.token_uri,
                                "client_id": creds.client_id,
                                "client_secret": creds.client_secret,
                                "scopes": creds.scopes or user_token.get("scopes", []),
                            }
                            
                            supabase_service.update_user_token(user_email, refreshed_token_dict)
                            logger.info(f"Refreshed token saved to database for user {user_email}")
                        except Exception as e:
                            logger.warning(
                                f"Failed to save refreshed token to database for {user_email}: {e}. "
                                "Token was refreshed but not persisted."
                            )
                except Exception as e:
                    logger.error(f"Failed to refresh token: {e}")
                    return {"calendars": {}, "unavailable": participant_emails}
            
            # Build temporary service
            service = build("calendar", "v3", credentials=creds)
            
            # Use provided timezone or default
            tz = pytz.timezone(timezone_str) if timezone_str else pytz.timezone("America/Sao_Paulo")
            
            # Ensure datetimes are timezone-aware
            if start_date.tzinfo is None:
                start_date = tz.localize(start_date)
            else:
                start_date = start_date.astimezone(tz)
                
            if end_date.tzinfo is None:
                end_date = tz.localize(end_date)
            else:
                end_date = end_date.astimezone(tz)
            
            # Format as RFC3339 for API
            time_min = start_date.isoformat()
            time_max = end_date.isoformat()
            
            # Prepare items (each email is a calendar to check)
            items = [{"id": email} for email in participant_emails]
            
            # Call freebusy API
            body = {
                "timeMin": time_min,
                "timeMax": time_max,
                "items": items,
            }
            
            freebusy_response = service.freebusy().query(body=body).execute()
            
            calendars_result = freebusy_response.get("calendars", {})
            unavailable = []
            
            # Check which calendars were successfully queried
            for email in participant_emails:
                if email not in calendars_result:
                    unavailable.append(email)
                elif "errors" in calendars_result[email]:
                    unavailable.append(email)
                    logger.warning(
                        f"Error accessing calendar for {email}: {calendars_result[email].get('errors')}"
                    )
            
            result = {
                "calendars": {
                    email: calendars_result[email]
                    for email in participant_emails
                    if email not in unavailable
                },
                "unavailable": unavailable,
            }
            
            logger.info(
                f"Freebusy query completed for user: {len(participant_emails) - len(unavailable)}/{len(participant_emails)} calendars accessible"
            )
            
            return result
            
        except HttpError as e:
            logger.error(f"Error querying freebusy with user token: {e}")
            return {"calendars": {}, "unavailable": participant_emails}
        except Exception as e:
            logger.error(f"Unexpected error in get_availability_slots: {e}")
            return {"calendars": {}, "unavailable": participant_emails}

    def find_common_free_slots(
        self,
        participant_emails: List[str],
        start_date: datetime,
        end_date: datetime,
        duration_minutes: int = 30,
        num_suggestions: int = 3,
        work_hours_start: int = 9,
        work_hours_end: int = 17,
        timezone_str: Optional[str] = None,
        calendars_busy: Optional[Dict[str, Any]] = None,
        unavailable: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Find common free time slots for multiple participants.

        Args:
            participant_emails: List of email addresses to find common availability
            start_date: Start of time range to search
            end_date: End of time range to search
            duration_minutes: Duration of meeting slots to find
            num_suggestions: Number of suggestions to return
            work_hours_start: Start of work day (24h format)
            work_hours_end: End of work day (24h format)
            timezone_str: Optional timezone string (e.g., "America/Sao_Paulo", "US/Pacific").
                        If None, uses self.timezone_str from settings
            calendars_busy: Optional pre-computed busy periods from freebusy query.
                          If provided, skips freebusy_query call (for multi-user scenarios).
            unavailable: Optional list of participant emails whose calendars couldn't be accessed.
                        Required if calendars_busy is provided.

        Returns:
            List of suggestions, each with:
            {
                "start": datetime,
                "end": datetime,
                "verified_participants": [emails],
                "unverified_participants": [emails]
            }
        """
        # Use provided timezone or fallback to default
        tz = pytz.timezone(timezone_str) if timezone_str else self.timezone

        # Query freebusy if not provided (backward compatibility)
        if calendars_busy is None:
            if not self.service:
                logger.warning("Google Calendar service not initialized")
                return []
            
            # Query freebusy (pass timezone down)
            freebusy_result = self.freebusy_query(
                participant_emails, start_date, end_date, duration_minutes, timezone_str
            )
            calendars_busy = freebusy_result.get("calendars", {})
            unavailable = freebusy_result.get("unavailable", [])
        else:
            # Use provided calendars_busy
            if unavailable is None:
                unavailable = []

        # If no calendars are accessible, return empty
        if not calendars_busy:
            logger.warning(
                "No calendars accessible for freebusy query. Cannot find common slots."
            )
            return []

        # Collect all busy periods from accessible calendars
        all_busy_periods = []
        for email, calendar_data in calendars_busy.items():
            busy_periods = calendar_data.get("busy", [])
            for period in busy_periods:
                # Parse ISO format datetimes
                busy_start = datetime.fromisoformat(
                    period["start"].replace("Z", "+00:00")
                )
                busy_end = datetime.fromisoformat(period["end"].replace("Z", "+00:00"))
                # Convert to specified timezone
                busy_start = busy_start.astimezone(tz)
                busy_end = busy_end.astimezone(tz)
                all_busy_periods.append((busy_start, busy_end))

        # Sort busy periods by start time
        all_busy_periods.sort(key=lambda x: x[0])

        # Find free slots
        suggestions = []
        start_date_local = start_date.astimezone(tz)
        end_date_local = end_date.astimezone(tz)
        duration_delta = timedelta(minutes=duration_minutes)

        # Ensure we never suggest times before the start_date (which should be current time or future)
        now_aware = datetime.now(tz)
        minimum_start = max(start_date_local, now_aware + timedelta(minutes=15))

        # Start from the day of start_date
        current_date = start_date_local.replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # Iterate through each day
        while current_date < end_date_local and len(suggestions) < num_suggestions:
            day_start = current_date.replace(
                hour=work_hours_start, minute=0, second=0, microsecond=0
            )
            day_end = current_date.replace(
                hour=work_hours_end, minute=0, second=0, microsecond=0
            )

            # Ensure day_start is not before minimum_start (current time + buffer)
            if day_start < minimum_start:
                day_start = minimum_start
                # Round up to nearest 15 minutes for cleaner suggestions
                if day_start.minute % 15 != 0:
                    minutes_to_add = 15 - (day_start.minute % 15)
                    day_start = day_start + timedelta(minutes=minutes_to_add)
                    day_start = day_start.replace(second=0, microsecond=0)

            if day_end > end_date_local:
                day_end = end_date_local
            if day_start >= day_end:
                current_date += timedelta(days=1)
                continue

            # Find busy periods that overlap with this day
            day_busy_periods = [
                (max(period_start, day_start), min(period_end, day_end))
                for period_start, period_end in all_busy_periods
                if period_start < day_end and period_end > day_start
            ]

            # Sort day busy periods
            day_busy_periods.sort(key=lambda x: x[0])

            # Find free slots in this day
            slot_start = day_start
            for busy_start, busy_end in day_busy_periods:
                # Check if there's a free slot before this busy period
                if slot_start + duration_delta <= busy_start:
                    # Double-check that the slot is in the future
                    if slot_start > minimum_start:
                        suggestions.append(
                            {
                                "start": slot_start,
                                "end": slot_start + duration_delta,
                                "verified_participants": list(calendars_busy.keys()),
                                "unverified_participants": unavailable,
                            }
                        )
                        if len(suggestions) >= num_suggestions:
                            break

                # Move slot_start to after this busy period
                slot_start = max(slot_start, busy_end)

            # Check if there's a free slot at the end of the day
            if (
                len(suggestions) < num_suggestions
                and slot_start + duration_delta <= day_end
            ):
                # Double-check that the slot is in the future
                if slot_start > minimum_start:
                    suggestions.append(
                        {
                            "start": slot_start,
                            "end": slot_start + duration_delta,
                            "verified_participants": list(calendars_busy.keys()),
                            "unverified_participants": unavailable,
                        }
                    )

            # Move to next day
            current_date += timedelta(days=1)

        logger.info(
            f"Found {len(suggestions)} common free slots for {len(participant_emails)} participants"
        )

        return suggestions
