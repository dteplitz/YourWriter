from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from backend.schemas.identity import IdentityResponse
from backend.schemas.studio import BriefResponse


SessionLifecycle = Literal["active", "complete", "imported", "skipped", "abandoned"]
SessionResumeMode = Literal["checkpoint", "artifact"]


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


class SessionTakeSummaryResponse(BaseModel):
    id: int
    take_number: int
    title: str | None = None
    word_count: int
    created_at: datetime


class SessionSummaryItemResponse(BaseModel):
    id: int
    writer_id: int
    lifecycle: SessionLifecycle
    brief_preview: str
    take_count: int
    created_at: datetime
    updated_at: datetime
    last_take: SessionTakeSummaryResponse | None = None


class WriterSessionsSummaryResponse(BaseModel):
    highlight: SessionSummaryItemResponse | None = None
    history: list[SessionSummaryItemResponse] = Field(default_factory=list)


class SessionTakeDetailResponse(BaseModel):
    id: int
    take_number: int
    title: str | None = None
    content: str
    word_count: int
    iteration_notes: str | None = None
    created_at: datetime


class SessionDetailResponse(BaseModel):
    id: int
    writer_id: int
    lifecycle: SessionLifecycle
    resume_mode: SessionResumeMode | None = None
    brief: BriefResponse
    brief_preview: str
    take_count: int
    created_at: datetime
    updated_at: datetime
    takes: list[SessionTakeDetailResponse] = Field(default_factory=list)


class SessionAbandonResponse(BaseModel):
    session_id: int
    writer_id: int
    lifecycle: Literal["abandoned"]
