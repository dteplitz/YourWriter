"""Chat service — bridges the backend API with the LangGraph agent layer."""

import os
import re
from collections.abc import AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import ChatMessage, MessageRole, Writer, WriterIdentity, WriterPiece
from backend.schemas.studio import BriefResponse


MAX_HISTORY_MESSAGES = 50


def _identity_to_agent_state(identity: WriterIdentity) -> dict:
    """Convert a DB WriterIdentity row into the dict format the agent expects."""
    personality = identity.personality or {}
    emotions = identity.emotions or {}

    # The agent expects personality/emotions as lists of strings for join().
    # DB stores them as dicts like {"voice": "neutral", "creativity": 0.7}.
    # Flatten: "voice: neutral", "creativity: 0.7"
    personality_list = [
        f"{k}: {v}" for k, v in personality.items()
    ] if isinstance(personality, dict) else list(personality)

    emotions_list = [
        f"{k}: {v}" for k, v in emotions.items()
    ] if isinstance(emotions, dict) else list(emotions)

    return {
        "purpose": "",  # filled from writer.purpose
        "personality": personality_list,
        "emotions": emotions_list,
        "constraints": identity.constraints or {},
        "lifelong_objectives": identity.lifelong_objectives or [],
    }


async def _load_history(db: AsyncSession, writer_id: int) -> list[dict[str, str]]:
    """Load recent chat messages as dicts for the agent state."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.writer_id == writer_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(MAX_HISTORY_MESSAGES)
    )
    rows = list(result.scalars().all())
    rows.reverse()  # oldest first
    return [{"role": msg.role.value, "content": msg.content} for msg in rows]


async def invoke_writer_agent(
    db: AsyncSession,
    writer: Writer,
    user_message: str,
) -> str:
    """Invoke the writer agent in conversational (Artist Profile) mode.

    Always uses the chat path — the writing pipeline is never triggered
    from the Artist Profile chat.

    Raises RuntimeError if ANTHROPIC_API_KEY is not set.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set")

    from agents.nodes.chat_node import chat_node  # noqa: E402

    # Load latest identity
    identity_row: WriterIdentity | None = None
    if writer.identities:
        identity_row = max(writer.identities, key=lambda i: i.version)

    identity_dict = _identity_to_agent_state(identity_row) if identity_row else {
        "purpose": writer.purpose,
        "personality": ["thoughtful"],
        "emotions": ["calm"],
        "constraints": {},
        "lifelong_objectives": [],
    }
    identity_dict["purpose"] = writer.purpose

    # Load chat history (excluding the just-persisted user message)
    history = await _load_history(db, writer.id)

    # Append the new user message to history for the agent
    messages = history + [{"role": "user", "content": user_message}]

    # Build agent state
    state = {
        "messages": messages,
        "writer_id": str(writer.id),
        "writer_name": writer.name,
        "identity": identity_dict,
        "constraints": identity_dict.get("constraints", {}),
    }

    # Always conversational — no intent detection, no writing pipeline
    result = await chat_node(state)

    # Extract the last assistant message
    result_messages = result.get("messages", [])
    for msg in reversed(result_messages):
        if msg.get("role") == "assistant":
            return msg["content"]

    return "[No response generated]"


async def stream_writer_agent(
    writer: Writer,
    user_message: str,
) -> AsyncIterator[str | dict]:
    """Stream the writer agent response as text chunks (Artist Profile chat).

    Always uses the conversational path — the writing pipeline is never
    triggered from the Artist Profile chat.

    Manages its own short-lived DB session for loading history so the
    caller does not need to hold a connection open during the LLM call.

    Yields:
      - str: text token for the client to display
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set")

    from agents.nodes.chat_node import chat_node_stream  # noqa: E402
    from backend.db.database import async_session  # noqa: E402

    # Load latest identity
    identity_row: WriterIdentity | None = None
    if writer.identities:
        identity_row = max(writer.identities, key=lambda i: i.version)

    identity_dict = _identity_to_agent_state(identity_row) if identity_row else {
        "purpose": writer.purpose,
        "personality": ["thoughtful"],
        "emotions": ["calm"],
        "constraints": {},
        "lifelong_objectives": [],
    }
    identity_dict["purpose"] = writer.purpose

    # Load chat history in a short-lived session, then release
    async with async_session() as db:
        history = await _load_history(db, writer.id)

    messages = history + [{"role": "user", "content": user_message}]

    state = {
        "messages": messages,
        "writer_id": str(writer.id),
        "writer_name": writer.name,
        "identity": identity_dict,
        "constraints": identity_dict.get("constraints", {}),
    }

    # Always conversational — no intent detection, stream directly
    async for chunk in chat_node_stream(state):
        yield chunk


async def generate_brief(writer: Writer, message: str) -> BriefResponse:
    """Parse a free-text user request into a structured BriefResponse.

    Calls Claude to interpret the request in the context of the writer's
    identity and constraints.  If the response cannot be parsed, returns
    sensible defaults rather than raising.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set")

    from langchain_anthropic import ChatAnthropic  # noqa: E402
    from langchain_core.messages import HumanMessage, SystemMessage  # noqa: E402

    from agents.prompts.system import BRIEF_GENERATION_PROMPT  # noqa: E402
    from agents.tools.constraints import format_constraints_for_prompt  # noqa: E402
    from backend.config import settings  # noqa: E402

    # Load latest identity
    identity_row: WriterIdentity | None = None
    if writer.identities:
        identity_row = max(writer.identities, key=lambda i: i.version)

    identity_dict = _identity_to_agent_state(identity_row) if identity_row else {
        "purpose": writer.purpose,
        "personality": ["thoughtful"],
        "emotions": ["calm"],
        "constraints": {},
        "lifelong_objectives": [],
    }
    identity_dict["purpose"] = writer.purpose

    constraints = identity_dict.get("constraints", {})
    personality_list = identity_dict.get("personality", [])

    prompt = BRIEF_GENERATION_PROMPT.format(
        name=writer.name,
        purpose=identity_dict["purpose"],
        personality=", ".join(personality_list) if personality_list else "thoughtful",
        constraints=format_constraints_for_prompt(constraints),
        message=message,
    )

    llm = ChatAnthropic(  # type: ignore[call-arg]
        model=settings.writing_model,
        max_tokens=1024,
    )
    structured_llm = llm.with_structured_output(BriefResponse)

    try:
        return await structured_llm.ainvoke(
            [
                SystemMessage(content="You are a writing production assistant."),
                HumanMessage(content=prompt),
            ]
        )
    except Exception:
        # Fallback: return sensible defaults rather than raising
        return BriefResponse(
            format="other",
            tone="neutral",
            constraints_applied=[],
            word_limit=None,
            notes=message if message else None,
            needs_clarification=True,
            clarification_question="Could you describe what you'd like to write in more detail?",
        )


async def stream_studio_session(
    writer: Writer,
    brief: BriefResponse,
    session_id: int | None = None,
    iteration_notes: str | None = None,
) -> AsyncIterator[str | dict]:
    """Run the Studio writing pipeline for a brief and stream tokens.

    Does NOT load or save chat history — each Studio session starts fresh.

    On the first call (session_id=None) a StudioSession is created and the
    session_id is yielded as {"session_started": {"session_id": N}} before
    the pipeline starts. On subsequent calls the existing session is reused
    and a new StudioTake is linked to it.

    Yields:
      - dict: {"session_started": {"session_id": N}} (first call only)
      - dict: phase events like {"phase": "outlining"}
      - str: text token from the refine stream
      - dict: final piece event {"piece": {...}} after the stream ends
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set")

    from agents.nodes.research_node import research_node_stream  # noqa: E402
    from agents.nodes.writing_nodes import (  # noqa: E402
        outline_node,
        draft_node,
        studio_refine_node_stream,
    )
    from backend.db.database import async_session  # noqa: E402
    from backend.db import session_repository  # noqa: E402

    # --- Session + take bookkeeping (short-lived DB session before LLM calls) ---
    async with async_session() as db:
        if session_id is None:
            studio_session = await session_repository.create_session(
                db,
                writer_id=writer.id,
                brief_json=brief.model_dump(),
            )
            session_id = studio_session.id
            await db.commit()
            yield {"session_started": {"session_id": session_id}}

        # Ownership check + 404 for supplied session_id
        existing = await session_repository.get_session_with_takes(db, session_id)
        if existing is None:
            raise ValueError(f"Session {session_id} not found")
        if existing.writer_id != writer.id:
            raise PermissionError(f"Session {session_id} does not belong to this writer")
        take_number = len(existing.takes) + 1

        take = await session_repository.create_take(
            db,
            session_id=session_id,
            take_number=take_number,
            iteration_notes=iteration_notes,
        )
        take_id = take.id
        await db.commit()

    # Load latest identity (no DB session held during LLM calls)
    identity_row: WriterIdentity | None = None
    if writer.identities:
        identity_row = max(writer.identities, key=lambda i: i.version)

    identity_dict = _identity_to_agent_state(identity_row) if identity_row else {
        "purpose": writer.purpose,
        "personality": ["thoughtful"],
        "emotions": ["calm"],
        "constraints": {},
        "lifelong_objectives": [],
    }
    identity_dict["purpose"] = writer.purpose

    # Build the studio request from the brief.
    # iteration_notes is kept separate from brief.notes (which is the original brief snapshot).
    studio_request = f"Write a {brief.format} with tone: {brief.tone}."
    if brief.word_limit:
        studio_request += f" Word limit: {brief.word_limit}."
    if brief.notes:
        studio_request += f" Notes: {brief.notes}"
    if iteration_notes:
        studio_request += f" Producer notes for this take: {iteration_notes}"

    state: dict = {
        "messages": [{"role": "user", "content": studio_request}],
        "writer_id": str(writer.id),
        "writer_name": writer.name,
        "identity": identity_dict,
        "constraints": identity_dict.get("constraints", {}),
    }

    # Research phase: web search if the request needs current information
    async for event in research_node_stream(state):
        if "search_results" in event:
            if event["search_results"]:
                state["search_results"] = event["search_results"]
        else:
            yield event  # forward tool_use / tool_result to SSE stream

    # Outline
    yield {"phase": "outlining"}
    outline_result = await outline_node(state)
    state.update(outline_result)

    # Draft
    yield {"phase": "drafting"}
    draft_result = await draft_node(state)
    state.update(draft_result)

    # Refine (streaming) — accumulate buffer while yielding tokens
    yield {"phase": "refining"}
    buffer = ""
    async for token in studio_refine_node_stream(state):
        buffer += token
        yield token

    # Parse title from buffer: ---TITLE: <title>---
    title_pattern = re.compile(r"\n---TITLE:\s*(.+?)---\s*$", re.DOTALL)
    match = title_pattern.search(buffer)
    if match:
        title = match.group(1).strip()
        content = buffer[: match.start()].rstrip()
    else:
        title = "Untitled"
        content = buffer

    word_count = len(content.split()) if content.strip() else 0

    # Save piece + update take in short-lived sessions (never hold DB during LLM calls)
    async with async_session() as db:
        piece = WriterPiece(
            writer_id=writer.id,
            title=title,
            content=content,
            format=brief.format,
            word_count=word_count,
        )
        db.add(piece)
        await db.flush()
        await db.refresh(piece)

        await session_repository.update_take_content(db, take_id, content, title)
        await db.commit()

    yield {
        "piece": {
            "id": piece.id,
            "title": title,
            "content": content,
            "format": brief.format,
            "word_count": word_count,
        }
    }
