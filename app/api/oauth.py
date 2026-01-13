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

# OAuth 2.0 scopes for regular users
# - calendar.freebusy: Read-only access to free/busy information only
#   This scope only allows checking availability (free/busy times), NOT reading event details
#   More privacy-friendly than calendar.readonly as it doesn't expose event details
# - userinfo.email: Get user's email address for identification
# - openid: Automatically added by Google when using userinfo.email (required)
#
# Note: 
# - gmail.modify is only needed for the Centi email address (centicoordinator@gmail.com)
# - Regular users only need calendar.freebusy to check availability
# - Events are created in Centi's calendar, so users don't need calendar write permissions
USER_SCOPES = [
    "openid",  # Required when using userinfo.email
    "https://www.googleapis.com/auth/calendar.freebusy",  # Free/busy access only (more privacy-friendly)
    "https://www.googleapis.com/auth/userinfo.email",
]

# Scopes for Centi email address (needs Gmail access to read/send emails and create calendar events)
# - calendar: Full access to create events in Centi's calendar and invite participants
# - gmail.modify: Required for email coordinator (read/send emails)
CENTI_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/calendar",  # Full calendar access (needed to create events in Centi's calendar)
    "https://www.googleapis.com/auth/gmail.modify",  # Required for email coordinator (read/send emails)
    "https://www.googleapis.com/auth/userinfo.email",
]

# Default to user scopes (will be overridden if user is Centi email)
SCOPES = USER_SCOPES

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
    centi_email = settings.CENTI_EMAIL_ADDRESS

    if not centi_email:
        logger.error(
            "CENTI_EMAIL_ADDRESS not configured. Please set CENTI_EMAIL_ADDRESS in your .env file."
        )
        raise ValueError("CENTI_EMAIL_ADDRESS must be configured")

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

    # Always use USER_SCOPES by default (only calendar access)
    # If user is Centi email, they'll need to re-authenticate to get gmail.modify
    flow = Flow.from_client_config(
        client_config,
        scopes=USER_SCOPES,
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
    request: Request,
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

        # Get actual scopes from callback URL (what Google actually returned)
        # This handles the case where user was redirected to get additional scopes (e.g., gmail.modify)
        from urllib.parse import parse_qs, urlparse
        parsed_url = urlparse(str(request.url))
        query_params = parse_qs(parsed_url.query)
        scope_param = query_params.get("scope", [""])[0]
        
        # Use the actual scopes returned by Google (from callback URL)
        if scope_param:
            # Split and filter out 'email' which is not a valid scope (it's just a value returned)
            # Valid scopes are URLs like https://www.googleapis.com/auth/...
            raw_scopes = scope_param.split()
            actual_scopes = [s for s in raw_scopes if s.startswith("https://") or s == "openid"]
            logger.info(f"Using scopes from callback URL (filtered): {actual_scopes}")
        else:
            # Fallback to USER_SCOPES if scope param not found
            actual_scopes = USER_SCOPES
            logger.info(f"No scope param in callback, using default: {actual_scopes}")

        # Create flow with the actual scopes returned by Google
        # This prevents scope mismatch errors
        flow = Flow.from_client_config(
            client_config,
            scopes=actual_scopes,
            redirect_uri=settings.OAUTH_REDIRECT_URI,
        )

        # Exchange authorization code for token
        # Using actual scopes should prevent scope mismatch errors
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=".*Scope has changed.*")
            warnings.filterwarnings("ignore", message=".*scope.*")
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

        # Check if this is the Centi email - if so, we need gmail.modify scope
        centi_email = settings.CENTI_EMAIL_ADDRESS.lower() if settings.CENTI_EMAIL_ADDRESS else None
        is_centi_email = user_email.lower() == centi_email if centi_email else False
        
        # Check if gmail.modify is in the scopes
        # Check both credentials.scopes (from token) and actual_scopes (from callback URL)
        token_scopes = credentials.scopes or []
        has_gmail_scope = (
            any("gmail.modify" in str(scope) for scope in token_scopes) or
            any("gmail.modify" in str(scope) for scope in actual_scopes)
        )
        
        logger.info(f"Checking gmail.modify scope for {user_email}: token_scopes={token_scopes}, actual_scopes={actual_scopes}, has_gmail_scope={has_gmail_scope}")
        
        # If this is Centi email but token doesn't have gmail.modify, we need to request it
        if is_centi_email and not has_gmail_scope:
            logger.warning(
                f"User {user_email} is Centi email but token missing gmail.modify scope. "
                f"Current scopes: {credentials.scopes}. User needs to re-authenticate with gmail.modify."
            )
            # Redirect to OAuth again with CENTI_SCOPES
            flow_centi = Flow.from_client_config(
                client_config,
                scopes=CENTI_SCOPES,
                redirect_uri=settings.OAUTH_REDIRECT_URI,
            )
            authorization_url, new_state = flow_centi.authorization_url(
                access_type="offline",
                include_granted_scopes="false",
                prompt="consent",
            )
            # Redirect to OAuth again with CENTI_SCOPES to get gmail.modify
            logger.info(f"Redirecting Centi email to OAuth with gmail.modify. State: {new_state}")
            return Response(
                status_code=302,
                headers={"Location": authorization_url},
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
        import urllib.parse

        # Get frontend URL from settings
        frontend_url = settings.FRONTEND_URL

        # Pass user_email as query parameter so frontend can set it in localStorage/cookie
        # This works around cross-domain cookie issues
        frontend_url_with_params = f"{frontend_url}?auth_success=true&email={urllib.parse.quote(user_email)}"

        # Create redirect response
        response = RedirectResponse(url=frontend_url_with_params, status_code=302)

        # Also try to set cookie (may not work cross-domain, but doesn't hurt to try)
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
            secure=True,  # Always secure for cross-domain cookies
            samesite="None",  # Required for cross-domain cookies (must be None with Secure)
            path="/",
        )

        logger.info(f"OAuth successful for {user_email}, redirecting to {frontend_url_with_params}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing OAuth callback: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process OAuth callback: {str(e)}",
        )
