"""Chat service — bridges the backend API with the LangGraph agent layer."""

import os
from collections.abc import AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import ChatMessage, MessageRole, Writer, WriterIdentity


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
    """Invoke the writer agent graph and return the assistant response text.

    Raises RuntimeError if ANTHROPIC_API_KEY is not set.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set")

    # Lazy import to avoid loading the agent layer at module import time
    from agents.graphs.writer_graph import writer_graph

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

    # Invoke the graph
    result = await writer_graph.ainvoke(state)

    # Extract the last assistant message
    result_messages = result.get("messages", [])
    for msg in reversed(result_messages):
        if msg.get("role") == "assistant":
            return msg["content"]

    return "[No response generated]"


async def stream_writer_agent(
    db: AsyncSession,
    writer: Writer,
    user_message: str,
) -> AsyncIterator[str]:
    """Stream the writer agent response as text chunks.

    Yields text chunks for chat-mode responses. Falls back to a single
    chunk for write-mode (streaming write pipeline is Sprint 2b).

    After all chunks are yielded, the caller is responsible for persisting
    the complete response.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set")

    from agents.graphs.writer_graph import detect_intent_node  # noqa: E402
    from agents.nodes.chat_node import chat_node_stream  # noqa: E402

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

    # Load chat history
    history = await _load_history(db, writer.id)
    messages = history + [{"role": "user", "content": user_message}]

    state = {
        "messages": messages,
        "writer_id": str(writer.id),
        "writer_name": writer.name,
        "identity": identity_dict,
        "constraints": identity_dict.get("constraints", {}),
    }

    # Detect intent
    intent_result = await detect_intent_node(state)
    mode = intent_result.get("mode", "chat")

    if mode == "chat":
        async for chunk in chat_node_stream(state):
            yield chunk
    else:
        # Write mode: fall back to non-streaming (Sprint 2b)
        response_text = await invoke_writer_agent(db, writer, user_message)
        yield response_text
