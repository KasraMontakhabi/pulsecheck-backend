from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class MonitorStatus(str, Enum):
    UP = "up"
    DOWN = "down"
    UNKNOWN = "unknown"


class Monitor(Base):
    __tablename__ = "monitor"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    url = Column(String, index=True, nullable=False)
    interval = Column(Integer, default=300)  # seconds
    status = Column(SQLEnum(MonitorStatus), default=MonitorStatus.UNKNOWN)
    last_latency_ms = Column(Integer, nullable=True)
    last_checked_at = Column(DateTime, nullable=True)
    last_alert_sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("user.id"), nullable=False)

    name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="monitors")