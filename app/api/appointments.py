"""Appointments API endpoints for frontend."""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.services.supabase_service import SupabaseService
from app.api.auth import get_user_email_from_session

logger = logging.getLogger(__name__)

router = APIRouter()
supabase_service = SupabaseService()


@router.get("/api/appointments")
async def get_appointments(request: Request):
    """Get all appointments for the authenticated user.
    
    Returns:
        List of appointments for the current user
    """
    user_email = get_user_email_from_session(request)
    
    if not user_email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        appointments = supabase_service.get_all_appointments(user_email=user_email)
        logger.info(f"Retrieved {len(appointments)} appointments for user {user_email}")
        return {"appointments": appointments}
    except Exception as e:
        logger.error(f"Error fetching appointments for user {user_email}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch appointments")

