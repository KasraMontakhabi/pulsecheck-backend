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
        self._shutdown = False

    async def connect(self, websocket: WebSocket, monitor_id: UUID):

        if monitor_id not in self.active_connections:
            self.active_connections[monitor_id] = set()

        self.active_connections[monitor_id].add(websocket)

        # Start Redis subscriber if not already running
        if self._subscriber_task is None and not self._shutdown:
            try:
                logger.info("Starting Redis subscriber task...")
                self._subscriber_task = asyncio.create_task(self._redis_subscriber())
                logger.info("Redis subscriber task started")
            except Exception as e:
                logger.error(f"Failed to start Redis subscriber: {e}")
                logger.debug("Exception details", exc_info=True)
                # Don't fail the connection, just log the error

        logger.info(
            f"WebSocket connected for monitor {monitor_id}. Total connections: {len(self.active_connections[monitor_id])}"
        )

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
            logger.debug(f"No active connections for monitor {monitor_id}")
            return

        disconnected = []
        successful_sends = 0

        for websocket in self.active_connections[monitor_id]:
            try:
                await websocket.send_text(message)
                successful_sends += 1
            except Exception as e:
                logger.error(f"Failed to broadcast to WebSocket for monitor {monitor_id}: {e}")
                disconnected.append(websocket)

        # Clean up disconnected WebSockets
        for websocket in disconnected:
            self.active_connections[monitor_id].discard(websocket)

        logger.debug(f"Broadcasted to {successful_sends} WebSockets for monitor {monitor_id}")

    async def _redis_subscriber(self):
        """Subscribe to Redis channels and broadcast to WebSockets"""
        logger.info("Starting Redis subscriber for WebSocket broadcasts")

        try:
            pubsub = self.redis.pubsub()
            await pubsub.psubscribe("monitor:*")

            async for message in pubsub.listen():
                if self._shutdown:
                    break

                if message["type"] == "pmessage":
                    try:
                        # Extract monitor_id from channel name (monitor:uuid)
                        channel = message["channel"].decode() if isinstance(message["channel"], bytes) else message[
                            "channel"]
                        monitor_id_str = channel.split(":", 1)[1]
                        monitor_id = UUID(monitor_id_str)

                        # Get message data
                        data = message["data"]
                        if isinstance(data, bytes):
                            data = data.decode()

                        # Broadcast to all connected WebSockets for this monitor
                        await self.broadcast_to_monitor(monitor_id, data)

                    except Exception as e:
                        logger.error(f"Error processing Redis message: {e}")
                        logger.debug(f"Message details: {message}")

        except asyncio.CancelledError:
            logger.info("Redis subscriber cancelled")
        except Exception as e:
            logger.error(f"Redis subscriber error: {e}")
        finally:
            try:
                await pubsub.unsubscribe()
                await pubsub.close()
            except:
                pass
            logger.info("Redis subscriber stopped")

    async def shutdown(self):
        """Shutdown the WebSocket manager"""
        self._shutdown = True

        if self._subscriber_task:
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except asyncio.CancelledError:
                pass

        # Close all active connections
        for monitor_id, websockets in self.active_connections.items():
            for websocket in websockets.copy():
                try:
                    await websocket.close()
                except:
                    pass

        self.active_connections.clear()
        logger.info("WebSocket manager shutdown complete")

    async def get_connection_stats(self) -> dict:
        """Get statistics about active connections"""
        total_connections = sum(len(websockets) for websockets in self.active_connections.values())
        return {
            "total_connections": total_connections,
            "monitors_with_connections": len(self.active_connections),
            "connections_per_monitor": {
                str(monitor_id): len(websockets)
                for monitor_id, websockets in self.active_connections.items()
            }
        }


# Global WebSocket manager instance
websocket_manager = WebSocketManager()