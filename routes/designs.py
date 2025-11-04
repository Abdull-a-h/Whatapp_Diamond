from fastapi import APIRouter, HTTPException, status
from typing import List
from uuid import UUID
from app.models.design import Design, DesignCreate, DesignUpdate
from app.database.supabase_client import get_supabase_client
from app.utils.exceptions import DesignNotFoundException, UserNotFoundException, DatabaseException
from app.utils.logger import log_to_database

router = APIRouter(prefix="/designs", tags=["designs"])


@router.post("", response_model=Design, status_code=status.HTTP_201_CREATED)
async def create_design(design: DesignCreate):
    """Create a new design record."""
    try:
        supabase = get_supabase_client()
        
        # Verify user exists
        user = supabase.table("users").select("id").eq("id", str(design.user_id)).execute()
        if not user.data:
            raise UserNotFoundException(str(design.user_id))
        
        # Create design
        result = supabase.table("designs").insert(design.model_dump()).execute()
        
        if not result.data:
            raise DatabaseException("Failed to create design")
        
        await log_to_database("api", "info", f"Design created: {result.data[0]['id']}", user_id=design.user_id)
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        await log_to_database("api", "error", f"Error creating design: {str(e)}", user_id=design.user_id)
        raise DatabaseException(str(e))


@router.get("", response_model=List[Design])
async def get_designs(
    user_id: UUID = None,
    diamond_id: UUID = None,
    design_type: str = None,
    status: str = None,
    skip: int = 0,
    limit: int = 100
):
    """Get designs with optional filters and pagination."""
    try:
        supabase = get_supabase_client()
        query = supabase.table("designs").select("*")
        
        if user_id:
            query = query.eq("user_id", str(user_id))
        if diamond_id:
            query = query.eq("diamond_id", str(diamond_id))
        if design_type:
            query = query.eq("type", design_type)
        if status:
            query = query.eq("status", status)
        
        result = query.range(skip, skip + limit - 1).order("created_at", desc=True).execute()
        return result.data
        
    except Exception as e:
        await log_to_database("api", "error", f"Error fetching designs: {str(e)}")
        raise DatabaseException(str(e))


@router.get("/{design_id}", response_model=Design)
async def get_design(design_id: UUID):
    """Get a specific design by ID."""
    try:
        supabase = get_supabase_client()
        result = supabase.table("designs").select("*").eq("id", str(design_id)).execute()
        
        if not result.data:
            raise DesignNotFoundException(str(design_id))
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        await log_to_database("api", "error", f"Error fetching design: {str(e)}")
        raise DatabaseException(str(e))


@router.patch("/{design_id}", response_model=Design)
async def update_design(design_id: UUID, design_update: DesignUpdate):
    """Update a design record."""
    try:
        supabase = get_supabase_client()
        
        # Check if design exists
        existing = supabase.table("designs").select("*").eq("id", str(design_id)).execute()
        if not existing.data:
            raise DesignNotFoundException(str(design_id))
        
        # Update only provided fields
        update_data = design_update.model_dump(exclude_unset=True)
        if not update_data:
            return existing.data[0]
        
        result = supabase.table("designs").update(update_data).eq("id", str(design_id)).execute()
        
        if not result.data:
            raise DatabaseException("Failed to update design")
        
        user_id = existing.data[0].get("user_id")
        await log_to_database("api", "info", f"Design updated: {design_id}", user_id=user_id)
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        await log_to_database("api", "error", f"Error updating design: {str(e)}")
        raise DatabaseException(str(e))


@router.delete("/{design_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_design(design_id: UUID):
    """Delete a design."""
    try:
        supabase = get_supabase_client()
        
        # Check if design exists
        existing = supabase.table("designs").select("*").eq("id", str(design_id)).execute()
        if not existing.data:
            raise DesignNotFoundException(str(design_id))
        
        # Delete design
        supabase.table("designs").delete().eq("id", str(design_id)).execute()
        
        user_id = existing.data[0].get("user_id")
        await log_to_database("api", "info", f"Design deleted: {design_id}", user_id=user_id)
        
    except HTTPException:
        raise
    except Exception as e:
        await log_to_database("api", "error", f"Error deleting design: {str(e)}")
        raise DatabaseException(str(e))

