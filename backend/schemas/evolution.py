from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from backend.schemas.identity import IdentityResponse


class EvolutionLogResponse(BaseModel):
    id: int
    writer_id: int
    field_changed: str
    old_value: str | None
    new_value: str | None
    reason: str | None
    source_session_id: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# SSE evolution event (emitido inline en el chat stream post-done)
# ---------------------------------------------------------------------------

class EvolutionChange(BaseModel):
    """Un cambio individual propuesto por el pipeline de evolución."""

    field: str                          # "emotions", "personality", "topics", etc.
    action: Literal["add", "modify", "remove"]
    key: str | None = None              # para dict fields (emotions, personality, constraints)
    old_value: Any = None
    new_value: Any = None
    value: Any = None                   # para list fields (topics, memories, lifelong_objectives)
    reason: str = ""


class EvolutionDetectedEvent(BaseModel):
    """Evento SSE emitido después de done:true cuando hay evolución de general stats."""

    evolution_detected: bool = True
    changes: list[EvolutionChange]
    reasoning: str


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------

class RollbackResponse(BaseModel):
    """Respuesta del endpoint POST /writers/{id}/identity/rollback."""

    writer_id: int
    rolled_back_to_version: int         # versión de la que se copió (N-1)
    new_version: int                    # versión recién creada (N+1)
    identity: IdentityResponse
