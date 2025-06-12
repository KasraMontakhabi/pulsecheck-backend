import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional
import httpx
import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import async_session, redis_client
from app.models.monitor import Monitor, MonitorStatus
from app.schemas.monitor import MonitorStatusUpdate
from app.services.email import EmailService
import json
import logging

logger = logging.getLogger(__name__)


class UptimeService:
    def __init__(self):
        self.redis = redis_client
        self.email_service = EmailService()
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def check_monitor(self, monitor: Monitor) -> MonitorStatusUpdate:
        """Check a single monitor's status"""
        start_time = time.time()
        status = MonitorStatus.DOWN
        latency_ms = None
        error_message = None

        try:
            response = await self.http_client.get(monitor.url)
            latency_ms = int((time.time() - start_time) * 1000)

            if 200 <= response.status_code < 400:
                status = MonitorStatus.UP
            else:
                status = MonitorStatus.DOWN
                error_message = f"HTTP {response.status_code}"

        except httpx.TimeoutException:
            error_message = "Request timeout"
            status = MonitorStatus.DOWN
        except Exception as e:
            error_message = str(e)
            status = MonitorStatus.DOWN

        return MonitorStatusUpdate(
            monitor_id=monitor.id,
            status=status,
            latency_ms=latency_ms,
            checked_at=datetime.utcnow(),
            error_message=error_message
        )

    async def update_monitor_status(self, session: AsyncSession, status_update: MonitorStatusUpdate):
        """Update monitor status in database"""
        result = await session.execute(
            select(Monitor).where(Monitor.id == status_update.monitor_id)
        )
        monitor = result.scalar_one_or_none()

        if not monitor:
            return

        old_status = monitor.status
        monitor.status = status_update.status
        monitor.last_latency_ms = status_update.latency_ms
        monitor.last_checked_at = status_update.checked_at
        monitor.updated_at = datetime.utcnow()

        session.add(monitor)
        await session.commit()

        # Check if we need to send alert
        if old_status != MonitorStatus.DOWN and status_update.status == MonitorStatus.DOWN:
            await self._check_and_send_alert(session, monitor, status_update.error_message)

        # Publish to Redis for WebSocket
        await self._publish_status_update(status_update)

    async def _check_and_send_alert(self, session: AsyncSession, monitor: Monitor, error_message: Optional[str]):
        """Send email alert if conditions are met"""
        now = datetime.utcnow()

        # Check debounce period
        if monitor.last_alert_sent_at:
            time_since_last_alert = now - monitor.last_alert_sent_at
            if time_since_last_alert < timedelta(minutes=settings.EMAIL_DEBOUNCE_MINUTES):
                return

        # Send alert
        await self.email_service.send_down_alert(monitor, error_message)

        # Update last alert time
        monitor.last_alert_sent_at = now
        session.add(monitor)
        await session.commit()

    async def _publish_status_update(self, status_update: MonitorStatusUpdate):
        """Publish status update to Redis for WebSocket broadcasting"""
        try:
            await self.redis.publish(
                f"monitor:{status_update.monitor_id}",
                json.dumps({
                    "monitor_id": str(status_update.monitor_id),
                    "status": status_update.status.value,
                    "latency_ms": status_update.latency_ms,
                    "checked_at": status_update.checked_at.isoformat(),
                    "error_message": status_update.error_message
                })
            )
        except Exception as e:
            logger.error(f"Failed to publish status update: {e}")

    async def get_active_monitors(self) -> list[Monitor]:
        """Get all active monitors that need checking"""
        async with async_session() as session:
            result = await session.execute(
                select(Monitor).where(Monitor.is_active == True)
            )
            return result.scalars().all()

    async def should_check_monitor(self, monitor: Monitor) -> bool:
        """Check if monitor should be checked based on interval"""
        if not monitor.last_checked_at:
            return True

        time_since_check = datetime.utcnow() - monitor.last_checked_at
        return time_since_check.total_seconds() >= monitor.interval

    async def close(self):
        """Clean up resources"""
        await self.http_client.aclose()