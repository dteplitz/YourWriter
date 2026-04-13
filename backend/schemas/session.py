from typing import Any, Literal

from pydantic import BaseModel, Field

from backend.schemas.identity import IdentityResponse


class SessionImportChange(BaseModel):
    field: str
    action: Literal["add", "modify", "remove"]
    key: str | None = None
    old_value: Any = None
    new_value: Any = None
    value: Any = None
    reason: str = ""


class SessionImportPlan(BaseModel):
    changes: list[SessionImportChange] = Field(default_factory=list)
    overall_reasoning: str = ""


class SessionImportProposalResponse(BaseModel):
    session_id: int
    writer_id: int
    lifecycle: Literal["complete"]
    changes: list[SessionImportChange]
    reasoning: str


class SessionImportRequest(BaseModel):
    changes: list[SessionImportChange] = Field(default_factory=list)
    reasoning: str = ""


class SessionImportResponse(BaseModel):
    session_id: int
    writer_id: int
    lifecycle: Literal["imported"]
    imported_changes: list[SessionImportChange]
    reasoning: str
    identity: IdentityResponse


class SessionSkipResponse(BaseModel):
    session_id: int
    writer_id: int
    lifecycle: Literal["skipped"]
