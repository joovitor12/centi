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
