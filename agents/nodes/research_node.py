"""Research node — decides whether to search the web for a writing request.

This node runs *before* ``outline_node`` in the writing pipeline.  It
examines the user's request, asks Claude whether current / factual
information would improve the response, and — if so — executes a web
search via Anthropic's built-in ``web_search_20250305`` tool.

The model is invoked through ``ChatAnthropic`` with the built-in tool
spec bound via ``bind_tools(...)`` — no direct anthropic SDK calls.

The search is transparent to the user: the node yields SSE-compatible
event dicts so the frontend can show a "Buscando…" pill while the
search is in progress.

Yields
------
{"tool_use": {"name": str, "display_name": str, "query": str}}
    Emitted when Claude decides to search — contains the query it chose.
{"tool_result": {"name": str, "summary": str}}
    Emitted after the search completes — contains a short summary snippet.
{"search_results": str}
    ALWAYS the final yield.  Contains the full research summary that
    ``outline_node`` can inject into its context.  Empty string if no
    search was performed.

Usage
-----
    async for event in research_node_stream(state):
        if "search_results" in event:
            state["search_results"] = event["search_results"]
        else:
            # forward tool_use / tool_result to the SSE stream
            yield event
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from backend.config import settings

# Anthropic native built-in tool spec for web search.  langchain-anthropic
# passes raw tool dicts through ``bind_tools(...)`` for built-ins.
_WEB_SEARCH_TOOL_SPEC: dict[str, str] = {
    "type": "web_search_20250305",
    "name": "web_search",
}
_WEB_SEARCH_DISPLAY_NAME = "Buscando"

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

RESEARCH_SYSTEM = """\
You are a research assistant supporting an AI writer.

Given a writing request, decide whether you need to search for current or
specific factual information that would materially improve the writing.

Use web_search when the request involves:
- Recent events, news, or developments (anything that may have changed in
  the last year or two)
- Specific statistics, data, or citations that require accuracy
- Named people, organisations, or places where current facts matter
- Scientific or technical topics where the latest findings are relevant

Do NOT search for:
- Creative, fictional, or purely stylistic requests
- General knowledge that has been stable for decades
- Requests where the user has already provided all the necessary facts

If you search, synthesise the results into a concise research summary that
will be used as background context for the writing.  Focus on what is
directly useful — do not pad.

If no search is needed, reply with exactly: NO_SEARCH_NEEDED
"""

_MAX_TOKENS = 2048


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_user_request(state: dict[str, Any]) -> str:
    """Return the latest user message from state."""
    messages = state.get("messages", [])
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return msg.get("content", "")
    return ""


def _block_type(block: Any) -> str:
    """Return the ``type`` of a content block, supporting both dict and object shapes."""
    if isinstance(block, dict):
        return block.get("type", "")
    return getattr(block, "type", "")


def _block_field(block: Any, name: str, default: Any = None) -> Any:
    """Read a field from a content block tolerating dict or object access."""
    if isinstance(block, dict):
        return block.get(name, default)
    return getattr(block, name, default)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def research_node_stream(state: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
    """Async generator that runs the research step for a writing request.

    Parameters
    ----------
    state:
        The current writer agent state dict.  Must contain a ``messages``
        key with at least one user message.

    Yields
    ------
    dict
        Event dicts suitable for forwarding to an SSE stream.  See module
        docstring for the full event contract.
    """
    user_request = _extract_user_request(state)

    if not user_request:
        yield {"search_results": ""}
        return

    llm = ChatAnthropic(  # type: ignore[call-arg]
        model=settings.writing_model,
        max_tokens=_MAX_TOKENS,
    )
    # web_search_20250305 is a native Anthropic built-in tool. langchain-anthropic
    # passes raw tool dicts through bind_tools(...) for built-ins.
    llm_with_tools = llm.bind_tools([_WEB_SEARCH_TOOL_SPEC])

    response = await llm_with_tools.ainvoke(
        [
            SystemMessage(content=RESEARCH_SYSTEM),
            HumanMessage(content=user_request),
        ]
    )

    # Walk the response content blocks and process tool_use / text blocks.
    # Anthropic server-side built-in tools (web_search_20250305) emit
    # ``server_tool_use`` and ``web_search_tool_result`` blocks, and the
    # final synthesis is split across multiple ``text`` blocks (some with
    # citations).  We join all text blocks into a single summary.
    search_query: str | None = None
    text_parts: list[str] = []

    content = response.content if isinstance(response.content, list) else [response.content]

    for block in content:
        btype = _block_type(block)
        if btype in ("server_tool_use", "tool_use"):
            tool_input = _block_field(block, "input", {}) or {}
            search_query = tool_input.get("query", "") if isinstance(tool_input, dict) else ""
            yield {
                "tool_use": {
                    "name": "web_search",
                    "display_name": _WEB_SEARCH_DISPLAY_NAME,
                    "query": search_query,
                }
            }
        elif btype == "text":
            text_value = _block_field(block, "text", "")
            if text_value:
                text_parts.append(text_value)

    joined = "".join(text_parts).strip()
    search_summary = "" if joined == "NO_SEARCH_NEEDED" else joined

    if search_query is not None:
        # Emit a tool_result event with a capped summary for the SSE pill.
        yield {
            "tool_result": {
                "name": "web_search",
                "summary": search_summary[:200],
            }
        }

    yield {"search_results": search_summary}
