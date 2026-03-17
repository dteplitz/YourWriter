from datetime import datetime

from pydantic import BaseModel


class BriefRequest(BaseModel):
    message: str


class BriefResponse(BaseModel):
    format: str
    tone: str
    constraints_applied: list[str]
    word_limit: int | None = None
    notes: str | None = None
    needs_clarification: bool = False
    clarification_question: str | None = None


class PieceResponse(BaseModel):
    id: int
    writer_id: int
    title: str
    content: str
    format: str
    word_count: int
    created_at: datetime

    model_config = {"from_attributes": True}
