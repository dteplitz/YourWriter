"""Service layer for the explicit post-session import flow."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from agents.evolution.identity import Identity
from agents.nodes.evolution_nodes import apply_node
from agents.prompts.system import SESSION_IMPORT_PROMPT
from backend.config import settings
from backend.db import session_repository
from backend.db.database import async_session
from backend.db.models import StudioSession, Writer, WriterIdentity
from backend.schemas.identity import IdentityResponse
from backend.schemas.session import (
    SessionImportPlan,
    SessionImportProposalResponse,
    SessionImportRequest,
    SessionImportResponse,
    SessionSkipResponse,
)
from backend.services.evolution_service import persist_identity_changes


logger = logging.getLogger(__name__)

_EMPTY_PROPOSAL_REASONING = "No durable learning detected from this Studio session."


class SessionImportError(Exception):
    """Domain error with explicit HTTP semantics for the sessions router."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass
class SessionImportContext:
    session: StudioSession
    writer: Writer
    identity: WriterIdentity


def _build_current_identity(writer: Writer, identity: WriterIdentity) -> dict[str, Any]:
    return {
        "purpose": writer.purpose,
        "personality": identity.personality or {},
        "emotions": identity.emotions or {},
        "memories": identity.memories or [],
        "topics": identity.topics or [],
        "constraints": identity.constraints or {},
        "lifelong_objectives": identity.lifelong_objectives or [],
    }


def _format_session_takes(session: StudioSession) -> str:
    if not session.takes:
        return "(no takes recorded)"

    blocks: list[str] = []
    for take in session.takes:
        lines = [f"Take {take.take_number}"]
        if take.iteration_notes:
            lines.append(f"Iteration notes: {take.iteration_notes}")
        if take.title:
            lines.append(f"Title: {take.title}")
        lines.append("Content:")
        lines.append(take.content or "(empty)")
        blocks.append("\n".join(lines))
    return "\n\n---\n\n".join(blocks)


async def _load_session_context(
    db: AsyncSession,
    session_id: int,
    user_id: int,
) -> SessionImportContext:
    result = await db.execute(
        select(StudioSession)
        .where(StudioSession.id == session_id)
        .options(
            selectinload(StudioSession.takes),
            joinedload(StudioSession.writer).selectinload(Writer.identities),
        )
    )
    session = result.unique().scalar_one_or_none()

    if session is None or session.writer is None or session.writer.user_id != user_id:
        raise SessionImportError(status_code=404, detail="Session not found")

    if not session.writer.identities:
        raise SessionImportError(status_code=404, detail="Identity not found for this writer")

    identity = max(session.writer.identities, key=lambda row: row.version)
    return SessionImportContext(session=session, writer=session.writer, identity=identity)


def _ensure_proposal_lifecycle(session: StudioSession) -> None:
    if session.lifecycle in {"active", "complete"}:
        return
    raise SessionImportError(
        status_code=409,
        detail=f"Session {session.id} is not eligible for import proposal from lifecycle '{session.lifecycle}'",
    )


def _ensure_complete_lifecycle(session: StudioSession, action: str) -> None:
    if session.lifecycle != "complete":
        raise SessionImportError(
            status_code=409,
            detail=f"Session {session.id} must be complete before {action}",
        )


async def _generate_import_plan(
    *,
    current_identity: dict[str, Any],
    brief_json: dict[str, Any],
    takes_text: str,
) -> SessionImportPlan:
    identity_text = Identity.from_dict(current_identity).to_prompt_string()
    prompt = SESSION_IMPORT_PROMPT.format(
        current_identity=identity_text,
        session_brief=json.dumps(brief_json, ensure_ascii=False, indent=2),
        session_takes=takes_text,
    )

    llm = ChatAnthropic(model=settings.evolution_compute_model)  # type: ignore[call-arg]
    structured_llm = llm.with_structured_output(SessionImportPlan)
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content="Return the durable identity changes for this Studio session."),
    ]

    try:
        return await structured_llm.ainvoke(messages)
    except Exception:
        logger.warning("session import proposal failed; returning empty proposal", exc_info=True)
        return SessionImportPlan(
            changes=[],
            overall_reasoning=_EMPTY_PROPOSAL_REASONING,
        )


async def generate_import_proposal(
    session_id: int,
    user_id: int,
) -> SessionImportProposalResponse:
    """Generate a structured import proposal for a completed Studio session."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set")

    async with async_session() as db:
        context = await _load_session_context(db, session_id, user_id)
        _ensure_proposal_lifecycle(context.session)

        if context.session.lifecycle == "active":
            await session_repository.advance_lifecycle(db, session_id, "complete")
            await db.commit()
            context.session.lifecycle = "complete"

    current_identity = _build_current_identity(context.writer, context.identity)
    plan = await _generate_import_plan(
        current_identity=current_identity,
        brief_json=context.session.brief_json,
        takes_text=_format_session_takes(context.session),
    )

    return SessionImportProposalResponse(
        session_id=context.session.id,
        writer_id=context.writer.id,
        lifecycle="complete",
        changes=plan.changes,
        reasoning=plan.overall_reasoning or _EMPTY_PROPOSAL_REASONING,
    )


async def apply_session_import(
    session_id: int,
    user_id: int,
    body: SessionImportRequest,
) -> SessionImportResponse:
    """Apply the user-selected subset of a session import proposal."""
    selected_changes = [change.model_dump(exclude_none=True) for change in body.changes]
    if not selected_changes:
        raise SessionImportError(status_code=400, detail="At least one change must be selected for import")

    async with async_session() as db:
        context = await _load_session_context(db, session_id, user_id)
        _ensure_complete_lifecycle(context.session, "importing")

        current_identity = _build_current_identity(context.writer, context.identity)
        apply_result = await apply_node(
            {
                "current_identity": current_identity,
                "changes": selected_changes,
            }
        )
        updated_identity = apply_result["updated_identity"]

        new_identity = await persist_identity_changes(
            db=db,
            writer_id=context.writer.id,
            changes=selected_changes,
            updated_identity=updated_identity,
            reason_prefix=f"[post_session_import session_id={session_id}]",
        )
        await session_repository.advance_lifecycle(db, session_id, "imported")
        await db.commit()

        return SessionImportResponse(
            session_id=context.session.id,
            writer_id=context.writer.id,
            lifecycle="imported",
            imported_changes=body.changes,
            reasoning=body.reasoning,
            identity=IdentityResponse.model_validate(new_identity),
        )


async def skip_session_import(
    session_id: int,
    user_id: int,
) -> SessionSkipResponse:
    """Explicitly skip importing anything from a completed Studio session."""
    async with async_session() as db:
        context = await _load_session_context(db, session_id, user_id)
        _ensure_complete_lifecycle(context.session, "skipping")

        await session_repository.advance_lifecycle(db, session_id, "skipped")
        await db.commit()

        return SessionSkipResponse(
            session_id=context.session.id,
            writer_id=context.writer.id,
            lifecycle="skipped",
        )
