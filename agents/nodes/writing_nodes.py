"""Writing pipeline nodes — outline, draft, and refine.

These nodes form the core content-generation pipeline:
  outline_node  →  draft_node  →  refine_node

Each node calls Claude via ChatAnthropic with a specialised prompt and
updates the relevant field in WriterState. Model id comes from
backend.config.settings.writing_model — never hardcoded here.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from agents.prompts.system import (
    OUTLINE_PROMPT,
    REFINE_PROMPT,
    STUDIO_REFINE_PROMPT,
    WRITER_SYSTEM_PROMPT,
)
from agents.tools.constraints import (
    format_constraints_for_prompt,
    validate_constraints,
)
from backend.config import settings


_MAX_TOKENS = 8192


def _make_llm() -> ChatAnthropic:
    return ChatAnthropic(  # type: ignore[call-arg]
        model=settings.writing_model,
        max_tokens=_MAX_TOKENS,
    )


def _content_to_text(content: Any) -> str:
    """Coerce a LangChain message content payload to plain text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)
    return ""


async def _call_claude(system: str, user_message: str) -> str:
    """Helper: send a single user message with a system prompt to Claude."""
    response = await _make_llm().ainvoke(
        [SystemMessage(content=system), HumanMessage(content=user_message)]
    )
    return _content_to_text(response.content)


async def _stream_claude(system: str, user_message: str) -> AsyncIterator[str]:
    """Helper: stream Claude tokens for a single (system, user) turn."""
    async for chunk in _make_llm().astream(
        [SystemMessage(content=system), HumanMessage(content=user_message)]
    ):
        text = _content_to_text(chunk.content)
        if text:
            yield text


def _extract_user_request(state: dict[str, Any]) -> str:
    """Pull the latest user message from state as the writing request."""
    messages = state.get("messages", [])
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return msg.get("content", "")
    return ""


# ---------------------------------------------------------------------------
# Outline
# ---------------------------------------------------------------------------

async def outline_node(state: dict[str, Any]) -> dict[str, Any]:
    """Create a structured outline for the requested content.

    Reads the user's request and the writer's constraints, then produces
    an outline that will guide the draft node.
    """
    identity: dict[str, Any] = state.get("identity", {})
    constraints = identity.get("constraints", {})
    user_request = _extract_user_request(state)

    prompt = OUTLINE_PROMPT.format(
        purpose=identity.get("purpose", "general-purpose writing"),
        constraints=format_constraints_for_prompt(constraints),
        request=user_request,
    )

    outline = await _call_claude(
        system="You are a writing planner.  Produce clear, actionable outlines.",
        user_message=prompt,
    )

    return {"outline": outline}


# ---------------------------------------------------------------------------
# Draft
# ---------------------------------------------------------------------------

async def draft_node(state: dict[str, Any]) -> dict[str, Any]:
    """Write the first draft based on the outline.

    Uses the full writer identity (personality, emotions, constraints) to
    produce content that sounds like *this* writer.
    """
    identity: dict[str, Any] = state.get("identity", {})
    constraints = identity.get("constraints", {})
    outline = state.get("outline", "")

    system = WRITER_SYSTEM_PROMPT.format(
        name=state.get("writer_name", "Writer"),
        purpose=identity.get("purpose", "general-purpose writing"),
        personality=", ".join(identity.get("personality", [])),
        emotions=", ".join(identity.get("emotions", [])),
        constraints=format_constraints_for_prompt(constraints),
        outline=outline,
    )

    draft = await _call_claude(
        system=system,
        user_message="Write the content now, following the outline above.",
    )

    return {"draft": draft}


# ---------------------------------------------------------------------------
# Refine
# ---------------------------------------------------------------------------

def _build_refine_prompt(state: dict[str, Any]) -> tuple[str, str]:
    """Build the system prompt and user message for the refine step.

    Returns (system_prompt, user_message).
    """
    identity: dict[str, Any] = state.get("identity", {})
    constraints = identity.get("constraints", {})
    draft = state.get("draft", "")

    validation = validate_constraints(draft, constraints)
    feedback_parts: list[str] = []

    if validation["violations"]:
        feedback_parts.append(
            "CONSTRAINT VIOLATIONS (must fix):\n"
            + "\n".join(f"  - {v}" for v in validation["violations"])
        )
    if validation["warnings"]:
        feedback_parts.append(
            "Warnings (review):\n"
            + "\n".join(f"  - {w}" for w in validation["warnings"])
        )

    user_request = _extract_user_request(state)
    if user_request:
        feedback_parts.append(f"User notes: {user_request}")

    feedback_text = "\n\n".join(feedback_parts) if feedback_parts else "None."

    prompt = REFINE_PROMPT.format(
        constraints=format_constraints_for_prompt(constraints),
        draft=draft,
        feedback=feedback_text,
    )

    return (
        "You are a meticulous editor.  Improve the writing while preserving voice.",
        prompt,
    )


async def refine_node(state: dict[str, Any]) -> dict[str, Any]:
    """Polish the draft and enforce constraints."""
    system, user_msg = _build_refine_prompt(state)
    refined = await _call_claude(system=system, user_message=user_msg)
    return {"refined_content": refined}


async def refine_node_stream(state: dict[str, Any]) -> AsyncIterator[str]:
    """Stream the refine step token-by-token."""
    system, user_msg = _build_refine_prompt(state)
    async for text in _stream_claude(system=system, user_message=user_msg):
        yield text


# ---------------------------------------------------------------------------
# Studio Refine (streaming) — same as refine_node_stream but uses
# STUDIO_REFINE_PROMPT which appends ---TITLE: <title>--- at the end
# ---------------------------------------------------------------------------

def _build_studio_refine_prompt(state: dict[str, Any]) -> tuple[str, str]:
    """Build the system prompt and user message for the Studio refine step.

    Returns (system_prompt, user_message).
    """
    identity: dict[str, Any] = state.get("identity", {})
    constraints = identity.get("constraints", {})
    draft = state.get("draft", "")

    validation = validate_constraints(draft, constraints)
    feedback_parts: list[str] = []

    if validation["violations"]:
        feedback_parts.append(
            "CONSTRAINT VIOLATIONS (must fix):\n"
            + "\n".join(f"  - {v}" for v in validation["violations"])
        )
    if validation["warnings"]:
        feedback_parts.append(
            "Warnings (review):\n"
            + "\n".join(f"  - {w}" for w in validation["warnings"])
        )

    feedback_text = "\n\n".join(feedback_parts) if feedback_parts else "None."

    prompt = STUDIO_REFINE_PROMPT.format(
        constraints=format_constraints_for_prompt(constraints),
        draft=draft,
        feedback=feedback_text,
    )

    return (
        "You are a meticulous editor.  Improve the writing while preserving voice.",
        prompt,
    )


async def studio_refine_node_stream(state: dict[str, Any]) -> AsyncIterator[str]:
    """Stream the Studio refine step token-by-token.

    Uses STUDIO_REFINE_PROMPT which appends ---TITLE: <title>--- at the very
    end of the output so the caller can extract a title for the saved piece.
    """
    system, user_msg = _build_studio_refine_prompt(state)
    async for text in _stream_claude(system=system, user_message=user_msg):
        yield text
