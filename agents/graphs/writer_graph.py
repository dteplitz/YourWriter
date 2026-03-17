"""Main writer LangGraph — handles chat and content generation.

The graph routes between two paths based on user intent:

  Chat path:    START → detect_intent → chat_node → END
  Write path:   START → detect_intent → outline → draft → refine → respond → END

State is carried in WriterState, a TypedDict that holds messages,
identity information, constraints, and intermediate writing artifacts.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END

from agents.nodes.chat_node import chat_node
from agents.nodes.writing_nodes import outline_node, draft_node, refine_node


# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------

class WriterState(TypedDict, total=False):
    """State carried through the writer graph."""

    messages: list[dict[str, str]]
    writer_id: str
    writer_name: str
    identity: dict[str, Any]
    constraints: dict[str, Any]
    mode: Literal["chat", "write"]
    outline: str
    draft: str
    refined_content: str
    evolution_pending: bool


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

async def detect_intent_node(state: WriterState) -> dict[str, Any]:
    """Determine whether the user wants to chat or write content.

    Uses simple heuristics on the latest user message.  A future version
    may call the LLM for more nuanced intent detection.
    """
    messages = state.get("messages", [])
    latest = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            latest = msg.get("content", "").lower()
            break

    # Writing-intent keywords
    write_signals = [
        "write", "draft", "compose", "create", "generate",
        "story", "article", "essay", "poem", "chapter",
        "blog post", "tweet", "script", "outline",
        "write me", "can you write", "please write",
    ]

    mode: Literal["chat", "write"] = "chat"
    for signal in write_signals:
        if re.search(r'\b' + re.escape(signal) + r'\b', latest):
            mode = "write"
            break

    return {"mode": mode}


def route_by_mode(state: WriterState) -> str:
    """Edge function: route to chat or writing pipeline based on mode."""
    return "chat_node" if state.get("mode") == "chat" else "outline_node"


async def respond_node(state: WriterState) -> dict[str, Any]:
    """Deliver the final refined content back as an assistant message.

    Appends the polished content to the message history and flags the
    session for evolution processing.
    """
    refined = state.get("refined_content", "")
    updated_messages = list(state.get("messages", []))
    updated_messages.append({"role": "assistant", "content": refined})

    return {
        "messages": updated_messages,
        "evolution_pending": True,
    }


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_writer_graph() -> StateGraph:
    """Construct and return the compiled writer StateGraph."""
    graph = StateGraph(WriterState)

    # Add nodes
    graph.add_node("detect_intent", detect_intent_node)
    graph.add_node("chat_node", chat_node)
    graph.add_node("outline_node", outline_node)
    graph.add_node("draft_node", draft_node)
    graph.add_node("refine_node", refine_node)
    graph.add_node("respond_node", respond_node)

    # Edges
    graph.add_edge(START, "detect_intent")
    graph.add_conditional_edges(
        "detect_intent",
        route_by_mode,
        {"chat_node": "chat_node", "outline_node": "outline_node"},
    )
    graph.add_edge("chat_node", END)
    graph.add_edge("outline_node", "draft_node")
    graph.add_edge("draft_node", "refine_node")
    graph.add_edge("refine_node", "respond_node")
    graph.add_edge("respond_node", END)

    return graph


# Pre-compiled graph instance — ready to invoke
writer_graph = build_writer_graph().compile()
