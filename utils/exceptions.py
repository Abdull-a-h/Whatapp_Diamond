from fastapi import HTTPException, status
from typing import Any, Dict, Optional


class BaseAPIException(HTTPException):
    """Base exception for API errors."""
    
    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = "An error occurred",
        headers: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class UserNotFoundException(BaseAPIException):
    """Exception raised when a user is not found."""
    
    def __init__(self, user_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )


class UploadNotFoundException(BaseAPIException):
    """Exception raised when an upload is not found."""
    
    def __init__(self, upload_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload with ID {upload_id} not found"
        )


class DiamondNotFoundException(BaseAPIException):
    """Exception raised when a diamond is not found."""
    
    def __init__(self, diamond_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diamond with ID {diamond_id} not found"
        )


class DesignNotFoundException(BaseAPIException):
    """Exception raised when a design is not found."""
    
    def __init__(self, design_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Design with ID {design_id} not found"
        )


class DatabaseException(BaseAPIException):
    """Exception raised when a database operation fails."""
    
    def __init__(self, detail: str = "Database operation failed"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )


class ValidationException(BaseAPIException):
    """Exception raised when validation fails."""
    
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail
        )

