from datetime import datetime

from pydantic import BaseModel


class ChatMessageCreate(BaseModel):
    content: str


class ChatMessageResponse(BaseModel):
    id: int
    writer_id: int
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
