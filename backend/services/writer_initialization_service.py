from __future__ import annotations

import os

from fastapi import HTTPException, status
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession

from agents.prompts.system import WRITER_INITIALIZATION_PROMPT
from backend.config import settings
from backend.db.models import Writer, WriterIdentity
from backend.schemas.writer_initialization import (
    WriterCreateFromPreviewRequest,
    WriterInitializationPreviewResponse,
)


_DEFAULT_EMOTIONS: dict[str, float] = {
    "curiosity": 0.62,
    "warmth": 0.42,
    "melancholy": 0.28,
}


def _trim_text(value: str, fallback: str) -> str:
    cleaned = value.strip()
    return cleaned or fallback


def _normalize_string_dict(data: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in data.items():
        clean_key = str(key).strip()
        clean_value = str(value).strip()
        if clean_key and clean_value:
            normalized[clean_key] = clean_value
    return normalized


def _normalize_string_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for value in values:
        cleaned = str(value).strip()
        lowered = cleaned.casefold()
        if cleaned and lowered not in seen:
            seen.add(lowered)
            normalized.append(cleaned)
    return normalized


def _normalize_emotions(data: dict[str, float]) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for key, value in data.items():
        clean_key = str(key).strip()
        if not clean_key:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        normalized[clean_key] = max(0.0, min(1.0, numeric))
    return normalized or dict(_DEFAULT_EMOTIONS)


def _normalize_preview(
    preview: WriterInitializationPreviewResponse,
) -> WriterInitializationPreviewResponse:
    name = _trim_text(preview.name, "Untitled Writer")
    purpose = _trim_text(
        preview.purpose,
        "Develop a distinct writing voice in collaboration with the user.",
    )
    summary = _trim_text(
        preview.summary,
        "A writer with a clear voice and room to keep evolving through collaboration.",
    )

    return WriterInitializationPreviewResponse(
        summary=summary,
        name=name,
        purpose=purpose,
        personality=_normalize_string_dict(preview.personality),
        emotions=_normalize_emotions(preview.emotions),
        topics=_normalize_string_list(preview.topics),
        constraints=_normalize_string_dict(preview.constraints),
        lifelong_objectives=_normalize_string_list(preview.lifelong_objectives),
    )


async def generate_writer_preview(description: str) -> WriterInitializationPreviewResponse:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set")

    llm = ChatAnthropic(  # type: ignore[call-arg]
        model=settings.writing_model,
        max_tokens=1400,
    )
    structured_llm = llm.with_structured_output(WriterInitializationPreviewResponse)

    try:
        preview = await structured_llm.ainvoke(
            [
                SystemMessage(content=WRITER_INITIALIZATION_PROMPT),
                HumanMessage(content=description.strip()),
            ]
        )
    except Exception as exc:  # pragma: no cover - exercised through route tests with monkeypatch
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate writer preview",
        ) from exc

    return _normalize_preview(preview)


async def create_writer_from_preview(
    db: AsyncSession,
    *,
    user_id: int,
    body: WriterCreateFromPreviewRequest,
) -> Writer:
    preview = _normalize_preview(
        WriterInitializationPreviewResponse.model_validate(body.model_dump())
    )

    writer = Writer(
        user_id=user_id,
        name=preview.name,
        purpose=preview.purpose,
    )
    db.add(writer)
    await db.flush()

    identity = WriterIdentity(
        writer_id=writer.id,
        personality=preview.personality,
        emotions=preview.emotions,
        memories=[],
        topics=preview.topics,
        constraints=preview.constraints,
        lifelong_objectives=preview.lifelong_objectives,
        version=1,
    )
    db.add(identity)
    await db.flush()
    await db.refresh(writer)
    return writer
