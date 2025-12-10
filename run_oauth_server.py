"""Script para rodar servidor FastAPI OAuth separadamente."""

import logging
import uvicorn
from fastapi import FastAPI
from app.api.oauth import router as oauth_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app for OAuth endpoints
app = FastAPI(title="Centi OAuth API", version="1.0.0")
app.include_router(oauth_router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "message": "Centi OAuth API is running",
        "endpoints": {
            "oauth": "/auth/google",
            "callback": "/auth/google/callback"
        }
    }


if __name__ == "__main__":
    logger.info("Starting OAuth server on http://localhost:8000")
    logger.info("OAuth endpoint: http://localhost:8000/auth/google")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

