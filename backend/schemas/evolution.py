from datetime import datetime

from pydantic import BaseModel


class EvolutionLogResponse(BaseModel):
    id: int
    writer_id: int
    field_changed: str
    old_value: str | None
    new_value: str | None
    reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
