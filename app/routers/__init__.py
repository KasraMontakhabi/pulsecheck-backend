from .monitors import router as monitors_router
from .websocket import router as websocket_router
from .auth import router as auth_router

__all__ = ["monitors_router", "websocket_router", "auth_router"]