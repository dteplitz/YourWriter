"""Tests for agents.nodes.research_node."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.nodes.research_node import research_node_stream


# ---------------------------------------------------------------------------
# Helpers to build mock Anthropic responses
# ---------------------------------------------------------------------------


def _text_block(text: str) -> SimpleNamespace:
    return SimpleNamespace(type="text", text=text)


def _tool_use_block(query: str, tool_id: str = "tu_01") -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", id=tool_id, name="web_search", input={"query": query})


def _tool_result_block(content: str, tool_use_id: str = "tu_01") -> SimpleNamespace:
    return SimpleNamespace(type="tool_result", tool_use_id=tool_use_id, content=content)


def _mock_response(content_blocks: list) -> MagicMock:
    response = MagicMock()
    response.content = content_blocks
    return response


# ---------------------------------------------------------------------------
# Base state
# ---------------------------------------------------------------------------


def _state(user_message: str = "Write about recent AI developments") -> dict:
    return {"messages": [{"role": "user", "content": user_message}]}


# ---------------------------------------------------------------------------
# Test: no user message in state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_user_message_yields_empty_search_results():
    """If state has no user messages, node skips API call and yields empty results."""
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
# Test: no tool use (Claude decides no search needed)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_search_needed_response():
    """When Claude replies NO_SEARCH_NEEDED, only the search_results event is emitted."""
    mock_response = _mock_response([_text_block("NO_SEARCH_NEEDED")])

    with patch("agents.nodes.research_node.anthropic.AsyncAnthropic") as MockClient:
        mock_messages = AsyncMock()
        mock_messages.create = AsyncMock(return_value=mock_response)
        MockClient.return_value.messages = mock_messages

        events = []
        async for event in research_node_stream(_state()):
            events.append(event)

    assert events == [{"search_results": ""}]
    # No tool_use or tool_result events
    assert not any("tool_use" in e for e in events)
    assert not any("tool_result" in e for e in events)


@pytest.mark.asyncio
async def test_no_text_block_yields_empty_search_results():
    """Response with no text block at all → empty search_results."""
    mock_response = _mock_response([])

    with patch("agents.nodes.research_node.anthropic.AsyncAnthropic") as MockClient:
        mock_messages = AsyncMock()
        mock_messages.create = AsyncMock(return_value=mock_response)
        MockClient.return_value.messages = mock_messages

        events = []
        async for event in research_node_stream(_state()):
            events.append(event)

    assert events[-1] == {"search_results": ""}


# ---------------------------------------------------------------------------
# Test: tool use case (Claude decides to search)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tool_use_yields_correct_events():
    """When Claude uses web_search, node emits tool_use, tool_result, search_results in order."""
    summary = "Recent AI developments include GPT-5 and Gemini Ultra 2."
    mock_response = _mock_response([
        _tool_use_block("recent AI developments 2025"),
        _text_block(summary),
    ])

    with patch("agents.nodes.research_node.anthropic.AsyncAnthropic") as MockClient:
        mock_messages = AsyncMock()
        mock_messages.create = AsyncMock(return_value=mock_response)
        MockClient.return_value.messages = mock_messages

        events = []
        async for event in research_node_stream(_state()):
            events.append(event)

    assert len(events) == 3

    tool_use_event = events[0]
    assert "tool_use" in tool_use_event
    assert tool_use_event["tool_use"]["name"] == "web_search"
    assert tool_use_event["tool_use"]["query"] == "recent AI developments 2025"
    assert tool_use_event["tool_use"]["display_name"] == "Buscando"

    tool_result_event = events[1]
    assert "tool_result" in tool_result_event
    assert tool_result_event["tool_result"]["name"] == "web_search"
    assert tool_result_event["tool_result"]["summary"] == summary[:200]

    search_results_event = events[2]
    assert search_results_event == {"search_results": summary}


@pytest.mark.asyncio
async def test_search_results_is_always_last_event():
    """search_results must always be the final emitted event."""
    mock_response = _mock_response([
        _tool_use_block("test query"),
        _text_block("Some research summary."),
    ])

    with patch("agents.nodes.research_node.anthropic.AsyncAnthropic") as MockClient:
        mock_messages = AsyncMock()
        mock_messages.create = AsyncMock(return_value=mock_response)
        MockClient.return_value.messages = mock_messages

        events = []
        async for event in research_node_stream(_state()):
            events.append(event)

    assert "search_results" in events[-1]


@pytest.mark.asyncio
async def test_tool_result_summary_is_capped_at_200_chars():
    """tool_result summary is truncated to 200 characters max."""
    long_summary = "A" * 500
    mock_response = _mock_response([
        _tool_use_block("query"),
        _text_block(long_summary),
    ])

    with patch("agents.nodes.research_node.anthropic.AsyncAnthropic") as MockClient:
        mock_messages = AsyncMock()
        mock_messages.create = AsyncMock(return_value=mock_response)
        MockClient.return_value.messages = mock_messages

        events = []
        async for event in research_node_stream(_state()):
            events.append(event)

    tool_result = events[1]["tool_result"]
    assert len(tool_result["summary"]) == 200

    # But search_results contains the full text
    assert events[2]["search_results"] == long_summary


@pytest.mark.asyncio
async def test_latest_user_message_is_used():
    """The node uses the latest user message when multiple exist."""
    state = {
        "messages": [
            {"role": "user", "content": "Earlier message"},
            {"role": "assistant", "content": "Some reply"},
            {"role": "user", "content": "Latest user message"},
        ]
    }
    mock_response = _mock_response([_text_block("NO_SEARCH_NEEDED")])

    captured_args: list = []

    async def capture_create(**kwargs):
        captured_args.append(kwargs)
        return mock_response

    with patch("agents.nodes.research_node.anthropic.AsyncAnthropic") as MockClient:
        mock_messages = MagicMock()
        mock_messages.create = capture_create
        MockClient.return_value.messages = mock_messages

        async for _ in research_node_stream(state):
            pass

    assert captured_args[0]["messages"][0]["content"] == "Latest user message"


@pytest.mark.asyncio
async def test_tool_use_query_empty_string_when_input_missing():
    """If tool_use block has no 'query' in input, search_query defaults to empty string."""
    mock_response = _mock_response([
        SimpleNamespace(type="tool_use", id="tu_01", name="web_search", input={}),
        _text_block("Some result"),
    ])

    with patch("agents.nodes.research_node.anthropic.AsyncAnthropic") as MockClient:
        mock_messages = AsyncMock()
        mock_messages.create = AsyncMock(return_value=mock_response)
        MockClient.return_value.messages = mock_messages

        events = []
        async for event in research_node_stream(_state()):
            events.append(event)

    tool_use_event = events[0]
    assert tool_use_event["tool_use"]["query"] == ""
