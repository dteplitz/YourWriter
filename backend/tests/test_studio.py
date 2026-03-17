"""Tests for Studio endpoints and service logic."""

import json
import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.auth.auth import get_current_user
from backend.main import app
from backend.schemas.studio import BriefResponse


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


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
    """Return a context-manager mock for async_session()."""
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


# ---------------------------------------------------------------------------
# Title parsing logic (unit tests — no HTTP, no mocks for Claude)
# ---------------------------------------------------------------------------

TITLE_PATTERN = re.compile(r"\n---TITLE:\s*(.+?)---\s*$", re.DOTALL)


def _parse_title(buffer: str) -> tuple[str, str]:
    """Mirror the title-parsing logic from stream_studio_session."""
    match = TITLE_PATTERN.search(buffer)
    if match:
        title = match.group(1).strip()
        content = buffer[: match.start()].rstrip()
    else:
        title = "Untitled"
        content = buffer
    return title, content


def test_title_parsing_extracts_title_and_content():
    """---TITLE: ..--- at end should be stripped and captured."""
    buffer = "Once upon a time there was a fox.\n---TITLE: The Clever Fox---"
    title, content = _parse_title(buffer)
    assert title == "The Clever Fox"
    assert content == "Once upon a time there was a fox."


def test_title_parsing_handles_missing_title():
    """If the model omits the title line, fall back to 'Untitled'."""
    buffer = "Once upon a time there was a fox."
    title, content = _parse_title(buffer)
    assert title == "Untitled"
    assert content == buffer


def test_title_parsing_handles_whitespace_around_title():
    """Leading/trailing whitespace inside the title tag should be stripped."""
    buffer = "Content here.\n---TITLE:   My Great Story   ---"
    title, content = _parse_title(buffer)
    assert title == "My Great Story"
    assert content == "Content here."


def test_title_parsing_multi_paragraph_content():
    """Multi-paragraph content before the title line must be preserved intact."""
    buffer = "Paragraph one.\n\nParagraph two.\n---TITLE: Two Paragraphs---"
    title, content = _parse_title(buffer)
    assert title == "Two Paragraphs"
    assert "Paragraph one." in content
    assert "Paragraph two." in content


def test_word_count_basic():
    """Word count logic: split on whitespace."""
    content = "The quick brown fox jumps"
    word_count = len(content.split())
    assert word_count == 5


# ---------------------------------------------------------------------------
# POST /api/chat/{writer_id}/brief — endpoint test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_brief_endpoint_returns_brief_response(client, mock_writer):
    """The /brief endpoint should proxy the service result as JSON."""
    expected = BriefResponse(
        format="short story",
        tone="melancholic",
        constraints_applied=[],
        word_limit=500,
        notes=None,
        needs_clarification=False,
        clarification_question=None,
    )

    with (
        patch("backend.api.routes.chat.get_writer", return_value=mock_writer),
        patch(
            "backend.api.routes.chat.generate_brief",
            new_callable=AsyncMock,
            return_value=expected,
        ),
    ):
        response = await client.post(
            "/api/chat/1/brief",
            json={"message": "Write me a sad short story about a lighthouse keeper"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["format"] == "short story"
    assert data["tone"] == "melancholic"
    assert data["word_limit"] == 500
    assert data["needs_clarification"] is False


@pytest.mark.asyncio
async def test_brief_endpoint_503_on_missing_api_key(client, mock_writer):
    """RuntimeError from service should surface as 503."""
    with (
        patch("backend.api.routes.chat.get_writer", return_value=mock_writer),
        patch(
            "backend.api.routes.chat.generate_brief",
            side_effect=RuntimeError("ANTHROPIC_API_KEY environment variable is not set"),
        ),
    ):
        response = await client.post(
            "/api/chat/1/brief",
            json={"message": "Write something"},
        )

    assert response.status_code == 503


# ---------------------------------------------------------------------------
# POST /api/chat/{writer_id}/studio/stream — endpoint test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_studio_stream_returns_sse_events(client, mock_writer):
    """Studio stream should emit phase, token, piece, and done events."""

    async def fake_studio_stream(*args, **kwargs):
        yield {"phase": "outlining"}
        yield {"phase": "drafting"}
        yield {"phase": "refining"}
        for token in ["Once", " upon", " a time"]:
            yield token
        yield {
            "piece": {
                "id": 42,
                "title": "The Story",
                "content": "Once upon a time",
                "format": "short story",
                "word_count": 4,
            }
        }

    session_ctx, _mock_db = _mock_async_session()

    with (
        patch("backend.api.routes.chat.async_session", return_value=session_ctx()),
        patch("backend.api.routes.chat.get_writer", return_value=mock_writer),
        patch(
            "backend.api.routes.chat.stream_studio_session",
            side_effect=fake_studio_stream,
        ),
    ):
        response = await client.post(
            "/api/chat/1/studio/stream",
            json={
                "brief": {
                    "format": "short story",
                    "tone": "melancholic",
                    "constraints_applied": [],
                    "word_limit": None,
                    "notes": None,
                    "needs_clarification": False,
                    "clarification_question": None,
                }
            },
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    events = []
    for line in response.text.strip().split("\n"):
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    phase_events = [e for e in events if "phase" in e]
    token_events = [e for e in events if "token" in e]
    piece_events = [e for e in events if "piece" in e]
    done_events = [e for e in events if "done" in e]

    assert [e["phase"] for e in phase_events] == ["outlining", "drafting", "refining"]
    assert len(token_events) == 3
    assert token_events[0]["token"] == "Once"
    assert len(piece_events) == 1
    assert piece_events[0]["piece"]["title"] == "The Story"
    assert len(done_events) == 1
    assert done_events[0]["done"] is True


@pytest.mark.asyncio
async def test_studio_stream_handles_errors(client, mock_writer):
    """RuntimeError in the studio stream should emit an error SSE event."""

    async def failing_stream(*args, **kwargs):
        raise RuntimeError("API key not set")
        yield  # make it a generator

    session_ctx, _mock_db = _mock_async_session()

    with (
        patch("backend.api.routes.chat.async_session", return_value=session_ctx()),
        patch("backend.api.routes.chat.get_writer", return_value=mock_writer),
        patch(
            "backend.api.routes.chat.stream_studio_session",
            side_effect=failing_stream,
        ),
    ):
        response = await client.post(
            "/api/chat/1/studio/stream",
            json={
                "brief": {
                    "format": "essay",
                    "tone": "formal",
                    "constraints_applied": [],
                    "word_limit": None,
                    "notes": None,
                    "needs_clarification": False,
                    "clarification_question": None,
                }
            },
        )

    assert response.status_code == 200

    events = []
    for line in response.text.strip().split("\n"):
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    error_events = [e for e in events if "error" in e]
    assert len(error_events) >= 1
