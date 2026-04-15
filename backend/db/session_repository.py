"""Repository helpers for StudioSession and StudioTake lifecycle + reads."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from backend.db.models import StudioSession, StudioTake

_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "active": {"complete", "abandoned"},
    "complete": {"imported", "skipped"},
    "imported": set(),
    "skipped": set(),
    "abandoned": set(),
}


async def create_session(
    db: AsyncSession,
    writer_id: int,
    brief_json: dict,
) -> StudioSession:
    session = StudioSession(writer_id=writer_id, brief_json=brief_json)
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


async def create_take(
    db: AsyncSession,
    session_id: int,
    take_number: int,
    iteration_notes: str | None = None,
) -> StudioTake:
    take = StudioTake(
        session_id=session_id,
        take_number=take_number,
        iteration_notes=iteration_notes,
    )
    db.add(take)
    await db.flush()
    await db.refresh(take)
    return take


async def update_take_content(
    db: AsyncSession,
    take_id: int,
    content: str,
    title: str,
) -> None:
    result = await db.execute(select(StudioTake).where(StudioTake.id == take_id))
    take = result.scalar_one()
    take.content = content
    take.title = title
    await db.flush()


async def get_session_with_takes(db: AsyncSession, session_id: int) -> StudioSession | None:
    result = await db.execute(
        select(StudioSession)
        .where(StudioSession.id == session_id)
        .options(selectinload(StudioSession.takes))
    )
    return result.scalar_one_or_none()


async def list_sessions_for_writer(
    db: AsyncSession,
    writer_id: int,
    *,
    include_abandoned: bool = False,
) -> list[StudioSession]:
    query = (
        select(StudioSession)
        .where(StudioSession.writer_id == writer_id)
        .options(selectinload(StudioSession.takes))
        .order_by(StudioSession.updated_at.desc(), StudioSession.id.desc())
    )
    if not include_abandoned:
        query = query.where(StudioSession.lifecycle != "abandoned")

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_owned_session_with_takes(
    db: AsyncSession,
    session_id: int,
) -> StudioSession | None:
    result = await db.execute(
        select(StudioSession)
        .where(StudioSession.id == session_id)
        .options(
            selectinload(StudioSession.takes),
            joinedload(StudioSession.writer),
        )
    )
    return result.unique().scalar_one_or_none()


async def advance_lifecycle(
    db: AsyncSession,
    session_id: int,
    new_lifecycle: str,
) -> StudioSession:
    result = await db.execute(select(StudioSession).where(StudioSession.id == session_id))
    session = result.scalar_one()
    allowed = _ALLOWED_TRANSITIONS.get(session.lifecycle, set())
    if new_lifecycle not in allowed:
        raise ValueError(
            f"Invalid lifecycle transition: {session.lifecycle!r} -> {new_lifecycle!r}. "
            f"Allowed: {allowed or 'none'}"
        )
    session.lifecycle = new_lifecycle
    await db.flush()
    return session
