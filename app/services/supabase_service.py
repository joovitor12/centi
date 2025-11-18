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
        self.client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    
    def get_all_appointments(self) -> List[Dict[str, Any]]:
        """Get all appointments ordered by time."""
        try:
            response = (
                self.client.table("appointments")
                .select("*")
                .order("time")
                .execute()
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
    
    def create_appointment(self, description: str, time: str) -> Dict[str, Any]:
        """Create a new appointment."""
        try:
            response = (
                self.client.table("appointments")
                .insert({"time": time, "description": description})
                .execute()
            )
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error(f"Error creating appointment: {e}")
            raise
    
    def update_appointment(
        self, 
        appointment_id: int, 
        description: Optional[str] = None,
        time: Optional[str] = None,
        updated_at: Optional[str] = None
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
            self.client.table("appointments").update(update_data).eq("id", appointment_id).execute()
            
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

