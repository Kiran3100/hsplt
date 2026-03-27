"""
Standardized API response schemas for consistent frontend integration.
All API endpoints must use these response formats.
"""
from typing import Any, Optional, List, Dict, Generic, TypeVar
from pydantic import BaseModel, Field
from datetime import datetime

T = TypeVar('T')


class APIResponse(BaseModel, Generic[T]):
    """
    Standard API response format for all endpoints.
    
    Success response:
    {
        "success": true,
        "message": "Operation completed successfully",
        "data": <payload>
    }
    
    Error response:
    {
        "success": false,
        "message": "Error description",
        "errors": ["Detailed error messages"],
        "data": null
    }
    """
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Human-readable message")
    data: Optional[T] = Field(None, description="Response payload")
    errors: Optional[List[str]] = Field(None, description="List of error messages")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class SuccessResponse(APIResponse[T]):
    """Success response wrapper"""
    success: bool = Field(True, description="Always true for success responses")
    errors: Optional[List[str]] = Field(None, description="Always null for success responses")


class ErrorResponse(APIResponse[None]):
    """Error response wrapper"""
    success: bool = Field(False, description="Always false for error responses")
    data: Optional[Any] = Field(None, description="Always null for error responses")
    errors: List[str] = Field(..., description="List of error messages")


# Specific response types for common patterns
class MessageOnlyResponse(SuccessResponse[Dict[str, str]]):
    """For endpoints that only return a message"""
    pass


class ListResponse(SuccessResponse[List[T]]):
    """For endpoints that return lists"""
    pass


class PaginatedResponse(SuccessResponse[Dict[str, Any]]):
    """For paginated endpoints"""
    pass


# Legacy response models that need to be migrated
class LegacyMessageResponse(BaseModel):
    """Legacy message response - to be replaced"""
    message: str
    status: Optional[str] = None


class LegacyAuthResponse(BaseModel):
    """Legacy auth response - to be replaced"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict