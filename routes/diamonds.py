from fastapi import APIRouter, HTTPException, status
from typing import List
from uuid import UUID
from app.models.diamond import Diamond, DiamondCreate, DiamondUpdate
from app.database.supabase_client import get_supabase_client
from app.utils.exceptions import DiamondNotFoundException, UserNotFoundException, DatabaseException
from app.utils.logger import log_to_database

router = APIRouter(prefix="/diamonds", tags=["diamonds"])


@router.post("", response_model=Diamond, status_code=status.HTTP_201_CREATED)
async def create_diamond(diamond: DiamondCreate):
    """Create a new diamond record."""
    try:
        supabase = get_supabase_client()
        
        # Verify user exists
        user = supabase.table("users").select("id").eq("id", str(diamond.user_id)).execute()
        if not user.data:
            raise UserNotFoundException(str(diamond.user_id))
        
        # Create diamond
        diamond_dict = diamond.model_dump()
        # Convert Decimal to float for JSON serialization
        if diamond_dict.get("carat"):
            diamond_dict["carat"] = float(diamond_dict["carat"])
        if diamond_dict.get("parsed_confidence"):
            diamond_dict["parsed_confidence"] = float(diamond_dict["parsed_confidence"])
        
        result = supabase.table("diamonds").insert(diamond_dict).execute()
        
        if not result.data:
            raise DatabaseException("Failed to create diamond")
        
        await log_to_database("api", "info", f"Diamond created: {result.data[0]['id']}", user_id=diamond.user_id)
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        await log_to_database("api", "error", f"Error creating diamond: {str(e)}", user_id=diamond.user_id)
        raise DatabaseException(str(e))


@router.get("", response_model=List[Diamond])
async def get_diamonds(user_id: UUID = None, skip: int = 0, limit: int = 100):
    """Get diamonds with optional user filter and pagination."""
    try:
        supabase = get_supabase_client()
        query = supabase.table("diamonds").select("*")
        
        if user_id:
            query = query.eq("user_id", str(user_id))
        
        result = query.range(skip, skip + limit - 1).order("created_at", desc=True).execute()
        return result.data
        
    except Exception as e:
        await log_to_database("api", "error", f"Error fetching diamonds: {str(e)}")
        raise DatabaseException(str(e))


@router.get("/{diamond_id}", response_model=Diamond)
async def get_diamond(diamond_id: UUID):
    """Get a specific diamond by ID."""
    try:
        supabase = get_supabase_client()
        result = supabase.table("diamonds").select("*").eq("id", str(diamond_id)).execute()
        
        if not result.data:
            raise DiamondNotFoundException(str(diamond_id))
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        await log_to_database("api", "error", f"Error fetching diamond: {str(e)}")
        raise DatabaseException(str(e))


@router.get("/certificate/{certificate_number}", response_model=Diamond)
async def get_diamond_by_certificate(certificate_number: str):
    """Get a diamond by GIA certificate number."""
    try:
        supabase = get_supabase_client()
        result = supabase.table("diamonds").select("*").eq("certificate_number", certificate_number).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Diamond with certificate number {certificate_number} not found"
            )
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        await log_to_database("api", "error", f"Error fetching diamond by certificate: {str(e)}")
        raise DatabaseException(str(e))


@router.patch("/{diamond_id}", response_model=Diamond)
async def update_diamond(diamond_id: UUID, diamond_update: DiamondUpdate):
    """Update a diamond record."""
    try:
        supabase = get_supabase_client()
        
        # Check if diamond exists
        existing = supabase.table("diamonds").select("*").eq("id", str(diamond_id)).execute()
        if not existing.data:
            raise DiamondNotFoundException(str(diamond_id))
        
        # Update only provided fields
        update_data = diamond_update.model_dump(exclude_unset=True)
        if not update_data:
            return existing.data[0]
        
        # Convert Decimal to float for JSON serialization
        if update_data.get("carat"):
            update_data["carat"] = float(update_data["carat"])
        if update_data.get("parsed_confidence"):
            update_data["parsed_confidence"] = float(update_data["parsed_confidence"])
        
        result = supabase.table("diamonds").update(update_data).eq("id", str(diamond_id)).execute()
        
        if not result.data:
            raise DatabaseException("Failed to update diamond")
        
        user_id = existing.data[0].get("user_id")
        await log_to_database("api", "info", f"Diamond updated: {diamond_id}", user_id=user_id)
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        await log_to_database("api", "error", f"Error updating diamond: {str(e)}")
        raise DatabaseException(str(e))


@router.delete("/{diamond_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_diamond(diamond_id: UUID):
    """Delete a diamond."""
    try:
        supabase = get_supabase_client()
        
        # Check if diamond exists
        existing = supabase.table("diamonds").select("*").eq("id", str(diamond_id)).execute()
        if not existing.data:
            raise DiamondNotFoundException(str(diamond_id))
        
        # Delete diamond
        supabase.table("diamonds").delete().eq("id", str(diamond_id)).execute()
        
        user_id = existing.data[0].get("user_id")
        await log_to_database("api", "info", f"Diamond deleted: {diamond_id}", user_id=user_id)
        
    except HTTPException:
        raise
    except Exception as e:
        await log_to_database("api", "error", f"Error deleting diamond: {str(e)}")
        raise DatabaseException(str(e))

