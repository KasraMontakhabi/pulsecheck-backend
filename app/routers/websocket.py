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


@router.websocket("/ws/{monitor_id}")
async def websocket_endpoint(
        websocket: WebSocket,
        monitor_id: UUID,
        session: AsyncSession = Depends(get_session)
):
    """WebSocket endpoint for real-time monitor status updates"""
    # Verify monitor exists (basic validation)
    result = await session.execute(
        select(Monitor).where(Monitor.id == monitor_id)
    )
    monitor = result.scalar_one_or_none()

    if not monitor:
        await websocket.close(code=4004, reason="Monitor not found")
        return

    # Connect WebSocket
    await websocket_manager.connect(websocket, monitor_id)

    try:
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
                break
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from WebSocket: {data}")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        websocket_manager.disconnect(websocket, monitor_id)


@router.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    """WebSocket endpoint for dashboard-wide updates"""
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()
            # Handle dashboard-wide messages
            message = json.loads(data)

            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Dashboard WebSocket error: {e}")
    finally:
        await websocket.close()