from fastapi import APIRouter, HTTPException, status
from typing import List
from uuid import UUID
from app.models.upload import Upload, UploadCreate, UploadUpdate
from app.database.supabase_client import get_supabase_client
from app.utils.exceptions import UploadNotFoundException, UserNotFoundException, DatabaseException
from app.utils.logger import log_to_database

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", response_model=Upload, status_code=status.HTTP_201_CREATED)
async def create_upload(upload: UploadCreate):
    """Create a new upload record."""
    try:
        supabase = get_supabase_client()
        
        # Verify user exists
        user = supabase.table("users").select("id").eq("id", str(upload.user_id)).execute()
        if not user.data:
            raise UserNotFoundException(str(upload.user_id))
        
        # Create upload
        result = supabase.table("uploads").insert(upload.model_dump()).execute()
        
        if not result.data:
            raise DatabaseException("Failed to create upload")
        
        await log_to_database("api", "info", f"Upload created: {result.data[0]['id']}", user_id=upload.user_id)
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        await log_to_database("api", "error", f"Error creating upload: {str(e)}", user_id=upload.user_id)
        raise DatabaseException(str(e))


@router.get("", response_model=List[Upload])
async def get_uploads(user_id: UUID = None, skip: int = 0, limit: int = 100):
    """Get uploads with optional user filter and pagination."""
    try:
        supabase = get_supabase_client()
        query = supabase.table("uploads").select("*")
        
        if user_id:
            query = query.eq("user_id", str(user_id))
        
        result = query.range(skip, skip + limit - 1).order("created_at", desc=True).execute()
        return result.data
        
    except Exception as e:
        await log_to_database("api", "error", f"Error fetching uploads: {str(e)}")
        raise DatabaseException(str(e))


@router.get("/{upload_id}", response_model=Upload)
async def get_upload(upload_id: UUID):
    """Get a specific upload by ID."""
    try:
        supabase = get_supabase_client()
        result = supabase.table("uploads").select("*").eq("id", str(upload_id)).execute()
        
        if not result.data:
            raise UploadNotFoundException(str(upload_id))
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        await log_to_database("api", "error", f"Error fetching upload: {str(e)}")
        raise DatabaseException(str(e))


@router.patch("/{upload_id}", response_model=Upload)
async def update_upload(upload_id: UUID, upload_update: UploadUpdate):
    """Update an upload record."""
    try:
        supabase = get_supabase_client()
        
        # Check if upload exists
        existing = supabase.table("uploads").select("*").eq("id", str(upload_id)).execute()
        if not existing.data:
            raise UploadNotFoundException(str(upload_id))
        
        # Update only provided fields
        update_data = upload_update.model_dump(exclude_unset=True)
        if not update_data:
            return existing.data[0]
        
        result = supabase.table("uploads").update(update_data).eq("id", str(upload_id)).execute()
        
        if not result.data:
            raise DatabaseException("Failed to update upload")
        
        user_id = existing.data[0].get("user_id")
        await log_to_database("api", "info", f"Upload updated: {upload_id}", user_id=user_id)
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        await log_to_database("api", "error", f"Error updating upload: {str(e)}")
        raise DatabaseException(str(e))


@router.delete("/{upload_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_upload(upload_id: UUID):
    """Delete an upload."""
    try:
        supabase = get_supabase_client()
        
        # Check if upload exists
        existing = supabase.table("uploads").select("*").eq("id", str(upload_id)).execute()
        if not existing.data:
            raise UploadNotFoundException(str(upload_id))
        
        # Delete upload
        supabase.table("uploads").delete().eq("id", str(upload_id)).execute()
        
        user_id = existing.data[0].get("user_id")
        await log_to_database("api", "info", f"Upload deleted: {upload_id}", user_id=user_id)
        
    except HTTPException:
        raise
    except Exception as e:
        await log_to_database("api", "error", f"Error deleting upload: {str(e)}")
        raise DatabaseException(str(e))

