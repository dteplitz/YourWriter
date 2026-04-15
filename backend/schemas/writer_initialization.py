from __future__ import annotations

from pydantic import BaseModel, Field


class WriterInitializationRequest(BaseModel):
    description: str = Field(min_length=1)


class WriterInitializationPreviewResponse(BaseModel):
    summary: str
    name: str
    purpose: str
    personality: dict[str, str] = Field(default_factory=dict)
    emotions: dict[str, float] = Field(default_factory=dict)
    topics: list[str] = Field(default_factory=list)
    constraints: dict[str, str] = Field(default_factory=dict)
    lifelong_objectives: list[str] = Field(default_factory=list)


class WriterCreateFromPreviewRequest(WriterInitializationPreviewResponse):
    pass
