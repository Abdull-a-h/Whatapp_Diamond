import logging
from typing import Optional, Dict, Any
from uuid import UUID
from app.database.supabase_client import get_supabase_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)


async def log_to_database(source: str,
                          log_type: str,
                          message: str,
                          user_id: Optional[UUID] = None,
                          details: Optional[Dict[str, Any]] = None) -> None:
    """
    Log a message to both console and database.
    
    Args:
        source: Log source (e.g., 'ocr', 'llm', 'whatsapp', 'image_gen')
        log_type: Log type (e.g., 'info', 'warning', 'error')
        message: Log message
        user_id: Optional user ID if related to a user action
        details: Optional additional details
    """
    try:
        # Log to console
        if log_type == "error":
            logger.error(f"[{source}] {message}")
        elif log_type == "warning":
            logger.warning(f"[{source}] {message}")
        else:
            logger.info(f"[{source}] {message}")

        # Log to database
        supabase = get_supabase_client()
        log_data = {
            "source": source,
            "log_type": log_type,
            "message": message,
            "details": details or {}
        }

        if user_id:
            log_data["user_id"] = str(user_id)

        supabase.table("system_logs").insert(log_data).execute()

    except Exception as e:
        logger.error(f"Failed to log to database: {str(e)}")


def get_logger(name: str):
    """Get a logger instance with the given name."""
    return logging.getLogger(name)
