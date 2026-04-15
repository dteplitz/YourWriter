from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.auth.auth import get_current_user
from backend.db.database import Base, get_db
from backend.db.models import User, Writer, WriterIdentity
from backend.main import app
from backend.schemas.writer_initialization import WriterInitializationPreviewResponse


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


@pytest_asyncio.fixture
async def client(session_factory):
    async with session_factory() as db:
        user = User(email="init@test.com", hashed_password="hashed")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        user_id = user.id

    current_user = MagicMock()
    current_user.id = user_id

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, session_factory, user_id

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_initialize_preview_endpoint_returns_structured_preview(client, monkeypatch):
    ac, _, _ = client

    async def fake_preview(description: str) -> WriterInitializationPreviewResponse:
        assert "ensayos" in description
        return WriterInitializationPreviewResponse(
            summary="Una ensayista sobria de observación cotidiana.",
            name="Lina Mercer",
            purpose="Escribir ensayos breves sobre tecnología y vida cotidiana.",
            personality={"voice": "clean", "humor": "dry"},
            emotions={"melancholy": 0.72, "curiosity": 0.58},
            topics=["technology", "city"],
            constraints={"tone": "Avoid corporate tone"},
            lifelong_objectives=["Name the emotional effect of the internet on urban life."],
        )

    monkeypatch.setattr(
        "backend.api.routes.writers.generate_writer_preview",
        fake_preview,
    )

    response = await ac.post(
        "/api/writers/initialize-preview",
        json={"description": "Quiero una escritora de ensayos sobre tecnología y vida cotidiana."},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Lina Mercer"
    assert data["summary"]
    assert data["personality"]["voice"] == "clean"
    assert data["emotions"]["melancholy"] == 0.72


@pytest.mark.asyncio
async def test_create_writer_from_preview_persists_identity(client):
    ac, session_factory, user_id = client

    response = await ac.post(
        "/api/writers/from-preview",
        json={
            "summary": "Una ensayista sobria de observación cotidiana.",
            "name": "Lina Mercer",
            "purpose": "Escribir ensayos breves sobre tecnología y vida cotidiana.",
            "personality": {"voice": "clean", "humor": "dry"},
            "emotions": {"melancholy": 0.72, "curiosity": 0.58},
            "topics": ["technology", "city"],
            "constraints": {"tone": "Avoid corporate tone"},
            "lifelong_objectives": [
                "Name the emotional effect of the internet on urban life."
            ],
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Lina Mercer"
    assert data["purpose"] == "Escribir ensayos breves sobre tecnología y vida cotidiana."

    async with session_factory() as db:
        writer_result = await db.execute(
            select(Writer).where(Writer.id == data["id"], Writer.user_id == user_id)
        )
        writer = writer_result.scalar_one()
        assert writer.name == "Lina Mercer"

        identity_result = await db.execute(
            select(WriterIdentity).where(WriterIdentity.writer_id == writer.id)
        )
        identity = identity_result.scalar_one()
        assert identity.personality["voice"] == "clean"
        assert identity.emotions["melancholy"] == 0.72
        assert identity.topics == ["technology", "city"]
        assert identity.constraints["tone"] == "Avoid corporate tone"
        assert identity.lifelong_objectives == [
            "Name the emotional effect of the internet on urban life."
        ]
        assert identity.memories == []
        assert identity.version == 1


@pytest.mark.asyncio
async def test_legacy_create_writer_endpoint_still_works(client):
    ac, session_factory, user_id = client

    response = await ac.post(
        "/api/writers",
        json={
            "name": "Legacy Writer",
            "purpose": "Write short notes",
            "style_description": "clear and direct",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Legacy Writer"

    async with session_factory() as db:
        identity_result = await db.execute(
            select(WriterIdentity)
            .join(Writer, WriterIdentity.writer_id == Writer.id)
            .where(Writer.id == data["id"], Writer.user_id == user_id)
        )
        identity = identity_result.scalar_one()
        assert identity.personality["style_description"] == "clear and direct"
