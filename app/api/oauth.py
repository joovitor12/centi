"""OAuth endpoints for multi-user Google Calendar integration."""

import logging
import warnings
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.config.settings import settings
from app.services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)

router = APIRouter()

# OAuth 2.0 scopes
# - calendar.freebusy: Read-only access to free/busy information (privacy-preserving)
#   This scope does NOT allow creating events, but it's safe and doesn't require app verification
# - userinfo.email: Get user's email address for identification
# - openid: Automatically added by Google when using userinfo.email (required)
SCOPES = [
    "openid",  # Required when using userinfo.email
    "https://www.googleapis.com/auth/calendar.freebusy",  # Privacy-preserving scope
    "https://www.googleapis.com/auth/userinfo.email",
]

# Initialize Supabase service
supabase_service = SupabaseService()


def generate_listen_address(user_email: str) -> str:
    """Generate listen address (agent email) for a user.

    For now, all users share the same Centi email address.
    The system identifies which user to use by checking who is in the email thread.

    Args:
        user_email: User's email address (used for logging, but doesn't affect result)

    Returns:
        The Centi email address from settings (same for all users)
    """
    # Use the same Centi email for all users
    # The system will identify which user to use by checking who is in the email thread
    centi_email = settings.CENTI_EMAIL_ADDRESS or "centinteractor@gmail.com"

    if not centi_email:
        logger.warning(
            "CENTI_EMAIL_ADDRESS not configured. Using default centinteractor@gmail.com"
        )
        return "centinteractor@gmail.com"

    return centi_email.lower()


@router.get("/auth/google")
async def auth_google(request: Request):
    """Initiate Google OAuth flow.

    Redirects user to Google OAuth consent screen.
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth credentials not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )

    # Create OAuth flow
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.OAUTH_REDIRECT_URI],
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=settings.OAUTH_REDIRECT_URI,
    )

    # Generate authorization URL
    authorization_url, state = flow.authorization_url(
        access_type="offline",  # Request refresh token
        include_granted_scopes="false",  # Don't include previously granted scopes
        prompt="consent",  # Force consent to get refresh token
    )

    logger.info(f"OAuth flow initiated. State: {state}")

    # Redirect to Google
    return Response(
        status_code=302,
        headers={"Location": authorization_url},
    )


@router.get("/auth/google/callback")
async def auth_google_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
):
    """Handle Google OAuth callback.

    Args:
        code: Authorization code from Google
        state: State parameter for CSRF protection
        error: Error message if authorization failed
    """
    if error:
        logger.error(f"OAuth error: {error}")
        raise HTTPException(
            status_code=400,
            detail=f"OAuth authorization failed: {error}",
        )

    if not code:
        raise HTTPException(
            status_code=400,
            detail="Authorization code not provided",
        )

    try:
        # Create OAuth flow
        client_config = {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.OAUTH_REDIRECT_URI],
            }
        }

        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=settings.OAUTH_REDIRECT_URI,
        )

        # Exchange authorization code for token
        # Note: Google automatically adds 'openid' scope when using userinfo.email
        # We suppress the warning since this is expected behavior
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=".*Scope has changed.*openid.*")
            flow.fetch_token(code=code)

        credentials = flow.credentials

        # Get user info from token
        # Note: calendar.freebusy scope doesn't provide user info in id_token
        # We'll need to use the email from the token response or make a separate API call
        # For now, we'll extract from the credentials

        # Build credentials dict for storage
        token_dict = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "scopes": credentials.scopes,
        }

        # Get user email from Google OAuth2 API
        user_email = None

        try:
            service = build("oauth2", "v2", credentials=credentials)
            user_info = service.userinfo().get().execute()
            user_email = user_info.get("email")

            if not user_email:
                logger.warning("User info retrieved but email is missing")
        except Exception as e:
            logger.error(f"Could not fetch user email from OAuth: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve user email: {str(e)}",
            )

        # Generate listen address
        listen_address = generate_listen_address(user_email)

        # Check if user already exists
        existing_user = supabase_service.get_user_by_email(user_email)

        if existing_user:
            # Update token
            supabase_service.update_user_token(user_email, token_dict)
            logger.info(f"Updated token for existing user: {user_email}")
        else:
            # Create new user
            supabase_service.create_user(
                user_email=user_email,
                calendar_access_token=token_dict,
                listen_address=listen_address,
            )
            logger.info(
                f"Created new user: {user_email} with listen_address: {listen_address}"
            )

        # Redirect to frontend after setting session cookie
        from fastapi.responses import RedirectResponse

        # Get frontend URL from settings
        frontend_url = settings.FRONTEND_URL

        # Create redirect response
        response = RedirectResponse(url=frontend_url, status_code=302)

        # Set session cookie for frontend authentication
        # In production, set secure=True, same_site='lax', http_only=False (so JS can access)
        import os
        # Check if running on Render (HTTPS) or local (HTTP)
        is_production = (
            os.environ.get("ENVIRONMENT") == "production" or 
            "onrender.com" in frontend_url or
            "onrender.com" in settings.BASE_URL
        )

        response.set_cookie(
            key="user_email",
            value=user_email,
            max_age=60 * 60 * 24 * 7,  # 7 days
            httponly=False,  # Allow JS to read (needed for frontend auth check)
            secure=is_production,  # Only send over HTTPS in production
            samesite="lax",
            path="/",
        )

        logger.info(f"OAuth successful for {user_email}, redirecting to {frontend_url}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing OAuth callback: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process OAuth callback: {str(e)}",
        )
