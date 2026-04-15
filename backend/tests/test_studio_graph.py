"""Tests for the Studio LangGraph runtime."""

import asyncio
from unittest.mock import patch

import pytest
from langgraph.checkpoint.memory import MemorySaver

from agents.graphs.studio_graph import build_studio_graph


def _input_state() -> dict:
    return {
        "writer_id": 1,
        "writer_name": "Test Writer",
        "identity": {
            "purpose": "testing",
            "personality": ["focused"],
            "emotions": ["calm"],
            "constraints": {},
            "lifelong_objectives": [],
        },
        "brief": {
            "format": "essay",
            "tone": "reflective",
            "constraints_applied": [],
            "word_limit": None,
            "notes": None,
            "needs_clarification": False,
            "clarification_question": None,
        },
        "iteration_notes": None,
        "studio_request": "Write a reflective essay.",
        "take_id": 10,
        "take_number": 1,
    }


@pytest.mark.asyncio
async def test_studio_graph_streams_events_and_persists_final_state():
    async def fake_research_node_stream(state):
        yield {
            "tool_use": {
                "name": "web_search",
                "display_name": "Buscando",
                "query": "latest findings",
            }
        }
        yield {
            "tool_result": {
                "name": "web_search",
                "summary": "Fresh context",
            }
        }
        yield {"search_results": "Fresh context"}

    async def fake_outline_node(state):
        return {"outline": "Outline"}

    async def fake_draft_node(state):
        return {"draft": "Draft"}

    async def fake_refine_node_stream(state):
        yield "Polished body."
        yield "\n---TITLE: Final Piece---"

    with (
        patch("agents.graphs.studio_graph.research_node_stream", fake_research_node_stream),
        patch("agents.graphs.studio_graph.outline_node", fake_outline_node),
        patch("agents.graphs.studio_graph.draft_node", fake_draft_node),
        patch("agents.graphs.studio_graph.studio_refine_node_stream", fake_refine_node_stream),
    ):
        graph = build_studio_graph().compile(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "session-1"}}

        events = []
        async for chunk in graph.astream(_input_state(), config, stream_mode="custom"):
            events.append(chunk)

        snapshot = await graph.aget_state(config)

    assert events == [
        {
            "tool_use": {
                "name": "web_search",
                "display_name": "Buscando",
                "query": "latest findings",
            }
        },
        {"tool_result": {"name": "web_search", "summary": "Fresh context"}},
        {"phase": "outlining"},
        {"phase": "drafting"},
        {"phase": "refining"},
        "Polished body.",
        "\n---TITLE: Final Piece---",
    ]
    assert snapshot.values["search_results"] == "Fresh context"
    assert snapshot.values["outline"] == "Outline"
    assert snapshot.values["draft"] == "Draft"
    assert snapshot.values["refined_content"] == "Polished body."
    assert snapshot.values["title"] == "Final Piece"
    assert snapshot.values["word_count"] == 2
    assert snapshot.next == ()


@pytest.mark.asyncio
async def test_studio_graph_resume_restarts_active_refine_node_from_checkpoint():
    gate = asyncio.Event()
    blocked_once = {"value": False}

    async def fake_research_node_stream(state):
        yield {"search_results": ""}

    async def fake_outline_node(state):
        return {"outline": "Outline"}

    async def fake_draft_node(state):
        return {"draft": "Draft"}

    async def fake_refine_node_stream(state):
        yield "First chunk. "
        if not blocked_once["value"]:
            blocked_once["value"] = True
            await gate.wait()
        yield "Second chunk."
        yield "\n---TITLE: Resumed Piece---"

    with (
        patch("agents.graphs.studio_graph.research_node_stream", fake_research_node_stream),
        patch("agents.graphs.studio_graph.outline_node", fake_outline_node),
        patch("agents.graphs.studio_graph.draft_node", fake_draft_node),
        patch("agents.graphs.studio_graph.studio_refine_node_stream", fake_refine_node_stream),
    ):
        graph = build_studio_graph().compile(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "session-2"}}

        agen = graph.astream(_input_state(), config, stream_mode="custom")
        seen = []
        while True:
            chunk = await agen.__anext__()
            seen.append(chunk)
            if chunk == "First chunk. ":
                break
        await agen.aclose()

        interrupted = await graph.aget_state(config)

        resumed_events = []
        async for chunk in graph.astream(None, config, stream_mode="custom"):
            resumed_events.append(chunk)

        final_snapshot = await graph.aget_state(config)

    assert {"phase": "refining"} in seen
    assert "First chunk. " in seen
    assert interrupted.next == ("refine",)

    assert resumed_events[0] == {"phase": "refining"}
    assert resumed_events[1:] == [
        "First chunk. ",
        "Second chunk.",
        "\n---TITLE: Resumed Piece---",
    ]
    assert final_snapshot.values["refined_content"] == "First chunk. Second chunk."
    assert final_snapshot.values["title"] == "Resumed Piece"
    assert final_snapshot.next == ()
