"""Evolution sub-package — identity management and evolution logic."""

from agents.evolution.identity import Identity
from agents.evolution.diff import compare_identities
from agents.evolution.templates import DEFAULT_IDENTITY

__all__ = [
    "Identity",
    "compare_identities",
    "DEFAULT_IDENTITY",
]
