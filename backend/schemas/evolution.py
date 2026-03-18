from datetime import datetime

from pydantic import BaseModel

from backend.schemas.identity import IdentityResponse


class EvolutionLogResponse(BaseModel):
    id: int
    writer_id: int
    field_changed: str
    old_value: str | None
    new_value: str | None
    reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RollbackResponse(BaseModel):
    writer_id: int
    rolled_back_to_version: int
    new_version: int
    identity: IdentityResponse
