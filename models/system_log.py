from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class SystemLogBase(BaseModel):
    """Base system log model with common fields."""
    source: str = Field(..., description="Log source: 'ocr', 'llm', 'whatsapp', 'image_gen'")
    log_type: str = Field(..., description="Log type: 'info', 'warning', 'error'")
    message: str = Field(..., description="Log message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional log details")


class SystemLogCreate(SystemLogBase):
    """Model for creating a new system log."""
    user_id: Optional[UUID] = Field(None, description="User ID if related to a user action")


class SystemLog(SystemLogBase):
    """Complete system log model including database fields."""
    id: UUID
    user_id: Optional[UUID]
    created_at: datetime

    class Config:
        from_attributes = True

