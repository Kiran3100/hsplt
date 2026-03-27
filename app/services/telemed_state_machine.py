"""
Telemedicine session state machine.
Enforces valid status transitions in one place.
"""
from typing import Set, Tuple
from fastapi import HTTPException, status

# Allowed transitions: (from_status, to_status)
ALLOWED_TRANSITIONS: Set[Tuple[str, str]] = {
    ("SCHEDULED", "READY"),
    ("SCHEDULED", "IN_PROGRESS"),
    ("SCHEDULED", "CANCELLED"),
    ("READY", "IN_PROGRESS"),
    ("READY", "CANCELLED"),
    ("IN_PROGRESS", "ENDED"),
}
TERMINAL_STATUSES = {"ENDED", "CANCELLED", "EXPIRED"}


def can_transition(from_status: str, to_status: str) -> bool:
    """Check if transition is allowed."""
    return (from_status, to_status) in ALLOWED_TRANSITIONS


def validate_transition(from_status: str, to_status: str) -> None:
    """
    Validate transition. Raises HTTPException 409 with INVALID_SESSION_TRANSITION if invalid.
    """
    if from_status in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "INVALID_SESSION_TRANSITION", "message": f"Cannot transition from terminal status {from_status}"},
        )
    if not can_transition(from_status, to_status):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "INVALID_SESSION_TRANSITION", "message": f"Invalid transition: {from_status} -> {to_status}"},
        )
