import os
import uvicorn
from src.api.main import app
from src.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
