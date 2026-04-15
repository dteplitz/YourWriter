"""Read-side helpers for Studio sessions UI (Slice 4)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import session_repository
from backend.db.models import StudioSession, StudioTake
from backend.schemas.session import (
    SessionAbandonResponse,
    SessionDetailResponse,
    SessionSummaryItemResponse,
    SessionTakeDetailResponse,
    SessionTakeSummaryResponse,
    WriterSessionsSummaryResponse,
)
from backend.services.writer_service import get_writer


class SessionQueryError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _word_count(content: str | None) -> int:
    if not content:
        return 0
    return len(content.split())


def _truncate(text: str, limit: int = 90) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def _build_brief_preview(brief_json: dict[str, Any]) -> str:
    notes = str(brief_json.get("notes") or "").strip()
    fmt = str(brief_json.get("format") or "").strip()
    tone = str(brief_json.get("tone") or "").strip()
    word_limit = brief_json.get("word_limit")

    parts: list[str] = []
    if notes:
        parts.append(_truncate(notes))
    if fmt:
        parts.append(fmt)
    if tone:
        parts.append(f"tono {tone}")
    if word_limit:
        parts.append(f"{word_limit} palabras")

    return " · ".join(parts) if parts else "Sesion de Studio"


def _serialize_take_summary(take: StudioTake | None) -> SessionTakeSummaryResponse | None:
    if take is None:
        return None
    return SessionTakeSummaryResponse(
        id=take.id,
        take_number=take.take_number,
        title=take.title,
        word_count=_word_count(take.content),
        created_at=take.created_at,
    )


async def _resolve_resume_mode(session: StudioSession) -> str | None:
    if session.lifecycle != "active":
        return None

    from agents.graphs import build_studio_graph, open_studio_checkpointer, studio_checkpointer_enabled

    if not studio_checkpointer_enabled():
        return "artifact" if session.takes and session.takes[-1].content else None

    async with open_studio_checkpointer() as checkpointer:
        graph = build_studio_graph().compile(checkpointer=checkpointer)
        snapshot = await graph.aget_state({"configurable": {"thread_id": str(session.id)}})

    if getattr(snapshot, "next", ()):
        return "checkpoint"
    if session.takes and session.takes[-1].content:
        return "artifact"
    return None


def _serialize_summary(session: StudioSession) -> SessionSummaryItemResponse:
    last_take = session.takes[-1] if session.takes else None
    return SessionSummaryItemResponse(
        id=session.id,
        writer_id=session.writer_id,
        lifecycle=session.lifecycle,
        brief_preview=_build_brief_preview(session.brief_json or {}),
        take_count=len(session.takes),
        created_at=session.created_at,
        updated_at=session.updated_at,
        last_take=_serialize_take_summary(last_take),
    )


def _pick_highlight(history: list[SessionSummaryItemResponse]) -> SessionSummaryItemResponse | None:
    for lifecycle in ("active", "complete"):
        for item in history:
            if item.lifecycle == lifecycle:
                return item
    return None


async def get_writer_sessions_summary(
    db: AsyncSession,
    *,
    writer_id: int,
    user_id: int,
) -> WriterSessionsSummaryResponse:
    await get_writer(db, writer_id=writer_id, user_id=user_id)

    sessions = await session_repository.list_sessions_for_writer(db, writer_id)
    history = [_serialize_summary(session) for session in sessions]
    return WriterSessionsSummaryResponse(
        highlight=_pick_highlight(history),
        history=history,
    )


async def get_session_detail(
    db: AsyncSession,
    *,
    session_id: int,
    user_id: int,
) -> SessionDetailResponse:
    session = await session_repository.get_owned_session_with_takes(db, session_id)
    if session is None or session.writer is None or session.writer.user_id != user_id:
        raise SessionQueryError(status_code=404, detail="Session not found")

    resume_mode = await _resolve_resume_mode(session)

    return SessionDetailResponse(
        id=session.id,
        writer_id=session.writer_id,
        lifecycle=session.lifecycle,
        resume_mode=resume_mode,
        brief=session.brief_json,
        brief_preview=_build_brief_preview(session.brief_json or {}),
        take_count=len(session.takes),
        created_at=session.created_at,
        updated_at=session.updated_at,
        takes=[
            SessionTakeDetailResponse(
                id=take.id,
                take_number=take.take_number,
                title=take.title,
                content=take.content,
                word_count=_word_count(take.content),
                iteration_notes=take.iteration_notes,
                created_at=take.created_at,
            )
            for take in session.takes
        ],
    )


async def abandon_session(
    db: AsyncSession,
    *,
    session_id: int,
    user_id: int,
) -> SessionAbandonResponse:
    session = await session_repository.get_owned_session_with_takes(db, session_id)
    if session is None or session.writer is None or session.writer.user_id != user_id:
        raise SessionQueryError(status_code=404, detail="Session not found")
    if session.lifecycle != "active":
        raise SessionQueryError(
            status_code=409,
            detail=f"Session {session.id} must be active before abandoning",
        )

    await session_repository.advance_lifecycle(db, session_id, "abandoned")
    return SessionAbandonResponse(
        session_id=session.id,
        writer_id=session.writer_id,
        lifecycle="abandoned",
    )
