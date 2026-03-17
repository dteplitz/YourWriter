"""Research node — decides whether to search the web for a writing request.

This node runs *before* ``outline_node`` in the writing pipeline.  It
examines the user's request, asks Claude whether current / factual
information would improve the response, and — if so — executes a web
search via Anthropic's built-in ``web_search_20250305`` tool.

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

import anthropic

from agents.tools.registry import TOOL_REGISTRY, get_anthropic_tools

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

    client = anthropic.AsyncAnthropic()

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=RESEARCH_SYSTEM,
        tools=get_anthropic_tools(["web_search"]),
        messages=[{"role": "user", "content": user_request}],
    )

    # Walk the response content blocks and process tool_use / text blocks.
    search_query: str | None = None
    search_summary: str = ""

    for block in response.content:
        if block.type == "tool_use":
            search_query = block.input.get("query", "") if isinstance(block.input, dict) else ""
            tool = TOOL_REGISTRY.get("web_search")
            yield {
                "tool_use": {
                    "name": "web_search",
                    "display_name": tool.display_name if tool else "Buscando",
                    "query": search_query,
                }
            }
        elif block.type == "text":
            text = block.text.strip()
            if text and text != "NO_SEARCH_NEEDED":
                search_summary = text

    if search_query is not None:
        # Emit a tool_result event with a capped summary for the SSE pill.
        yield {
            "tool_result": {
                "name": "web_search",
                "summary": search_summary[:200],
            }
        }

    yield {"search_results": search_summary}
