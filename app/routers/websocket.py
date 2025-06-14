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


# IMPORTANT: Dashboard routes MUST come before the {monitor_id} route
# Otherwise FastAPI will try to parse "dashboard" as a UUID

@router.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    """WebSocket endpoint for dashboard-wide updates"""
    import traceback
    from uuid import UUID

    print("🔍 Dashboard WebSocket endpoint called")

    # Accept the connection first
    await websocket.accept()
    print("✅ Dashboard WebSocket connection accepted")

    # Use a special UUID for dashboard connections
    dashboard_id = UUID('00000000-0000-0000-0000-000000000000')

    try:
        # Register with WebSocket manager
        print(f"📝 Registering with WebSocket manager using ID: {dashboard_id}")
        await websocket_manager.connect(websocket, dashboard_id)
        print("✅ Successfully registered with WebSocket manager")

        # Send welcome message
        welcome_msg = {"type": "welcome", "message": "Dashboard WebSocket connected"}
        await websocket.send_json(welcome_msg)
        print("📤 Sent welcome message")

        # Keep connection alive
        while True:
            try:
                # Wait for messages
                data = await websocket.receive_text()
                print(f"📥 Received: {data}")

                # Parse message
                try:
                    message = json.loads(data)

                    if message.get("type") == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": message.get("timestamp")
                        })
                        print("📤 Sent pong response")
                    else:
                        # Echo other messages
                        await websocket.send_json({
                            "type": "echo",
                            "received": message
                        })
                        print("📤 Sent echo response")

                except json.JSONDecodeError:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid JSON format"
                    })
                    print("⚠️ Received invalid JSON")

            except WebSocketDisconnect:
                print("🔌 Client disconnected normally")
                break
            except Exception as e:
                print(f"❌ Error in message loop: {type(e).__name__}: {e}")
                traceback.print_exc()
                break

    except Exception as e:
        print(f"❌ Error in dashboard WebSocket: {type(e).__name__}: {e}")
        traceback.print_exc()

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
        print("🔌 Unregistered from WebSocket manager")


@router.websocket("/ws/dashboard/test")
async def simple_dashboard_websocket(websocket: WebSocket):
    """Simple WebSocket endpoint for testing without dependencies"""
    print("🔍 Simple Dashboard WebSocket endpoint called")

    try:
        print("📡 Accepting WebSocket connection...")
        await websocket.accept()
        print("✅ WebSocket connection accepted")

        # Send welcome message
        await websocket.send_text('{"type": "welcome", "message": "Simple Dashboard WebSocket connected"}')
        print("📤 Sent welcome message")

        while True:
            try:
                data = await websocket.receive_text()
                print(f"📥 Received: {data}")

                # Simple echo
                await websocket.send_text(f'{{"type": "echo", "data": {data}}}')
                print("📤 Sent echo response")

            except WebSocketDisconnect:
                print("🔌 WebSocket disconnected")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                break

    except Exception as e:
        print(f"❌ Connection error: {e}")
        import traceback
        traceback.print_exc()


@router.websocket("/ws/dashboard/no-manager")
async def dashboard_websocket_no_manager(websocket: WebSocket):
    """Dashboard WebSocket that bypasses the manager for testing"""
    print("🔍 No-manager Dashboard WebSocket endpoint called")

    await websocket.accept()
    print("✅ WebSocket connection accepted")

    try:
        # Send welcome message
        await websocket.send_json({
            "type": "welcome",
            "message": "Dashboard WebSocket connected (no manager)"
        })

        # Simple message loop
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                else:
                    await websocket.send_json({"type": "echo", "data": message})

            except WebSocketDisconnect:
                print("🔌 Client disconnected")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                break

    except Exception as e:
        print(f"❌ Connection error: {e}")
        import traceback
        traceback.print_exc()


# MONITOR ROUTE MUST COME LAST because {monitor_id} will match any string
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
            await websocket.close(code=4004, reason="Monitor not found")
            return

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