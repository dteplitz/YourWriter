from datetime import datetime
from typing import Any

from pydantic import BaseModel


class IdentityResponse(BaseModel):
    id: int
    writer_id: int
    personality: dict[str, Any]
    emotions: dict[str, Any]
    memories: list[Any]
    topics: list[Any]
    constraints: dict[str, Any]
    lifelong_objectives: list[Any]
    version: int
    created_at: datetime

    model_config = {"from_attributes": True}


class IdentityUpdate(BaseModel):
    personality: dict[str, Any] | None = None
    emotions: dict[str, Any] | None = None
    memories: list[Any] | None = None
    topics: list[Any] | None = None
    lifelong_objectives: list[Any] | None = None


class ConstraintsUpdate(BaseModel):
    constraints: dict[str, Any]
