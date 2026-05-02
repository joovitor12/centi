"""Parlant session management endpoints."""

import logging
import httpx
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Request

from app.config.settings import settings
from app.services.supabase_service import SupabaseService
from app.api.auth import get_user_email_from_session

logger = logging.getLogger(__name__)

router = APIRouter()
supabase_service = SupabaseService()

# Get from settings
PARLANT_SERVER_URL = settings.PARLANT_SERVER_URL
PARLANT_AGENT_ID = settings.PARLANT_AGENT_ID


async def get_agent_id() -> Optional[str]:
    """Get the Parlant agent ID.

    First tries from settings (may be set dynamically), then attempts to fetch from Parlant API.

    Returns:
        Agent ID if found, None otherwise
    """
    # First try from settings (re-read in case it was set dynamically)
    current_agent_id = settings.PARLANT_AGENT_ID
    if current_agent_id:
        return current_agent_id

    # Try to fetch agents from Parlant API
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{PARLANT_SERVER_URL}/agents",
                timeout=5.0,
            )
            if response.status_code == 200:
                agents = response.json()
                # If it's a list, get the first agent
                if isinstance(agents, list) and len(agents) > 0:
                    agent_id = agents[0].get("id") or agents[0].get("agent_id")
                    if agent_id:
                        logger.info(f"Found agent ID from Parlant API: {agent_id}")
                        # Cache it in settings
                        settings.PARLANT_AGENT_ID = str(agent_id)
                        return agent_id
                # If it's a dict with agents key
                elif isinstance(agents, dict):
                    agents_list = agents.get("agents", [])
                    if agents_list and len(agents_list) > 0:
                        agent_id = agents_list[0].get("id") or agents_list[0].get(
                            "agent_id"
                        )
                        if agent_id:
                            logger.info(f"Found agent ID from Parlant API: {agent_id}")
                            # Cache it in settings
                            settings.PARLANT_AGENT_ID = str(agent_id)
                            return agent_id
    except Exception as e:
        logger.warning(f"Could not fetch agent ID from Parlant API: {e}")

    return None


async def create_parlant_session(user_email: str) -> str:
    """Create a new Parlant session for a user.

    Args:
        user_email: User's email address

    Returns:
        Parlant session ID
    """
    try:
        # Get agent ID
        agent_id = await get_agent_id()
        if not agent_id:
            logger.error(
                "No agent ID available. Set PARLANT_AGENT_ID environment variable or ensure agent is created."
            )
            raise HTTPException(
                status_code=500,
                detail="Parlant agent ID not found. Please configure PARLANT_AGENT_ID or ensure agent is created.",
            )

        # Create a customer object for Parlant
        # The Parlant REST API expects agent_id and customer email
        async with httpx.AsyncClient() as client:
            # Create session via Parlant REST API
            # API endpoint: POST /sessions
            response = await client.post(
                f"{PARLANT_SERVER_URL}/sessions",
                json={
                    "agent_id": agent_id,
                    "customer": {
                        "email": user_email,
                    },
                },
                timeout=10.0,
            )

            if response.status_code == 200 or response.status_code == 201:
                session_data = response.json()
                session_id = session_data.get("id") or session_data.get("session_id")
                if session_id:
                    logger.info(
                        f"Created Parlant session {session_id} for user {user_email}"
                    )
                    
                    # Send initial welcome message informing about email interactor
                    try:
                        centi_email = settings.CENTI_EMAIL_ADDRESS or "centicoordinator@gmail.com"
                        welcome_message = (
                            "Hi! 👋\n\n"
                            "I'm Centi, your calendar assistant. Currently, I don't support creating reminders "
                            "or appointments via chat. Instead, please use the Email Interactor feature:\n\n"
                            "📧 **How to use Email Interactor:**\n"
                            "1. Send an email to the person you want to schedule with\n"
                            f"2. Add **{centi_email}** in CC\n"
                            "3. Mention 'Centi' in your message asking to schedule a meeting\n"
                            "4. I'll analyze your calendars and suggest available times\n"
                            "5. Reply confirming your preferred time\n"
                            "6. I'll create the calendar event and confirm with everyone\n\n"
                            "For more details, check the 'How to use Email Interactor' guide in the header above.\n\n"
                            "Thanks for using Centi! 🎉"
                        )
                        
                        await client.post(
                            f"{PARLANT_SERVER_URL}/sessions/{session_id}/events",
                            json={
                                "kind": "message",
                                "source": "agent",
                                "message": welcome_message,
                            },
                            timeout=5.0,
                        )
                        logger.info(f"Sent welcome message to session {session_id}")
                    except Exception as e:
                        logger.warning(f"Failed to send welcome message: {e}")
                    
                    return session_id
                else:
                    logger.error(
                        f"Parlant API returned success but no session ID: {session_data}"
                    )
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to create Parlant session: no session ID returned",
                    )
            else:
                logger.error(
                    f"Parlant API error: {response.status_code} - {response.text}"
                )
                # If the API format is different, try alternative approach
                # Some Parlant versions might use different endpoints
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to create Parlant session: {response.status_code}",
                )

    except httpx.RequestError as e:
        logger.error(f"Failed to connect to Parlant server: {e}")
        raise HTTPException(status_code=503, detail="Parlant server is not available")
    except Exception as e:
        logger.error(f"Error creating Parlant session: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to create Parlant session: {str(e)}"
        )


@router.get("/api/session/current")
async def get_current_session(request: Request):
    """Get or create Parlant session for current user.

    Returns:
        Session information including session_id
    """
    user_email = get_user_email_from_session(request)

    if not user_email:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Get user from database
    user = supabase_service.get_user_by_email(user_email)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if user already has a Parlant session
    parlant_session_id = user.get("parlant_session_id")

    if parlant_session_id:
        # Verify session still exists in Parlant
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{PARLANT_SERVER_URL}/sessions/{parlant_session_id}",
                    timeout=5.0,
                )

                if response.status_code == 200:
                    # Session exists, return it
                    return {
                        "session_id": parlant_session_id,
                        "user_email": user_email,
                        "exists": True,
                    }
        except Exception as e:
            logger.warning(
                f"Session {parlant_session_id} verification failed: {e}, creating new one"
            )
            # Session doesn't exist or is invalid, create new one

    # Create new session
    try:
        new_session_id = await create_parlant_session(user_email)

        # Save session ID to database
        supabase_service.update_user_parlant_session(user_email, new_session_id)

        return {
            "session_id": new_session_id,
            "user_email": user_email,
            "exists": False,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting/creating session: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get/create session: {str(e)}"
        )


@router.post("/api/session/create")
async def create_session(request: Request):
    """Create a new Parlant session for the authenticated user.

    This endpoint creates a new session even if one already exists.

    Returns:
        Session information
    """
    user_email = get_user_email_from_session(request)

    if not user_email:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Verify user exists
    user = supabase_service.get_user_by_email(user_email)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Create new session
    try:
        new_session_id = await create_parlant_session(user_email)

        # Save session ID to database
        supabase_service.update_user_parlant_session(user_email, new_session_id)

        return {
            "session_id": new_session_id,
            "user_email": user_email,
            "message": "Session created successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating session: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to create session: {str(e)}"
        )
