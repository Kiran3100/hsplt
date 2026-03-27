"""
Utility functions for creating standardized API responses.
Helps developers migrate existing endpoints to the new response format.
"""
from typing import Any, List, Dict, Optional, TypeVar
from app.schemas.response import SuccessResponse, APIResponse

T = TypeVar('T')


def success_response(
    message: str,
    data: Any = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a standardized success response.
    
    Args:
        message: Human-readable success message
        data: Response payload (can be any serializable type)
        **kwargs: Additional fields (for backward compatibility)
    
    Returns:
        Standardized success response dictionary
    
    Example:
        return success_response(
            message="User created successfully",
            data={"user_id": "123", "email": "user@example.com"}
        )
    """
    return SuccessResponse(
        success=True,
        message=message,
        data=data
    ).dict()


def error_response(
    message: str,
    errors: Optional[List[str]] = None,
    status_code: int = 400
) -> Dict[str, Any]:
    """
    Create a standardized error response.
    
    Args:
        message: Human-readable error message
        errors: List of detailed error messages
        status_code: HTTP status code (for reference, not used in response)
    
    Returns:
        Standardized error response dictionary
    
    Example:
        return error_response(
            message="Validation failed",
            errors=["Email is required", "Password too short"]
        )
    """
    from app.schemas.response import ErrorResponse
    return ErrorResponse(
        success=False,
        message=message,
        errors=errors or [message],
        data=None
    ).dict()


def paginated_response(
    message: str,
    items: List[Any],
    total: int,
    page: int = 1,
    page_size: int = 10,
    **metadata
) -> Dict[str, Any]:
    """
    Create a standardized paginated response.
    
    Args:
        message: Human-readable message
        items: List of items for current page
        total: Total number of items
        page: Current page number
        page_size: Items per page
        **metadata: Additional pagination metadata
    
    Returns:
        Standardized paginated response
    
    Example:
        return paginated_response(
            message="Users retrieved successfully",
            items=user_list,
            total=150,
            page=2,
            page_size=20
        )
    """
    total_pages = (total + page_size - 1) // page_size
    
    pagination_data = {
        "items": items,
        "pagination": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            **metadata
        }
    }
    
    return success_response(message=message, data=pagination_data)


def list_response(
    message: str,
    items: List[Any],
    count: Optional[int] = None
) -> Dict[str, Any]:
    """
    Create a standardized list response.
    
    Args:
        message: Human-readable message
        items: List of items
        count: Optional count (defaults to len(items))
    
    Returns:
        Standardized list response
    
    Example:
        return list_response(
            message="Hospitals retrieved successfully",
            items=hospital_list
        )
    """
    if count is None:
        count = len(items)
    
    return success_response(
        message=message,
        data={
            "items": items,
            "count": count
        }
    )


def message_only_response(message: str) -> Dict[str, Any]:
    """
    Create a response with only a message (no data payload).
    
    Args:
        message: Human-readable message
    
    Returns:
        Standardized message-only response
    
    Example:
        return message_only_response("Password changed successfully")
    """
    return success_response(
        message=message,
        data={"status": "success"}
    )


# Migration helpers for legacy response formats
def migrate_dict_response(legacy_dict: Dict[str, Any], message: str) -> Dict[str, Any]:
    """
    Migrate a legacy dictionary response to standardized format.
    
    Args:
        legacy_dict: Existing dictionary response
        message: Message to use in standardized response
    
    Returns:
        Standardized response wrapping the legacy data
    """
    return success_response(message=message, data=legacy_dict)


def migrate_list_response(legacy_list: List[Any], message: str) -> Dict[str, Any]:
    """
    Migrate a legacy list response to standardized format.
    
    Args:
        legacy_list: Existing list response
        message: Message to use in standardized response
    
    Returns:
        Standardized list response
    """
    return list_response(message=message, items=legacy_list)


def migrate_message_response(legacy_message: str) -> Dict[str, Any]:
    """
    Migrate a legacy string message to standardized format.
    
    Args:
        legacy_message: Existing string message
    
    Returns:
        Standardized message response
    """
    return message_only_response(legacy_message)