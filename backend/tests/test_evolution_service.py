"""Tests for the evolution service — run_evolution() and persist_evolution()."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from agents.evolution.result import EvolutionResult
from agents.nodes.evolution_nodes import apply_node
from backend.db.database import Base
from backend.db import models  # noqa: F401 — ensure models are registered
from backend.db.models import Writer, WriterIdentity, User
from backend.services.evolution_service import run_evolution, persist_evolution


# ---------------------------------------------------------------------------
# In-memory SQLite fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def engine():
    """Create a fresh SQLite in-memory engine for each test."""
    _engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield _engine
    await _engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    """Yield a fresh AsyncSession bound to the in-memory engine."""
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def writer_with_identity(db_session: AsyncSession):
    """Create a User, Writer, and initial WriterIdentity in the test DB."""
    user = User(
        email="test@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()

    writer = Writer(
        user_id=user.id,
        name="Test Writer",
        purpose="testing",
    )
    db_session.add(writer)
    await db_session.flush()

    identity = WriterIdentity(
        writer_id=writer.id,
        personality={"voice": "neutral"},
        emotions={"melancholy": 0.3, "curiosity": 0.5},
        memories=["A memory from the past"],
        topics=["poetry"],
        constraints={},
        lifelong_objectives=["write beautifully"],
        version=1,
    )
    db_session.add(identity)
    await db_session.flush()

    return writer, identity


# ---------------------------------------------------------------------------
# Test: run_evolution returns EvolutionResult when should_evolve is True
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_evolution_returns_result_when_should_evolve_true():
    """When the graph returns should_evolve=True, run_evolution returns an EvolutionResult."""
    current_identity = {
        "purpose": "testing",
        "personality": {"voice": "neutral"},
        "emotions": {"melancholy": 0.3},
        "memories": [],
        "topics": ["poetry"],
        "constraints": {},
        "lifelong_objectives": [],
    }
    updated_identity = {
        **current_identity,
        "emotions": {"melancholy": 0.5},
    }

    with patch("backend.services.evolution_service.evolution_graph") as mock_graph:
        mock_graph.ainvoke = AsyncMock(return_value={
            "should_evolve": True,
            "confidence": 0.9,
            "signal": "Usuario reforzó explícitamente el estilo oscuro en múltiples exchanges",
            "changes": [
                {
                    "field": "emotions",
                    "action": "modify",
                    "key": "melancholy",
                    "old_value": 0.3,
                    "new_value": 0.5,
                    "reason": "User repeatedly reinforced dark, melancholic tone",
                }
            ],
            "reasoning": "The user consistently pushed for a darker aesthetic.",
            "updated_identity": updated_identity,
        })

        result = await run_evolution(
            current_identity=current_identity,
            chat_history=[{"role": "user", "content": "quiero que seas más oscuro"}],
            last_user_message="quiero que seas más oscuro, seguí así",
        )

    assert result is not None
    assert isinstance(result, EvolutionResult)
    assert result.confidence == 0.9
    assert result.signal == "Usuario reforzó explícitamente el estilo oscuro en múltiples exchanges"
    assert len(result.changes) == 1
    assert result.changes[0]["field"] == "emotions"
    assert result.changes[0]["key"] == "melancholy"
    assert result.updated_identity["emotions"]["melancholy"] == 0.5
    assert result.reasoning == "The user consistently pushed for a darker aesthetic."


# ---------------------------------------------------------------------------
# Test: run_evolution returns None when should_evolve is False
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_evolution_returns_none_when_should_evolve_false():
    """When the graph returns should_evolve=False, run_evolution returns None."""
    current_identity = {
        "purpose": "testing",
        "personality": {"voice": "neutral"},
        "emotions": {"melancholy": 0.3},
        "memories": [],
        "topics": [],
        "constraints": {},
        "lifelong_objectives": [],
    }

    with patch("backend.services.evolution_service.evolution_graph") as mock_graph:
        mock_graph.ainvoke = AsyncMock(return_value={
            "should_evolve": False,
            "confidence": 0.1,
            "signal": "",
        })

        result = await run_evolution(
            current_identity=current_identity,
            chat_history=[{"role": "user", "content": "write this in a formal tone"}],
            last_user_message="write this in a formal tone",
        )

    assert result is None


# ---------------------------------------------------------------------------
# Test: persist_evolution creates a new WriterIdentity version and EvolutionLog
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_persist_evolution_creates_new_version(
    db_session: AsyncSession,
    writer_with_identity,
):
    """persist_evolution creates a new WriterIdentity with version+1 and EvolutionLog entries."""
    writer, initial_identity = writer_with_identity

    updated_identity = {
        "purpose": "testing",
        "personality": {"voice": "lacónico"},
        "emotions": {"melancholy": 0.5, "curiosity": 0.5},
        "memories": ["A memory from the past"],
        "topics": ["poetry", "noir fiction"],
        "constraints": {},
        "lifelong_objectives": ["write beautifully"],
    }

    result = EvolutionResult(
        changes=[
            {
                "field": "emotions",
                "action": "modify",
                "key": "melancholy",
                "old_value": 0.3,
                "new_value": 0.5,
                "reason": "User reinforced dark tone",
            },
            {
                "field": "topics",
                "action": "add",
                "value": "noir fiction",
                "reason": "User mentioned noir fiction repeatedly",
            },
        ],
        reasoning="Gradual shift toward darker aesthetic.",
        updated_identity=updated_identity,
        signal="User reinforced dark tone across multiple exchanges",
        confidence=0.85,
    )

    new_identity = await persist_evolution(
        db=db_session,
        writer_id=writer.id,
        result=result,
    )

    # New version should be initial + 1
    assert new_identity.version == initial_identity.version + 1
    assert new_identity.writer_id == writer.id

    # Updated emotions should be persisted
    assert new_identity.emotions["melancholy"] == 0.5

    # Updated topics should include the new one
    assert "noir fiction" in new_identity.topics

    # Two EvolutionLog entries should have been created
    from sqlalchemy import select
    from backend.db.models import EvolutionLog

    log_result = await db_session.execute(
        select(EvolutionLog).where(EvolutionLog.writer_id == writer.id)
    )
    logs = log_result.scalars().all()
    assert len(logs) == 2

    log_fields = {log.field_changed for log in logs}
    assert "emotions" in log_fields
    assert "topics" in log_fields


# ---------------------------------------------------------------------------
# Test: apply_node correctly modifies dict fields (emotions, personality)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_apply_node_dict_fields():
    """apply_node correctly applies modify/add/remove on dict-type identity fields."""
    current_identity = {
        "purpose": "testing",
        "personality": {"voice": "neutral", "rhythm": "fast"},
        "emotions": {"melancholy": 0.3, "curiosity": 0.6},
        "memories": [],
        "topics": ["poetry"],
        "constraints": {},
        "lifelong_objectives": ["write beautifully"],
    }

    state = {
        "current_identity": current_identity,
        "changes": [
            # Modify an existing emotion
            {
                "field": "emotions",
                "action": "modify",
                "key": "melancholy",
                "old_value": 0.3,
                "new_value": 0.5,
                "reason": "test",
            },
            # Add a new emotion
            {
                "field": "emotions",
                "action": "add",
                "key": "joy",
                "new_value": 0.2,
                "reason": "test",
            },
            # Modify a personality key
            {
                "field": "personality",
                "action": "modify",
                "key": "voice",
                "old_value": "neutral",
                "new_value": "lacónico",
                "reason": "test",
            },
            # Remove a personality key
            {
                "field": "personality",
                "action": "remove",
                "key": "rhythm",
                "reason": "test",
            },
            # Add a topic (list field)
            {
                "field": "topics",
                "action": "add",
                "value": "noir fiction",
                "reason": "test",
            },
            # Remove a topic (list field)
            {
                "field": "topics",
                "action": "remove",
                "value": "poetry",
                "reason": "test",
            },
        ],
    }

    result = await apply_node(state)

    updated = result["updated_identity"]

    # Emotion modified correctly
    assert updated["emotions"]["melancholy"] == 0.5

    # New emotion added
    assert updated["emotions"]["joy"] == 0.2

    # Emotion unchanged
    assert updated["emotions"]["curiosity"] == 0.6

    # Personality voice updated
    assert updated["personality"]["voice"] == "lacónico"

    # Personality rhythm removed
    assert "rhythm" not in updated["personality"]

    # Topic added
    assert "noir fiction" in updated["topics"]

    # Topic removed
    assert "poetry" not in updated["topics"]

    # Unchanged fields preserved
    assert updated["purpose"] == "testing"
    assert updated["lifelong_objectives"] == ["write beautifully"]
