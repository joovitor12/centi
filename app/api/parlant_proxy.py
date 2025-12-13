"""Proxy router to forward Parlant API requests from frontend to Parlant server."""

import httpx
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import StreamingResponse
import logging

from app.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["parlant-proxy"])


async def proxy_request(request: Request, path: str):
    """Proxy a request to the Parlant server."""
    parlant_url = settings.PARLANT_SERVER_URL.rstrip('/')
    target_url = f"{parlant_url}/sessions/{path}"
    
    # Get query parameters
    query_params = dict(request.query_params)
    
    # Get request body if present
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.body()
        except Exception:
            pass
    
    # Get headers (excluding host and connection)
    headers = {}
    for key, value in request.headers.items():
        if key.lower() not in ["host", "connection", "content-length"]:
            headers[key] = value
    
    logger.debug(f"Proxying {request.method} {target_url} with query params: {query_params}")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Make request to Parlant server
            response = await client.request(
                method=request.method,
                url=target_url,
                params=query_params,
                content=body,
                headers=headers,
                follow_redirects=True,
            )
            
            # Get response content
            content = response.content
            
            # Create response with same status and headers (excluding some)
            response_headers = {}
            for key, value in response.headers.items():
                if key.lower() not in ["content-encoding", "transfer-encoding", "connection"]:
                    response_headers[key] = value
            
            return Response(
                content=content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get("content-type", "application/json"),
            )
    except httpx.TimeoutException:
        logger.error(f"Timeout proxying request to {target_url}")
        raise HTTPException(status_code=504, detail="Gateway Timeout")
    except httpx.ConnectError:
        logger.error(f"Could not connect to Parlant server at {parlant_url}")
        raise HTTPException(
            status_code=502,
            detail=f"Bad Gateway: Could not connect to Parlant server at {parlant_url}",
        )
    except Exception as e:
        logger.error(f"Error proxying request to {target_url}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy_session(path: str, request: Request):
    """Proxy any session-related request to Parlant server."""
    return await proxy_request(request, path)

