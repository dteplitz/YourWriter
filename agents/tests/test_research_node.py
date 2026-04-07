"""Tests for agents.nodes.research_node.

These tests mock ``ChatAnthropic`` so we never hit the real API.  The
node uses ``llm.bind_tools(...)`` and then ``ainvoke``; we patch the
class so its instance returns a fake bound runnable whose ``ainvoke``
yields a pre-built response object.

Anthropic returns content as a list of blocks.  For server-side
built-in tools (web_search_20250305) the block types are
``server_tool_use`` and ``web_search_tool_result``, plus one or more
``text`` blocks for the synthesis.  We test both the legacy
``tool_use`` shape and the modern ``server_tool_use`` shape.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.nodes.research_node import research_node_stream


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _text_block(text: str) -> dict:
    return {"type": "text", "text": text}


def _server_tool_use_block(query: str) -> dict:
    return {
        "type": "server_tool_use",
        "id": "stu_01",
        "name": "web_search",
        "input": {"query": query},
    }


def _make_response(content_blocks: list) -> SimpleNamespace:
    return SimpleNamespace(content=content_blocks)


def _patch_chat_anthropic(response):
    """Return a context manager that patches ChatAnthropic in research_node.

    The patched class returns an instance whose ``bind_tools`` returns a
    runnable whose ``ainvoke`` yields ``response``.
    """
    bound = MagicMock()
    bound.ainvoke = AsyncMock(return_value=response)

    instance = MagicMock()
    instance.bind_tools.return_value = bound

    patcher = patch("agents.nodes.research_node.ChatAnthropic")
    mock_class = patcher.start()
    mock_class.return_value = instance
    return patcher, bound


def _state(user_message: str = "Write about recent AI developments") -> dict:
    return {"messages": [{"role": "user", "content": user_message}]}


# ---------------------------------------------------------------------------
# Tests: empty / no user message
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_user_message_yields_empty_search_results():
    events = []
    async for event in research_node_stream({"messages": []}):
        events.append(event)

    assert events == [{"search_results": ""}]


@pytest.mark.asyncio
async def test_empty_messages_yields_empty_search_results():
    events = []
    async for event in research_node_stream({}):
        events.append(event)

    assert events == [{"search_results": ""}]


# ---------------------------------------------------------------------------
# Tests: NO_SEARCH_NEEDED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_search_needed_response():
    """When the model replies NO_SEARCH_NEEDED, only search_results is emitted."""
    response = _make_response([_text_block("NO_SEARCH_NEEDED")])
    patcher, _ = _patch_chat_anthropic(response)
    try:
        events = []
        async for event in research_node_stream(_state()):
            events.append(event)
    finally:
        patcher.stop()

    assert events == [{"search_results": ""}]


@pytest.mark.asyncio
async def test_empty_content_yields_empty_search_results():
    response = _make_response([])
    patcher, _ = _patch_chat_anthropic(response)
    try:
        events = []
        async for event in research_node_stream(_state()):
            events.append(event)
    finally:
        patcher.stop()

    assert events[-1] == {"search_results": ""}


# ---------------------------------------------------------------------------
# Tests: web_search server-side tool use
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_server_tool_use_yields_correct_events():
    """server_tool_use blocks are emitted as tool_use SSE events."""
    summary = "Recent AI developments include GPT-5 and Gemini Ultra 2."
    response = _make_response([
        _server_tool_use_block("recent AI developments 2026"),
        _text_block(summary),
    ])
    patcher, _ = _patch_chat_anthropic(response)
    try:
        events = []
        async for event in research_node_stream(_state()):
            events.append(event)
    finally:
        patcher.stop()

    assert len(events) == 3

    tool_use_event = events[0]
    assert tool_use_event["tool_use"]["name"] == "web_search"
    assert tool_use_event["tool_use"]["query"] == "recent AI developments 2026"
    assert tool_use_event["tool_use"]["display_name"] == "Buscando"

    tool_result_event = events[1]
    assert tool_result_event["tool_result"]["name"] == "web_search"
    assert tool_result_event["tool_result"]["summary"] == summary[:200]

    assert events[2] == {"search_results": summary}


@pytest.mark.asyncio
async def test_multiple_text_blocks_are_joined():
    """Anthropic splits the synthesis across multiple text blocks (citations etc)."""
    response = _make_response([
        _server_tool_use_block("query"),
        _text_block("Part one. "),
        _text_block("Part two."),
    ])
    patcher, _ = _patch_chat_anthropic(response)
    try:
        events = []
        async for event in research_node_stream(_state()):
            events.append(event)
    finally:
        patcher.stop()

    assert events[-1] == {"search_results": "Part one. Part two."}


@pytest.mark.asyncio
async def test_tool_result_summary_capped_at_200_chars():
    long_summary = "A" * 500
    response = _make_response([
        _server_tool_use_block("query"),
        _text_block(long_summary),
    ])
    patcher, _ = _patch_chat_anthropic(response)
    try:
        events = []
        async for event in research_node_stream(_state()):
            events.append(event)
    finally:
        patcher.stop()

    assert len(events[1]["tool_result"]["summary"]) == 200
    assert events[2]["search_results"] == long_summary


@pytest.mark.asyncio
async def test_search_results_is_always_last_event():
    response = _make_response([
        _server_tool_use_block("test query"),
        _text_block("Some research summary."),
    ])
    patcher, _ = _patch_chat_anthropic(response)
    try:
        events = []
        async for event in research_node_stream(_state()):
            events.append(event)
    finally:
        patcher.stop()

    assert "search_results" in events[-1]


@pytest.mark.asyncio
async def test_latest_user_message_is_used():
    state = {
        "messages": [
            {"role": "user", "content": "Earlier message"},
            {"role": "assistant", "content": "Some reply"},
            {"role": "user", "content": "Latest user message"},
        ]
    }
    response = _make_response([_text_block("NO_SEARCH_NEEDED")])
    patcher, bound = _patch_chat_anthropic(response)
    try:
        async for _ in research_node_stream(state):
            pass
    finally:
        patcher.stop()

    # The HumanMessage passed to ainvoke must contain the latest user message.
    args, _kwargs = bound.ainvoke.call_args
    sent_messages = args[0]
    human_messages = [m for m in sent_messages if m.__class__.__name__ == "HumanMessage"]
    assert human_messages[-1].content == "Latest user message"


@pytest.mark.asyncio
async def test_tool_use_query_empty_string_when_input_missing():
    response = _make_response([
        {"type": "server_tool_use", "id": "stu_01", "name": "web_search", "input": {}},
        _text_block("Some result"),
    ])
    patcher, _ = _patch_chat_anthropic(response)
    try:
        events = []
        async for event in research_node_stream(_state()):
            events.append(event)
    finally:
        patcher.stop()

    assert events[0]["tool_use"]["query"] == ""
