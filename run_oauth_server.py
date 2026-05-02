"""Script para rodar servidor FastAPI com todas as rotas da API."""

import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.oauth import router as oauth_router
from app.api.auth import router as auth_router
from app.api.appointments import router as appointments_router
from app.api.session import router as session_router
from app.api.parlant_proxy import router as parlant_proxy_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app with all API endpoints
app = FastAPI(title="Centi API", version="1.0.0")

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8800"],  # Frontend and Parlant Sandbox
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(oauth_router)
app.include_router(auth_router)
app.include_router(appointments_router)
app.include_router(session_router)
app.include_router(parlant_proxy_router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "message": "Centi API is running",
        "endpoints": {
            "oauth": "/auth/google",
            "callback": "/auth/google/callback",
            "appointments": "/api/appointments",
            "session": "/api/session",
            "parlant_proxy": "/sessions"
        }
    }


if __name__ == "__main__":
    logger.info("Starting Centi API server on http://localhost:8000")
    logger.info("OAuth endpoint: http://localhost:8000/auth/google")
    logger.info("API endpoints available at http://localhost:8000/api/*")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

