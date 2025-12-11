"""Calendar availability tools for Parlant."""

import logging
from datetime import datetime, timedelta
from typing import Optional
import parlant.sdk as p
from app.services.supabase_service import SupabaseService
from app.services.google_calendar_service import GoogleCalendarService

logger = logging.getLogger(__name__)


def create_calendar_availability_tools(
    supabase_service: SupabaseService,
):
    """Create calendar availability tools for Parlant.

    Args:
        supabase_service: SupabaseService instance for accessing user tokens

    Returns:
        List of tool functions
    """

    @p.tool
    async def get_availability_slots(
        context: p.ToolContext,
        start_date: datetime,
        end_date: datetime,
        participant_emails: Optional[list[str]] = None,
        duration_minutes: int = 30,
    ) -> p.ToolResult:
        """Get calendar availability slots for the customer.
        
        When you need to find the calendar availability of the customer,
        use this tool. It will query the customer's Google Calendar for
        free/busy information and return available time slots.
        
        Args:
            context: Parlant tool context (automatically provided)
            start_date: Start of time range to check (datetime)
            end_date: End of time range to check (datetime)
            participant_emails: Optional list of participant email addresses to check.
                             If not provided, only checks the customer's calendar.
            duration_minutes: Minimum duration for free slots (default: 30)
            
        Returns:
            ToolResult with availability information
        """
        try:
            # Get customer from context
            customer = p.Customer.from_context(context)
            
            if not customer:
                return p.ToolResult(
                    data="Error: Could not identify customer from context",
                    control={"lifespan": "response"},
                )
            
            # Get customer email
            customer_email = customer.email if hasattr(customer, "email") else None
            
            if not customer_email:
                return p.ToolResult(
                    data="Error: Customer email not available",
                    control={"lifespan": "response"},
                )
            
            logger.info(f"Getting availability for customer: {customer_email}")
            
            # Get user from database
            user = supabase_service.get_user_by_email(customer_email)
            
            if not user:
                return p.ToolResult(
                    data=f"Error: User {customer_email} not found. Please complete OAuth setup first.",
                    control={"lifespan": "response"},
                )
            
            # Get user's calendar token
            calendar_token = user.get("calendar_access_token")
            
            if not calendar_token:
                return p.ToolResult(
                    data=f"Error: Calendar access token not found for {customer_email}",
                    control={"lifespan": "response"},
                )
            
            # Determine which calendars to check
            emails_to_check = participant_emails or [customer_email]
            
            # Add customer email if not already included
            if customer_email.lower() not in [e.lower() for e in emails_to_check]:
                emails_to_check.append(customer_email.lower())
            
            # Query availability using user's token
            result = GoogleCalendarService.get_availability_slots(
                user_token=calendar_token,
                participant_emails=emails_to_check,
                start_date=start_date,
                end_date=end_date,
                duration_minutes=duration_minutes,
                timezone_str="America/Sao_Paulo",  # TODO: Get from user settings
                supabase_service=supabase_service,
                user_email=customer_email,
            )
            
            # Format result for response
            calendars_data = result.get("calendars", {})
            unavailable = result.get("unavailable", [])
            
            # Extract busy periods
            busy_periods = []
            for email, calendar_info in calendars_data.items():
                busy = calendar_info.get("busy", [])
                for period in busy:
                    busy_periods.append({
                        "email": email,
                        "start": period.get("start"),
                        "end": period.get("end"),
                    })
            
            return p.ToolResult(
                data={
                    "available_calendars": list(calendars_data.keys()),
                    "unavailable_calendars": unavailable,
                    "busy_periods": busy_periods,
                    "time_range": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat(),
                    },
                    "duration_minutes": duration_minutes,
                }
            )
            
        except Exception as e:
            logger.error(f"Error getting availability slots: {e}", exc_info=True)
            return p.ToolResult(
                data=f"Failed to get availability slots: {str(e)}",
                control={"lifespan": "response"},
            )

    return [get_availability_slots]

