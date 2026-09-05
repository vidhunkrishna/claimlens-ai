import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import settings
from src.api.health import router as health_router
from src.api.ingestion import router as ingestion_router
from src.api.rules import router as rules_router
from src.api.reasoning import router as reasoning_router
from src.api.retrieval import router as retrieval_router
from src.api.contradictions import router as contradictions_router
from src.api.investigation import router as investigation_router
from src.models.schemas import RootResponse

def create_app() -> FastAPI:
    """
    Factory function to initialize and configure the FastAPI application.
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="ClaimLens AI - Insurance Claims Evidence Review Assistant (PS02)",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API Routers
    app.include_router(health_router)
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(ingestion_router)
    app.include_router(rules_router)
    app.include_router(reasoning_router)
    app.include_router(retrieval_router)
    app.include_router(contradictions_router)
    app.include_router(investigation_router)

    # Mount static files directory for frontend UI assets
    if os.path.exists("static"):
        app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/", tags=["Root"])
    def read_root(request: Request):
        accept = request.headers.get("accept", "")
        # If requested by browser HTML navigation, return frontend application
        if "text/html" in accept:
            index_path = os.path.join("static", "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path, media_type="text/html")
        
        # Default JSON response for programmatic API calls & test suite
        return RootResponse(
            message="Welcome to ClaimLens AI API",
            service=settings.APP_NAME,
            version=settings.APP_VERSION,
            docs_url="/docs",
            health_url="/health"
        )

    return app

app = create_app()

