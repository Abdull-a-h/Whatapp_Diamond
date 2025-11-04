from typing import Any, Optional, List, Dict
from pydantic import BaseModel


class SuccessResponse(BaseModel):
    """Standard success response model."""
    success: bool = True
    message: str
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Standard error response model."""
    success: bool = False
    error: str
    detail: Optional[str] = None


class PaginatedResponse(BaseModel):
    """Paginated response model."""
    success: bool = True
    data: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


def success_response(message: str, data: Any = None) -> Dict[str, Any]:
    """Create a success response."""
    return {
        "success": True,
        "message": message,
        "data": data
    }


def error_response(error: str, detail: Optional[str] = None) -> Dict[str, Any]:
    """Create an error response."""
    response = {
        "success": False,
        "error": error
    }
    if detail:
        response["detail"] = detail
    return response

