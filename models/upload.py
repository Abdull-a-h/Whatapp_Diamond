from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class UploadBase(BaseModel):
    """Base upload model with common fields."""
    file_url: str = Field(..., description="URL to uploaded file (Supabase Storage or WhatsApp)")
    file_type: Optional[str] = Field(None, description="File type: 'pdf', 'image', etc.")


class UploadCreate(UploadBase):
    """Model for creating a new upload."""
    user_id: UUID = Field(..., description="User ID who uploaded the file")
    status: str = Field(default="uploaded", description="Upload status")
    error_message: Optional[str] = None


class UploadUpdate(BaseModel):
    """Model for updating an upload."""
    status: Optional[str] = None
    error_message: Optional[str] = None


class Upload(UploadBase):
    """Complete upload model including database fields."""
    id: UUID
    user_id: UUID
    status: str
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

