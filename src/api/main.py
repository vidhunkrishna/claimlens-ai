from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import settings
from src.api.health import router as health_router
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

    @app.get("/", response_model=RootResponse, tags=["Root"])
    def read_root():
        return RootResponse(
            message="Welcome to ClaimLens AI API",
            service=settings.APP_NAME,
            version=settings.APP_VERSION,
            docs_url="/docs",
            health_url="/health"
        )

    return app

app = create_app()
