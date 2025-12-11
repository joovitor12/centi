"""Appointment management tools for Parlant."""

import logging
from datetime import datetime, timedelta
from typing import Optional
import parlant.sdk as p
from app.services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)


def get_customer_email_from_context(context: p.ToolContext, supabase_service: SupabaseService) -> Optional[str]:
    """Helper function to extract customer email from Parlant ToolContext.
    
    Tries multiple methods to get the customer email from the context.
    
    Args:
        context: Parlant ToolContext
        supabase_service: SupabaseService instance for fallback lookup
        
    Returns:
        Customer email if found, None otherwise
    """
    customer_email = None
    
    # Method 1: Use session_id to lookup user in database (most reliable)
    if hasattr(context, "session_id"):
        try:
            session_id = str(context.session_id)
            logger.info(f"Looking up user by session_id from context: {session_id}")
            user = supabase_service.get_user_by_parlant_session(session_id)
            if user:
                customer_email = user.get("user_email")
                logger.info(f"Found customer email via session_id lookup: {customer_email}")
                return customer_email
            else:
                logger.warning(f"No user found in database for session_id: {session_id}")
        except Exception as e:
            logger.warning(f"Could not get email from session_id: {e}", exc_info=True)
    
    # Method 2: Use customer_id if available (might be customer ID, not email)
    if not customer_email and hasattr(context, "customer_id"):
        customer_id = context.customer_id
        logger.info(f"Context has customer_id: {customer_id}")
        # If customer_id looks like an email, use it
        if isinstance(customer_id, str) and "@" in customer_id:
            customer_email = customer_id
            logger.info(f"Using customer_id as email (looks like email): {customer_email}")
            return customer_email
    
    # Method 3: Fallback - try context.session if it exists
    if not customer_email and hasattr(context, "session"):
        if hasattr(context.session, "customer") and hasattr(context.session.customer, "email"):
            customer_email = context.session.customer.email
            logger.info(f"Found customer email via session.customer.email: {customer_email}")
            return customer_email
        elif hasattr(context.session, "customer_email"):
            customer_email = context.session.customer_email
            logger.info(f"Found customer email via session.customer_email: {customer_email}")
            return customer_email
    
    if not customer_email:
        logger.error(f"Could not find customer email. Context attributes: {[a for a in dir(context) if not a.startswith('_')]}")
        if hasattr(context, "session_id"):
            logger.error(f"session_id: {context.session_id}")
        if hasattr(context, "customer_id"):
            logger.error(f"customer_id: {context.customer_id}")
    
    return customer_email


def create_appointment_tools(
    supabase_service: SupabaseService,
    google_calendar_service=None,
):
    """Create appointment management tools.

    Args:
        supabase_service: SupabaseService instance
        google_calendar_service: Optional GoogleCalendarService instance for calendar sync

    Returns:
        List of tool functions
    """

    @p.tool
    async def find_appointments(context: p.ToolContext, query: str) -> p.ToolResult:
        """Find appointments based on query. Can search by description or time period."""
        try:
            logger.info(f"Query received: {query}")

            # Get customer email from context
            customer_email = get_customer_email_from_context(context, supabase_service)
            
            if not customer_email:
                logger.error(f"Could not find customer email from context")
                return p.ToolResult(
                    data="Error: Could not identify customer email from context",
                    control={"lifespan": "response"},
                )
            
            logger.info(f"Finding appointments for user: {customer_email}")

            appointments = supabase_service.get_all_appointments(user_email=customer_email)

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

            # Get customer email from context
            customer_email = get_customer_email_from_context(context, supabase_service)
            
            if not customer_email:
                # Extra debug info
                logger.error(f"Could not find customer email from context")
                logger.error(f"Context repr: {repr(context)[:500]}")
                if hasattr(context, "session"):
                    logger.error(f"Session repr: {repr(context.session)[:500]}")
                return p.ToolResult(
                    data="Error: Could not identify customer email from context",
                    control={"lifespan": "response"},
                )
            
            logger.info(f"Adding appointment for user: {customer_email}")

            # Get user from database to retrieve token
            user = supabase_service.get_user_by_email(customer_email)
            if not user:
                return p.ToolResult(
                    data=f"Error: User {customer_email} not found. Please complete OAuth setup first.",
                    control={"lifespan": "response"},
                )
            
            # Get user's calendar token
            calendar_token = user.get("calendar_access_token")
            if not calendar_token:
                return p.ToolResult(
                    data=f"Error: Calendar access token not found for {customer_email}",
                    control={"lifespan": "response"},
                )
            
            # Parse token if it's a string
            if isinstance(calendar_token, str):
                import json
                calendar_token = json.loads(calendar_token)

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

            # Sync to Google Calendar using user's token (only if token has calendar scope)
            calendar_event_id = None
            token_scopes = calendar_token.get("scopes", [])
            # Check if token has calendar scope (not just freebusy)
            # freebusy scope: https://www.googleapis.com/auth/calendar.freebusy (read-only)
            # full calendar scope: https://www.googleapis.com/auth/calendar (read/write)
            has_calendar_scope = any(
                "calendar" in scope and "freebusy" not in scope
                for scope in token_scopes
            )
            
            if has_calendar_scope:
                try:
                    from app.services.google_calendar_service import GoogleCalendarService
                    calendar_event_id = GoogleCalendarService.create_event_with_token(
                        user_token=calendar_token,
                        description=description,
                        start_time=appointment_time,
                        supabase_service=supabase_service,
                        user_email=customer_email,
                    )
                    if calendar_event_id:
                        logger.info(
                            f"Appointment synced to Google Calendar: {calendar_event_id}"
                        )
                    else:
                        logger.warning(
                            "Failed to sync appointment to Google Calendar, but appointment will be saved to database"
                        )
                except Exception as e:
                    # Log error but don't fail the appointment creation
                    logger.warning(
                        f"Error syncing appointment to Google Calendar: {e}. "
                        "Appointment will be saved to database."
                    )
            else:
                logger.info(
                    f"Token has only freebusy scope, skipping Google Calendar sync. "
                    "Appointment will be saved to database only."
                )

            # Save to database (including google_calendar_event_id and user_email if available)
            appointment = supabase_service.create_appointment(
                description=description,
                time=appointment_time.isoformat(),
                user_email=customer_email,
                google_calendar_event_id=calendar_event_id,
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

            # Get customer email from context
            customer_email = get_customer_email_from_context(context, supabase_service)
            
            if not customer_email:
                logger.error(f"Could not find customer email from context")
                return p.ToolResult(
                    data="Error: Could not identify customer email from context",
                    control={"lifespan": "response"},
                )
            
            logger.info(f"Deleting appointment for user: {customer_email}")

            # First, verify the appointment exists and belongs to this user
            appointment = supabase_service.get_appointment_by_id(appointment_id, user_email=customer_email)

            if not appointment:
                logger.warning(f"Appointment ID {appointment_id} not found for user {customer_email}")
                return p.ToolResult(
                    data=f"No appointment found with ID {appointment_id}",
                    control={"lifespan": "response"},
                )

            # Delete from Google Calendar if event_id exists and token has calendar scope
            google_calendar_event_id = appointment.get("google_calendar_event_id")
            if google_calendar_event_id:
                user = supabase_service.get_user_by_email(customer_email)
                calendar_token = None
                if user:
                    calendar_token = user.get("calendar_access_token")
                    if isinstance(calendar_token, str):
                        import json
                        calendar_token = json.loads(calendar_token)
                    
                    # Check if token has calendar scope (not just freebusy)
                    token_scopes = calendar_token.get("scopes", [])
                    has_calendar_scope = any("calendar" in scope and "freebusy" not in scope for scope in token_scopes)
                    
                    if has_calendar_scope and calendar_token:
                        try:
                            from app.services.google_calendar_service import GoogleCalendarService
                            deleted = GoogleCalendarService.delete_event_with_token(
                                user_token=calendar_token,
                                event_id=google_calendar_event_id,
                                supabase_service=supabase_service,
                                user_email=customer_email,
                            )
                            if deleted:
                                logger.info(
                                    f"Deleted Google Calendar event: {google_calendar_event_id}"
                                )
                            else:
                                logger.warning(
                                    f"Failed to delete Google Calendar event: {google_calendar_event_id}"
                                )
                        except Exception as e:
                            # Log error but continue with database deletion
                            logger.warning(
                                f"Error deleting Google Calendar event: {e}. "
                                "Proceeding with database deletion."
                            )
                    else:
                        logger.info(
                            "Token has only freebusy scope, skipping Google Calendar deletion. "
                            "Appointment will be deleted from database only."
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

            # Get customer email from context
            customer_email = get_customer_email_from_context(context, supabase_service)
            
            if not customer_email:
                logger.error(f"Could not find customer email from context")
                return p.ToolResult(
                    data="Error: Could not identify customer email from context",
                    control={"lifespan": "response"},
                )
            
            logger.info(f"Editing appointment for user: {customer_email}")

            # First, verify the appointment exists and belongs to this user
            appointment = supabase_service.get_appointment_by_id(appointment_id, user_email=customer_email)

            if not appointment:
                logger.warning(f"Appointment ID {appointment_id} not found for user {customer_email}")
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

            # Update Google Calendar event if event_id exists and token has calendar scope
            google_calendar_event_id = appointment.get("google_calendar_event_id")
            if google_calendar_event_id:
                user = supabase_service.get_user_by_email(customer_email)
                calendar_token = None
                if user:
                    calendar_token = user.get("calendar_access_token")
                    if isinstance(calendar_token, str):
                        import json
                        calendar_token = json.loads(calendar_token)
                    
                    # Check if token has calendar scope (not just freebusy)
                    token_scopes = calendar_token.get("scopes", [])
                    has_calendar_scope = any("calendar" in scope and "freebusy" not in scope for scope in token_scopes)
                    
                    if has_calendar_scope and calendar_token:
                        try:
                            # Prepare update parameters for Google Calendar
                            calendar_start_time = None
                            calendar_end_time = None

                            if update_time:
                                calendar_start_time = datetime.fromisoformat(
                                    update_time.replace("T", " ")
                                )
                                calendar_end_time = calendar_start_time + timedelta(hours=1)

                            from app.services.google_calendar_service import GoogleCalendarService
                            updated = GoogleCalendarService.update_event_with_token(
                                user_token=calendar_token,
                                event_id=google_calendar_event_id,
                                description=update_description,
                                start_time=calendar_start_time,
                                end_time=calendar_end_time,
                                supabase_service=supabase_service,
                                user_email=customer_email,
                            )
                            if updated:
                                logger.info(
                                    f"Updated Google Calendar event: {google_calendar_event_id}"
                                )
                            else:
                                logger.warning(
                                    f"Failed to update Google Calendar event: {google_calendar_event_id}"
                                )
                        except Exception as e:
                            # Log error but continue with database update
                            logger.warning(
                                f"Error updating Google Calendar event: {e}. "
                                "Proceeding with database update."
                            )
                    else:
                        logger.info(
                            "Token has only freebusy scope, skipping Google Calendar update. "
                            "Appointment will be updated in database only."
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
