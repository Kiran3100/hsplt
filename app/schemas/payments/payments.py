from pydantic import BaseModel
from typing import Optional, Any


# -----------------------------
# Client → API payment request
# -----------------------------
class PaymentCreate(BaseModel):
    amount: float                # API accepts float; gateway converts to paise/cents
    currency: str = "INR"
    gateway: str = "razorpay"
    receipt_id: Optional[str] = None


# -----------------------------
# API → Client payment response
# -----------------------------
class PaymentResponse(BaseModel):
    transaction_id: int
    order_id: str
    gateway: str
    amount: float
    currency: str
    data: Any                    # gateway order response
