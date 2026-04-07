"""YourWriter agent layer — LangGraph pipelines, tools, and evolution logic.

Top-level exports for convenient access to the compiled graphs,
key functions, and identity types.
"""

from agents.graphs.evolution_graph import (
    evolution_graph,
    EvolutionState,
    build_evolution_graph,
)
from agents.evolution.identity import Identity
from agents.evolution.templates import DEFAULT_IDENTITY
from agents.evolution.diff import compare_identities

__all__ = [
    # Graphs
    "evolution_graph",
    "EvolutionState",
    "build_evolution_graph",
    # Identity
    "Identity",
    "DEFAULT_IDENTITY",
    "compare_identities",
]
