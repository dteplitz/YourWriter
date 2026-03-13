from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.models import Writer, WriterIdentity

# ---------------------------------------------------------------------------
# Default identity template — used when creating a new writer
# ---------------------------------------------------------------------------

DEFAULT_PERSONALITY: dict = {
    "voice": "neutral",
    "style": "clear and concise",
    "creativity": 0.7,
}

DEFAULT_EMOTIONS: dict = {
    "enthusiasm": 0.5,
    "empathy": 0.5,
    "humor": 0.3,
}

DEFAULT_LIFELONG_OBJECTIVES: list = [
    "Continuously improve writing quality",
    "Adapt to user preferences over time",
]


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------


async def create_writer(
    db: AsyncSession,
    user_id: int,
    name: str,
    purpose: str = "",
    style_description: str = "",
) -> Writer:
    """Create a new writer with a default identity and return it."""
    writer = Writer(user_id=user_id, name=name, purpose=purpose)
    db.add(writer)
    await db.flush()

    personality = dict(DEFAULT_PERSONALITY)
    if style_description:
        personality["style_description"] = style_description

    identity = WriterIdentity(
        writer_id=writer.id,
        personality=personality,
        emotions=DEFAULT_EMOTIONS,
        memories=[],
        topics=[],
        constraints={},
        lifelong_objectives=DEFAULT_LIFELONG_OBJECTIVES,
        version=1,
    )
    db.add(identity)
    await db.flush()
    await db.refresh(writer)
    return writer


async def get_writers(db: AsyncSession, user_id: int) -> list[Writer]:
    """Return all writers belonging to *user_id*."""
    result = await db.execute(
        select(Writer)
        .where(Writer.user_id == user_id)
        .order_by(Writer.created_at.desc())
    )
    return list(result.scalars().all())


async def get_writer(db: AsyncSession, writer_id: int, user_id: int) -> Writer:
    """Return a single writer, ensuring it belongs to *user_id*.

    Raises 404 if not found or not owned by the user.
    """
    result = await db.execute(
        select(Writer)
        .options(selectinload(Writer.identities))
        .where(Writer.id == writer_id, Writer.user_id == user_id)
    )
    writer = result.scalar_one_or_none()
    if writer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Writer not found")
    return writer


async def update_writer(
    db: AsyncSession,
    writer_id: int,
    user_id: int,
    name: str | None = None,
    purpose: str | None = None,
) -> Writer:
    """Update a writer's name and/or purpose."""
    writer = await get_writer(db, writer_id, user_id)
    if name is not None:
        writer.name = name
    if purpose is not None:
        writer.purpose = purpose
    await db.flush()
    await db.refresh(writer)
    return writer


async def delete_writer(db: AsyncSession, writer_id: int, user_id: int) -> None:
    """Delete a writer (cascading to identity, messages, evolution logs)."""
    writer = await get_writer(db, writer_id, user_id)
    await db.delete(writer)
    await db.flush()
