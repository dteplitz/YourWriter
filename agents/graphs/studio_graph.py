"""Studio LangGraph runtime with persistent checkpointing.

This graph powers the Studio writing pipeline:

    START -> research -> outline -> draft -> refine -> END

It reuses the existing writing/research nodes and wraps them in LangGraph
nodes that emit the same streaming signals the frontend already consumes.
Checkpointing is intentionally runtime-only: product lifecycle and DB
entities remain outside the graph.
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from agents.nodes.research_node import research_node_stream
from agents.nodes.writing_nodes import draft_node, outline_node, studio_refine_node_stream
from backend.db.database import DATABASE_URL


_TITLE_PATTERN = re.compile(r"\n---TITLE:\s*(.+?)---\s*$", re.DOTALL)


class StudioState(TypedDict, total=False):
    """Persisted Studio pipeline state keyed by StudioSession.id."""

    writer_id: int
    writer_name: str
    identity: dict[str, Any]
    brief: dict[str, Any]
    iteration_notes: str | None
    studio_request: str
    take_id: int
    take_number: int
    search_results: str
    outline: str
    draft: str
    refined_content: str
    title: str
    word_count: int


def _normalize_checkpoint_conn_string(database_url: str) -> str:
    """Convert the app DB URL into a psycopg-compatible Postgres URL."""
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql://", 1)
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if database_url.startswith("postgresql://"):
        return database_url
    raise RuntimeError("Studio checkpointer requires PostgreSQL DATABASE_URL")


def studio_checkpointer_enabled() -> bool:
    """Return True when the app is configured to use PostgreSQL."""
    return DATABASE_URL.startswith("postgres")


@asynccontextmanager
async def open_studio_checkpointer() -> AsyncIterator[AsyncPostgresSaver]:
    """Open a Postgres-backed LangGraph checkpointer for the Studio graph."""
    conn_string = _normalize_checkpoint_conn_string(DATABASE_URL)
    async with AsyncPostgresSaver.from_conn_string(conn_string) as checkpointer:
        yield checkpointer


async def setup_studio_checkpointer() -> None:
    """Create/check LangGraph checkpoint tables during app startup."""
    if not studio_checkpointer_enabled():
        return
    async with open_studio_checkpointer() as checkpointer:
        await checkpointer.setup()


def parse_studio_output(buffer: str) -> tuple[str, str]:
    """Extract the generated title marker from the refine stream output."""
    match = _TITLE_PATTERN.search(buffer)
    if match:
        title = match.group(1).strip()
        content = buffer[: match.start()].rstrip()
    else:
        title = "Untitled"
        content = buffer
    return title, content


def _to_node_state(state: StudioState) -> dict[str, Any]:
    """Adapt persisted StudioState to the existing writing node contract."""
    identity = state.get("identity", {})
    return {
        "messages": [{"role": "user", "content": state.get("studio_request", "")}],
        "writer_id": str(state.get("writer_id", "")),
        "writer_name": state.get("writer_name", "Writer"),
        "identity": identity,
        "constraints": identity.get("constraints", {}),
        "search_results": state.get("search_results", ""),
        "outline": state.get("outline", ""),
        "draft": state.get("draft", ""),
    }


async def research_step(state: StudioState) -> dict[str, Any]:
    """Run the optional web research step and forward tool events."""
    stream = get_stream_writer()

    async for event in research_node_stream(_to_node_state(state)):
        if "search_results" in event:
            return {"search_results": event["search_results"]}
        stream(event)

    return {"search_results": ""}


async def outline_step(state: StudioState) -> dict[str, Any]:
    """Generate the outline and emit the current phase."""
    get_stream_writer()({"phase": "outlining"})
    return await outline_node(_to_node_state(state))


async def draft_step(state: StudioState) -> dict[str, Any]:
    """Generate the draft and emit the current phase."""
    get_stream_writer()({"phase": "drafting"})
    return await draft_node(_to_node_state(state))


async def refine_step(state: StudioState) -> dict[str, Any]:
    """Stream the refine step, parse the final title and persist the result in state."""
    stream = get_stream_writer()
    stream({"phase": "refining"})

    buffer = ""
    async for token in studio_refine_node_stream(_to_node_state(state)):
        buffer += token
        stream(token)

    title, content = parse_studio_output(buffer)
    word_count = len(content.split()) if content.strip() else 0

    return {
        "refined_content": content,
        "title": title,
        "word_count": word_count,
    }


def build_studio_graph() -> StateGraph:
    """Build the Studio writing graph without binding a checkpointer."""
    graph = StateGraph(StudioState)

    graph.add_node("research", research_step)
    graph.add_node("outline", outline_step)
    graph.add_node("draft", draft_step)
    graph.add_node("refine", refine_step)

    graph.add_edge(START, "research")
    graph.add_edge("research", "outline")
    graph.add_edge("outline", "draft")
    graph.add_edge("draft", "refine")
    graph.add_edge("refine", END)

    return graph
