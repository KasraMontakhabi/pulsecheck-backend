import json
import logging
from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.models.monitor import Monitor
from app.services.websocket import websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    """WebSocket endpoint for dashboard-wide updates"""
    import traceback
    from uuid import UUID

    logger.info("Dashboard WebSocket endpoint called")

    await websocket.accept()
    logger.info("Dashboard WebSocket connection accepted")

    # Use a special UUID for dashboard connections
    dashboard_id = UUID('00000000-0000-0000-0000-000000000000')

    try:
        logger.info(f"Registering with WebSocket manager using ID: {dashboard_id}")
        await websocket_manager.connect(websocket, dashboard_id)
        logger.info("Successfully registered with WebSocket manager")

        # Send welcome message
        welcome_msg = {"type": "welcome", "message": "Dashboard WebSocket connected"}
        await websocket.send_json(welcome_msg)
        logger.info("Sent welcome message")

        # Keep connection alive
        while True:
            try:
                # Wait for messages
                data = await websocket.receive_text()
                logger.debug(f"Received: {data}")

                # Parse message
                try:
                    message = json.loads(data)

                    if message.get("type") == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": message.get("timestamp")
                        })
                        logger.debug("Sent pong response")
                    else:
                        # Echo other messages
                        await websocket.send_json({
                            "type": "echo",
                            "received": message
                        })
                        logger.debug("Sent echo response")

                except json.JSONDecodeError:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid JSON format"
                    })
                    logger.warning("Received invalid JSON")

            except WebSocketDisconnect:
                logger.info("Client disconnected normally")
                break
            except Exception as e:
                logger.error(f"Error in message loop: {type(e).__name__}: {e}")
                logger.debug("Exception details", exc_info=True)
                break

    except Exception as e:
        logger.error(f"Error in dashboard WebSocket: {type(e).__name__}: {e}")
        logger.debug("Exception details", exc_info=True)

        # Try to send error message to client
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Server error: {str(e)}"
            })
        except:
            pass

        # Close connection with error code
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
    finally:
        # Always unregister from manager
        websocket_manager.disconnect(websocket, dashboard_id)
        logger.info("Unregistered from WebSocket manager")

@router.websocket("/ws/{monitor_id}")
async def websocket_endpoint(
        websocket: WebSocket,
        monitor_id: UUID,
        session: AsyncSession = Depends(get_session)
):
    """WebSocket endpoint for real-time monitor status updates"""

    # First accept the WebSocket connection
    await websocket.accept()

    try:
        # Then verify monitor exists
        result = await session.execute(
            select(Monitor).where(Monitor.id == monitor_id)
        )
        monitor = result.scalar_one_or_none()

        if not monitor:
            logger.warning(f"Monitor not found: {monitor_id}")
            await websocket.close(code=4004, reason="Monitor not found")
            return

        logger.info(f"Monitor WebSocket connection established for monitor: {monitor_id}")

        # Register WebSocket connection
        await websocket_manager.connect(websocket, monitor_id)

        # Send initial status
        initial_status = {
            "monitor_id": str(monitor_id),
            "status": monitor.status.value,
            "last_latency_ms": monitor.last_latency_ms,
            "last_checked_at": monitor.last_checked_at.isoformat() if monitor.last_checked_at else None,
            "type": "status_update"
        }

        await websocket_manager.send_personal_message(
            json.dumps(initial_status),
            websocket
        )
        logger.debug(f"Sent initial status for monitor: {monitor_id}")

        # Keep connection alive and handle client messages
        while True:
            try:
                data = await websocket.receive_text()
                # Handle client messages if needed
                message = json.loads(data)

                if message.get("type") == "ping":
                    await websocket_manager.send_personal_message(
                        json.dumps({"type": "pong"}),
                        websocket
                    )

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for monitor {monitor_id}")
                break
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from WebSocket: {data}")
                # Send error message instead of breaking
                await websocket_manager.send_personal_message(
                    json.dumps({"type": "error", "message": "Invalid JSON format"}),
                    websocket
                )
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break

    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass  # Connection might already be closed
    finally:
        websocket_manager.disconnect(websocket, monitor_id)
        logger.info(f"WebSocket connection closed for monitor: {monitor_id}")