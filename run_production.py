"""Production entry point - runs both Parlant and FastAPI OAuth server."""

import asyncio
import logging
import os
import threading
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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
from app.api.auth import router as auth_router
from app.api.session import router as session_router
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app for OAuth endpoints
api_app = FastAPI(title="Centi API", version="1.0.0")

# Configure CORS to allow frontend requests
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:8000",  # Same origin as API
        os.environ.get("FRONTEND_URL", "http://localhost:3000"),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_app.include_router(oauth_router)
api_app.include_router(auth_router)
api_app.include_router(session_router)

# Serve static files from frontend/build directory (if it exists)
frontend_build_path = os.path.join(os.path.dirname(__file__), "frontend", "build")
if os.path.exists(frontend_build_path):
    api_app.mount(
        "/static",
        StaticFiles(directory=os.path.join(frontend_build_path, "static")),
        name="static",
    )

    @api_app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve React frontend for all non-API routes."""
        # Don't serve API routes
        if full_path.startswith(("api/", "auth/", "docs", "openapi.json", "redoc")):
            raise HTTPException(status_code=404, detail="Not found")

        # If the path exists as a file, serve it
        file_path = os.path.join(frontend_build_path, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)

        # Otherwise serve index.html for React routes
        index_path = os.path.join(frontend_build_path, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        else:
            raise HTTPException(status_code=404, detail="Frontend not built")
else:
    logger.warning(
        f"Frontend build directory not found at {frontend_build_path}. Frontend will not be served."
    )


@api_app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "message": "Centi API is running",
        "services": {
            "oauth": "/auth/google",
            "callback": "/auth/google/callback",
            "parlant": "running",
        },
    }


def run_fastapi_server():
    """Run FastAPI server in a separate thread."""
    try:
        # Get port from environment (Render provides PORT env var)
        port = int(os.environ.get("PORT", 8000))
        logger.info(f"Starting FastAPI OAuth server on port {port}")
        logger.info(f"FastAPI app routes: {[route.path for route in api_app.routes]}")
        uvicorn.run(
            api_app,
            host="0.0.0.0",
            port=port,
            log_level="info",
            access_log=True,  # Enable access log for debugging
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

            # Get and log agent ID
            # First check if it's already in settings (.env)
            agent_id = settings.PARLANT_AGENT_ID
            
            if agent_id:
                logger.info(f"Using agent ID from settings: {agent_id}")
            else:
                # Try to get from agent object
                agent_id = getattr(agent, "id", None) or getattr(agent, "_id", None)
                if agent_id:
                    logger.info(f"Found agent ID from agent object: {agent_id}")
                    settings.PARLANT_AGENT_ID = str(agent_id)
                else:
                    # Try to get from agent attributes (for debugging)
                    agent_attrs = dir(agent)
                    id_attrs = [a for a in agent_attrs if 'id' in a.lower()]
                    logger.debug(f"Agent attributes with 'id': {id_attrs}")
                    
                    # Try to get agent ID via API
                    try:
                        import httpx

                        async with httpx.AsyncClient() as client:
                            response = await client.get(
                                f"{settings.PARLANT_SERVER_URL}/agents",
                                timeout=5.0,
                            )
                            if response.status_code == 200:
                                agents = response.json()
                                if isinstance(agents, list) and len(agents) > 0:
                                    agent_id = agents[0].get("id") or agents[0].get(
                                        "agent_id"
                                    )
                                    if agent_id:
                                        logger.info(f"Found agent ID from API: {agent_id}")
                                        settings.PARLANT_AGENT_ID = str(agent_id)
                    except Exception as e:
                        logger.warning(f"Could not fetch agent ID from API: {e}")
            
            # Final verification
            if not settings.PARLANT_AGENT_ID:
                logger.error(
                    "⚠️  Agent ID not found! Please set PARLANT_AGENT_ID in .env file. "
                    "Example: PARLANT_AGENT_ID=0DLeR4E7PM"
                )
            else:
                logger.info(f"✅ Agent ID configured: {settings.PARLANT_AGENT_ID}")

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

    port = int(os.environ.get("PORT", 8000))
    logger.info("Both services started:")
    logger.info(f"  - FastAPI OAuth server: http://0.0.0.0:{port}")
    logger.info("  - Parlant agent: running")
    logger.info(f"  - Available routes: {[route.path for route in api_app.routes]}")

    # Run Parlant in main async context
    await run_parlant_app()


if __name__ == "__main__":
    # Print initial appointments for debugging
    temp_supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    response = temp_supabase.table("appointments").select("*").execute()
    print("Appointments from Supabase:", response.data)

    asyncio.run(main())
