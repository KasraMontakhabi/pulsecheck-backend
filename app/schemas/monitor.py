from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, HttpUrl, Field, validator
from app.models.monitor import MonitorStatus


class MonitorCreate(BaseModel):
    url: HttpUrl
    interval: int = Field(default=300, ge=30, le=3600)
    name: Optional[str] = Field(None, max_length=100)

    @validator("url")
    def validate_url(cls, v):
        url_str = str(v)
        if not (url_str.startswith("http://") or url_str.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return url_str


class MonitorUpdate(BaseModel):
    url: Optional[HttpUrl] = None
    interval: Optional[int] = Field(None, ge=30, le=3600)
    name: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class MonitorResponse(BaseModel):
    id: UUID
    url: str
    interval: int
    status: MonitorStatus
    last_latency_ms: Optional[int]
    last_checked_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    name: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class MonitorStatusUpdate(BaseModel):
    monitor_id: UUID
    status: MonitorStatus
    latency_ms: Optional[int]
    checked_at: datetime
    error_message: Optional[str] = None