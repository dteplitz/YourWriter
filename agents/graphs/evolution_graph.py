"""Evolution LangGraph — 2-stage identity evolution pipeline.

Implements the following flow:

    START → detect_node → [should_evolve?]
                                ├── no  → END
                                └── yes → compute_node → apply_node → END

detect_node (Haiku):   decides IF the conversation contains identity-shaping signals.
compute_node (Sonnet): decides WHAT changes to propose.
apply_node (no LLM):   applies the structured changes to current_identity.

The graph returns the final state dict.  Persistence (creating a new
WriterIdentity row + EvolutionLog entries) is handled outside the graph by
the evolution service.
"""

from __future__ import annotations

from typing import Any, Literal

from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END

from agents.nodes.evolution_nodes import detect_node, compute_node, apply_node


# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------

class EvolutionState(TypedDict, total=False):
    """State carried through the evolution graph."""

    writer_id: int
    current_identity: dict[str, Any]
    chat_history: list[dict]         # [{"role": "user"|"assistant", "content": "..."}]
    last_user_message: str

    # detect_node output
    should_evolve: bool
    confidence: float
    signal: str

    # compute_node output
    changes: list[dict[str, Any]]
    reasoning: str

    # apply_node output
    updated_identity: dict[str, Any]


# ---------------------------------------------------------------------------
# Conditional routing
# ---------------------------------------------------------------------------

def _route_after_detect(state: EvolutionState) -> Literal["compute", "__end__"]:
    """Route to compute_node if evolution was detected, otherwise END."""
    if state.get("should_evolve"):
        return "compute"
    return "__end__"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_evolution_graph() -> StateGraph:
    """Construct and return the compiled evolution StateGraph."""
    graph = StateGraph(EvolutionState)

    # Nodes
    graph.add_node("detect", detect_node)
    graph.add_node("compute", compute_node)
    graph.add_node("apply", apply_node)

    # Edges
    graph.add_edge(START, "detect")
    graph.add_conditional_edges(
        "detect",
        _route_after_detect,
        {"compute": "compute", "__end__": END},
    )
    graph.add_edge("compute", "apply")
    graph.add_edge("apply", END)

    return graph


# Pre-compiled graph instance — import and invoke directly
evolution_graph = build_evolution_graph().compile()
