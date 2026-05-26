import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    # Start the FastAPI application with configured host and port
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
