"""Email meeting coordinator service for handling meeting scheduling via email."""

import logging
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import pytz
from pydantic import BaseModel, Field
from openai import AsyncOpenAI

from app.config.settings import settings
from app.services.gmail_service import GmailService
from app.services.google_calendar_service import GoogleCalendarService
from app.services.supabase_service import SupabaseService

# Import prompts from Langfuse
from app.agent.prompts.email_meeting_coordination.detect_meeting_request.system import (
    prompt as detect_meeting_request_system_prompt,
)
from app.agent.prompts.email_meeting_coordination.detect_meeting_request.user import (
    prompt as detect_meeting_request_user_prompt,
)
from app.agent.prompts.email_meeting_coordination.extract_meeting_context.system import (
    prompt as extract_context_system_prompt,
)
from app.agent.prompts.email_meeting_coordination.extract_meeting_context.user import (
    prompt as extract_context_user_prompt,
)
from app.agent.prompts.email_meeting_coordination.process_meeting_response.system import (
    prompt as process_response_system_prompt,
)
from app.agent.prompts.email_meeting_coordination.process_meeting_response.user import (
    prompt as process_response_user_prompt,
)

logger = logging.getLogger(__name__)


# Pydantic models for structured outputs
class MeetingContext(BaseModel):
    """Extracted meeting context from email."""

    is_meeting_request: bool = Field(
        description="Whether this email is requesting meeting scheduling"
    )
    duration_minutes: int = Field(default=30, description="Meeting duration in minutes")
    timezone_str: Optional[str] = Field(
        default=None,
        description="Timezone string (e.g., 'America/Sao_Paulo', 'US/Pacific') if mentioned",
    )
    meeting_description: Optional[str] = Field(
        default=None, description="Brief description of the meeting"
    )
    meeting_title: Optional[str] = Field(
        default=None,
        description="Specific title/name for the meeting if provided by user (e.g., 'Team Sync', 'Project Review'). If not provided, should be None.",
    )
    days_ahead: int = Field(
        default=14, description="How many days ahead to search for availability"
    )


class MeetingResponse(BaseModel):
    """Processed meeting response from email."""

    accepted: bool = Field(
        default=False, description="Whether a suggestion was accepted and the meeting should be confirmed"
    )
    selected_suggestion_index: Optional[int] = Field(
        default=None,
        description="0-based index of selected suggestion (if accepted)",
    )
    needs_new_suggestions: bool = Field(
        default=False, description="Whether user wants different time options"
    )
    cancelled: bool = Field(
        default=False, description="Whether the meeting was cancelled"
    )


class EmailMeetingCoordinator:
    """Coordinates meeting scheduling via email threads."""

    def __init__(
        self,
        gmail_service: GmailService,
        calendar_service: GoogleCalendarService,
        supabase_service: SupabaseService,
    ):
        """Initialize email meeting coordinator.

        Args:
            gmail_service: Gmail service instance
            calendar_service: Google Calendar service instance
            supabase_service: Supabase service instance
        """
        self.gmail_service = gmail_service
        self.calendar_service = calendar_service
        self.supabase_service = supabase_service
        self.centi_email = settings.CENTI_EMAIL_ADDRESS.lower()
        self.timezone = pytz.timezone(settings.GOOGLE_CALENDAR_TIMEZONE)

        # Initialize OpenAI client
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def detect_meeting_request(self, email_body: str) -> bool:
        """Detect if email contains a meeting scheduling request using OpenAI.

        Args:
            email_body: Email body text

        Returns:
            True if meeting request detected
        """
        if not email_body:
            return False

        try:
            # Get prompts from Langfuse
            system_prompt = detect_meeting_request_system_prompt.compile()
            user_prompt = detect_meeting_request_user_prompt.compile(
                email_body=email_body[:2000]
            )

            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )

            result = json.loads(response.choices[0].message.content)
            return result.get("is_meeting_request", False)
        except Exception as e:
            logger.error(f"Error detecting meeting request with OpenAI: {e}")
            # Fallback to simple keyword detection
            return (
                "find a time" in email_body.lower()
                or "schedule" in email_body.lower()
                or "centi" in email_body.lower()
            )

    async def extract_meeting_context(self, email_body: str) -> Dict[str, Any]:
        """Extract meeting context from email body using OpenAI.

        Args:
            email_body: Email body text

        Returns:
            Dictionary with duration_minutes, timezone hints, meeting_description, etc.
        """
        if not email_body:
            return {
                "duration_minutes": 30,
                "timezone_str": None,
                "meeting_description": None,
                "meeting_title": None,
                "days_ahead": 14,
            }

        try:
            # Get prompts from Langfuse
            system_prompt = extract_context_system_prompt.compile()
            user_prompt = extract_context_user_prompt.compile(
                email_body=email_body[:2000]
            )

            response = await self.openai_client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                response_format=MeetingContext,
                temperature=0.1,
            )

            context = response.choices[0].message.parsed
            return {
                "duration_minutes": context.duration_minutes,
                "timezone_str": context.timezone_str,
                "meeting_description": context.meeting_description,
                "meeting_title": context.meeting_title,
                "days_ahead": context.days_ahead,
            }
        except Exception as e:
            logger.error(f"Error extracting meeting context with OpenAI: {e}")
            # Fallback to defaults
            return {
                "duration_minutes": 30,
                "timezone_str": None,
                "meeting_description": None,
                "meeting_title": None,
                "days_ahead": 14,
            }

    def get_participants_from_email(
        self, email_data: Dict[str, Any], exclude_centi: bool = True
    ) -> List[str]:
        """Extract all participant emails from email, excluding Centi.

        Args:
            email_data: Full email dictionary
            exclude_centi: If True, exclude Centi's email from participants

        Returns:
            List of participant email addresses (lowercase)
        """
        participants = self.gmail_service.extract_participants(email_data)

        all_participants = set()
        all_participants.update(participants.get("from", []))
        all_participants.update(participants.get("to", []))
        all_participants.update(participants.get("cc", []))

        # Remove Centi's email
        if exclude_centi:
            all_participants.discard(self.centi_email)

        return [email.lower() for email in all_participants if email]

    def generate_time_suggestions(
        self,
        participant_emails: List[str],
        duration_minutes: int = 30,
        days_ahead: int = 14,
        num_suggestions: int = 3,
        timezone_str: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Generate time suggestions for participants.

        Args:
            participant_emails: List of participant emails
            duration_minutes: Meeting duration
            days_ahead: Number of days ahead to search
            num_suggestions: Number of suggestions to generate
            timezone_str: Optional timezone override

        Returns:
            List of suggestion dictionaries with start, end, verified_participants, etc.
            All suggestions will be in the future (after current time).
        """
        if not participant_emails:
            logger.warning("No participants provided for time suggestions")
            return []

        # Use provided timezone or fallback to default
        tz_str = timezone_str or settings.GOOGLE_CALENDAR_TIMEZONE
        tz = pytz.timezone(tz_str) if tz_str else self.timezone

        # Calculate date range - start from NOW (not midnight) to ensure all suggestions are future
        now = datetime.now(tz)
        # Add 15 minutes buffer to current time to avoid suggesting times too soon
        start_date = now + timedelta(minutes=15)
        # Round down to nearest 15 minutes for cleaner suggestions
        start_date = start_date.replace(minute=(start_date.minute // 15) * 15, second=0, microsecond=0)
        end_date = now + timedelta(days=days_ahead)

        # Generate suggestions using calendar service
        suggestions = self.calendar_service.find_common_free_slots(
            participant_emails=participant_emails,
            start_date=start_date,
            end_date=end_date,
            duration_minutes=duration_minutes,
            num_suggestions=num_suggestions,
            work_hours_start=9,
            work_hours_end=17,
            timezone_str=tz_str,
        )

        # Filter out any suggestions that are in the past (safety check)
        now_aware = datetime.now(tz)
        future_suggestions = [
            s for s in suggestions
            if s["start"] > now_aware
        ]

        logger.info(
            f"Filtered {len(suggestions) - len(future_suggestions)} past suggestions. "
            f"Returning {len(future_suggestions)} future suggestions."
        )

        return future_suggestions

    def format_suggestion_email(
        self,
        suggestions: List[Dict[str, Any]],
        meeting_description: Optional[str] = None,
        unverified_participants: List[str] = None,
    ) -> str:
        """Format email body with time suggestions.

        Args:
            suggestions: List of time suggestions
            meeting_description: Optional meeting description
            unverified_participants: List of participants whose calendars weren't accessible

        Returns:
            Formatted email body
        """
        if not suggestions:
            return self._format_no_suggestions_email(unverified_participants)

        unverified_participants = unverified_participants or []

        # Format suggestions
        suggestions_text = []
        for i, suggestion in enumerate(suggestions, 1):
            start_dt = suggestion["start"]
            end_dt = suggestion["end"]

            # Format datetime in readable format
            start_str = start_dt.strftime("%A, %B %d, %Y at %I:%M %p")
            end_str = end_dt.strftime("%I:%M %p")

            suggestions_text.append(f"{i}. {start_str} - {end_str}")

        # Build email body
        body_parts = [
            "Hi everyone,",
            "",
        ]

        if meeting_description:
            body_parts.append(
                f"I found some available times for: {meeting_description}"
            )
        else:
            body_parts.append("I found some available times for our meeting:")

        body_parts.extend(
            [
                "",
                "Here are my suggestions:",
            ]
        )

        body_parts.extend(suggestions_text)

        body_parts.append("")
        body_parts.append(
            "Please reply with the number of your preferred time, or let me know if you need different options."
        )

        if unverified_participants:
            unverified_list = ", ".join(unverified_participants)
            body_parts.append("")
            body_parts.append(
                f"Note: I couldn't access the calendars for: {unverified_list}. Suggestions are based on available calendars only."
            )

        body_parts.extend(
            [
                "",
                "Best regards,",
                "Centi",
            ]
        )

        return "\n".join(body_parts)

    def _format_no_suggestions_email(
        self, unverified_participants: List[str] = None
    ) -> str:
        """Format email when no suggestions are available."""
        unverified_participants = unverified_participants or []

        body_parts = [
            "Hi everyone,",
            "",
            "I checked the calendars but couldn't find any available time slots in the next two weeks.",
        ]

        if unverified_participants:
            unverified_list = ", ".join(unverified_participants)
            body_parts.append("")
            body_parts.append(
                f"Note: I couldn't access the calendars for: {unverified_list}. This may have affected the availability search."
            )

        body_parts.extend(
            [
                "",
                "Please suggest some times that work for you, and I'll check availability.",
                "",
                "Best regards,",
                "Centi",
            ]
        )

        return "\n".join(body_parts)

    async def process_meeting_response(
        self, email_body: str, thread_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process response to meeting suggestions using OpenAI.

        Args:
            email_body: Response email body
            thread_data: Thread data from database with suggested_times

        Returns:
            Dictionary with:
            - accepted: bool
            - selected_suggestion_index: Optional[int] (0-based)
            - needs_new_suggestions: bool
            - cancelled: bool
        """
        if not email_body:
            return {
                "accepted": False,
                "selected_suggestion_index": None,
                "needs_new_suggestions": False,
                "cancelled": False,
            }

        # Get suggested times for context
        suggested_times = thread_data.get("suggested_times", [])
        
        suggestions_context = ""
        if suggested_times and isinstance(suggested_times, list):
            suggestions_context = "Available suggestions:\n"
            for i, suggestion in enumerate(suggested_times, 1):
                start = suggestion.get("start", {})
                end = suggestion.get("end", {})
                if isinstance(start, str):
                    suggestions_context += f"{i}. {start} - {end}\n"
                else:
                    suggestions_context += f"{i}. Suggestion {i}\n"
        else:
            suggestions_context = "No previous suggestions available."

        try:
            # Get prompts from Langfuse
            system_prompt = process_response_system_prompt.compile()
            user_prompt = process_response_user_prompt.compile(
                suggestions_context=suggestions_context,
                email_body=email_body[:2000],
            )

            response = await self.openai_client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                response_format=MeetingResponse,
                temperature=0.1,
            )

            result = response.choices[0].message.parsed
            return {
                "accepted": result.accepted,
                "selected_suggestion_index": result.selected_suggestion_index,
                "needs_new_suggestions": result.needs_new_suggestions,
                "cancelled": result.cancelled,
            }
        except Exception as e:
            logger.error(f"Error processing meeting response with OpenAI: {e}")
            # Fallback: return default (no action)
            return {
                "accepted": False,
                "selected_suggestion_index": None,
                "needs_new_suggestions": False,
                "cancelled": False,
            }

    def confirm_meeting(
        self,
        thread_id: str,
        selected_time: Dict[str, Any],
        participant_emails: List[str],
        meeting_description: Optional[str] = None,
        owner_email: Optional[str] = None,
        meeting_title: Optional[str] = None,
    ) -> Optional[str]:
        """Confirm meeting and create calendar event.

        Args:
            thread_id: Gmail thread ID
            selected_time: Selected time suggestion dictionary
            participant_emails: List of participant emails
            meeting_description: Meeting description
            owner_email: Owner email (for calendar creation)
            meeting_title: Optional meeting title/name provided by user

        Returns:
            Google Calendar event ID if successful, None otherwise
        """
        start_time = selected_time["start"]
        end_time = selected_time["end"]

        # Use meeting_title if provided, otherwise default to "Meeting"
        event_summary = meeting_title.strip() if meeting_title and meeting_title.strip() else "Meeting"

        # Build event description with participants
        description_parts = []
        if meeting_description:
            description_parts.append(meeting_description)
        if len(participant_emails) > 1:
            # Add participants list
            if description_parts:
                description_parts.append("")
            description_parts.append("Participants:")
            description_parts.extend([f"- {email}" for email in participant_emails])

        # Create event in Google Calendar with attendees
        event_id = self.calendar_service.create_event(
            description="\n".join(description_parts) if description_parts else "",
            start_time=start_time,
            end_time=end_time,
            summary=event_summary,
            attendees=participant_emails,
        )

        if event_id:
            logger.info(f"Created calendar event {event_id} for thread {thread_id}")
        else:
            logger.error(f"Failed to create calendar event for thread {thread_id}")

        return event_id

    def format_partial_acceptance_email(
        self,
        selected_time: Dict[str, Any],
        meeting_description: Optional[str] = None,
        participant_emails: Optional[List[str]] = None,
        accepting_participant: Optional[str] = None,
    ) -> str:
        """Format email when a participant accepts but is waiting for others.

        Args:
            selected_time: Selected time suggestion
            meeting_description: Optional meeting description
            participant_emails: List of all participants
            accepting_participant: Email of the participant who accepted

        Returns:
            Formatted email body
        """
        start_dt = selected_time["start"]
        end_dt = selected_time["end"]

        start_str = start_dt.strftime("%A, %B %d, %Y at %I:%M %p")
        end_str = end_dt.strftime("%I:%M %p")

        body_parts = [
            "Hi everyone,",
            "",
            f"Great! I received confirmation for: {start_str} - {end_str}",
            "",
        ]

        if meeting_description:
            body_parts.append(f"Meeting: {meeting_description}")
            body_parts.append("")

        # Get remaining participants (excluding the one who already accepted)
        remaining_participants = []
        if participant_emails and accepting_participant:
            remaining_participants = [
                p for p in participant_emails
                if p.lower() != accepting_participant.lower()
            ]

        if remaining_participants:
            participant_list = ", ".join(remaining_participants)
            body_parts.append(
                f"Waiting for confirmation from: {participant_list}"
            )
            body_parts.append("")
            body_parts.append(
                "Please reply to confirm if this time works for you!"
            )
        else:
            body_parts.append("Waiting for confirmation from the remaining participants.")
            body_parts.append("")

        body_parts.extend(
            [
                "Best regards,",
                "Centi",
            ]
        )

        return "\n".join(body_parts)

    def format_confirmation_email(
        self,
        selected_time: Dict[str, Any],
        meeting_description: Optional[str] = None,
    ) -> str:
        """Format confirmation email.

        Args:
            selected_time: Selected time suggestion
            meeting_description: Optional meeting description

        Returns:
            Formatted email body
        """
        start_dt = selected_time["start"]
        end_dt = selected_time["end"]

        start_str = start_dt.strftime("%A, %B %d, %Y at %I:%M %p")
        end_str = end_dt.strftime("%I:%M %p")

        body_parts = [
            "Hi everyone,",
            "",
            "Great! The meeting has been confirmed:",
            "",
            f"Date & Time: {start_str} - {end_str}",
        ]

        if meeting_description:
            body_parts.append(f"Description: {meeting_description}")

        body_parts.extend(
            [
                "",
                "I've created a calendar event and sent invitations. See you then!",
                "",
                "Best regards,",
                "Centi",
            ]
        )

        return "\n".join(body_parts)
