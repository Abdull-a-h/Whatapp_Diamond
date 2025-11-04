from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from decimal import Decimal


class DiamondBase(BaseModel):
    """Base diamond model with common fields."""
    shape: Optional[str] = Field(None, description="Diamond shape")
    carat: Optional[Decimal] = Field(None, description="Diamond carat weight")
    color_type: Optional[str] = Field(None, description="Color type")
    primary_hue: Optional[str] = Field(None, description="Primary hue")
    modifier: Optional[str] = Field(None, description="Color modifier")
    intensity: Optional[str] = Field(None, description="Color intensity")
    clarity: Optional[str] = Field(None, description="Diamond clarity")
    cut: Optional[str] = Field(None, description="Diamond cut grade")
    polish: Optional[str] = Field(None, description="Polish grade")
    symmetry: Optional[str] = Field(None, description="Symmetry grade")
    fluorescence: Optional[str] = Field(None, description="Fluorescence")
    certificate_number: Optional[str] = Field(None, description="GIA certificate number")
    parsed_confidence: Optional[Decimal] = Field(None, description="Parser confidence score (0-1)")


class DiamondCreate(DiamondBase):
    """Model for creating a new diamond record."""
    user_id: UUID = Field(..., description="User ID who owns this diamond")
    upload_id: Optional[UUID] = Field(None, description="Upload ID of the source file")


class DiamondUpdate(DiamondBase):
    """Model for updating a diamond record."""
    pass


class Diamond(DiamondBase):
    """Complete diamond model including database fields."""
    id: UUID
    upload_id: Optional[UUID]
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

