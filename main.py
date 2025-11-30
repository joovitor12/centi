"""Main application entry point."""

import asyncio
import logging
import parlant.sdk as p
from supabase import create_client, Client

from app.config.settings import settings
from app.services.supabase_service import SupabaseService
from app.services.google_calendar_service import GoogleCalendarService
from app.services.gmail_service import GmailService
from app.tools.appointments import create_appointment_tools
from app.tools.recurring_appointments import create_recurring_appointment_tools
from app.agent.guidelines import setup_guidelines
from app.workers.email_worker import EmailWorker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Main application function."""
    # Validate settings
    settings.validate()

    # Initialize services
    supabase_service = SupabaseService()
    google_calendar_service = GoogleCalendarService()

    # Initialize Gmail service (optional - only if CENTI_EMAIL_ADDRESS is configured)
    gmail_service = None
    email_worker = None

    if settings.CENTI_EMAIL_ADDRESS:
        try:
            gmail_service = GmailService()
            email_worker = EmailWorker(
                gmail_service, google_calendar_service, supabase_service
            )
            logger.info("Gmail service and Email worker initialized")
        except Exception as e:
            logger.warning(
                f"Failed to initialize Gmail service: {e}. Email meeting coordination will be disabled."
            )
    else:
        logger.info(
            "CENTI_EMAIL_ADDRESS not configured. Email meeting coordination disabled."
        )

    # Create tools
    appointment_tools = create_appointment_tools(
        supabase_service, google_calendar_service
    )
    recurring_appointment_tools = create_recurring_appointment_tools(
        supabase_service, google_calendar_service
    )

    worker_task = None

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

            # Start email worker in background if configured
            if email_worker:
                worker_task = asyncio.create_task(email_worker.start())
                logger.info("Email worker started in background")

            # The context manager blocks here until server shuts down
            # When it exits, we'll clean up the worker below

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        raise
    finally:
        # Stop email worker when server shuts down
        if email_worker:
            email_worker.stop()
            if worker_task:
                worker_task.cancel()
            logger.info("Email worker stopped")


if __name__ == "__main__":
    # Print initial appointments for debugging
    temp_supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    response = temp_supabase.table("appointments").select("*").execute()
    print("Appointments from Supabase:", response.data)

    asyncio.run(main())
