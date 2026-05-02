"""Production entry point for the Parlant agent."""

import asyncio
import logging
import os
import parlant.sdk as p

from app.config.settings import settings
from app.services.newsletter_builder_service import NewsletterBuilderService
from app.services.newsletter_service import NewsletterService
from app.services.supabase_service import SupabaseService
from app.tools.appointments import create_appointment_tools
from app.tools.newsletters import create_newsletter_tools
from app.tools.recurring_appointments import create_recurring_appointment_tools
from app.agent.guidelines import setup_guidelines

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_parlant_app():
    """Run Parlant main application."""
    # Validate settings
    settings.validate()

    # Initialize services
    supabase_service = SupabaseService()
    newsletter_service = NewsletterService(supabase_service=supabase_service)
    newsletter_builder_service = NewsletterBuilderService()

    # Create tools
    appointment_tools = create_appointment_tools(supabase_service)
    recurring_appointment_tools = create_recurring_appointment_tools(supabase_service)
    newsletter_tools = create_newsletter_tools(
        newsletter_service=newsletter_service,
        newsletter_builder_service=newsletter_builder_service,
    )

    try:
        port = int(os.environ.get("PORT", "8800"))
        tool_service_port = int(
            os.environ.get("PARLANT_TOOL_SERVICE_PORT", str(port + 18))
        )
        logger.info(
            "Starting Parlant server on port=%s tool_service_port=%s",
            port,
            tool_service_port,
        )
        async with p.Server(
            host="0.0.0.0",
            port=port,
            tool_service_port=tool_service_port,
            nlp_service=p.NLPServices.openai,
        ) as server:
            # Create agent
            agent = await server.create_agent(
                name="Centi",
                description="You are a professional assistant like Jarvis from Ironman.",
            )

            # Setup guidelines (tools are auto-discovered through guidelines)
            await setup_guidelines(
                agent,
                appointment_tools,
                recurring_appointment_tools,
                newsletter_tools,
            )

            logger.info("Agent initialized successfully")

            # The context manager blocks here until server shuts down

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        raise


async def main():
    """Main function."""
    await run_parlant_app()


if __name__ == "__main__":
    asyncio.run(main())
