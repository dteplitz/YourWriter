"""EvolutionResult dataclass — returned by the evolution pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvolutionResult:
    """Represents the outcome of one evolution pipeline run.

    Produced by ``run_evolution()`` in the evolution service when the detect
    stage decides that the conversation contains identity-shaping signals.
    """

    changes: list[dict[str, Any]] = field(default_factory=list)
    reasoning: str = ""
    updated_identity: dict[str, Any] = field(default_factory=dict)
    signal: str = ""
    confidence: float = 0.0
