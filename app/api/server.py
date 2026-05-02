"""FastAPI application server for Centi APIs."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.newsletters import router as newsletters_router


def create_app() -> FastAPI:
    app = FastAPI(title="Centi API", version="0.1.0")

    raw_origins = os.environ.get("CORS_ALLOW_ORIGINS", "http://localhost:3000")
    allow_origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health_check():
        return {"ok": True}

    app.include_router(newsletters_router)
    return app


app = create_app()
