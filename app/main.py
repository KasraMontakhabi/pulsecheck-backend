import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocket

from app.core.config import settings
from app.core.database import create_db_and_tables
from app.routers import monitors_router, websocket_router, auth_router
from app.workers import monitor_worker
from app.services.websocket import websocket_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("Starting PulseCheck backend...")
    await create_db_and_tables()

    await monitor_worker.start()

    logger.info("PulseCheck backend started successfully")

    yield

    logger.info("Shutting down PulseCheck backend...")

    await monitor_worker.stop()

    await websocket_manager.shutdown()

    logger.info("PulseCheck backend shutdown complete")



app = FastAPI(
    title=settings.APP_NAME,
    description="A simple uptime monitoring service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(monitors_router, prefix="/api/v1")
app.include_router(websocket_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "PulseCheck API is running", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )