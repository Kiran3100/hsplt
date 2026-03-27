"""Receipt response."""
from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class ReceiptResponse(BaseModel):
    id: UUID
    payment_id: UUID
    receipt_number: str
    pdf_path: Optional[str]
    emailed_to: Optional[str]
    is_duplicate: bool
    created_at: datetime

    class Config:
        from_attributes = True
