"""Production entry point - runs both Parlant and FastAPI OAuth server."""

import asyncio
import logging
import os
import threading
from fastapi import FastAPI
import uvicorn
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
from app.api.oauth import router as oauth_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app for OAuth endpoints
api_app = FastAPI(title="Centi OAuth API", version="1.0.0")
api_app.include_router(oauth_router)


@api_app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "message": "Centi API is running",
        "services": {
            "oauth": "/auth/google",
            "callback": "/auth/google/callback",
            "parlant": "running"
        }
    }


def run_fastapi_server():
    """Run FastAPI server in a separate thread."""
    try:
        # Get port from environment (Render provides PORT env var)
        port = int(os.environ.get("PORT", 8000))
        logger.info(f"Starting FastAPI OAuth server on port {port}")
        uvicorn.run(
            api_app,
            host="0.0.0.0",
            port=port,
            log_level="info",
            access_log=False  # Reduce logging noise
        )
    except Exception as e:
        logger.error(f"Failed to start FastAPI server: {e}", exc_info=True)


async def run_parlant_app():
    """Run Parlant main application."""
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


async def main():
    """Main function - starts both services."""
    # Start FastAPI server in background thread
    fastapi_thread = threading.Thread(target=run_fastapi_server, daemon=True)
    fastapi_thread.start()
    
    # Give FastAPI a moment to start
    await asyncio.sleep(1)
    
    logger.info("Both services started:")
    logger.info("  - FastAPI OAuth server: http://0.0.0.0:8000")
    logger.info("  - Parlant agent: running")
    
    # Run Parlant in main async context
    await run_parlant_app()


if __name__ == "__main__":
    # Print initial appointments for debugging
    temp_supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    response = temp_supabase.table("appointments").select("*").execute()
    print("Appointments from Supabase:", response.data)

    asyncio.run(main())

