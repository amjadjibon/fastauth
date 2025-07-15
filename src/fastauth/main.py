from contextlib import asynccontextmanager

from fastapi import FastAPI
import uvicorn

from fastauth.api.auth import router as auth_router
from fastauth.core.config import settings
from fastauth.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await init_db()
    yield
    # Shutdown
    pass


app = FastAPI(
    title=settings.app_name,
    description="High-performance authentication system with FastAPI and async PostgreSQL",
    version="0.1.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["authentication"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "FastAuth API is running"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}    

if __name__ == "__main__":
    uvicorn.run(
        "fastauth.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
