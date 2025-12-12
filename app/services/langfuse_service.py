"""Langfuse integration service for tracking tools and conversations."""

import logging
from typing import Optional, Any, Callable
import functools
import parlant.sdk as p
from langfuse import get_client, propagate_attributes

from app.config.settings import settings

logger = logging.getLogger(__name__)

# Initialize Langfuse client
_langfuse_client = None


def get_langfuse_client():
    """Get or initialize Langfuse client."""
    global _langfuse_client
    if _langfuse_client is None:
        try:
            if settings.LANGFUSE_SECRET_KEY and settings.LANGFUSE_PUBLIC_KEY:
                from langfuse import Langfuse
                _langfuse_client = Langfuse(
                    secret_key=settings.LANGFUSE_SECRET_KEY,
                    public_key=settings.LANGFUSE_PUBLIC_KEY,
                    host=settings.LANGFUSE_BASE_URL if settings.LANGFUSE_BASE_URL else None,
                )
                logger.info("Langfuse client initialized successfully")
            else:
                logger.warning(
                    "Langfuse credentials not configured. Tracking will be disabled."
                )
                _langfuse_client = None
        except Exception as e:
            logger.error(f"Failed to initialize Langfuse client: {e}")
            _langfuse_client = None
    return _langfuse_client


def extract_session_id_from_context(context: p.ToolContext) -> Optional[str]:
    """Extract session_id from Parlant ToolContext.
    
    Args:
        context: Parlant ToolContext
        
    Returns:
        Session ID string if found, None otherwise
    """
    try:
        if hasattr(context, "session_id"):
            session_id = str(context.session_id)
            if session_id:
                return session_id
    except Exception as e:
        logger.debug(f"Could not extract session_id from context: {e}")
    
    return None


def extract_user_id_from_context(context: p.ToolContext) -> Optional[str]:
    """Extract user_id (email) from Parlant ToolContext.
    
    Args:
        context: Parlant ToolContext
        
    Returns:
        User email if found, None otherwise
    """
    try:
        # Try multiple methods to get user email
        if hasattr(context, "customer_id"):
            customer_id = context.customer_id
            if isinstance(customer_id, str) and "@" in customer_id:
                return customer_id
        
        if hasattr(context, "customer") and context.customer:
            if hasattr(context.customer, "email"):
                return context.customer.email
        
        if hasattr(context, "session") and hasattr(context.session, "customer"):
            if hasattr(context.session.customer, "email"):
                return context.session.customer.email
    except Exception as e:
        logger.debug(f"Could not extract user_id from context: {e}")
    
    return None


def track_parlant_tool(func: Callable) -> Callable:
    """Decorator to track Parlant tool calls with Langfuse.
    
    This decorator wraps a Parlant tool function and automatically tracks
    its execution in Langfuse with proper session and user context.
    
    Args:
        func: The tool function to wrap
        
    Returns:
        Wrapped function with Langfuse tracking
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract context (first positional arg or from kwargs)
        context = None
        if args and isinstance(args[0], p.ToolContext):
            context = args[0]
        elif "context" in kwargs:
            context = kwargs["context"]
        
        # Extract session_id and user_id from context
        session_id = None
        user_id = None
        if context:
            session_id = extract_session_id_from_context(context)
            user_id = extract_user_id_from_context(context)
        
        # Get Langfuse client
        langfuse = get_langfuse_client()
        
        # If Langfuse is not configured, just execute the function normally
        if langfuse is None:
            return await func(*args, **kwargs)
        
        # Prepare input data (exclude context from tracking)
        input_data = {}
        if args:
            # Skip first arg if it's context
            if len(args) > 1:
                input_data["args"] = [str(arg) for arg in args[1:]]
        if kwargs:
            filtered_kwargs = {k: v for k, v in kwargs.items() if k != "context"}
            if filtered_kwargs:
                input_data.update(filtered_kwargs)
        
        # Create span name from function name
        span_name = func.__name__
        
        try:
            # Create trace with session_id and user_id
            # Use propagate_attributes to set session_id and user_id on all child observations
            with propagate_attributes(
                session_id=session_id,
                user_id=user_id,
                metadata={
                    "tool_name": span_name,
                    "source": "parlant",
                },
            ):
                with langfuse.start_as_current_observation(
                    as_type="span",
                    name=span_name,
                    input=input_data,
                ) as span:
                    # Execute the tool function
                    result = await func(*args, **kwargs)
                    
                    # Extract output from result
                    output_data = None
                    if isinstance(result, p.ToolResult):
                        output_data = result.data
                    else:
                        output_data = result
                    
                    # Update span with output
                    span.update(output=output_data)
                    
                    return result
        except Exception as e:
            # Log error but don't fail the tool execution
            logger.error(f"Error tracking tool {span_name} in Langfuse: {e}", exc_info=True)
            # Still execute the function even if tracking fails
            return await func(*args, **kwargs)
    
    return wrapper

