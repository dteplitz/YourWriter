from datetime import datetime
from typing import Any

from pydantic import BaseModel

from backend.schemas.identity import IdentityResponse


class WriterCreate(BaseModel):
    name: str
    purpose: str = ""
    style_description: str = ""


class WriterUpdate(BaseModel):
    name: str | None = None
    purpose: str | None = None


class WriterResponse(BaseModel):
    id: int
    user_id: int
    name: str
    purpose: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WriterWithIdentity(WriterResponse):
    identity: IdentityResponse | None = None
