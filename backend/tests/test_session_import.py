"""Tests for the post-session import backend flow."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.auth.auth import get_current_user
from backend.db.database import Base
from backend.db.models import EvolutionLog, StudioSession, StudioTake, User, Writer, WriterIdentity
from backend.main import app
from backend.schemas.identity import IdentityResponse
from backend.schemas.session import (
    SessionImportChange,
    SessionImportPlan,
    SessionImportProposalResponse,
    SessionImportRequest,
    SessionImportResponse,
    SessionSkipResponse,
)
from backend.services.session_import_service import (
    SessionImportError,
    apply_session_import,
    generate_import_proposal,
    skip_session_import,
)


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = 1
    return user


@pytest_asyncio.fixture
async def client(mock_user):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def engine():
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield test_engine
    await test_engine.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _seed_import_context(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    lifecycle: str = "active",
) -> dict[str, int]:
    async with session_factory() as db:
        user = User(email="import@test.com", hashed_password="hashed")
        db.add(user)
        await db.flush()

        writer = Writer(user_id=user.id, name="Import Writer", purpose="Write with bite")
        db.add(writer)
        await db.flush()

        identity = WriterIdentity(
            writer_id=writer.id,
            personality={"voice": "precise"},
            emotions={"melancholy": 0.3, "curiosity": 0.4},
            memories=["Old city lights"],
            topics=["urban life"],
            constraints={},
            lifelong_objectives=["Find sharper images"],
            version=1,
        )
        db.add(identity)
        await db.flush()

        studio_session = StudioSession(
            writer_id=writer.id,
            brief_json={
                "format": "short story",
                "tone": "noir",
                "constraints_applied": [],
                "word_limit": 800,
                "notes": "Focus on the city at night",
                "needs_clarification": False,
                "clarification_question": None,
            },
            lifecycle=lifecycle,
        )
        db.add(studio_session)
        await db.flush()

        db.add_all(
            [
                StudioTake(
                    session_id=studio_session.id,
                    take_number=1,
                    iteration_notes=None,
                    title="Night Shift",
                    content="The avenue smelled like rain and copper.",
                ),
                StudioTake(
                    session_id=studio_session.id,
                    take_number=2,
                    iteration_notes="Push the melancholy harder",
                    title="Night Shift Again",
                    content="The avenue smelled like rain, copper, and old regret.",
                ),
            ]
        )
        await db.commit()

        return {
            "user_id": user.id,
            "writer_id": writer.id,
            "session_id": studio_session.id,
        }


@pytest.mark.asyncio
async def test_generate_import_proposal_transitions_active_session_to_complete(session_factory, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    seeded = await _seed_import_context(session_factory, lifecycle="active")
    proposal = SessionImportPlan(
        changes=[
            SessionImportChange(
                field="emotions",
                action="modify",
                key="melancholy",
                old_value=0.3,
                new_value=0.45,
                reason="The writer leaned into lasting noir melancholy across both takes.",
            )
        ],
        overall_reasoning="The session consistently reinforced a darker emotional baseline.",
    )

    with (
        patch("backend.services.session_import_service.async_session", session_factory),
        patch(
            "backend.services.session_import_service._generate_import_plan",
            AsyncMock(return_value=proposal),
        ),
    ):
        response = await generate_import_proposal(seeded["session_id"], seeded["user_id"])

    assert response.lifecycle == "complete"
    assert response.session_id == seeded["session_id"]
    assert len(response.changes) == 1
    assert response.changes[0].key == "melancholy"

    async with session_factory() as db:
        stored_session = await db.get(StudioSession, seeded["session_id"])
        assert stored_session is not None
        assert stored_session.lifecycle == "complete"


@pytest.mark.asyncio
async def test_generate_import_proposal_allows_empty_result(session_factory, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    seeded = await _seed_import_context(session_factory, lifecycle="active")

    with (
        patch("backend.services.session_import_service.async_session", session_factory),
        patch(
            "backend.services.session_import_service._generate_import_plan",
            AsyncMock(return_value=SessionImportPlan(changes=[], overall_reasoning="")),
        ),
    ):
        response = await generate_import_proposal(seeded["session_id"], seeded["user_id"])

    assert response.lifecycle == "complete"
    assert response.changes == []
    assert response.reasoning == "No durable learning detected from this Studio session."


@pytest.mark.asyncio
async def test_apply_session_import_creates_identity_and_logs_and_marks_imported(session_factory):
    seeded = await _seed_import_context(session_factory, lifecycle="complete")
    request = SessionImportRequest(
        changes=[
            SessionImportChange(
                field="emotions",
                action="modify",
                key="melancholy",
                old_value=0.3,
                new_value=0.45,
                reason="The final direction stayed durably more noir and wistful.",
            ),
            SessionImportChange(
                field="topics",
                action="add",
                value="urban decay",
                reason="Both takes returned to city corrosion as a core fascination.",
            ),
        ],
        reasoning="This session revealed a stable pull toward nocturnal urban melancholy.",
    )

    with patch("backend.services.session_import_service.async_session", session_factory):
        response = await apply_session_import(seeded["session_id"], seeded["user_id"], request)

    assert response.lifecycle == "imported"
    assert response.identity.version == 2
    assert response.identity.emotions["melancholy"] == 0.45
    assert "urban decay" in response.identity.topics

    async with session_factory() as db:
        stored_session = await db.get(StudioSession, seeded["session_id"])
        assert stored_session is not None
        assert stored_session.lifecycle == "imported"

        identity_count = await db.scalar(
            select(func.count()).select_from(WriterIdentity).where(WriterIdentity.writer_id == seeded["writer_id"])
        )
        assert identity_count == 2

        log_result = await db.execute(
            select(EvolutionLog)
            .where(EvolutionLog.writer_id == seeded["writer_id"])
            .order_by(EvolutionLog.id.asc())
        )
        logs = list(log_result.scalars().all())
        assert len(logs) == 2
        assert all("[post_session_import session_id=" in (log.reason or "") for log in logs)


@pytest.mark.asyncio
async def test_skip_session_import_marks_skipped_without_creating_identity(session_factory):
    seeded = await _seed_import_context(session_factory, lifecycle="complete")

    with patch("backend.services.session_import_service.async_session", session_factory):
        response = await skip_session_import(seeded["session_id"], seeded["user_id"])

    assert response.lifecycle == "skipped"

    async with session_factory() as db:
        stored_session = await db.get(StudioSession, seeded["session_id"])
        assert stored_session is not None
        assert stored_session.lifecycle == "skipped"

        identity_count = await db.scalar(
            select(func.count()).select_from(WriterIdentity).where(WriterIdentity.writer_id == seeded["writer_id"])
        )
        assert identity_count == 1


@pytest.mark.asyncio
async def test_import_proposal_endpoint_returns_contract(client):
    proposal = SessionImportProposalResponse(
        session_id=12,
        writer_id=1,
        lifecycle="complete",
        changes=[
            SessionImportChange(
                field="topics",
                action="add",
                value="urban decay",
                reason="The session kept circling back to decaying city imagery.",
            )
        ],
        reasoning="The session exposed a durable thematic fixation.",
    )

    with patch(
        "backend.api.routes.sessions.generate_import_proposal",
        AsyncMock(return_value=proposal),
    ):
        response = await client.post("/api/sessions/12/import-proposal")

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == 12
    assert data["lifecycle"] == "complete"
    assert data["changes"][0]["value"] == "urban decay"


@pytest.mark.asyncio
async def test_import_endpoint_returns_contract(client):
    imported = SessionImportResponse(
        session_id=12,
        writer_id=1,
        lifecycle="imported",
        imported_changes=[
            SessionImportChange(
                field="emotions",
                action="modify",
                key="melancholy",
                old_value=0.3,
                new_value=0.45,
                reason="Durable tonal shift.",
            )
        ],
        reasoning="The session made the writer durably darker.",
        identity=IdentityResponse(
            id=2,
            writer_id=1,
            personality={"voice": "precise"},
            emotions={"melancholy": 0.45, "curiosity": 0.4},
            memories=["Old city lights"],
            topics=["urban life"],
            constraints={},
            lifelong_objectives=["Find sharper images"],
            version=2,
            created_at=datetime.now(timezone.utc),
        ),
    )

    with patch(
        "backend.api.routes.sessions.apply_session_import",
        AsyncMock(return_value=imported),
    ):
        response = await client.post(
            "/api/sessions/12/import",
            json={
                "changes": [
                    {
                        "field": "emotions",
                        "action": "modify",
                        "key": "melancholy",
                        "old_value": 0.3,
                        "new_value": 0.45,
                        "reason": "Durable tonal shift.",
                    }
                ],
                "reasoning": "The session made the writer durably darker.",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["lifecycle"] == "imported"
    assert data["identity"]["version"] == 2


@pytest.mark.asyncio
async def test_skip_endpoint_returns_contract(client):
    skipped = SessionSkipResponse(session_id=12, writer_id=1, lifecycle="skipped")

    with patch(
        "backend.api.routes.sessions.skip_session_import",
        AsyncMock(return_value=skipped),
    ):
        response = await client.post("/api/sessions/12/skip")

    assert response.status_code == 200
    assert response.json() == {
        "session_id": 12,
        "writer_id": 1,
        "lifecycle": "skipped",
    }


@pytest.mark.asyncio
async def test_import_endpoint_maps_session_import_errors(client):
    with patch(
        "backend.api.routes.sessions.apply_session_import",
        AsyncMock(side_effect=SessionImportError(status_code=409, detail="Session must be complete before importing")),
    ):
        response = await client.post("/api/sessions/12/import", json={"changes": [], "reasoning": ""})

    assert response.status_code == 409
    assert response.json()["detail"] == "Session must be complete before importing"
