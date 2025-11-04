from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from uuid import UUID
from app.models.user import User, UserCreate, UserUpdate
from app.database.supabase_client import get_supabase_client
from app.utils.exceptions import UserNotFoundException, DatabaseException
from app.utils.responses import success_response
from app.utils.logger import log_to_database

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    """Create a new user."""
    try:
        supabase = get_supabase_client()
        
        # Check if user already exists
        existing = supabase.table("users").select("*").eq("whatsapp_number", user.whatsapp_number).execute()
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with WhatsApp number {user.whatsapp_number} already exists"
            )
        
        # Create user
        result = supabase.table("users").insert(user.model_dump()).execute()
        
        if not result.data:
            raise DatabaseException("Failed to create user")
        
        await log_to_database("api", "info", f"User created: {user.whatsapp_number}")
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        await log_to_database("api", "error", f"Error creating user: {str(e)}")
        raise DatabaseException(str(e))


@router.get("", response_model=List[User])
async def get_users(skip: int = 0, limit: int = 100):
    """Get all users with pagination."""
    try:
        supabase = get_supabase_client()
        result = supabase.table("users").select("*").range(skip, skip + limit - 1).execute()
        return result.data
        
    except Exception as e:
        await log_to_database("api", "error", f"Error fetching users: {str(e)}")
        raise DatabaseException(str(e))


@router.get("/{user_id}", response_model=User)
async def get_user(user_id: UUID):
    """Get a specific user by ID."""
    try:
        supabase = get_supabase_client()
        result = supabase.table("users").select("*").eq("id", str(user_id)).execute()
        
        if not result.data:
            raise UserNotFoundException(str(user_id))
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        await log_to_database("api", "error", f"Error fetching user: {str(e)}", user_id=user_id)
        raise DatabaseException(str(e))


@router.get("/whatsapp/{whatsapp_number}", response_model=User)
async def get_user_by_whatsapp(whatsapp_number: str):
    """Get a user by WhatsApp number."""
    try:
        supabase = get_supabase_client()
        result = supabase.table("users").select("*").eq("whatsapp_number", whatsapp_number).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with WhatsApp number {whatsapp_number} not found"
            )
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        await log_to_database("api", "error", f"Error fetching user by WhatsApp: {str(e)}")
        raise DatabaseException(str(e))


@router.patch("/{user_id}", response_model=User)
async def update_user(user_id: UUID, user_update: UserUpdate):
    """Update a user."""
    try:
        supabase = get_supabase_client()
        
        # Check if user exists
        existing = supabase.table("users").select("*").eq("id", str(user_id)).execute()
        if not existing.data:
            raise UserNotFoundException(str(user_id))
        
        # Update only provided fields
        update_data = user_update.model_dump(exclude_unset=True)
        if not update_data:
            return existing.data[0]
        
        result = supabase.table("users").update(update_data).eq("id", str(user_id)).execute()
        
        if not result.data:
            raise DatabaseException("Failed to update user")
        
        await log_to_database("api", "info", f"User updated: {user_id}", user_id=user_id)
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        await log_to_database("api", "error", f"Error updating user: {str(e)}", user_id=user_id)
        raise DatabaseException(str(e))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: UUID):
    """Delete a user."""
    try:
        supabase = get_supabase_client()
        
        # Check if user exists
        existing = supabase.table("users").select("*").eq("id", str(user_id)).execute()
        if not existing.data:
            raise UserNotFoundException(str(user_id))
        
        # Delete user (cascades to related records)
        supabase.table("users").delete().eq("id", str(user_id)).execute()
        
        await log_to_database("api", "info", f"User deleted: {user_id}", user_id=user_id)
        
    except HTTPException:
        raise
    except Exception as e:
        await log_to_database("api", "error", f"Error deleting user: {str(e)}", user_id=user_id)
        raise DatabaseException(str(e))

