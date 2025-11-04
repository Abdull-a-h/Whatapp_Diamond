from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserBase(BaseModel):
    """Base user model with common fields."""
    whatsapp_number: str = Field(..., description="WhatsApp phone number")
    full_name: Optional[str] = Field(None, description="User's full name")
    last_intent: Optional[str] = Field(None, description="Last user intent (e.g., 'gia_upload', 'jewelry_design')")


class UserCreate(UserBase):
    """Model for creating a new user."""
    pass


class UserUpdate(BaseModel):
    """Model for updating a user."""
    full_name: Optional[str] = None
    last_intent: Optional[str] = None


class User(UserBase):
    """Complete user model including database fields."""
    id: UUID
    last_interaction: datetime
    created_at: datetime

    class Config:
        from_attributes = True

