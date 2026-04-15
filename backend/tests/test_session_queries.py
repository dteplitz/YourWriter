from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.auth.auth import get_current_user
from backend.db.database import Base, get_db
from backend.db.models import EvolutionLog, StudioSession, StudioTake, User, Writer, WriterIdentity
from backend.main import app


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


async def _seed_sessions(session_factory: async_sessionmaker[AsyncSession]) -> dict[str, int]:
    async with session_factory() as db:
        user = User(email="slice4@test.com", hashed_password="hashed")
        other_user = User(email="other@test.com", hashed_password="hashed")
        db.add_all([user, other_user])
        await db.flush()

        writer = Writer(user_id=user.id, name="Ariadna", purpose="Urban melancholy")
        db.add(writer)
        await db.flush()

        db.add(
            WriterIdentity(
                writer_id=writer.id,
                personality={"voice": "observant"},
                emotions={"melancholy": 0.6},
                memories=[],
                topics=["ai"],
                constraints={},
                lifelong_objectives=[],
                version=1,
            )
        )
        await db.flush()

        active = StudioSession(
            writer_id=writer.id,
            brief_json={
                "format": "column",
                "tone": "sobrio",
                "constraints_applied": [],
                "word_limit": 120,
                "notes": "IA como paisaje cotidiano",
                "needs_clarification": False,
                "clarification_question": None,
            },
            lifecycle="active",
        )
        complete = StudioSession(
            writer_id=writer.id,
            brief_json={
                "format": "essay",
                "tone": "reflective",
                "constraints_applied": [],
                "word_limit": 600,
                "notes": "Revisar import de una sesion cerrada",
                "needs_clarification": False,
                "clarification_question": None,
            },
            lifecycle="complete",
        )
        imported = StudioSession(
            writer_id=writer.id,
            brief_json={
                "format": "poem",
                "tone": "lyrical",
                "constraints_applied": [],
                "word_limit": 80,
                "notes": "",
                "needs_clarification": False,
                "clarification_question": None,
            },
            lifecycle="imported",
        )
        abandoned = StudioSession(
            writer_id=writer.id,
            brief_json={
                "format": "note",
                "tone": "dry",
                "constraints_applied": [],
                "word_limit": 50,
                "notes": "No deberia aparecer",
                "needs_clarification": False,
                "clarification_question": None,
            },
            lifecycle="abandoned",
        )
        db.add_all([active, complete, imported, abandoned])
        await db.flush()

        db.add_all(
            [
                StudioTake(
                    session_id=active.id,
                    take_number=1,
                    title="La Velocidad Se Ha Vuelto Paisaje",
                    content="La velocidad se ha vuelto paisaje en la ciudad.",
                ),
                StudioTake(
                    session_id=active.id,
                    take_number=2,
                    iteration_notes="Mas sobrio",
                    title="El Ruido de Fondo",
                    content="La IA ya no irrumpe: se filtra como ruido de fondo.",
                ),
                StudioTake(
                    session_id=complete.id,
                    take_number=1,
                    title="Manual de Ruido Cotidiano",
                    content="Todo se vuelve costumbre demasiado rapido.",
                ),
            ]
        )
        await db.flush()

        db.add(
            EvolutionLog(
                writer_id=writer.id,
                field_changed="topics",
                old_value="[]",
                new_value="['ai']",
                reason="[post_session_import session_id=%d] Durable thematic shift" % complete.id,
            )
        )
        await db.commit()

        return {
            "user_id": user.id,
            "writer_id": writer.id,
            "active_session_id": active.id,
            "complete_session_id": complete.id,
        }


@pytest_asyncio.fixture
async def client(session_factory):
    seeded = await _seed_sessions(session_factory)
    current_user = MagicMock()
    current_user.id = seeded["user_id"]

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, seeded

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_writer_sessions_summary_returns_highlight_and_history(client):
    ac, seeded = client

    response = await ac.get(f"/api/writers/{seeded['writer_id']}/sessions/summary")

    assert response.status_code == 200
    data = response.json()
    assert data["highlight"]["id"] == seeded["active_session_id"]
    assert data["highlight"]["lifecycle"] == "active"
    assert data["highlight"]["take_count"] == 2
    assert data["highlight"]["last_take"]["title"] == "El Ruido de Fondo"
    assert all(item["lifecycle"] != "abandoned" for item in data["history"])
    assert len(data["history"]) == 3
    assert seeded["active_session_id"] in [item["id"] for item in data["history"]]
    assert seeded["complete_session_id"] in [item["id"] for item in data["history"]]


@pytest.mark.asyncio
async def test_session_detail_returns_takes_and_brief(client):
    ac, seeded = client

    response = await ac.get(f"/api/sessions/{seeded['active_session_id']}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == seeded["active_session_id"]
    assert data["resume_mode"] == "artifact"
    assert data["brief"]["format"] == "column"
    assert data["take_count"] == 2
    assert data["takes"][1]["iteration_notes"] == "Mas sobrio"
    assert data["takes"][1]["word_count"] > 0


@pytest.mark.asyncio
async def test_abandon_session_marks_active_session_abandoned(client):
    ac, seeded = client

    response = await ac.post(f"/api/sessions/{seeded['active_session_id']}/abandon")

    assert response.status_code == 200
    data = response.json()
    assert data == {
        "session_id": seeded["active_session_id"],
        "writer_id": seeded["writer_id"],
        "lifecycle": "abandoned",
    }

    summary = await ac.get(f"/api/writers/{seeded['writer_id']}/sessions/summary")
    summary_data = summary.json()
    assert summary_data["highlight"]["id"] == seeded["complete_session_id"]
    assert all(item["id"] != seeded["active_session_id"] for item in summary_data["history"])


@pytest.mark.asyncio
async def test_evolution_log_exposes_source_session_id(client):
    ac, seeded = client

    response = await ac.get(f"/api/writers/{seeded['writer_id']}/evolution")

    assert response.status_code == 200
    data = response.json()
    assert data[0]["source_session_id"] == seeded["complete_session_id"]
