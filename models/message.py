from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class MessageBase(BaseModel):
    """Base message model with common fields."""
    direction: str = Field(..., description="Message direction: 'inbound' or 'outbound'")
    message_type: Optional[str] = Field(None, description="Message type: 'text', 'image', 'document', 'audio'")
    content: Optional[str] = Field(None, description="Text message content or caption")
    media_url: Optional[str] = Field(None, description="URL for media messages")
    meta: Optional[Dict[str, Any]] = Field(None, description="Metadata (webhook payload, etc.)")


class MessageCreate(MessageBase):
    """Model for creating a new message."""
    user_id: UUID = Field(..., description="User ID for this message")


class MessageUpdate(BaseModel):
    """Model for updating a message."""
    content: Optional[str] = None
    media_url: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class Message(MessageBase):
    """Complete message model including database fields."""
    id: UUID
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

