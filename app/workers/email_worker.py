"""Background worker for processing email meeting requests."""

import asyncio
import logging
import base64
from datetime import datetime
from typing import Optional, Dict, Any
from datetime import datetime as dt
from langfuse import observe, propagate_attributes

from app.config.settings import settings
from app.services.gmail_service import GmailService
from app.services.google_calendar_service import GoogleCalendarService
from app.services.supabase_service import SupabaseService
from app.services.email_meeting_coordinator import EmailMeetingCoordinator

logger = logging.getLogger(__name__)


class EmailWorker:
    """Background worker that polls Gmail and processes meeting requests."""

    def __init__(
        self,
        gmail_service: GmailService,
        calendar_service: GoogleCalendarService,
        supabase_service: SupabaseService,
    ):
        """Initialize email worker.

        Args:
            gmail_service: Gmail service instance
            calendar_service: Google Calendar service instance
            supabase_service: Supabase service instance
        """
        self.gmail_service = gmail_service
        self.calendar_service = calendar_service
        self.supabase_service = supabase_service
        self.coordinator = EmailMeetingCoordinator(
            gmail_service, calendar_service, supabase_service
        )
        self.running = False
        self.poll_interval = settings.GMAIL_POLL_INTERVAL_SECONDS
        self.centi_email = settings.CENTI_EMAIL_ADDRESS.lower()

    async def start(self):
        """Start the email polling loop."""
        self.running = True
        logger.info(
            f"Email worker started. Polling every {self.poll_interval} seconds."
        )

        while self.running:
            try:
                await self.process_new_emails()
            except Exception as e:
                logger.error(f"Error in email worker loop: {e}", exc_info=True)

            # Wait before next poll
            await asyncio.sleep(self.poll_interval)

    def stop(self):
        """Stop the email polling loop."""
        logger.info("Stopping email worker...")
        self.running = False

    async def process_new_emails(self):
        """Process new unread emails."""
        if not self.gmail_service.service:
            logger.warning("Gmail service not initialized. Skipping email check.")
            return

        try:
            # Get unread emails
            messages = self.gmail_service.get_unread_emails()

            if not messages:
                return

            logger.info(f"Processing {len(messages)} unread email(s)")

            for message_info in messages:
                try:
                    email_id = message_info["id"]
                    await self.process_email(email_id)
                except Exception as e:
                    logger.error(
                        f"Error processing email {email_id}: {e}", exc_info=True
                    )

        except Exception as e:
            logger.error(f"Error fetching emails: {e}", exc_info=True)

    @observe(name="process_email")
    async def process_email(self, email_id: str):
        """Process a single email.

        Args:
            email_id: Gmail message ID
        """
        try:
            # Get full email data
            email_data = self.gmail_service.get_email_by_id(email_id)

            if not email_data:
                logger.warning(f"Could not fetch email {email_id}")
                return

            # Extract thread ID
            thread_id = email_data.get("threadId")
            if not thread_id:
                logger.warning(f"Email {email_id} has no thread ID")
                return

            # Get thread data first to check if it's an existing thread
            thread_data = self.supabase_service.get_email_meeting_thread_by_thread_id(
                thread_id
            )
            
            # Check if Centi is CC'd (only processes when CC'd for privacy)
            # For existing threads: if Centi was originally CC'd, accept replies
            # For new threads: check if Centi is CC'd in the current email
            centi_in_thread = False
            if thread_data:
                # Existing thread - check if Centi was originally CC'd
                # If so, we accept the reply regardless of TO/CC in current message
                thread_data_full = self.gmail_service.get_thread_by_id(thread_id)
                if thread_data_full:
                    # Check if originally CC'd (privacy requirement)
                    originally_ccd = self.gmail_service.is_centi_in_thread(
                        thread_data_full, self.centi_email
                    )
                    if originally_ccd:
                        # If originally CC'd, accept this reply even if Centi is in TO
                        centi_in_thread = True
                        logger.info(
                            f"Thread {thread_id} is existing meeting thread. "
                            "Centi was originally CC'd, processing reply."
                        )
                    else:
                        logger.info(
                            f"Thread {thread_id} exists but Centi was not originally CC'd. Skipping."
                        )
            else:
                # New thread - check if Centi is CC'd in current email
                centi_in_thread = self.gmail_service.is_centi_mentioned(
                    email_data, self.centi_email
                )
                if not centi_in_thread:
                    logger.info(
                        f"New email {email_id} skipped: Centi not CC'd (privacy requirement)"
                    )
            
            if not centi_in_thread:
                # Not CC'd, mark as read and skip
                # Centi only responds when explicitly CC'd, not when directly addressed
                self.gmail_service.mark_as_read(email_id)
                return

            # Multi-user: Identify which user is in the thread
            # Extract all participant emails from the thread
            participants = self.gmail_service.extract_participants(email_data)
            all_participant_emails = set()
            all_participant_emails.update(participants.get("from", []))
            all_participant_emails.update(participants.get("to", []))
            all_participant_emails.update(participants.get("cc", []))
            
            # Also check full thread to find all participants
            thread_data_full = self.gmail_service.get_thread_by_id(thread_id)
            if thread_data_full:
                for message in thread_data_full.get("messages", []):
                    msg_participants = self.gmail_service.extract_participants(message)
                    all_participant_emails.update(msg_participants.get("from", []))
                    all_participant_emails.update(msg_participants.get("to", []))
                    all_participant_emails.update(msg_participants.get("cc", []))
            
            # Find which registered user is in the thread
            # Exclude Centi email from owner search (Centi is the bot, not a real user)
            owner_email = None
            owner_user_data = None
            
            # Try to find a registered user in the thread (excluding Centi email)
            for email in all_participant_emails:
                # Skip Centi email - it's the bot, not a real user
                if email.lower() == self.centi_email:
                    continue
                    
                user_data = self.supabase_service.get_user_by_email(email.lower())
                if user_data:
                    owner_email = email.lower()
                    owner_user_data = user_data
                    logger.info(
                        f"Found registered user in thread {thread_id}: {owner_email}"
                    )
                    break
            
            # Fallback to settings.GOOGLE_CALENDAR_ID for backward compatibility
            if not owner_email:
                owner_email = settings.GOOGLE_CALENDAR_ID
                if owner_email:
                    logger.info(
                        f"Using fallback owner_email from settings: {owner_email}"
                    )
            
            # Security check: Only process if a registered user is in thread
            if not owner_email:
                logger.warning(
                    f"No registered user found in thread {thread_id}. Skipping."
                )
                self.gmail_service.mark_as_read(email_id)
                return
            
            if not owner_user_data and owner_email:
                # Try to fetch user data if we used fallback
                owner_user_data = self.supabase_service.get_user_by_email(owner_email.lower())
                if not owner_user_data:
                    logger.warning(
                        f"User {owner_email} not found in database. Skipping thread {thread_id}."
                    )
                    self.gmail_service.mark_as_read(email_id)
                    return

            # Extract email body
            email_body = self._extract_email_body(email_data)
            if not email_body:
                logger.warning(f"Could not extract body from email {email_id}")
                self.gmail_service.mark_as_read(email_id)
                return

            # Use thread_id as session_id for Langfuse tracking
            # This groups all operations related to this email thread
            with propagate_attributes(
                session_id=f"email_thread_{thread_id}",
                user_id=owner_email if owner_email else None,
                metadata={
                    "email_id": email_id,
                    "thread_id": thread_id,
                    "source": "email_worker",
                },
            ):
                if thread_data:
                    # Existing thread - process as response
                    await self.handle_meeting_response(
                        email_id, thread_id, email_data, email_body, thread_data, 
                        owner_email=owner_email
                    )
                else:
                    # New thread - check if it's a meeting request
                    await self.handle_new_meeting_request(
                        email_id, thread_id, email_data, email_body, 
                        owner_email=owner_email
                    )

            # Mark email as processed (read)
            self.gmail_service.mark_as_read(email_id)

        except Exception as e:
            logger.error(f"Error processing email {email_id}: {e}", exc_info=True)

    @observe(name="handle_new_meeting_request")
    async def handle_new_meeting_request(
        self,
        email_id: str,
        thread_id: str,
        email_data: Dict[str, Any],
        email_body: str,
        owner_email: str,
    ):
        """Handle a new meeting request email.

        Args:
            email_id: Gmail message ID
            thread_id: Gmail thread ID
            email_data: Full email dictionary
            email_body: Email body text
        """
        try:
            # Detect if it's a meeting request
            is_meeting_request = await self.coordinator.detect_meeting_request(
                email_body
            )

            if not is_meeting_request:
                logger.info(f"Email {email_id} is not a meeting request. Skipping.")
                return

            logger.info(f"New meeting request detected in thread {thread_id}")

            # Extract participants
            participant_emails = self.coordinator.get_participants_from_email(
                email_data
            )

            if not participant_emails:
                logger.warning(f"No participants found in email {email_id}. Skipping.")
                return

            # Extract meeting context
            context = await self.coordinator.extract_meeting_context(email_body)

            # Get subject from email headers
            subject = self._extract_subject(email_data)

            # Generate time suggestions based only on the owner's calendar
            # We can only query calendars of users who have authenticated with Centi (owner)
            # Fetch owner user data to get their token
            owner_user_data = self.supabase_service.get_user_by_email(owner_email.lower()) if owner_email else None
            owner_token = owner_user_data.get("calendar_access_token") if owner_user_data else None
            owner_participant_tokens = {}
            if owner_email and owner_token:
                owner_participant_tokens[owner_email.lower()] = owner_token
            
            # Generate time suggestions using owner's token (only calendar we can access)
            suggestions = self.coordinator.generate_time_suggestions(
                participant_emails=participant_emails,  # Keep all participants for context/email
                duration_minutes=context.get("duration_minutes", 30),
                days_ahead=context.get("days_ahead", 14),
                timezone_str=context.get("timezone_str"),
                participant_tokens=owner_participant_tokens if owner_participant_tokens else None,
            )

            # Create thread record in database
            suggested_times_list = []
            for suggestion in suggestions:
                suggested_times_list.append(
                    {
                        "start": suggestion["start"].isoformat(),
                        "end": suggestion["end"].isoformat(),
                        "verified_participants": suggestion.get(
                            "verified_participants", []
                        ),
                        "unverified_participants": suggestion.get(
                            "unverified_participants", []
                        ),
                    }
                )

            self.supabase_service.create_email_meeting_thread(
                thread_id=thread_id,
                owner_email=owner_email,
                participant_emails=participant_emails,
                subject=subject,
                status="suggestions_sent" if suggestions else "pending",
                duration_minutes=context.get("duration_minutes", 30),
                meeting_description=context.get("meeting_description"),
                meeting_title=context.get("meeting_title"),
            )

            # Update with suggested times if any
            if suggested_times_list:
                self.supabase_service.update_email_meeting_thread(
                    thread_id=thread_id,
                    suggested_times=suggested_times_list,
                    last_email_id=email_id,
                    last_processed_at=datetime.now().isoformat(),
                )

            # Format and send reply
            reply_body = self.coordinator.format_suggestion_email(
                suggestions=suggestions,
                meeting_description=context.get("meeting_description"),
            )

            # Get all participants (excluding Centi) for reply
            participants = self.coordinator.get_participants_from_email(
                email_data, exclude_centi=True
            )

            # Get headers for threading
            headers = email_data.get("payload", {}).get("headers", [])
            message_id = next(
                (h.get("value") for h in headers if h.get("name") == "Message-ID"),
                None,
            )
            references = next(
                (h.get("value") for h in headers if h.get("name") == "References"),
                None,
            )

            # Send reply
            reply_subject = subject
            if not reply_subject.startswith("Re: "):
                reply_subject = f"Re: {reply_subject}"

            self.gmail_service.send_reply(
                thread_id=thread_id,
                to=participants,
                subject=reply_subject,
                body=reply_body,
                in_reply_to=message_id,
                references=references,
            )

            logger.info(f"Sent meeting suggestions for thread {thread_id}")

        except Exception as e:
            logger.error(f"Error handling new meeting request: {e}", exc_info=True)

    @observe(name="handle_meeting_response")
    async def handle_meeting_response(
        self,
        email_id: str,
        thread_id: str,
        email_data: Dict[str, Any],
        email_body: str,
        thread_data: Dict[str, Any],
        owner_email: str,
    ):
        """Handle a response to meeting suggestions.

        Args:
            email_id: Gmail message ID
            thread_id: Gmail thread ID
            email_data: Full email dictionary
            email_body: Email body text
            thread_data: Thread data from database
        """
        try:
            # owner_email is already identified in process_email() from registered users
            # We just need to verify the sender is the same user
            if not owner_email:
                logger.warning(
                    "No owner email provided. Cannot verify sender."
                )
                return

            # Extract sender email
            headers = email_data.get("payload", {}).get("headers", [])
            from_email = next(
                (
                    h.get("value")
                    for h in headers
                    if h.get("name", "").lower() == "from"
                ),
                None,
            )

            # Extract email from "Name <email>" format if needed
            if from_email and "<" in from_email:
                from_email = from_email.split("<")[1].split(">")[0]

            # Check if sender matches the identified owner (registered user)
            if from_email and from_email.lower() != owner_email.lower():
                logger.info(
                    f"Response from {from_email} ignored. Only the registered user ({owner_email}) can confirm meetings."
                )
                # Mark as read and ignore
                self.gmail_service.mark_as_read(email_id)
                return

            status = thread_data.get("status", "pending")

            # If already confirmed, ignore
            if status == "confirmed":
                logger.info(f"Thread {thread_id} already confirmed. Ignoring response.")
                return

            logger.info(
                f"Processing response from calendar owner for thread {thread_id}"
            )

            # Process the response
            response = await self.coordinator.process_meeting_response(
                email_body, thread_data
            )

            # Update last processed info
            self.supabase_service.update_email_meeting_thread(
                thread_id=thread_id,
                last_email_id=email_id,
                last_processed_at=datetime.now().isoformat(),
            )

            # Handle cancellation
            if response.get("cancelled"):
                self.supabase_service.update_email_meeting_thread(
                    thread_id=thread_id,
                    status="cancelled",
                )
                logger.info(f"Meeting cancelled for thread {thread_id}")
                return

            # Handle acceptance (full confirmation)
            # Note: Only the calendar owner can confirm meetings, so we treat all acceptances as full confirmations
            if response.get("accepted"):
                selected_index = response.get("selected_suggestion_index")
                suggested_times = thread_data.get("suggested_times", [])
                if not isinstance(suggested_times, list):
                    suggested_times = []

                if selected_index is not None and selected_index < len(suggested_times):
                    selected_suggestion = suggested_times[selected_index]

                    # Parse datetime strings back to datetime objects
                    start_dt = dt.fromisoformat(
                        selected_suggestion["start"].replace("Z", "+00:00")
                    )
                    end_dt = dt.fromisoformat(
                        selected_suggestion["end"].replace("Z", "+00:00")
                    )

                    selected_time = {
                        "start": start_dt,
                        "end": end_dt,
                    }

                    # Confirm meeting
                    participant_emails = thread_data.get("participant_emails", [])
                    owner_email = thread_data.get("owner_email")
                    meeting_description = thread_data.get("meeting_description")

                    # Get meeting_title from thread_data (now stored directly in the database field)
                    meeting_title = thread_data.get("meeting_title")

                    # Create event in Centi's calendar (users don't need calendar write permissions)
                    event_id = self.coordinator.confirm_meeting(
                        thread_id=thread_id,
                        selected_time=selected_time,
                        participant_emails=participant_emails,
                        meeting_description=meeting_description,
                        owner_email=owner_email,
                        meeting_title=meeting_title,
                    )

                    if event_id:
                        # Update thread status
                        self.supabase_service.update_email_meeting_thread(
                            thread_id=thread_id,
                            status="confirmed",
                            confirmed_time=start_dt.isoformat(),
                        )

                        # Send confirmation email
                        confirmation_body = self.coordinator.format_confirmation_email(
                            selected_time=selected_time,
                            meeting_description=meeting_description,
                        )

                        # Get participants for reply
                        participants = self.coordinator.get_participants_from_email(
                            email_data, exclude_centi=True
                        )

                        # Get headers for threading
                        headers = email_data.get("payload", {}).get("headers", [])
                        message_id = next(
                            (
                                h.get("value")
                                for h in headers
                                if h.get("name") == "Message-ID"
                            ),
                            None,
                        )
                        references = next(
                            (
                                h.get("value")
                                for h in headers
                                if h.get("name") == "References"
                            ),
                            None,
                        )

                        subject = thread_data.get("subject", "Meeting Confirmed")
                        if not subject.startswith("Re: "):
                            subject = f"Re: {subject}"

                        self.gmail_service.send_reply(
                            thread_id=thread_id,
                            to=participants,
                            subject=subject,
                            body=confirmation_body,
                            in_reply_to=message_id,
                            references=references,
                        )

                        logger.info(
                            f"Meeting confirmed and event created for thread {thread_id}"
                        )
                    else:
                        logger.error(
                            f"Failed to create calendar event for thread {thread_id}"
                        )

                return

            # Handle request for new suggestions
            if response.get("needs_new_suggestions"):
                logger.info(f"User requested new suggestions for thread {thread_id}")

                participant_emails = thread_data.get("participant_emails", [])
                duration_minutes = thread_data.get("duration_minutes", 30)
                owner_email = thread_data.get("owner_email")

                # Generate new suggestions based only on the owner's calendar
                owner_user_data = self.supabase_service.get_user_by_email(owner_email.lower()) if owner_email else None
                owner_token = owner_user_data.get("calendar_access_token") if owner_user_data else None
                owner_participant_tokens = {}
                if owner_email and owner_token:
                    owner_participant_tokens[owner_email.lower()] = owner_token
                
                # Get previously suggested times to exclude them from new suggestions
                previous_suggestions = thread_data.get("suggested_times", [])
                logger.info(f"Found {len(previous_suggestions)} previous suggestions to exclude: {previous_suggestions}")
                
                # Generate time suggestions using owner's token (only calendar we can access)
                suggestions = self.coordinator.generate_time_suggestions(
                    participant_emails=participant_emails,  # Keep all participants for context
                    duration_minutes=duration_minutes,
                    participant_tokens=owner_participant_tokens if owner_participant_tokens else None,
                    exclude_suggestions=previous_suggestions if previous_suggestions else None,
                )

                # Update suggested times
                suggested_times_list = []
                for suggestion in suggestions:
                    suggested_times_list.append(
                        {
                            "start": suggestion["start"].isoformat(),
                            "end": suggestion["end"].isoformat(),
                            "verified_participants": suggestion.get(
                                "verified_participants", []
                            ),
                            "unverified_participants": suggestion.get(
                                "unverified_participants", []
                            ),
                        }
                    )

                self.supabase_service.update_email_meeting_thread(
                    thread_id=thread_id,
                    status="suggestions_sent",
                    suggested_times=suggested_times_list,
                )

                # Send new suggestions
                meeting_description = thread_data.get("meeting_description")

                reply_body = self.coordinator.format_suggestion_email(
                    suggestions=suggestions,
                    meeting_description=meeting_description,
                )

                participants = self.coordinator.get_participants_from_email(
                    email_data, exclude_centi=True
                )

                headers = email_data.get("payload", {}).get("headers", [])
                message_id = next(
                    (h.get("value") for h in headers if h.get("name") == "Message-ID"),
                    None,
                )
                references = next(
                    (h.get("value") for h in headers if h.get("name") == "References"),
                    None,
                )

                subject = thread_data.get("subject", "New Meeting Suggestions")
                if not subject.startswith("Re: "):
                    subject = f"Re: {subject}"

                self.gmail_service.send_reply(
                    thread_id=thread_id,
                    to=participants,
                    subject=subject,
                    body=reply_body,
                    in_reply_to=message_id,
                    references=references,
                )

                logger.info(f"Sent new suggestions for thread {thread_id}")

        except Exception as e:
            logger.error(f"Error handling meeting response: {e}", exc_info=True)

    def _extract_email_body(self, email_data: Dict[str, Any]) -> Optional[str]:
        """Extract email body text from email data.

        Args:
            email_data: Full email dictionary from Gmail API

        Returns:
            Email body text, or None if not found
        """
        try:
            payload = email_data.get("payload", {})
            body_text = None

            # Check if message has parts (multipart) or is plain text
            parts = payload.get("parts", [])
            if parts:
                # Multipart message
                for part in parts:
                    mime_type = part.get("mimeType", "")
                    body = part.get("body", {})
                    data = body.get("data")

                    if mime_type == "text/plain" and data:
                        body_text = base64.urlsafe_b64decode(data).decode(
                            "utf-8", errors="ignore"
                        )
                        break
                    elif mime_type == "text/html" and data and not body_text:
                        # Fallback to HTML if plain text not found
                        html_body = base64.urlsafe_b64decode(data).decode(
                            "utf-8", errors="ignore"
                        )
                        # Simple HTML to text conversion
                        import re

                        body_text = re.sub(r"<[^>]+>", "", html_body)
                        body_text = body_text.strip()
            else:
                # Plain text message
                body = payload.get("body", {})
                data = body.get("data")
                if data:
                    body_text = base64.urlsafe_b64decode(data).decode(
                        "utf-8", errors="ignore"
                    )

            return body_text

        except Exception as e:
            logger.error(f"Error extracting email body: {e}")
            return None

    def _extract_subject(self, email_data: Dict[str, Any]) -> Optional[str]:
        """Extract email subject from email data.

        Args:
            email_data: Full email dictionary from Gmail API

        Returns:
            Email subject, or None if not found
        """
        try:
            headers = email_data.get("payload", {}).get("headers", [])
            for header in headers:
                if header.get("name", "").lower() == "subject":
                    return header.get("value", "")
            return None
        except Exception as e:
            logger.error(f"Error extracting subject: {e}")
            return None
