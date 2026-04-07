"""Evolution pipeline nodes — detect, compute, apply.

These three nodes implement the 2-stage identity-evolution pipeline:

  detect_node  — Stage 1 (Haiku): decide whether the conversation contains
                 identity-shaping signals.
  compute_node — Stage 2 (Sonnet): propose specific, incremental changes.
  apply_node   — No LLM: apply structured changes to the current identity dict.

LLM calls go through ChatAnthropic + with_structured_output(...) so the
response is parsed into Pydantic models — no markdown-fence regex hacks.
Model IDs come from backend.config.settings, never hardcoded here.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from agents.evolution.identity import Identity
from agents.prompts.system import EVOLUTION_DETECT_PROMPT, EVOLUTION_SYSTEM_PROMPT
from backend.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic schemas — structured output contracts enforced via tool-use
# ---------------------------------------------------------------------------


class EvolutionDecision(BaseModel):
    """Stage 1 output — does this conversation warrant evolving the writer?"""

    should_evolve: bool = Field(
        description="True iff the conversation contains a clear, unambiguous identity-shaping signal."
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence between 0.0 and 1.0.",
    )
    signal: str = Field(
        default="",
        description="One-sentence summary of WHY it triggers, or empty string if it does not.",
    )


class EvolutionChange(BaseModel):
    """A single proposed change to the writer's identity."""

    field: str = Field(
        description=(
            "Identity field name: emotions, personality, topics, memories, "
            "lifelong_objectives, constraints, or purpose."
        )
    )
    action: str = Field(description="add, modify, or remove.")
    key: str | None = Field(
        default=None,
        description="Dict key — used for dict-typed fields (emotions, personality, constraints).",
    )
    value: str | None = Field(
        default=None,
        description="String value — used for list-typed fields (topics, memories, lifelong_objectives).",
    )
    old_value: Any = Field(
        default=None,
        description="Previous value — used for modify and (for list fields) remove actions.",
    )
    new_value: Any = Field(
        default=None,
        description="New value — used for add and modify actions on dict-typed fields.",
    )
    reason: str = Field(
        default="",
        description="Specific reason tied to the signal.",
    )


class EvolutionPlan(BaseModel):
    """Stage 2 output — the proposed evolution as a list of incremental changes."""

    changes: list[EvolutionChange] = Field(default_factory=list)
    overall_reasoning: str = Field(default="")


# ---------------------------------------------------------------------------
# detect_node — Stage 1 (Haiku)
# ---------------------------------------------------------------------------

async def detect_node(state: dict[str, Any]) -> dict[str, Any]:
    """Detect whether the conversation contains identity-shaping signals.

    Uses a fast, conservative Haiku call to decide IF evolution should happen.
    Defaults to no-evolution on any failure.
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

    llm = ChatAnthropic(model=settings.evolution_detect_model)  # type: ignore[call-arg]
    structured_llm = llm.with_structured_output(EvolutionDecision)
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content="Analyze the conversation and return the decision."),
    ]

    try:
        decision = await structured_llm.ainvoke(messages)
        return {
            "should_evolve": bool(decision.should_evolve),
            "confidence": float(decision.confidence),
            "signal": decision.signal or "",
        }
    except Exception:
        logger.warning("detect_node failed — defaulting to no-evolve", exc_info=True)
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

    Uses Sonnet with the signal from detect_node to produce a structured
    EvolutionPlan describing what should change and why.
    """
    current_identity: dict[str, Any] = state.get("current_identity", {})
    signal: str = state.get("signal", "")

    identity_obj = Identity.from_dict(current_identity)
    identity_text = identity_obj.to_prompt_string()

    prompt = EVOLUTION_SYSTEM_PROMPT.format(
        signal=signal,
        current_identity=identity_text,
    )

    llm = ChatAnthropic(model=settings.evolution_compute_model)  # type: ignore[call-arg]
    structured_llm = llm.with_structured_output(EvolutionPlan)
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content="Propose the identity changes based on the signal above."),
    ]

    try:
        plan = await structured_llm.ainvoke(messages)
        # apply_node and the rest of the pipeline expect plain dicts.
        # exclude_none=True keeps the same shape the previous JSON-parsing path produced:
        # only the keys relevant to a given action are present.
        return {
            "changes": [change.model_dump(exclude_none=True) for change in plan.changes],
            "reasoning": plan.overall_reasoning or "",
        }
    except Exception:
        logger.warning("compute_node failed — returning empty changes", exc_info=True)
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
