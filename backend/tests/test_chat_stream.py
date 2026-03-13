"""Tests for the SSE streaming chat endpoint."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.auth.auth import get_current_user
from backend.main import app


@pytest.fixture
def mock_writer():
    writer = MagicMock()
    writer.id = 1
    writer.name = "Test Writer"
    writer.purpose = "testing"
    writer.identities = []
    return writer


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


def _mock_async_session():
    mock_db = MagicMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    class FakeSessionCtx:
        async def __aenter__(self):
            return mock_db
        async def __aexit__(self, *args):
            pass

    return FakeSessionCtx, mock_db


@pytest.mark.asyncio
async def test_stream_chat_returns_sse_format(client, mock_writer):
    """Chat-mode streaming should return token + done events."""

    async def fake_stream(*args, **kwargs):
        for chunk in ["Hello", " world", "!"]:
            yield chunk

    session_ctx, mock_db = _mock_async_session()

    with (
        patch("backend.api.routes.chat.get_writer", return_value=mock_writer),
        patch("backend.api.routes.chat.stream_writer_agent", side_effect=fake_stream),
        patch("backend.api.routes.chat.async_session", return_value=session_ctx()),
    ):
        response = await client.post(
            "/api/chat/1/message/stream",
            json={"content": "Hello"},
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    events = []
    for line in response.text.strip().split("\n"):
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    token_events = [e for e in events if "token" in e]
    done_events = [e for e in events if "done" in e]

    assert len(token_events) >= 1
    assert len(done_events) == 1
    assert done_events[0]["done"] is True


@pytest.mark.asyncio
async def test_stream_write_mode_produces_phase_events(client, mock_writer):
    """Write-mode streaming should emit phase events then token events."""

    async def fake_write_stream(*args, **kwargs):
        yield {"phase": "outlining"}
        yield {"phase": "drafting"}
        yield {"phase": "refining"}
        for chunk in ["Once", " upon", " a time"]:
            yield chunk

    session_ctx, mock_db = _mock_async_session()

    with (
        patch("backend.api.routes.chat.get_writer", return_value=mock_writer),
        patch("backend.api.routes.chat.stream_writer_agent", side_effect=fake_write_stream),
        patch("backend.api.routes.chat.async_session", return_value=session_ctx()),
    ):
        response = await client.post(
            "/api/chat/1/message/stream",
            json={"content": "Write me a story"},
        )

    assert response.status_code == 200

    events = []
    for line in response.text.strip().split("\n"):
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    phase_events = [e for e in events if "phase" in e]
    token_events = [e for e in events if "token" in e]
    done_events = [e for e in events if "done" in e]

    # Phase events come first, in order
    assert [e["phase"] for e in phase_events] == ["outlining", "drafting", "refining"]
    # Then token events
    assert len(token_events) == 3
    assert token_events[0]["token"] == "Once"
    # Then done
    assert len(done_events) == 1


@pytest.mark.asyncio
async def test_stream_endpoint_handles_errors(client, mock_writer):
    """The streaming endpoint should emit an error SSE event on failure."""

    async def failing_stream(*args, **kwargs):
        raise RuntimeError("API key not set")
        yield  # make it a generator  # noqa: E501

    session_ctx, mock_db = _mock_async_session()

    with (
        patch("backend.api.routes.chat.get_writer", return_value=mock_writer),
        patch("backend.api.routes.chat.stream_writer_agent", side_effect=failing_stream),
        patch("backend.api.routes.chat.async_session", return_value=session_ctx()),
    ):
        response = await client.post(
            "/api/chat/1/message/stream",
            json={"content": "Hello"},
        )

    assert response.status_code == 200

    events = []
    for line in response.text.strip().split("\n"):
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    error_events = [e for e in events if "error" in e]
    assert len(error_events) >= 1
