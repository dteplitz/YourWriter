"""Evolution pipeline nodes — analyze, evaluate, decide, apply.

These nodes form the identity-evolution pipeline that runs after a
writing session to incrementally update the writer's personality,
emotions, memories, and objectives.
"""

from __future__ import annotations

import json
from typing import Any

import anthropic

from agents.prompts.system import EVOLUTION_SYSTEM_PROMPT
from agents.evolution.identity import Identity


async def _call_claude(system: str, user_message: str) -> str:
    """Helper: single-turn Claude call."""
    client = anthropic.AsyncAnthropic()
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


# ---------------------------------------------------------------------------
# Analyze
# ---------------------------------------------------------------------------

async def analyze_node(state: dict[str, Any]) -> dict[str, Any]:
    """Analyze the recent writing session and user reactions.

    Produces a summary of what happened, what the user liked or disliked,
    and what patterns are emerging.
    """
    content_written = state.get("content_written", "")
    user_feedback = state.get("user_feedback", "")

    analysis = await _call_claude(
        system=(
            "You are an analytical assistant.  Given a piece of writing and "
            "the user's feedback, produce a concise analysis covering: "
            "(1) the writing's strengths, (2) its weaknesses, "
            "(3) implicit user preferences revealed by their feedback, "
            "(4) any patterns worth noting.  Be specific and evidence-based."
        ),
        user_message=(
            f"## Content written\n{content_written}\n\n"
            f"## User feedback\n{user_feedback}"
        ),
    )

    return {"analysis": analysis}


# ---------------------------------------------------------------------------
# Evaluate
# ---------------------------------------------------------------------------

async def evaluate_node(state: dict[str, Any]) -> dict[str, Any]:
    """Compare the analysis against the current identity.

    Identifies gaps between who the writer *is* (identity) and what the
    analysis suggests the writer *should become*.
    """
    current_identity = state.get("current_identity", {})
    analysis = state.get("analysis", "")

    identity_obj = Identity.from_dict(current_identity)
    identity_text = identity_obj.to_prompt_string()

    evaluation = await _call_claude(
        system=(
            "You are an identity evaluator for an AI writer.  Compare the "
            "writer's current identity against a recent analysis of their "
            "work and user feedback.  Identify: (1) traits that served the "
            "writing well, (2) traits that were absent but needed, "
            "(3) emotions that should shift, (4) new topics or skills "
            "demonstrated, (5) objectives that need updating.  Be specific."
        ),
        user_message=(
            f"## Current identity\n{identity_text}\n\n"
            f"## Analysis of recent session\n{analysis}"
        ),
    )

    return {"evaluation": evaluation}


# ---------------------------------------------------------------------------
# Decide
# ---------------------------------------------------------------------------

async def decide_node(state: dict[str, Any]) -> dict[str, Any]:
    """Propose specific identity changes with reasons.

    Uses the full EVOLUTION_SYSTEM_PROMPT to output structured JSON
    describing incremental changes.
    """
    current_identity = state.get("current_identity", {})
    content_written = state.get("content_written", "")
    user_feedback = state.get("user_feedback", "")

    identity_obj = Identity.from_dict(current_identity)
    identity_text = identity_obj.to_prompt_string()

    prompt = EVOLUTION_SYSTEM_PROMPT.format(
        current_identity=identity_text,
        content_written=content_written,
        user_feedback=user_feedback,
    )

    raw_response = await _call_claude(
        system=prompt,
        user_message=(
            "Based on the analysis and evaluation above, propose specific "
            "changes to the writer's identity.  Return ONLY valid JSON."
        ),
    )

    # Parse the JSON response; fall back gracefully on parse errors
    try:
        result = json.loads(raw_response)
        changes = result.get("changes", [])
        reasoning = result.get("overall_reasoning", "")
    except json.JSONDecodeError:
        changes = []
        reasoning = f"Failed to parse evolution response: {raw_response[:200]}"

    return {"changes": changes, "reasoning": reasoning}


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------

async def apply_node(state: dict[str, Any]) -> dict[str, Any]:
    """Apply proposed changes to produce the updated identity.

    This node does not call the LLM — it applies the structured changes
    from the decide node to the current identity dict and returns the
    final evolution result.
    """
    current_identity = state.get("current_identity", {})
    changes: list[dict[str, Any]] = state.get("changes", [])
    reasoning: str = state.get("reasoning", "")

    # Deep copy via Identity dataclass so we don't mutate state
    identity = Identity.from_dict(current_identity)
    updated = identity.to_dict()

    for change in changes:
        field = change.get("field", "")
        action = change.get("action", "")
        value = change.get("value", "")
        old_value = change.get("old_value")

        if field not in updated:
            continue

        target = updated[field]

        if isinstance(target, str):
            # Scalar fields like "purpose"
            if action in ("add", "modify"):
                updated[field] = value

        elif isinstance(target, list):
            if action == "add" and value not in target:
                target.append(value)
            elif action == "remove":
                removal = old_value if old_value else value
                if removal in target:
                    target.remove(removal)
            elif action == "modify" and old_value in target:
                idx = target.index(old_value)
                target[idx] = value

        elif isinstance(target, dict):
            if action == "add" or action == "modify":
                # For constraints dict, we parse the key from the value
                # if the change specifies a key-value pair
                if isinstance(value, dict):
                    target.update(value)
                else:
                    # Treat value as the new constraint value for a key
                    key = old_value if old_value else "custom"
                    target[key] = value
            elif action == "remove" and old_value in target:
                del target[old_value]

    return {
        "current_identity": updated,
        "changes": changes,
        "reasoning": reasoning,
    }
