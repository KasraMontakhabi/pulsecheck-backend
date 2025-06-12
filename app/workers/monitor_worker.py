import asyncio
import logging
from datetime import datetime
from app.core.database import async_session
from app.services.uptime import UptimeService

logger = logging.getLogger(__name__)


class MonitorWorker:
    def __init__(self):
        self.uptime_service = UptimeService()
        self.is_running = False
        self._task = None

    async def start(self):
        """Start the monitoring worker"""
        if self.is_running:
            return

        self.is_running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Monitor worker started")

    async def stop(self):
        """Stop the monitoring worker"""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        await self.uptime_service.close()
        logger.info("Monitor worker stopped")

    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                await self._check_all_monitors()
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retrying

    async def _check_all_monitors(self):
        """Check all active monitors"""
        try:
            monitors = await self.uptime_service.get_active_monitors()

            # Check which monitors need to be checked
            tasks = []
            for monitor in monitors:
                if await self.uptime_service.should_check_monitor(monitor):
                    tasks.append(self._check_single_monitor(monitor))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"Error checking monitors: {e}")

    async def _check_single_monitor(self, monitor):
        """Check a single monitor"""
        try:
            # Perform the uptime check
            status_update = await self.uptime_service.check_monitor(monitor)

            # Update database and send notifications
            async with async_session() as session:
                await self.uptime_service.update_monitor_status(session, status_update)

            logger.debug(f"Checked monitor {monitor.id}: {status_update.status}")

        except Exception as e:
            logger.error(f"Error checking monitor {monitor.id}: {e}")


# Global worker instance
monitor_worker = MonitorWorker()