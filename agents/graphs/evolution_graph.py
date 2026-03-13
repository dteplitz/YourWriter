"""Evolution LangGraph — reflects on a writing session and evolves identity.

Linear pipeline: analyze → evaluate → decide → apply → END

Runs after a writing session completes.  Takes the current identity,
the content that was produced, and user feedback, then outputs a set
of proposed identity changes with reasoning.
"""

from __future__ import annotations

from typing import Any

from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END

from agents.nodes.evolution_nodes import (
    analyze_node,
    evaluate_node,
    decide_node,
    apply_node,
)


# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------

class EvolutionState(TypedDict, total=False):
    """State carried through the evolution graph."""

    writer_id: str
    current_identity: dict[str, Any]
    content_written: str
    user_feedback: str
    # Intermediate fields populated by nodes
    analysis: str
    evaluation: str
    changes: list[dict[str, Any]]
    reasoning: str


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_evolution_graph() -> StateGraph:
    """Construct and return the compiled evolution StateGraph."""
    graph = StateGraph(EvolutionState)

    # Add nodes
    graph.add_node("analyze", analyze_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("decide", decide_node)
    graph.add_node("apply", apply_node)

    # Linear flow
    graph.add_edge(START, "analyze")
    graph.add_edge("analyze", "evaluate")
    graph.add_edge("evaluate", "decide")
    graph.add_edge("decide", "apply")
    graph.add_edge("apply", END)

    return graph


# Pre-compiled graph instance — ready to invoke
evolution_graph = build_evolution_graph().compile()
