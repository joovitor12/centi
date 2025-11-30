"""Supabase database service."""

import logging
from typing import Optional, List, Dict, Any
from supabase import create_client, Client
from app.config.settings import settings

logger = logging.getLogger(__name__)


class SupabaseService:
    """Service for interacting with Supabase database."""

    def __init__(self):
        """Initialize Supabase client."""
        self.client: Client = create_client(
            settings.SUPABASE_URL, settings.SUPABASE_KEY
        )

    def get_all_appointments(self) -> List[Dict[str, Any]]:
        """Get all appointments ordered by time."""
        try:
            response = (
                self.client.table("appointments").select("*").order("time").execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error fetching appointments: {e}")
            raise

    def get_appointment_by_id(self, appointment_id: int) -> Optional[Dict[str, Any]]:
        """Get a single appointment by ID."""
        try:
            response = (
                self.client.table("appointments")
                .select("*")
                .eq("id", appointment_id)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error fetching appointment {appointment_id}: {e}")
            raise

    def create_appointment(
        self,
        description: str,
        time: str,
        google_calendar_event_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new appointment."""
        try:
            data = {"time": time, "description": description}
            if google_calendar_event_id:
                data["google_calendar_event_id"] = google_calendar_event_id
            response = self.client.table("appointments").insert(data).execute()
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error(f"Error creating appointment: {e}")
            raise

    def update_appointment(
        self,
        appointment_id: int,
        description: Optional[str] = None,
        time: Optional[str] = None,
        updated_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an existing appointment."""
        try:
            update_data = {}
            if description is not None:
                update_data["description"] = description
            if time is not None:
                update_data["time"] = time
            if updated_at is not None:
                update_data["updated_at"] = updated_at

            # Execute the update
            self.client.table("appointments").update(update_data).eq(
                "id", appointment_id
            ).execute()

            # Fetch and return the updated appointment
            return self.get_appointment_by_id(appointment_id) or {}
        except Exception as e:
            logger.error(f"Error updating appointment {appointment_id}: {e}")
            raise

    def delete_appointment(self, appointment_id: int) -> bool:
        """Delete an appointment."""
        try:
            response = (
                self.client.table("appointments")
                .delete()
                .eq("id", appointment_id)
                .execute()
            )
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error deleting appointment {appointment_id}: {e}")
            raise

    def create_recurring_appointment(
        self,
        description: str,
        start_time: str,
        recurrence_pattern: str,
        recurrence_interval: int = 1,
        recurrence_byday: Optional[str] = None,
        recurrence_bymonthday: Optional[int] = None,
        end_time: Optional[str] = None,
        end_date: Optional[str] = None,
        max_occurrences: Optional[int] = None,
        google_calendar_event_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new recurring appointment template."""
        try:
            data = {
                "description": description,
                "start_time": start_time,
                "recurrence_pattern": recurrence_pattern,
                "recurrence_interval": recurrence_interval,
            }

            # Add optional fields only if provided
            if end_time is not None:
                data["end_time"] = end_time
            if recurrence_byday is not None:
                data["recurrence_byday"] = recurrence_byday
            if recurrence_bymonthday is not None:
                data["recurrence_bymonthday"] = recurrence_bymonthday
            if end_date is not None:
                data["end_date"] = end_date
            if max_occurrences is not None:
                data["max_occurrences"] = max_occurrences
            if google_calendar_event_id is not None:
                data["google_calendar_event_id"] = google_calendar_event_id

            response = (
                self.client.table("recurring_appointments").insert(data).execute()
            )
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error(f"Error creating recurring appointment: {e}")
            raise

    def get_all_recurring_appointments(
        self, active_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Get all recurring appointments, optionally filtered by active status."""
        try:
            query = self.client.table("recurring_appointments").select("*")

            if active_only:
                query = query.eq("is_active", True)

            response = query.order("start_time").execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error fetching recurring appointments: {e}")
            raise

    def get_recurring_appointment_by_id(
        self, recurring_appointment_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get a single recurring appointment by ID."""
        try:
            response = (
                self.client.table("recurring_appointments")
                .select("*")
                .eq("id", recurring_appointment_id)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(
                f"Error fetching recurring appointment {recurring_appointment_id}: {e}"
            )
            raise

    def update_recurring_appointment(
        self,
        recurring_appointment_id: int,
        description: Optional[str] = None,
        start_time: Optional[str] = None,
        recurrence_pattern: Optional[str] = None,
        recurrence_interval: Optional[int] = None,
        recurrence_byday: Optional[str] = None,
        recurrence_bymonthday: Optional[int] = None,
        end_time: Optional[str] = None,
        end_date: Optional[str] = None,
        max_occurrences: Optional[int] = None,
        is_active: Optional[bool] = None,
        google_calendar_event_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an existing recurring appointment."""
        try:
            update_data = {}

            # Only include fields that are explicitly provided (not None)
            if description is not None:
                update_data["description"] = description
            if start_time is not None:
                update_data["start_time"] = start_time
            if recurrence_pattern is not None:
                update_data["recurrence_pattern"] = recurrence_pattern
            if recurrence_interval is not None:
                update_data["recurrence_interval"] = recurrence_interval
            if recurrence_byday is not None:
                update_data["recurrence_byday"] = recurrence_byday
            if recurrence_bymonthday is not None:
                update_data["recurrence_bymonthday"] = recurrence_bymonthday
            if end_time is not None:
                update_data["end_time"] = end_time
            if end_date is not None:
                update_data["end_date"] = end_date
            if max_occurrences is not None:
                update_data["max_occurrences"] = max_occurrences
            if is_active is not None:
                update_data["is_active"] = is_active
            if google_calendar_event_id is not None:
                update_data["google_calendar_event_id"] = google_calendar_event_id

            # Always update updated_at timestamp
            from datetime import datetime

            update_data["updated_at"] = datetime.now().isoformat()

            # Execute the update
            self.client.table("recurring_appointments").update(update_data).eq(
                "id", recurring_appointment_id
            ).execute()

            # Fetch and return the updated recurring appointment
            return self.get_recurring_appointment_by_id(recurring_appointment_id) or {}
        except Exception as e:
            logger.error(
                f"Error updating recurring appointment {recurring_appointment_id}: {e}"
            )
            raise

    def delete_recurring_appointment(self, recurring_appointment_id: int) -> bool:
        """Delete a recurring appointment."""
        try:
            response = (
                self.client.table("recurring_appointments")
                .delete()
                .eq("id", recurring_appointment_id)
                .execute()
            )
            return bool(response.data)
        except Exception as e:
            logger.error(
                f"Error deleting recurring appointment {recurring_appointment_id}: {e}"
            )
            raise
    
    def create_email_meeting_thread(
        self,
        thread_id: str,
        owner_email: str,
        participant_emails: List[str],
        subject: Optional[str] = None,
        status: str = "pending",
        duration_minutes: int = 30,
        meeting_description: Optional[str] = None,
        meeting_title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new email meeting thread record.
        
        Args:
            thread_id: Gmail thread ID (unique)
            owner_email: Email of the Centi account owner
            participant_emails: List of participant email addresses
            subject: Email subject
            status: Initial status (default: 'pending')
            duration_minutes: Meeting duration in minutes
            meeting_description: Description of the meeting
            meeting_title: Optional meeting title/name
            
        Returns:
            Created thread record
        """
        try:
            data = {
                "thread_id": thread_id,
                "owner_email": owner_email,
                "participant_emails": participant_emails,
                "status": status,
                "duration_minutes": duration_minutes,
            }
            
            if subject is not None:
                data["subject"] = subject
            if meeting_description is not None:
                data["meeting_description"] = meeting_description
            if meeting_title is not None:
                data["meeting_title"] = meeting_title
                
            response = (
                self.client.table("email_meeting_threads").insert(data).execute()
            )
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error(f"Error creating email meeting thread: {e}")
            raise

    def get_email_meeting_thread_by_thread_id(
        self, thread_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get email meeting thread by Gmail thread ID.
        
        Args:
            thread_id: Gmail thread ID
            
        Returns:
            Thread record if found, None otherwise
        """
        try:
            response = (
                self.client.table("email_meeting_threads")
                .select("*")
                .eq("thread_id", thread_id)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error fetching email meeting thread {thread_id}: {e}")
            raise

    def update_email_meeting_thread(
        self,
        thread_id: str,
        status: Optional[str] = None,
        suggested_times: Optional[List[Dict[str, Any]]] = None,
        confirmed_time: Optional[str] = None,
        last_email_id: Optional[str] = None,
        last_processed_at: Optional[str] = None,
        meeting_description: Optional[str] = None,
        meeting_title: Optional[str] = None,
        duration_minutes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Update an existing email meeting thread.
        
        Args:
            thread_id: Gmail thread ID
            status: New status ('pending', 'suggestions_sent', 'confirmed', 'cancelled')
            suggested_times: List of suggested time slots (JSONB)
            confirmed_time: Confirmed meeting time (ISO format string)
            last_email_id: ID of last processed email in thread
            last_processed_at: Timestamp of last processing (ISO format string)
            meeting_description: Updated meeting description
            meeting_title: Updated meeting title
            duration_minutes: Updated duration
            
        Returns:
            Updated thread record
        """
        try:
            update_data = {}
            
            if status is not None:
                update_data["status"] = status
            if suggested_times is not None:
                update_data["suggested_times"] = suggested_times
            if confirmed_time is not None:
                update_data["confirmed_time"] = confirmed_time
            if last_email_id is not None:
                update_data["last_email_id"] = last_email_id
            if last_processed_at is not None:
                update_data["last_processed_at"] = last_processed_at
            if meeting_description is not None:
                update_data["meeting_description"] = meeting_description
            if meeting_title is not None:
                update_data["meeting_title"] = meeting_title
            if duration_minutes is not None:
                update_data["duration_minutes"] = duration_minutes
                
            # Always update updated_at timestamp
            from datetime import datetime
            update_data["updated_at"] = datetime.now().isoformat()
            
            # Execute the update
            self.client.table("email_meeting_threads").update(update_data).eq(
                "thread_id", thread_id
            ).execute()
            
            # Fetch and return the updated thread
            return self.get_email_meeting_thread_by_thread_id(thread_id) or {}
        except Exception as e:
            logger.error(f"Error updating email meeting thread {thread_id}: {e}")
            raise

    def get_pending_email_threads(
        self, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get email meeting threads by status.
        
        Args:
            status: Filter by status ('pending', 'suggestions_sent', etc.)
                   If None, returns all threads
                   
        Returns:
            List of thread records
        """
        try:
            query = self.client.table("email_meeting_threads").select("*")
            
            if status is not None:
                query = query.eq("status", status)
                
            response = query.order("created_at", desc=True).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error fetching pending email threads: {e}")
            raise
