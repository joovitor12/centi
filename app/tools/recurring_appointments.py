"""Recurring appointment management tools for Parlant."""

import logging
from datetime import datetime
from typing import Optional
import parlant.sdk as p
from app.services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)


def create_recurring_appointment_tools(
    supabase_service: SupabaseService,
):
    """Create recurring appointment management tools.

    Args:
        supabase_service: SupabaseService instance

    Returns:
        List of tool functions
    """

    @p.tool
    async def create_recurring_appointment(
        context: p.ToolContext,
        description: str,
        start_time: str,
        recurrence_pattern: str,
        recurrence_interval: int = 1,
        recurrence_byday: Optional[str] = None,
        recurrence_bymonthday: Optional[int] = None,
        end_time: Optional[str] = None,
        end_date: Optional[str] = None,
        max_occurrences: Optional[int] = None,
    ) -> p.ToolResult:
        """Create a recurring appointment that repeats automatically.

        Args:
            description: What the recurring appointment is about
            start_time: First occurrence time in format "YYYY-MM-DD HH:MM:SS"
            recurrence_pattern: Pattern type ("daily", "weekly", "monthly", "yearly")
            recurrence_interval: Interval (e.g., every 2 weeks = 2)
            recurrence_byday: Days of week for weekly (e.g., "MO,WE,FR" or "MO")
            recurrence_bymonthday: Day of month for monthly (e.g., 15)
            end_time: Event duration end time (optional, defaults to 1 hour after start)
            end_date: When recurrence should stop (optional, format "YYYY-MM-DD HH:MM:SS")
            max_occurrences: Maximum number of occurrences (optional)
        """
        try:
            logger.info(
                f"Creating recurring appointment: description={description}, pattern={recurrence_pattern}"
            )

            # Parse start_time
            try:
                start_datetime = datetime.fromisoformat(start_time.replace("T", " "))
            except ValueError:
                return p.ToolResult(
                    data=f"Invalid datetime format: '{start_time}'. Please use 'YYYY-MM-DD HH:MM:SS' format.",
                    control={"lifespan": "response"},
                )

            # Parse end_time if provided
            if end_time:
                try:
                    datetime.fromisoformat(end_time.replace("T", " "))
                except ValueError:
                    return p.ToolResult(
                        data=f"Invalid end_time format: '{end_time}'. Please use 'YYYY-MM-DD HH:MM:SS' format.",
                        control={"lifespan": "response"},
                    )

            # Parse end_date if provided
            if end_date:
                try:
                    datetime.fromisoformat(end_date.replace("T", " "))
                except ValueError:
                    return p.ToolResult(
                        data=f"Invalid end_date format: '{end_date}'. Please use 'YYYY-MM-DD HH:MM:SS' format.",
                        control={"lifespan": "response"},
                    )

            # Validate recurrence_pattern
            if recurrence_pattern.lower() not in [
                "daily",
                "weekly",
                "monthly",
                "yearly",
            ]:
                return p.ToolResult(
                    data=f"Invalid recurrence_pattern: '{recurrence_pattern}'. Must be one of: daily, weekly, monthly, yearly",
                    control={"lifespan": "response"},
                )

            # Save to database
            recurring_appointment = supabase_service.create_recurring_appointment(
                description=description,
                start_time=start_time,
                recurrence_pattern=recurrence_pattern,
                recurrence_interval=recurrence_interval,
                recurrence_byday=recurrence_byday,
                recurrence_bymonthday=recurrence_bymonthday,
                end_time=end_time,
                end_date=end_date,
                max_occurrences=max_occurrences,
            )

            formatted_start = start_datetime.strftime("%B %d, %Y at %I:%M %p")

            return p.ToolResult(
                data={
                    "message": f"Recurring appointment '{description}' created. First occurrence: {formatted_start}",
                    "recurring_appointment": recurring_appointment,
                }
            )
        except Exception as e:
            logger.error(f"Error creating recurring appointment: {e}", exc_info=True)
            return p.ToolResult(
                data=f"Failed to create recurring appointment: {str(e)}",
                control={"lifespan": "response"},
            )

    @p.tool
    async def list_recurring_appointments(
        context: p.ToolContext, active_only: bool = True
    ) -> p.ToolResult:
        """List all recurring appointments.

        Args:
            active_only: If True, only show active recurring appointments
        """
        try:
            logger.info(f"Listing recurring appointments (active_only={active_only})")

            recurring_appointments = supabase_service.get_all_recurring_appointments(
                active_only=active_only
            )

            if not recurring_appointments:
                return p.ToolResult(
                    data={
                        "recurring_appointments": [],
                        "message": "No recurring appointments found",
                    }
                )

            formatted_appointments = []
            for apt in recurring_appointments:
                try:
                    start_time_str = apt.get("start_time")
                    if start_time_str:
                        try:
                            parsed_time = datetime.fromisoformat(start_time_str)
                            formatted_time = parsed_time.strftime(
                                "%B %d, %Y at %I:%M %p"
                            )
                        except ValueError:
                            formatted_time = start_time_str
                    else:
                        formatted_time = "Time not specified"

                    formatted_appointments.append(
                        {
                            "id": apt.get("id"),
                            "description": apt.get("description"),
                            "start_time": formatted_time,
                            "pattern": apt.get("recurrence_pattern"),
                            "interval": apt.get("recurrence_interval"),
                            "is_active": apt.get("is_active"),
                        }
                    )
                except Exception as e:
                    logger.error(f"Error formatting recurring appointment {apt}: {e}")
                    formatted_appointments.append(apt)

            return p.ToolResult(
                data={
                    "recurring_appointments": formatted_appointments,
                    "count": len(formatted_appointments),
                }
            )
        except Exception as e:
            logger.error(f"Error listing recurring appointments: {e}")
            return p.ToolResult(
                data=f"Failed to list recurring appointments: {str(e)}",
                control={"lifespan": "response"},
            )

    @p.tool
    async def get_recurring_appointment(
        context: p.ToolContext, recurring_appointment_id: int
    ) -> p.ToolResult:
        """Get details of a specific recurring appointment."""
        try:
            logger.info(f"Getting recurring appointment ID: {recurring_appointment_id}")

            recurring_appointment = supabase_service.get_recurring_appointment_by_id(
                recurring_appointment_id
            )

            if not recurring_appointment:
                return p.ToolResult(
                    data=f"No recurring appointment found with ID {recurring_appointment_id}",
                    control={"lifespan": "response"},
                )

            return p.ToolResult(data={"recurring_appointment": recurring_appointment})
        except Exception as e:
            logger.error(f"Error getting recurring appointment: {e}")
            return p.ToolResult(
                data=f"Failed to get recurring appointment: {str(e)}",
                control={"lifespan": "response"},
            )

    @p.tool
    async def edit_recurring_appointment(
        context: p.ToolContext,
        recurring_appointment_id: int,
        description: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        recurrence_pattern: Optional[str] = None,
        recurrence_interval: Optional[int] = None,
        recurrence_byday: Optional[str] = None,
        recurrence_bymonthday: Optional[int] = None,
        end_date: Optional[str] = None,
    ) -> p.ToolResult:
        """Edit a recurring appointment.

        Updates the recurring appointment template in database.
        
        Args:
            recurring_appointment_id: ID of the recurring appointment to edit
            description: New description (optional)
            start_time: New start time in format "YYYY-MM-DD HH:MM:SS" (optional)
            end_time: New end time in format "YYYY-MM-DD HH:MM:SS" (optional). Used for event duration.
            recurrence_pattern: New recurrence pattern (optional)
            recurrence_interval: New recurrence interval (optional)
            recurrence_byday: New days of week for weekly patterns (optional)
            recurrence_bymonthday: New day of month for monthly patterns (optional)
            end_date: When recurrence should stop (optional)
        """
        try:
            logger.info(f"Editing recurring appointment ID {recurring_appointment_id}")

            # Get existing recurring appointment
            existing = supabase_service.get_recurring_appointment_by_id(
                recurring_appointment_id
            )

            if not existing:
                return p.ToolResult(
                    data=f"No recurring appointment found with ID {recurring_appointment_id}",
                    control={"lifespan": "response"},
                )

            # Update in database
            updated_appointment = supabase_service.update_recurring_appointment(
                recurring_appointment_id=recurring_appointment_id,
                description=description,
                start_time=start_time,
                end_time=end_time,
                recurrence_pattern=recurrence_pattern,
                recurrence_interval=recurrence_interval,
                recurrence_byday=recurrence_byday,
                recurrence_bymonthday=recurrence_bymonthday,
                end_date=end_date,
            )

            return p.ToolResult(
                data={
                    "message": f"Recurring appointment ID {recurring_appointment_id} updated successfully",
                    "recurring_appointment": updated_appointment,
                }
            )
        except Exception as e:
            logger.error(f"Error editing recurring appointment: {e}", exc_info=True)
            return p.ToolResult(
                data=f"Failed to edit recurring appointment: {str(e)}",
                control={"lifespan": "response"},
            )

    @p.tool
    async def pause_recurring_appointment(
        context: p.ToolContext, recurring_appointment_id: int
    ) -> p.ToolResult:
        """Pause a recurring appointment (stops creating new occurrences)."""
        try:
            logger.info(f"Pausing recurring appointment ID: {recurring_appointment_id}")

            # Get existing to check if it exists
            existing = supabase_service.get_recurring_appointment_by_id(
                recurring_appointment_id
            )

            if not existing:
                return p.ToolResult(
                    data=f"No recurring appointment found with ID {recurring_appointment_id}",
                    control={"lifespan": "response"},
                )

            # Mark as inactive in database
            updated_appointment = supabase_service.update_recurring_appointment(
                recurring_appointment_id=recurring_appointment_id,
                is_active=False,
            )

            return p.ToolResult(
                data={
                    "message": f"Recurring appointment ID {recurring_appointment_id} paused successfully",
                    "recurring_appointment": updated_appointment,
                }
            )
        except Exception as e:
            logger.error(f"Error pausing recurring appointment: {e}", exc_info=True)
            return p.ToolResult(
                data=f"Failed to pause recurring appointment: {str(e)}",
                control={"lifespan": "response"},
            )

    @p.tool
    async def resume_recurring_appointment(
        context: p.ToolContext, recurring_appointment_id: int
    ) -> p.ToolResult:
        """Resume a paused recurring appointment."""
        try:
            logger.info(
                f"Resuming recurring appointment ID: {recurring_appointment_id}"
            )

            # Get existing
            existing = supabase_service.get_recurring_appointment_by_id(
                recurring_appointment_id
            )

            if not existing:
                return p.ToolResult(
                    data=f"No recurring appointment found with ID {recurring_appointment_id}",
                    control={"lifespan": "response"},
                )

            # Mark as active
            updated_appointment = supabase_service.update_recurring_appointment(
                recurring_appointment_id=recurring_appointment_id,
                is_active=True,
            )

            return p.ToolResult(
                data={
                    "message": f"Recurring appointment ID {recurring_appointment_id} resumed successfully",
                    "recurring_appointment": updated_appointment,
                }
            )
        except Exception as e:
            logger.error(f"Error resuming recurring appointment: {e}", exc_info=True)
            return p.ToolResult(
                data=f"Failed to resume recurring appointment: {str(e)}",
                control={"lifespan": "response"},
            )

    @p.tool
    async def delete_recurring_appointment(
        context: p.ToolContext, recurring_appointment_id: int
    ) -> p.ToolResult:
        """Delete a recurring appointment completely.
        """
        try:
            logger.info(
                f"Deleting recurring appointment ID: {recurring_appointment_id}"
            )

            # Get existing to confirm it exists
            existing = supabase_service.get_recurring_appointment_by_id(
                recurring_appointment_id
            )

            if not existing:
                return p.ToolResult(
                    data=f"No recurring appointment found with ID {recurring_appointment_id}",
                    control={"lifespan": "response"},
                )

            # Delete from database
            success = supabase_service.delete_recurring_appointment(
                recurring_appointment_id
            )

            if not success:
                return p.ToolResult(
                    data=f"Failed to delete recurring appointment ID {recurring_appointment_id}",
                    control={"lifespan": "response"},
                )

            return p.ToolResult(
                data=f"Recurring appointment ID {recurring_appointment_id} deleted successfully"
            )
        except Exception as e:
            logger.error(f"Error deleting recurring appointment: {e}", exc_info=True)
            return p.ToolResult(
                data=f"Failed to delete recurring appointment: {str(e)}",
                control={"lifespan": "response"},
            )

    return [
        create_recurring_appointment,
        list_recurring_appointments,
        get_recurring_appointment,
        edit_recurring_appointment,
        pause_recurring_appointment,
        resume_recurring_appointment,
        delete_recurring_appointment,
    ]
