"""EvolutionResult — contrato de retorno del evolution graph.

Lo que run_evolution() retorna cuando detect dice sí.
La persistencia (nueva WriterIdentity + EvolutionLog) la hace evolution_service.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvolutionResult:
    """Resultado del pipeline de evolución.

    Retornado por run_evolution() cuando should_evolve=True.
    Contiene los cambios propuestos, la identidad actualizada y
    el contexto del detect stage.
    """

    changes: list[dict[str, Any]] = field(default_factory=list)
    reasoning: str = ""
    updated_identity: dict[str, Any] = field(default_factory=dict)
    signal: str = ""        # resumen del detect stage: por qué triggereó
    confidence: float = 0.0
