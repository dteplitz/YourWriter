"""Writing pipeline nodes — outline, draft, and refine.

These nodes form the core content-generation pipeline:
  outline_node  →  draft_node  →  refine_node

Each node calls the Anthropic API with a specialised prompt and updates
the relevant field in WriterState.
"""

from __future__ import annotations

from typing import Any

import anthropic

from agents.prompts.system import (
    OUTLINE_PROMPT,
    WRITER_SYSTEM_PROMPT,
    REFINE_PROMPT,
)
from agents.tools.constraints import (
    format_constraints_for_prompt,
    validate_constraints,
)


async def _call_claude(system: str, user_message: str) -> str:
    """Helper: send a single user message with a system prompt to Claude."""
    client = anthropic.AsyncAnthropic()
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


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

async def refine_node(state: dict[str, Any]) -> dict[str, Any]:
    """Polish the draft and enforce constraints.

    Runs constraint validation first, then asks the LLM to refine the
    draft — fixing violations and incorporating any user feedback.
    """
    identity: dict[str, Any] = state.get("identity", {})
    constraints = identity.get("constraints", {})
    draft = state.get("draft", "")

    # Validate before refining so we can tell the editor what to fix
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

    # Include explicit user feedback if present in the latest message
    user_request = _extract_user_request(state)
    if user_request:
        feedback_parts.append(f"User notes: {user_request}")

    feedback_text = "\n\n".join(feedback_parts) if feedback_parts else "None."

    prompt = REFINE_PROMPT.format(
        constraints=format_constraints_for_prompt(constraints),
        draft=draft,
        feedback=feedback_text,
    )

    refined = await _call_claude(
        system="You are a meticulous editor.  Improve the writing while preserving voice.",
        user_message=prompt,
    )

    return {"refined_content": refined}
