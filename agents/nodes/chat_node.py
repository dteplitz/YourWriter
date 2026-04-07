"""Chat node — handles conversational interaction with the writer.

Uses ChatAnthropic from langchain-anthropic so the agent layer never
talks to the Anthropic SDK directly. The writer's system prompt is sent
with cache_control={"type": "ephemeral"} so subsequent turns in the
same conversation reuse the cached prefix (lower latency, lower cost)
once it crosses Anthropic's caching threshold.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from agents.prompts.system import ARTIST_PROFILE_CHAT_SYSTEM_PROMPT
from agents.tools.constraints import format_constraints_for_prompt
from agents.tools.memory import get_memories_as_prompt
from backend.config import settings


_MAX_TOKENS = 4096


def _build_system_prompt(state: dict[str, Any]) -> str:
    """Assemble the chat system prompt from writer state."""
    identity: dict[str, Any] = state.get("identity", {})

    return ARTIST_PROFILE_CHAT_SYSTEM_PROMPT.format(
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


def _build_lc_messages(state: dict[str, Any]) -> list[BaseMessage]:
    """Assemble the LangChain message list for a chat turn.

    The system prompt is sent as a structured content block tagged with
    cache_control so Anthropic can reuse its KV-cache between turns.
    """
    system_prompt = _build_system_prompt(state)
    system_message = SystemMessage(
        content=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]
    )

    lc_messages: list[BaseMessage] = [system_message]
    for msg in state.get("messages", []):
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "assistant":
            lc_messages.append(AIMessage(content=content))
        else:
            lc_messages.append(HumanMessage(content=content))

    return lc_messages


def _make_llm() -> ChatAnthropic:
    return ChatAnthropic(  # type: ignore[call-arg]
        model=settings.chat_model,
        max_tokens=_MAX_TOKENS,
    )


def _content_to_text(content: Any) -> str:
    """Coerce a LangChain message content payload to plain text.

    LangChain returns ``content`` as either a plain string or a list of
    content blocks (dicts) when the underlying provider streams structured
    deltas. We only care about text blocks here.
    """
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


async def chat_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node: handle a conversational turn (non-streaming).

    Reads the current messages from state, calls Claude via ChatAnthropic
    with the writer's system prompt, and appends the assistant response.
    """
    lc_messages = _build_lc_messages(state)

    response = await _make_llm().ainvoke(lc_messages)
    assistant_text = _content_to_text(response.content)

    updated_messages = list(state.get("messages", []))
    updated_messages.append({"role": "assistant", "content": assistant_text})

    return {"messages": updated_messages}


async def chat_node_stream(state: dict[str, Any]) -> AsyncIterator[str]:
    """Async generator that yields text chunks from Claude streaming API."""
    lc_messages = _build_lc_messages(state)

    async for chunk in _make_llm().astream(lc_messages):
        text = _content_to_text(chunk.content)
        if text:
            yield text
