from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class DesignBase(BaseModel):
    """Base design model with common fields."""
    type: str = Field(..., description="Design type: 'auto', 'create_another', 'describe_own'")
    user_input: Optional[str] = Field(None, description="User input for 'describe_own' type")
    previous_prompt: Optional[str] = Field(None, description="Previous prompt for variations")
    generated_prompt: Optional[str] = Field(None, description="AI-generated design prompt")
    generated_image_url: Optional[str] = Field(None, description="URL to generated image")
    status: str = Field(default="created", description="Design status: 'created', 'image_generated', 'approved', 'rejected'")


class DesignCreate(DesignBase):
    """Model for creating a new design."""
    user_id: UUID = Field(..., description="User ID who requested the design")
    diamond_id: Optional[UUID] = Field(None, description="Diamond ID for this design")


class DesignUpdate(BaseModel):
    """Model for updating a design."""
    generated_prompt: Optional[str] = None
    generated_image_url: Optional[str] = None
    status: Optional[str] = None


class Design(DesignBase):
    """Complete design model including database fields."""
    id: UUID
    user_id: UUID
    diamond_id: Optional[UUID]
    created_at: datetime

    class Config:
        from_attributes = True

