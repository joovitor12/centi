import asyncio
import logging
import os
import parlant.sdk as p
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime, timedelta

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")


async def main():
    # Create Supabase client inside main() so tools can access it
    global supabase
    supabase = create_client(url, key)

    @p.tool
    async def find_appointments(context: p.ToolContext, query: str) -> p.ToolResult:
        """Find appointments based on query. Can search by description or time period."""
        try:
            logger.info(f"Query received: {query}")

            response = (
                supabase.table("appointments").select("*").order("time").execute()
            )
            appointments = response.data

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
            response = (
                supabase.table("appointments")
                .insert(
                    {"time": appointment_time.isoformat(), "description": description}
                )
                .execute()
            )

            # Format user-friendly response
            formatted_time = appointment_time.strftime("%B %d, %Y at %I:%M %p")

            return p.ToolResult(
                data={
                    "message": f"'{description}' scheduled for {formatted_time}",
                    "appointment": response.data[0] if response.data else None,
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
            check_response = (
                supabase.table("appointments")
                .select("*")
                .eq("id", appointment_id)
                .execute()
            )

            if not check_response.data:
                logger.warning(f"Appointment ID {appointment_id} not found")
                return p.ToolResult(
                    data=f"No appointment found with ID {appointment_id}",
                    control={"lifespan": "response"},
                )

            # Delete the appointment
            response = (
                supabase.table("appointments")
                .delete()
                .eq("id", appointment_id)
                .execute()
            )

            # Verify deletion was successful
            if not response.data:
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
        new_description: str = None,
        new_when: str = None,
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
            check_response = (
                supabase.table("appointments")
                .select("*")
                .eq("id", appointment_id)
                .execute()
            )

            if not check_response.data:
                logger.warning(f"Appointment ID {appointment_id} not found")
                return p.ToolResult(
                    data=f"No appointment found with ID {appointment_id}",
                    control={"lifespan": "response"},
                )

            logger.info(f"Found appointment to edit: {check_response.data[0]}")

            update_data = {}
            if new_description:
                update_data["description"] = new_description
            if new_when:
                try:
                    appointment_time = datetime.fromisoformat(
                        new_when.replace("T", " ")
                    )
                    update_data["time"] = appointment_time.isoformat()
                except ValueError:
                    return p.ToolResult(
                        data=f"Invalid datetime format: '{new_when}'. Please use 'YYYY-MM-DD HH:MM:SS' format.",
                        control={"lifespan": "response"},
                    )

            if not update_data:
                return p.ToolResult(
                    data="No updates provided.", control={"lifespan": "response"}
                )

            # Update the appointment
            update_data["updated_at"] = datetime.now().isoformat()
            logger.info(f"Updating appointment with data: {update_data}")

            # Execute the update
            update_response = (
                supabase.table("appointments")
                .update(update_data)
                .eq("id", appointment_id)
                .execute()
            )

            # Fetch the updated appointment to return it
            response = (
                supabase.table("appointments")
                .select("*")
                .eq("id", appointment_id)
                .execute()
            )

            if not response.data:
                logger.error(
                    f"Update may have failed - could not fetch updated appointment ID {appointment_id}"
                )
                return p.ToolResult(
                    data=f"Failed to update appointment ID {appointment_id}. Appointment may not exist.",
                    control={"lifespan": "response"},
                )

            logger.info(f"Successfully updated appointment: {response.data[0]}")
            return p.ToolResult(
                data={
                    "message": f"Appointment ID {appointment_id} updated successfully.",
                    "appointment": response.data[0],
                }
            )
        except Exception as e:
            logger.error(f"Error editing appointment: {e}", exc_info=True)
            return p.ToolResult(
                data=f"Failed to edit appointment: {str(e)}",
                control={"lifespan": "response"},
            )

    try:
        async with p.Server() as server:
            agent = await server.create_agent(
                name="Centi",
                description="You are a professional assistant like Jarvis from Ironman.",
            )

            # Create specific guidelines following Parlant best practices
            await agent.create_guideline(
                condition="User wants to schedule, add, or create an appointment, meeting, reminder, or task",
                action=f"""You must calculate the exact datetime and provide it in the correct format.

EXAMPLES:
- If user says "in 5 hours" and current time is 09:24, calculate: 09:24 + 5 hours = 14:24, then format as "2025-11-14 14:24:00"
- If user says "tomorrow at 4:30pm", format as "2025-11-15 16:30:00" 
- If user says "today at 2pm", format as "2025-11-14 14:00:00"

CRITICAL: 
- NEVER use placeholder text like "calculated_datetime_based_on_current_time_plus_5_hours"
- ALWAYS provide an actual datetime string like "2025-11-14 14:24:00"
- Format must be exactly "YYYY-MM-DD HH:MM:SS"

Use add_appointment tool with description and the calculated when parameter. Today datetime is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}.""",
                tools=[add_appointment],
            )

            await agent.create_guideline(
                condition="User asks about their schedule, appointments, calendar, or what they have planned",
                action="Search and display their appointments using find_appointments",
                tools=[find_appointments],
            )

            await agent.create_guideline(
                condition="User wants to change or update an existing appointment, meeting, reminder, or task, need to return all existing appointments first for the user to decide which to edit",
                action="""When user wants to edit an appointment:
1. First use find_appointments to list all appointments
2. When the user specifies which appointment to edit (by ID number, description, or time), you MUST call the edit_appointment tool
3. CRITICALLY IMPORTANT: Use the 'id' field from the appointment data returned by find_appointments, NOT the position/index in the list
4. For example, if find_appointments returns appointments with ids [4, 5, 6, 7, 8] and the user says "ID 8" or "appointment 8", use appointment_id=8 (the database ID)
5. Extract the new description and/or new time from the user's request
6. Call edit_appointment with: appointment_id (the database ID), new_description (if changed), and new_when (if changed, in format "YYYY-MM-DD HH:MM:SS")
7. DO NOT just say you updated it - you MUST actually call the edit_appointment tool function""",
                tools=[find_appointments, edit_appointment],
            )

            await agent.create_guideline(
                condition="User wants to delete an appointment, meeting, reminder, or task",
                action="""When user wants to delete an appointment:
1. First use find_appointments to list all appointments
2. When the user specifies which appointment to delete (by ID number, description, or time), you MUST call the delete_appointment tool
3. CRITICALLY IMPORTANT: Use the 'id' field from the appointment data returned by find_appointments, NOT the position/index in the list
4. For example, if find_appointments returns appointments with ids [4, 5, 6, 7, 8] and the user says "ID 8" or "appointment 8", use appointment_id=8 (the database ID)
5. Call delete_appointment with: appointment_id (the database ID)""",
                tools=[find_appointments, delete_appointment],
            )

            logger.info("Agent initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        raise


if __name__ == "__main__":
    # Create a temporary client just to print initial data
    temp_supabase: Client = create_client(url, key)
    response = temp_supabase.table("appointments").select("*").execute()
    print("Appointments from Supabase:", response.data)
    asyncio.run(main())
