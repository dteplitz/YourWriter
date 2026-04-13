"""Tests for session_repository: CRUD and lifecycle transitions."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.db.database import Base
from backend.db.models import User, Writer
from backend.db import session_repository


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    engine = create_async_engine(TEST_DATABASE_URL, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        # Seed a user and writer
        user = User(email="test@test.com", hashed_password="x")
        session.add(user)
        await session.flush()

        writer = Writer(user_id=user.id, name="Test Writer", purpose="testing")
        session.add(writer)
        await session.commit()
        await session.refresh(writer)

        session.info["writer_id"] = writer.id
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_session(db):
    writer_id = db.info["writer_id"]
    brief = {"format": "poem", "tone": "melancholic"}

    studio_session = await session_repository.create_session(db, writer_id, brief)
    await db.commit()

    assert studio_session.id is not None
    assert studio_session.writer_id == writer_id
    assert studio_session.brief_json == brief
    assert studio_session.lifecycle == "active"


@pytest.mark.asyncio
async def test_create_take(db):
    writer_id = db.info["writer_id"]
    studio_session = await session_repository.create_session(db, writer_id, {"format": "essay"})
    await db.commit()

    take = await session_repository.create_take(db, studio_session.id, take_number=1, iteration_notes="Try a darker tone")
    await db.commit()

    assert take.id is not None
    assert take.session_id == studio_session.id
    assert take.take_number == 1
    assert take.iteration_notes == "Try a darker tone"
    assert take.content == ""


@pytest.mark.asyncio
async def test_update_take_content(db):
    writer_id = db.info["writer_id"]
    studio_session = await session_repository.create_session(db, writer_id, {"format": "poem"})
    await db.commit()

    take = await session_repository.create_take(db, studio_session.id, take_number=1)
    await db.commit()

    await session_repository.update_take_content(db, take.id, content="The final poem.", title="Ode to Nothing")
    await db.commit()

    refreshed = await session_repository.get_session_with_takes(db, studio_session.id)
    assert refreshed is not None
    assert refreshed.takes[0].content == "The final poem."
    assert refreshed.takes[0].title == "Ode to Nothing"


@pytest.mark.asyncio
async def test_get_session_with_takes_orders_by_take_number(db):
    writer_id = db.info["writer_id"]
    studio_session = await session_repository.create_session(db, writer_id, {"format": "essay"})
    await db.commit()

    await session_repository.create_take(db, studio_session.id, take_number=2)
    await session_repository.create_take(db, studio_session.id, take_number=1)
    await db.commit()

    loaded = await session_repository.get_session_with_takes(db, studio_session.id)
    assert loaded is not None
    assert [t.take_number for t in loaded.takes] == [1, 2]


@pytest.mark.asyncio
async def test_advance_lifecycle_valid_transition(db):
    writer_id = db.info["writer_id"]
    studio_session = await session_repository.create_session(db, writer_id, {})
    await db.commit()

    updated = await session_repository.advance_lifecycle(db, studio_session.id, "complete")
    await db.commit()

    assert updated.lifecycle == "complete"


@pytest.mark.asyncio
async def test_advance_lifecycle_invalid_transition_raises(db):
    writer_id = db.info["writer_id"]
    studio_session = await session_repository.create_session(db, writer_id, {})
    await db.commit()

    with pytest.raises(ValueError, match="Invalid lifecycle transition"):
        await session_repository.advance_lifecycle(db, studio_session.id, "imported")


@pytest.mark.asyncio
async def test_advance_lifecycle_complete_to_imported(db):
    writer_id = db.info["writer_id"]
    studio_session = await session_repository.create_session(db, writer_id, {})
    await db.commit()

    await session_repository.advance_lifecycle(db, studio_session.id, "complete")
    updated = await session_repository.advance_lifecycle(db, studio_session.id, "imported")
    await db.commit()

    assert updated.lifecycle == "imported"


@pytest.mark.asyncio
async def test_get_session_with_takes_returns_none_for_missing(db):
    result = await session_repository.get_session_with_takes(db, session_id=9999)
    assert result is None
