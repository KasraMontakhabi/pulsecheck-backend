import asyncio
import json
import logging
from typing import Dict, Set
from uuid import UUID
from fastapi import WebSocket
import redis.asyncio as redis
from app.core.database import redis_client

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[UUID, Set[WebSocket]] = {}
        self.redis = redis_client
        self._subscriber_task = None

    async def connect(self, websocket: WebSocket, monitor_id: UUID):
        """Accept WebSocket connection and subscribe to monitor updates"""
        await websocket.accept()

        if monitor_id not in self.active_connections:
            self.active_connections[monitor_id] = set()

        self.active_connections[monitor_id].add(websocket)

        # Start Redis subscriber if not already running
        if self._subscriber_task is None:
            self._subscriber_task = asyncio.create_task(self._redis_subscriber())

        logger.info(f"WebSocket connected for monitor {monitor_id}")

    def disconnect(self, websocket: WebSocket, monitor_id: UUID):
        """Remove WebSocket connection"""
        if monitor_id in self.active_connections:
            self.active_connections[monitor_id].discard(websocket)

            # Clean up empty sets
            if not self.active_connections[monitor_id]:
                del self.active_connections[monitor_id]

        logger.info(f"WebSocket disconnected for monitor {monitor_id}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific WebSocket"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")

    async def broadcast_to_monitor(self, monitor_id: UUID, message: str):
        """Broadcast message to all WebSockets for a specific monitor"""
        if monitor_id not in self.active_connections:
            return

        disconnected = []
        for websocket in self.active_connections[monitor_id]:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to WebSocket: {e}")
                disconnected.append(websocket)

        # Clean up disconnected WebSockets
        for websocket in disconnected:
            self.active_connections[monitor_id].discard(websocket)

    async def _redis_subscriber(self):
        """Subscribe to Redis channels and broadcast to WebSockets"""
        try:
            pubsub = self.redis.pubsub()
            await pubsub.psubscribe("monitor:*")

            async for message in pubsub.listen():
                if message["type"] == "pmessage":
                    try:
                        # Extract monitor_id from channel name
                        channel = message["channel"]
                        monitor_id_str = channel.split(":", 1)[1]
                        monitor_id = UUID(monitor_id_str)

                        # Broadcast to all connected WebSockets for this monitor
                        await self.broadcast_to_monitor(monitor_id, message["data"])

                    except Exception as e:
                        logger.error(f"Error processing Redis message: {e}")

        except Exception as e:
            logger.error(f"Redis subscriber error: {e}")
        finally:
            await pubsub.unsubscribe()

    async def get_monitor_status(self, monitor_id: UUID) -> dict:
        """Get current status for a monitor"""
        # This would typically fetch from database
        # For now, return a placeholder
        return {
            "monitor_id": str(monitor_id),
            "status": "unknown",
            "timestamp": "2025-06-10T12:00:00Z"
        }


# Global WebSocket manager instance
websocket_manager = WebSocketManager()