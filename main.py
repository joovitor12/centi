"""Main application entry point."""

import asyncio
import logging
import parlant.sdk as p
from supabase import create_client, Client

from app.config.settings import settings
from app.services.supabase_service import SupabaseService
from app.services.google_calendar_service import GoogleCalendarService
from app.tools.appointments import create_appointment_tools
from app.tools.recurring_appointments import create_recurring_appointment_tools
from app.agent.guidelines import setup_guidelines

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Main application function."""
    # Validate settings
    settings.validate()

    # Initialize services
    supabase_service = SupabaseService()
    google_calendar_service = GoogleCalendarService()

    # Create tools
    appointment_tools = create_appointment_tools(
        supabase_service, google_calendar_service
    )
    recurring_appointment_tools = create_recurring_appointment_tools(
        supabase_service, google_calendar_service
    )

    try:
        async with p.Server() as server:
            # Create agent
            agent = await server.create_agent(
                name="Centi",
                description="You are a professional assistant like Jarvis from Ironman.",
            )

            # Setup guidelines (tools are auto-discovered through guidelines)
            await setup_guidelines(
                agent, appointment_tools, recurring_appointment_tools
            )

            logger.info("Agent initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        raise


if __name__ == "__main__":
    # Print initial appointments for debugging
    temp_supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    response = temp_supabase.table("appointments").select("*").execute()
    print("Appointments from Supabase:", response.data)

    asyncio.run(main())
