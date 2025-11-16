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
    @p.tool
    async def find_appointments(context: p.ToolContext, query: str) -> p.ToolResult:
        """Find appointments based on query. Can search by description or time period."""
        try:
            logger.info(f"Query received: {query}")
            
            response = supabase.table("appointments").select("*").order("time").execute()
            appointments = response.data
            
            if not appointments:
                return p.ToolResult(
                    data={"appointments": [], "message": "No appointments found"}
                )
            
            formatted_appointments = []
            for apt in appointments:
                try:
                    if apt.get('time'):
                        try:
                            parsed_time = datetime.fromisoformat(apt['time'])
                            formatted_time = parsed_time.strftime("%B %d, %Y at %I:%M %p")
                        except:
                            formatted_time = apt['time']
                    else:
                        formatted_time = "Time not specified"
                        
                    formatted_appointments.append({
                        "id": apt.get('id'),
                        "description": apt.get('description'),
                        "time": formatted_time,
                        "raw_time": apt.get('time'),
                        "created_at": apt.get('created_at')
                    })
                except Exception as e:
                    logger.error(f"Error formatting appointment {apt}: {e}")
                    formatted_appointments.append(apt)
            
            return p.ToolResult(
                data={"appointments": formatted_appointments, "count": len(formatted_appointments)}
            )
        except Exception as e:
            logger.error(f"Error finding appointments: {e}")
            return p.ToolResult(
                data=f"Failed to find appointments: {str(e)}",
                control={"lifespan": "response"}
            )
        
    @p.tool
    async def add_appointment(
        context: p.ToolContext, 
        description: str,
        when: str
    ) -> p.ToolResult:
        """Add a new appointment/reminder.
        
        Args:
            description: What the appointment is about
            when: When the appointment should happen in format "YYYY-MM-DD HH:MM:SS"
        """
        try:
            logger.info(f"Adding appointment: description={description}, when={when}")
            
            try:
                appointment_time = datetime.fromisoformat(when.replace('T', ' '))
            except ValueError:
                return p.ToolResult(
                    data=f"Invalid datetime format: '{when}'. Please use 'YYYY-MM-DD HH:MM:SS' format.",
                    control={"lifespan": "response"}
                )
            
            # Basic validation: no appointments in the past
            if appointment_time < datetime.now() - timedelta(minutes=1):
                return p.ToolResult(
                    data=f"Cannot schedule appointments in the past. Requested: {when}",
                    control={"lifespan": "response"}
                )
            
            # Save to database
            response = supabase.table("appointments").insert({
                "time": appointment_time.isoformat(),
                "description": description
            }).execute()
            
            # Format user-friendly response
            formatted_time = appointment_time.strftime("%B %d, %Y at %I:%M %p")
            
            return p.ToolResult(
                data={
                    "message": f"'{description}' scheduled for {formatted_time}",
                    "appointment": response.data[0] if response.data else None
                }
            )
        except Exception as e:
            logger.error(f"Error adding appointment: {e}")
            return p.ToolResult(
                data=f"Failed to add appointment: {str(e)}",
                control={"lifespan": "response"}
            )
    
    @p.tool
    async def edit_appointment(
        context: p.ToolContext, 
        appointment_id: int,
        new_description: str = None,
        new_when: str = None
    ) -> p.ToolResult:
        """Edit an existing appointment.
        
        Args:
            appointment_id: ID of the appointment to edit
            new_description: New description (optional)
            new_when: New time in format "YYYY-MM-DD HH:MM:SS" (optional)
        """
        try:
            logger.info(f"Editing appointment ID {appointment_id}")
            
            update_data = {}
            if new_description:
                update_data["description"] = new_description
            if new_when:
                try:
                    appointment_time = datetime.fromisoformat(new_when.replace('T', ' '))
                    update_data["time"] = appointment_time.isoformat()
                except ValueError:
                    return p.ToolResult(
                        data=f"Invalid datetime format: '{new_when}'. Please use 'YYYY-MM-DD HH:MM:SS' format.",
                        control={"lifespan": "response"}
                    )
            
            if not update_data:
                return p.ToolResult(
                    data="No updates provided.",
                    control={"lifespan": "response"}
                )
            
            response = supabase.table("appointments").update(update_data).eq("id", appointment_id).execute()
            
            if not response.data:
                return p.ToolResult(
                    data=f"No appointment found with ID {appointment_id}",
                    control={"lifespan": "response"}
                )
            
            return p.ToolResult(
                data={
                    "message": f"Appointment ID {appointment_id} updated successfully.",
                    "appointment": response.data[0]
                }
            )
        except Exception as e:
            logger.error(f"Error editing appointment: {e}")
            return p.ToolResult(
                data=f"Failed to edit appointment: {str(e)}",
                control={"lifespan": "response"}
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
                tools=[add_appointment]
            )
            
            await agent.create_guideline(
                condition="User asks about their schedule, appointments, calendar, or what they have planned",
                action="Search and display their appointments using find_appointments",
                tools=[find_appointments]
            )

            await agent.create_guideline(
                condition="User wants to change or update an existing appointment, meeting, reminder, or task, need to return all existing appointments first for the user to decide which to edit",
                action="First use find_appointments to list all appointments, then use edit_appointment to make changes based on user input",
                tools=[find_appointments, edit_appointment]
            )
            
            logger.info("Agent initialized successfully")
            
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        raise

if __name__ == "__main__":
    supabase: Client = create_client(url, key)
    response = supabase.table("appointments").select("*").execute()
    print("Appointments from Supabase:", response.data)
    asyncio.run(main())