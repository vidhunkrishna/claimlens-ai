from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    """
    Schema for the health check response.
    """
    status: str = Field(..., description="Service health status", json_schema_extra={"example": "ok"})
    service: str = Field(..., description="Service name", json_schema_extra={"example": "ClaimLens AI"})
    version: str = Field(..., description="Service version", json_schema_extra={"example": "0.1.0"})
    timestamp: str = Field(..., description="UTC timestamp of the health check")

class RootResponse(BaseModel):
    """
    Schema for the root welcome endpoint response.
    """
    message: str = Field(..., json_schema_extra={"example": "Welcome to ClaimLens AI API"})
    service: str = Field(..., json_schema_extra={"example": "ClaimLens AI"})
    version: str = Field(..., json_schema_extra={"example": "0.1.0"})
    docs_url: str = Field(..., json_schema_extra={"example": "/docs"})
    health_url: str = Field(..., json_schema_extra={"example": "/health"})
