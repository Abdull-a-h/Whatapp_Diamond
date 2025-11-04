from fastapi import APIRouter, HTTPException, status
from typing import List
from uuid import UUID
from app.models.message import Message, MessageCreate
from app.database.supabase_client import get_supabase_client
from app.utils.exceptions import UserNotFoundException, DatabaseException
from app.utils.logger import log_to_database

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("", response_model=Message, status_code=status.HTTP_201_CREATED)
async def create_message(message: MessageCreate):
    """Create a new message record."""
    try:
        supabase = get_supabase_client()
        
        # Verify user exists
        user = supabase.table("users").select("id").eq("id", str(message.user_id)).execute()
        if not user.data:
            raise UserNotFoundException(str(message.user_id))
        
        # Create message
        result = supabase.table("messages").insert(message.model_dump()).execute()
        
        if not result.data:
            raise DatabaseException("Failed to create message")
        
        # Don't log every message to system_logs to avoid clutter
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        await log_to_database("api", "error", f"Error creating message: {str(e)}", user_id=message.user_id)
        raise DatabaseException(str(e))


@router.get("", response_model=List[Message])
async def get_messages(
    user_id: UUID = None,
    direction: str = None,
    message_type: str = None,
    skip: int = 0,
    limit: int = 100
):
    """Get messages with optional filters and pagination."""
    try:
        supabase = get_supabase_client()
        query = supabase.table("messages").select("*")
        
        if user_id:
            query = query.eq("user_id", str(user_id))
        if direction:
            query = query.eq("direction", direction)
        if message_type:
            query = query.eq("message_type", message_type)
        
        result = query.range(skip, skip + limit - 1).order("created_at", desc=True).execute()
        return result.data
        
    except Exception as e:
        await log_to_database("api", "error", f"Error fetching messages: {str(e)}")
        raise DatabaseException(str(e))


@router.get("/{message_id}", response_model=Message)
async def get_message(message_id: UUID):
    """Get a specific message by ID."""
    try:
        supabase = get_supabase_client()
        result = supabase.table("messages").select("*").eq("id", str(message_id)).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Message with ID {message_id} not found"
            )
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        await log_to_database("api", "error", f"Error fetching message: {str(e)}")
        raise DatabaseException(str(e))


@router.get("/conversation/{user_id}", response_model=List[Message])
async def get_conversation(user_id: UUID, limit: int = 50):
    """Get conversation history for a user (most recent messages)."""
    try:
        supabase = get_supabase_client()
        
        # Verify user exists
        user = supabase.table("users").select("id").eq("id", str(user_id)).execute()
        if not user.data:
            raise UserNotFoundException(str(user_id))
        
        result = (supabase.table("messages")
                 .select("*")
                 .eq("user_id", str(user_id))
                 .order("created_at", desc=True)
                 .limit(limit)
                 .execute())
        
        # Return in chronological order
        return list(reversed(result.data))
        
    except HTTPException:
        raise
    except Exception as e:
        await log_to_database("api", "error", f"Error fetching conversation: {str(e)}", user_id=user_id)
        raise DatabaseException(str(e))


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(message_id: UUID):
    """Delete a message."""
    try:
        supabase = get_supabase_client()
        
        # Check if message exists
        existing = supabase.table("messages").select("*").eq("id", str(message_id)).execute()
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Message with ID {message_id} not found"
            )
        
        # Delete message
        supabase.table("messages").delete().eq("id", str(message_id)).execute()
        
    except HTTPException:
        raise
    except Exception as e:
        await log_to_database("api", "error", f"Error deleting message: {str(e)}")
        raise DatabaseException(str(e))

