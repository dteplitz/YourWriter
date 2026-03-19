"""Evolution service — orchestrates the evolution pipeline and persists results.

Two responsibilities:
  run_evolution()     — runs the LangGraph pipeline, no DB access.
  persist_evolution() — writes the new WriterIdentity version + EvolutionLog
                        entries to DB.  Must be called with a SHORT-LIVED session,
                        never during or after an LLM call in the same session.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from agents.evolution.result import EvolutionResult
from backend.db.models import WriterIdentity, EvolutionLog


async def run_evolution(
    current_identity: dict,
    chat_history: list[dict],
    last_user_message: str,
) -> EvolutionResult | None:
    """Run the evolution graph.  No DB access.

    Returns None if detect_node decides no evolution should happen.
    Returns an EvolutionResult with the proposed changes and updated identity
    if evolution was triggered.

    Parameters
    ----------
    current_identity:
        The writer's current identity as a plain dict.
    chat_history:
        List of message dicts: [{"role": "user"|"assistant", "content": "..."}]
    last_user_message:
        The most recent user message (also the evolution trigger candidate).
    """
    # Import inside function to avoid circular imports at module load time
    from agents.graphs.evolution_graph import evolution_graph

    result = await evolution_graph.ainvoke({
        "current_identity": current_identity,
        "chat_history": chat_history,
        "last_user_message": last_user_message,
    })

    if not result.get("should_evolve"):
        return None

    return EvolutionResult(
        changes=result.get("changes", []),
        reasoning=result.get("reasoning", ""),
        updated_identity=result.get("updated_identity", current_identity),
        signal=result.get("signal", ""),
        confidence=float(result.get("confidence", 0.0)),
    )


async def persist_evolution(
    db: AsyncSession,
    writer_id: int,
    result: EvolutionResult,
) -> WriterIdentity:
    """Persist a new identity version and EvolutionLog entries.

    Creates a new WriterIdentity row with version = current_version + 1.
    Creates one EvolutionLog row per change in result.changes.
    Uses flush() + refresh() so callers can read the new row immediately.

    This must be called with a short-lived session opened OUTSIDE any ongoing
    LLM call — never hold the session open during LLM inference.

    Parameters
    ----------
    db:
        An open AsyncSession.
    writer_id:
        The DB id of the writer being evolved.
    result:
        The EvolutionResult from run_evolution().

    Returns
    -------
    WriterIdentity
        The newly created identity row (refreshed from DB).
    """
    # Load the current (latest) version to get the version number and fallback fields
    query = (
        select(WriterIdentity)
        .where(WriterIdentity.writer_id == writer_id)
        .order_by(WriterIdentity.version.desc())
        .limit(1)
    )
    row = await db.execute(query)
    current = row.scalar_one()

    identity = result.updated_identity

    new_identity = WriterIdentity(
        writer_id=writer_id,
        personality=identity.get("personality", current.personality),
        emotions=identity.get("emotions", current.emotions),
        memories=identity.get("memories", current.memories),
        topics=identity.get("topics", current.topics),
        constraints=identity.get("constraints", current.constraints),
        lifelong_objectives=identity.get("lifelong_objectives", current.lifelong_objectives),
        version=current.version + 1,
    )
    db.add(new_identity)

    for change in result.changes:
        log = EvolutionLog(
            writer_id=writer_id,
            field_changed=change.get("field", ""),
            old_value=str(change.get("old_value", change.get("value", ""))),
            new_value=str(change.get("new_value", change.get("value", ""))),
            reason=change.get("reason", ""),
        )
        db.add(log)

    await db.flush()
    await db.refresh(new_identity)
    return new_identity
