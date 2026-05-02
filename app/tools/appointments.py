"""Appointment management tools for Parlant."""

import logging
from datetime import datetime, timedelta
from typing import Optional
import parlant.sdk as p
from app.services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)


def create_appointment_tools(
    supabase_service: SupabaseService,
):
    """Create appointment management tools.

    Args:
        supabase_service: SupabaseService instance

    Returns:
        List of tool functions
    """

    @p.tool
    async def find_appointments(context: p.ToolContext, query: str) -> p.ToolResult:
        """Find appointments based on query. Can search by description or time period."""
        try:
            logger.info(f"Query received: {query}")

            appointments = supabase_service.get_all_appointments()

            if not appointments:
                return p.ToolResult(
                    data={"appointments": [], "message": "No appointments found"}
                )

            formatted_appointments = []
            for apt in appointments:
                try:
                    if apt.get("time"):
                        try:
                            parsed_time = datetime.fromisoformat(apt["time"])
                            formatted_time = parsed_time.strftime(
                                "%B %d, %Y at %I:%M %p"
                            )
                        except ValueError:
                            formatted_time = apt["time"]
                    else:
                        formatted_time = "Time not specified"

                    formatted_appointments.append(
                        {
                            "id": apt.get("id"),
                            "description": apt.get("description"),
                            "time": formatted_time,
                            "raw_time": apt.get("time"),
                            "created_at": apt.get("created_at"),
                        }
                    )
                except Exception as e:
                    logger.error(f"Error formatting appointment {apt}: {e}")
                    formatted_appointments.append(apt)

            # Add a note about using the ID for editing
            return p.ToolResult(
                data={
                    "appointments": formatted_appointments,
                    "count": len(formatted_appointments),
                    "note": "To edit an appointment, use the 'id' field (not the position in the list). For example, if you want to edit the first appointment shown, use its 'id' value.",
                }
            )

        except Exception as e:
            logger.error(f"Error finding appointments: {e}")
            return p.ToolResult(
                data=f"Failed to find appointments: {str(e)}",
                control={"lifespan": "response"},
            )

    @p.tool
    async def add_appointment(
        context: p.ToolContext, description: str, when: str
    ) -> p.ToolResult:
        """Add a new appointment/reminder.

        Args:
            description: What the appointment is about
            when: When the appointment should happen in format "YYYY-MM-DD HH:MM:SS"
        """
        try:
            logger.info(f"Adding appointment: description={description}, when={when}")

            try:
                appointment_time = datetime.fromisoformat(when.replace("T", " "))
            except ValueError:
                return p.ToolResult(
                    data=f"Invalid datetime format: '{when}'. Please use 'YYYY-MM-DD HH:MM:SS' format.",
                    control={"lifespan": "response"},
                )

            # Basic validation: no appointments in the past
            if appointment_time < datetime.now() - timedelta(minutes=1):
                return p.ToolResult(
                    data=f"Cannot schedule appointments in the past. Requested: {when}",
                    control={"lifespan": "response"},
                )

            # Save to database
            appointment = supabase_service.create_appointment(
                description=description,
                time=appointment_time.isoformat(),
            )

            # Format user-friendly response
            formatted_time = appointment_time.strftime("%B %d, %Y at %I:%M %p")

            return p.ToolResult(
                data={
                    "message": f"'{description}' scheduled for {formatted_time}",
                    "appointment": appointment,
                }
            )
        except Exception as e:
            logger.error(f"Error adding appointment: {e}")
            return p.ToolResult(
                data=f"Failed to add appointment: {str(e)}",
                control={"lifespan": "response"},
            )

    @p.tool
    async def delete_appointment(
        context: p.ToolContext,
        appointment_id: int,
    ) -> p.ToolResult:
        """Delete an existing appointment.
        IMPORTANT: Use the 'id' field from the appointment data (from find_appointments), NOT the position/index in the list.
        For example, if find_appointments returns appointments with ids [4, 5, 6, 7, 8], and the user says "appointment 5",
        use appointment_id=5 (the actual database ID), not 5 as an index.

        Args:
            appointment_id: The database ID of the appointment to delete (from the 'id' field in find_appointments results). REQUIRED.
        """
        try:
            logger.info(f"Deleting appointment ID: {appointment_id}")

            # First, verify the appointment exists
            appointment = supabase_service.get_appointment_by_id(appointment_id)

            if not appointment:
                logger.warning(f"Appointment ID {appointment_id} not found")
                return p.ToolResult(
                    data=f"No appointment found with ID {appointment_id}",
                    control={"lifespan": "response"},
                )

            # Delete the appointment from database
            success = supabase_service.delete_appointment(appointment_id)

            if not success:
                logger.warning(
                    f"Deletion may have failed - no data returned for ID {appointment_id}"
                )
                return p.ToolResult(
                    data=f"Failed to delete appointment ID {appointment_id}",
                    control={"lifespan": "response"},
                )

            logger.info(f"Successfully deleted appointment ID {appointment_id}")
            return p.ToolResult(
                data=f"Appointment ID {appointment_id} deleted successfully.",
                control={"lifespan": "response"},
            )
        except Exception as e:
            logger.error(f"Error deleting appointment: {e}", exc_info=True)
            return p.ToolResult(
                data=f"Failed to delete appointment: {str(e)}",
                control={"lifespan": "response"},
            )

    @p.tool
    async def edit_appointment(
        context: p.ToolContext,
        appointment_id: int,
        new_description: Optional[str] = None,
        new_when: Optional[str] = None,
    ) -> p.ToolResult:
        """Edit an existing appointment.

        IMPORTANT: Use the 'id' field from the appointment data (from find_appointments), NOT the position/index in the list.
        For example, if find_appointments returns appointments with ids [4, 5, 6, 7, 8], and the user says "appointment 5",
        use appointment_id=5 (the actual database ID), not 5 as an index.

        Args:
            appointment_id: The database ID of the appointment to edit (from the 'id' field in find_appointments results). REQUIRED.
            new_description: New description. At least one of new_description or new_when must be provided.
            new_when: New time in format "YYYY-MM-DD HH:MM:SS". At least one of new_description or new_when must be provided.
        """
        try:
            logger.info(
                f"Editing appointment ID {appointment_id} with new_description={new_description}, new_when={new_when}"
            )

            # First, verify the appointment exists
            appointment = supabase_service.get_appointment_by_id(appointment_id)

            if not appointment:
                logger.warning(f"Appointment ID {appointment_id} not found")
                return p.ToolResult(
                    data=f"No appointment found with ID {appointment_id}",
                    control={"lifespan": "response"},
                )

            logger.info(f"Found appointment to edit: {appointment}")

            # Prepare update data
            update_description = None
            update_time = None

            if new_description:
                update_description = new_description
            if new_when:
                try:
                    appointment_time = datetime.fromisoformat(
                        new_when.replace("T", " ")
                    )
                    update_time = appointment_time.isoformat()
                except ValueError:
                    return p.ToolResult(
                        data=f"Invalid datetime format: '{new_when}'. Please use 'YYYY-MM-DD HH:MM:SS' format.",
                        control={"lifespan": "response"},
                    )

            if not update_description and not update_time:
                return p.ToolResult(
                    data="No updates provided.", control={"lifespan": "response"}
                )

            # Update the appointment in database
            updated_at = datetime.now().isoformat()
            logger.info(
                f"Updating appointment with description={update_description}, time={update_time}"
            )

            updated_appointment = supabase_service.update_appointment(
                appointment_id=appointment_id,
                description=update_description,
                time=update_time,
                updated_at=updated_at,
            )

            if not updated_appointment:
                logger.error(
                    f"Update may have failed - could not fetch updated appointment ID {appointment_id}"
                )
                return p.ToolResult(
                    data=f"Failed to update appointment ID {appointment_id}. Appointment may not exist.",
                    control={"lifespan": "response"},
                )

            logger.info(f"Successfully updated appointment: {updated_appointment}")
            return p.ToolResult(
                data={
                    "message": f"Appointment ID {appointment_id} updated successfully.",
                    "appointment": updated_appointment,
                }
            )
        except Exception as e:
            logger.error(f"Error editing appointment: {e}", exc_info=True)
            return p.ToolResult(
                data=f"Failed to edit appointment: {str(e)}",
                control={"lifespan": "response"},
            )

    return [find_appointments, add_appointment, delete_appointment, edit_appointment]
