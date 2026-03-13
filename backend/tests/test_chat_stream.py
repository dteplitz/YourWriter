"""Tests for the SSE streaming chat endpoint."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.fixture
def mock_writer():
    """Create a mock writer with identity."""
    writer = MagicMock()
    writer.id = 1
    writer.name = "Test Writer"
    writer.purpose = "testing"
    writer.identities = []
    return writer


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers():
    """Create a mock auth token."""
    return {"Authorization": "Bearer test-token"}


@pytest.mark.asyncio
async def test_stream_endpoint_returns_sse_format(client, auth_headers, mock_writer):
    """The streaming endpoint should return proper SSE events."""

    async def fake_stream(*args, **kwargs):
        for chunk in ["Hello", " world", "!"]:
            yield chunk

    with (
        patch("backend.api.routes.chat.get_current_user", return_value=MagicMock(id=1)),
        patch("backend.api.routes.chat.get_writer", return_value=mock_writer),
        patch("backend.api.routes.chat.stream_writer_agent", side_effect=fake_stream),
        patch("backend.api.routes.chat.get_db"),
    ):
        response = await client.post(
            "/api/chat/1/message/stream",
            json={"content": "Hello"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    # Parse SSE events from response body
    events = []
    for line in response.text.strip().split("\n"):
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    # Should have token events followed by a done event
    token_events = [e for e in events if "token" in e]
    done_events = [e for e in events if "done" in e]

    assert len(token_events) >= 1
    assert len(done_events) == 1
    assert done_events[0]["done"] is True


@pytest.mark.asyncio
async def test_stream_endpoint_handles_errors(client, auth_headers, mock_writer):
    """The streaming endpoint should emit an error SSE event on failure."""

    async def failing_stream(*args, **kwargs):
        raise RuntimeError("API key not set")
        yield  # make it a generator  # noqa: E501

    with (
        patch("backend.api.routes.chat.get_current_user", return_value=MagicMock(id=1)),
        patch("backend.api.routes.chat.get_writer", return_value=mock_writer),
        patch("backend.api.routes.chat.stream_writer_agent", side_effect=failing_stream),
        patch("backend.api.routes.chat.get_db"),
    ):
        response = await client.post(
            "/api/chat/1/message/stream",
            json={"content": "Hello"},
            headers=auth_headers,
        )

    assert response.status_code == 200  # SSE always returns 200, errors in stream

    events = []
    for line in response.text.strip().split("\n"):
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    error_events = [e for e in events if "error" in e]
    assert len(error_events) >= 1
