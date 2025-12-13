"""Authentication endpoints for frontend."""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from app.services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)

router = APIRouter()
supabase_service = SupabaseService()


def get_user_email_from_session(request: Request) -> Optional[str]:
    """Get user email from session cookie.
    
    Args:
        request: FastAPI request object
        
    Returns:
        User email if authenticated, None otherwise
    """
    # Get session cookie (set during OAuth callback)
    session_email = request.cookies.get("user_email")
    logger.debug(f"get_user_email_from_session: found email={session_email}, all cookies: {list(request.cookies.keys())}")
    return session_email


@router.get("/api/auth/check")
async def check_auth(request: Request):
    """Check if user is authenticated.
    
    Returns:
        User information if authenticated, 401 otherwise
    """
    user_email = get_user_email_from_session(request)
    
    logger.debug(f"check_auth called, user_email from cookie: {user_email}, cookies: {list(request.cookies.keys())}")
    
    if not user_email:
        logger.debug("check_auth: No user_email in cookie, returning 401")
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get user from database
    user = supabase_service.get_user_by_email(user_email)
    
    if not user:
        logger.warning(f"check_auth: User not found in database: {user_email}")
        raise HTTPException(status_code=401, detail="User not found")
    
    logger.debug(f"check_auth: User authenticated: {user_email}")
    return {
        "authenticated": True,
        "user_email": user_email,
        "has_calendar_access": bool(user.get("calendar_access_token")),
    }


@router.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    """Logout user by clearing session cookie.
    
    Returns:
        Success message
    """
    import os
    # Clear session cookie with same attributes used when setting it
    # Must match: secure=True, samesite="None" for cross-domain cookies
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    is_production = (
        os.environ.get("ENVIRONMENT") == "production" or 
        "onrender.com" in frontend_url
    )
    
    # Delete cookie with same attributes as when it was set
    response.delete_cookie(
        key="user_email",
        path="/",
        secure=True,  # Must match the secure flag used when setting
        samesite="None",  # Must match the samesite used when setting
    )
    
    logger.info("User logged out, cookie cleared")
    
    return {"success": True, "message": "Logged out successfully"}


@router.post("/api/auth/verify")
async def verify_auth(request: Request, response: Response, email: Optional[str] = None):
    """Verify auth after OAuth callback and set cookie.
    
    This endpoint is called by the frontend after OAuth redirect
    to set the session cookie on the backend domain.
    
    Args:
        email: User email from OAuth callback (query parameter or body)
        request: FastAPI request object
        response: FastAPI response object
        
    Returns:
        Success message
    """
    # Try to get email from multiple sources (query params, body, or function param)
    if not email:
        email = request.query_params.get("email")
    
    # Also try to get from request body (in case frontend sends as POST body)
    if not email:
        try:
            body = await request.json()
            email = body.get("email")
        except Exception:
            pass
    
    logger.info(f"Verify auth called with email: {email}, user agent: {request.headers.get('user-agent', 'unknown')}")
    
    if not email:
        logger.error("Email is required but not provided")
        raise HTTPException(status_code=400, detail="Email is required")
    
    # Verify user exists in database
    try:
        user = supabase_service.get_user_by_email(email)
    except Exception as e:
        logger.error(f"Error fetching user from database: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    
    if not user:
        logger.error(f"User not found in database: {email}")
        raise HTTPException(status_code=404, detail="User not found")
    
    # Set session cookie with proper attributes for cross-domain (especially iOS Safari)
    # iOS Safari requires SameSite=None AND Secure=True for cross-domain cookies
    import os
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    
    # Always use secure=True and samesite=None for cross-domain cookies
    # This is required for iOS Safari to accept the cookie
    response.set_cookie(
        key="user_email",
        value=email,
        max_age=60 * 60 * 24 * 7,  # 7 days
        httponly=False,  # Allow JS to read (needed for frontend auth check)
        secure=True,  # MUST be True when SameSite=None (required for iOS Safari)
        samesite="None",  # Required for cross-domain cookies (frontend and backend on different domains)
        path="/",  # Make cookie available for all paths
        domain=None,  # Don't set domain - let browser use default (current domain)
    )
    
    logger.info(f"Auth verified and cookie set for {email}")
    
    # Return response with additional headers to help with CORS
    return JSONResponse(
        content={
            "success": True,
            "message": "Auth verified successfully",
            "user_email": email,
        },
        headers={
            "Access-Control-Allow-Origin": frontend_url,
            "Access-Control-Allow-Credentials": "true",
        }
    )


@router.get("/api/user/me")
async def get_current_user(request: Request):
    """Get current authenticated user information.
    
    Returns:
        User information
    """
    user_email = get_user_email_from_session(request)
    
    logger.info(f"get_current_user called, user_email from cookie: {user_email}")
    
    if not user_email:
        logger.warning("get_current_user: No user_email in cookie")
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get user from database
    try:
        user = supabase_service.get_user_by_email(user_email)
    except Exception as e:
        logger.error(f"Error fetching user from database: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    
    if not user:
        logger.warning(f"User not found in database: {user_email}")
        raise HTTPException(status_code=404, detail="User not found")
    
    logger.info(f"User data retrieved successfully for: {user_email}")
    
    # Return user info (without sensitive data)
    return {
        "user_email": user.get("user_email"),
        "listen_address": user.get("listen_address"),
        "has_calendar_access": bool(user.get("calendar_access_token")),
        "parlant_session_id": user.get("parlant_session_id"),
    }

