from datetime import datetime
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.deps import current_active_user
from app.models.monitor import Monitor
from app.models.user import User
from app.schemas.monitor import MonitorCreate, MonitorUpdate, MonitorResponse

router = APIRouter(prefix="/monitors", tags=["monitors"])


@router.post("/", response_model=MonitorResponse, status_code=status.HTTP_201_CREATED)
async def create_monitor(
        monitor_data: MonitorCreate,
        session: AsyncSession = Depends(get_session),
        current_user: User = Depends(current_active_user)
):
    """Create a new monitor"""
    monitor = Monitor(
        url=str(monitor_data.url),
        interval=monitor_data.interval,
        name=monitor_data.name,
        user_id=current_user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    session.add(monitor)
    await session.commit()
    await session.refresh(monitor)

    return monitor


@router.get("/", response_model=List[MonitorResponse])
async def get_monitors(
        session: AsyncSession = Depends(get_session),
        current_user: User = Depends(current_active_user)
):
    """Get all monitors for the current user"""
    result = await session.execute(
        select(Monitor)
        .where(Monitor.user_id == current_user.id)
        .order_by(Monitor.created_at.desc())
    )

    monitors = result.scalars().all()
    return monitors


@router.get("/{monitor_id}", response_model=MonitorResponse)
async def get_monitor(
        monitor_id: UUID,
        session: AsyncSession = Depends(get_session),
        current_user: User = Depends(current_active_user)
):
    """Get a specific monitor"""
    result = await session.execute(
        select(Monitor)
        .where(Monitor.id == monitor_id)
        .where(Monitor.user_id == current_user.id)
    )

    monitor = result.scalar_one_or_none()
    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found"
        )

    return monitor


@router.put("/{monitor_id}", response_model=MonitorResponse)
async def update_monitor(
        monitor_id: UUID,
        monitor_data: MonitorUpdate,
        session: AsyncSession = Depends(get_session),
        current_user: User = Depends(current_active_user)
):
    result = await session.execute(
        select(Monitor)
        .where(Monitor.id == monitor_id)
        .where(Monitor.user_id == current_user.id)
    )

    monitor = result.scalar_one_or_none()
    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found"
        )

    # Update fields
    if monitor_data.url is not None:
        monitor.url = str(monitor_data.url)
    if monitor_data.interval is not None:
        monitor.interval = monitor_data.interval
    if monitor_data.name is not None:
        monitor.name = monitor_data.name
    if monitor_data.is_active is not None:
        monitor.is_active = monitor_data.is_active

    monitor.updated_at = datetime.utcnow()

    session.add(monitor)
    await session.commit()
    await session.refresh(monitor)

    return monitor


@router.delete("/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_monitor(
        monitor_id: UUID,
        session: AsyncSession = Depends(get_session),
        current_user: User = Depends(current_active_user)
):
    result = await session.execute(
        select(Monitor)
        .where(Monitor.id == monitor_id)
        .where(Monitor.user_id == current_user.id)
    )

    monitor = result.scalar_one_or_none()
    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found"
        )

    await session.delete(monitor)
    await session.commit()


@router.post("/{monitor_id}/check", response_model=MonitorResponse)
async def manual_check(
        monitor_id: UUID,
        session: AsyncSession = Depends(get_session),
        current_user: User = Depends(current_active_user)
):
    """Manually trigger a monitor check"""
    result = await session.execute(
        select(Monitor)
        .where(Monitor.id == monitor_id)
        .where(Monitor.user_id == current_user.id)
    )

    monitor = result.scalar_one_or_none()
    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found"
        )

    from app.services.uptime import UptimeService

    uptime_service = UptimeService()
    try:
        status_update = await uptime_service.check_monitor(monitor)
        await uptime_service.update_monitor_status(session, status_update)

        await session.refresh(monitor)
        return monitor

    finally:
        await uptime_service.close()