"""Evolution pipeline nodes — detect, compute, apply.

These three nodes implement the 2-stage identity-evolution pipeline:

  detect_node  — Stage 1 (Haiku): decide whether the conversation contains
                 identity-shaping signals.
  compute_node — Stage 2 (Sonnet): propose specific, incremental changes.
  apply_node   — No LLM: apply structured changes to the current identity dict.

All LLM calls use ChatAnthropic from langchain_anthropic — no SDK calls.
"""

from __future__ import annotations

import json
import re
from typing import Any


def _parse_json_response(raw: str) -> dict:
    """Parse a JSON response that may be wrapped in a markdown code block."""
    raw = raw.strip()
    # Strip markdown code fences: ```json ... ``` or ``` ... ```
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw.strip())
    return json.loads(raw.strip())

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from agents.prompts.system import EVOLUTION_DETECT_PROMPT, EVOLUTION_SYSTEM_PROMPT
from agents.evolution.identity import Identity


# ---------------------------------------------------------------------------
# detect_node — Stage 1 (Haiku)
# ---------------------------------------------------------------------------

async def detect_node(state: dict[str, Any]) -> dict[str, Any]:
    """Detect whether the conversation contains identity-shaping signals.

    Uses a fast, conservative Haiku call to decide IF evolution should happen.
    Defaults to no-evolution on any parse failure.
    """
    chat_history: list[dict] = state.get("chat_history", [])
    last_user_message: str = state.get("last_user_message", "")

    # Format chat history for the prompt
    history_lines: list[str] = []
    for msg in chat_history:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        history_lines.append(f"{role.upper()}: {content}")
    formatted_history = "\n".join(history_lines) if history_lines else "(no previous messages)"

    prompt = EVOLUTION_DETECT_PROMPT.format(
        chat_history=formatted_history,
        last_user_message=last_user_message,
    )

    llm = ChatAnthropic(model="claude-haiku-4-5-20251001")  # type: ignore[call-arg]
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content="Analyze the conversation and respond with the JSON object."),
    ]

    try:
        response = await llm.ainvoke(messages)
        raw = response.content if isinstance(response.content, str) else str(response.content)
        result = _parse_json_response(raw)
        return {
            "should_evolve": bool(result.get("should_evolve", False)),
            "confidence": float(result.get("confidence", 0.0)),
            "signal": str(result.get("signal", "")),
        }
    except Exception:
        # Conservative default: do not evolve on any failure
        return {
            "should_evolve": False,
            "confidence": 0.0,
            "signal": "",
        }


# ---------------------------------------------------------------------------
# compute_node — Stage 2 (Sonnet)
# ---------------------------------------------------------------------------

async def compute_node(state: dict[str, Any]) -> dict[str, Any]:
    """Propose specific, incremental identity changes.

    Uses Sonnet with the signal from detect_node to produce structured JSON
    describing what should change and why.
    """
    current_identity: dict[str, Any] = state.get("current_identity", {})
    signal: str = state.get("signal", "")

    identity_obj = Identity.from_dict(current_identity)
    identity_text = identity_obj.to_prompt_string()

    prompt = EVOLUTION_SYSTEM_PROMPT.format(
        signal=signal,
        current_identity=identity_text,
    )

    llm = ChatAnthropic(model="claude-sonnet-4-6")  # type: ignore[call-arg]
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content="Propose the identity changes based on the signal above. Return ONLY valid JSON."),
    ]

    try:
        response = await llm.ainvoke(messages)
        raw = response.content if isinstance(response.content, str) else str(response.content)
        result = _parse_json_response(raw)
        return {
            "changes": result.get("changes", []),
            "reasoning": result.get("overall_reasoning", ""),
        }
    except Exception:
        return {
            "changes": [],
            "reasoning": "parse error",
        }


# ---------------------------------------------------------------------------
# apply_node — No LLM
# ---------------------------------------------------------------------------

async def apply_node(state: dict[str, Any]) -> dict[str, Any]:
    """Apply structured changes to the current identity dict.

    No LLM call. Takes the list of changes from compute_node and mutates
    a copy of current_identity, returning it as updated_identity.

    Dict fields (emotions, personality, constraints): changes use "key" to
    index into the dict.
    List fields (topics, memories, lifelong_objectives): changes use "value".
    Failures are silently skipped — the field or key simply does not exist.
    """
    current_identity: dict[str, Any] = state.get("current_identity", {})
    changes: list[dict[str, Any]] = state.get("changes", [])

    # Work on a copy via Identity round-trip to avoid mutating state
    identity_obj = Identity.from_dict(current_identity)
    identity = identity_obj.to_dict()

    # Dict fields — keyed access
    DICT_FIELDS = {"emotions", "personality", "constraints"}
    # List fields — value-based access
    LIST_FIELDS = {"topics", "memories", "lifelong_objectives"}

    for change in changes:
        field = change.get("field", "")
        action = change.get("action", "")

        if field not in identity:
            continue

        target = identity[field]

        if field in DICT_FIELDS and isinstance(target, dict):
            key = change.get("key", "")
            new_value = change.get("new_value")
            old_value = change.get("old_value")

            if action in ("modify", "add"):
                if key:
                    target[key] = new_value
            elif action == "remove":
                if key and key in target:
                    del target[key]

        elif field in LIST_FIELDS and isinstance(target, list):
            value = change.get("value", "")
            old_value = change.get("old_value", "")

            if action == "add":
                if value and value not in target:
                    target.append(value)
            elif action == "remove":
                removal = old_value if old_value else value
                if removal in target:
                    target.remove(removal)
            elif action == "modify":
                if old_value in target:
                    idx = target.index(old_value)
                    target[idx] = value

        elif field == "purpose" and isinstance(target, str):
            value = change.get("value", change.get("new_value", ""))
            if action in ("modify", "add") and value:
                identity[field] = value

    return {"updated_identity": identity}
