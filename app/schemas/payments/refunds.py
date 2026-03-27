from pydantic import BaseModel
from typing import Optional


class RefundRequest(BaseModel):
    amount: int                 # paise/cents expected in your service layer
    reason: Optional[str] = None
