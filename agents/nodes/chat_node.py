"""Chat node — handles conversational interaction with the writer.

Uses the Anthropic Python SDK to call Claude, injecting the writer's
identity into the system prompt so responses stay in character.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import anthropic

from agents.prompts.system import CHAT_SYSTEM_PROMPT
from agents.tools.memory import get_memories_as_prompt
from agents.tools.constraints import format_constraints_for_prompt


def _build_system_prompt(state: dict[str, Any]) -> str:
    """Assemble the chat system prompt from writer state."""
    identity: dict[str, Any] = state.get("identity", {})

    return CHAT_SYSTEM_PROMPT.format(
        name=state.get("writer_name", "Writer"),
        purpose=identity.get("purpose", "general-purpose writing"),
        personality=", ".join(identity.get("personality", ["thoughtful"])),
        emotions=", ".join(identity.get("emotions", ["calm"])),
        memories=get_memories_as_prompt(state.get("writer_id", "default")),
        constraints=format_constraints_for_prompt(
            identity.get("constraints", {})
        ),
        objectives="\n".join(
            f"- {o}" for o in identity.get("lifelong_objectives", [])
        )
        or "None set yet.",
    )


def _messages_to_anthropic(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Convert LangGraph message dicts to the Anthropic messages format.

    Keeps only role and content, filtering to roles that Claude accepts
    (user, assistant).
    """
    converted: list[dict[str, str]] = []
    for msg in messages:
        role = msg.get("role", "user")
        if role not in ("user", "assistant"):
            role = "user"
        converted.append({"role": role, "content": msg.get("content", "")})
    return converted


async def chat_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node: handle a conversational turn.

    Reads the current messages from state, calls the Anthropic API with
    the writer's system prompt, and appends the assistant response.

    Parameters
    ----------
    state:
        The current WriterState dict.

    Returns
    -------
    dict with updated ``messages`` list.
    """
    system_prompt = _build_system_prompt(state)
    messages = _messages_to_anthropic(state.get("messages", []))

    # The API key is expected to be passed through state or env.
    # For now we rely on the ANTHROPIC_API_KEY environment variable.
    client = anthropic.AsyncAnthropic()

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=system_prompt,
        messages=messages,
    )

    assistant_text = response.content[0].text

    updated_messages = list(state.get("messages", []))
    updated_messages.append({"role": "assistant", "content": assistant_text})

    return {"messages": updated_messages}


async def chat_node_stream(state: dict[str, Any]) -> AsyncIterator[str]:
    """Async generator that yields text chunks from Claude streaming API."""
    system_prompt = _build_system_prompt(state)
    messages = _messages_to_anthropic(state.get("messages", []))

    client = anthropic.AsyncAnthropic()

    async with client.messages.stream(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=system_prompt,
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            yield text
