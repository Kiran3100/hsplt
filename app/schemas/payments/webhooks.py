from pydantic import BaseModel


class WebhookAck(BaseModel):
    ok: bool
    message: str
