import asyncio
import logging
import os
import parlant.sdk as p
from pydantic import BaseModel
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

class Appointment(BaseModel):
    time: str
    description: str

async def main():
    @p.tool
    async def find_appointments(context: p.ToolContext, query: str) -> p.ToolResult:
        """Find appointments based on query."""
        try:
            logger.info(f"Query received: {query}")
            
            response = supabase.table("appointments").select("*").execute()
            print("Supabase response:", response)
            appointments = response.data
            
            return p.ToolResult(data=appointments)
        except Exception as e:
            logger.error(f"Error finding appointments: {e}")
            return p.ToolResult(error=str(e))
        
    @p.tool
    async def add_appointment(context: p.ToolContext, appointment: Appointment) -> p.ToolResult:
        """Add a new appointment."""
        try:
            logger.info(f"Adding appointment: {appointment}")
            
            response = supabase.table("appointments").insert({
                "time": appointment.time,
                "description": appointment.description
            }).execute()
            print("Supabase insert response:", response)
            
            return p.ToolResult(data=response.data)
        except Exception as e:
            logger.error(f"Error adding appointment: {e}")
            return p.ToolResult(error=str(e))
    
    try:
        async with p.Server() as server:
            agent = await server.create_agent(
                name="Centi",
                description="You are a professional assistant like Jarvis from Ironman.",
            )
            
            await agent.attach_tool(
                condition="When user asks about appointments, schedule, or calendar", 
                tool=find_appointments
            )

            await agent.attach_tool(
                condition="When user wants to add a new appointment/reminder/task to their schedule", 
                tool=add_appointment
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