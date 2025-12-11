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
    return session_email


@router.get("/api/auth/check")
async def check_auth(request: Request):
    """Check if user is authenticated.
    
    Returns:
        User information if authenticated, 401 otherwise
    """
    user_email = get_user_email_from_session(request)
    
    if not user_email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get user from database
    user = supabase_service.get_user_by_email(user_email)
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return {
        "authenticated": True,
        "user_email": user_email,
        "has_calendar_access": bool(user.get("calendar_access_token")),
    }


@router.post("/api/auth/logout")
async def logout(response: Response):
    """Logout user by clearing session cookie.
    
    Returns:
        Success message
    """
    # Clear session cookie
    response.delete_cookie("user_email", path="/")
    
    return {"success": True, "message": "Logged out successfully"}


@router.post("/api/auth/verify")
async def verify_auth(email: str, request: Request, response: Response):
    """Verify auth after OAuth callback and set cookie.
    
    This endpoint is called by the frontend after OAuth redirect
    to set the session cookie on the backend domain.
    
    Args:
        email: User email from OAuth callback
        request: FastAPI request object
        response: FastAPI response object
        
    Returns:
        Success message
    """
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    # Verify user exists in database
    user = supabase_service.get_user_by_email(email)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Set session cookie
    import os
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    is_production = (
        os.environ.get("ENVIRONMENT") == "production" or 
        "onrender.com" in frontend_url
    )
    
    response.set_cookie(
        key="user_email",
        value=email,
        max_age=60 * 60 * 24 * 7,  # 7 days
        httponly=False,  # Allow JS to read
        secure=True,  # Always secure for cross-domain cookies
        samesite="None",  # Required for cross-domain cookies
        path="/",
    )
    
    logger.info(f"Auth verified and cookie set for {email}")
    
    return {
        "success": True,
        "message": "Auth verified successfully",
        "user_email": email,
    }


@router.get("/api/user/me")
async def get_current_user(request: Request):
    """Get current authenticated user information.
    
    Returns:
        User information
    """
    user_email = get_user_email_from_session(request)
    
    if not user_email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get user from database
    user = supabase_service.get_user_by_email(user_email)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Return user info (without sensitive data)
    return {
        "user_email": user.get("user_email"),
        "listen_address": user.get("listen_address"),
        "has_calendar_access": bool(user.get("calendar_access_token")),
        "parlant_session_id": user.get("parlant_session_id"),
    }

