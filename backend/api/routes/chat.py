import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.auth import get_current_user
from backend.db.database import async_session, get_db
from backend.db.models import ChatMessage, MessageRole, User
from backend.schemas.chat import ChatMessageCreate, ChatMessageResponse
from backend.schemas.studio import BriefRequest, BriefResponse
from backend.services.chat_service import (
    generate_brief,
    invoke_writer_agent,
    stream_studio_session,
    stream_writer_agent,
)
from backend.services.writer_service import get_writer


class StudioStreamRequest(BaseModel):
    brief: BriefResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/{writer_id}/message", response_model=ChatMessageResponse, status_code=201)
async def send_message(
    writer_id: int,
    body: ChatMessageCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ChatMessageResponse:
    """Save a user message, invoke the writer agent, and return the response."""
    # Verify writer belongs to user (also eager-loads identities)
    writer = await get_writer(db, writer_id=writer_id, user_id=current_user.id)

    # Persist user message
    user_msg = ChatMessage(
        writer_id=writer_id,
        role=MessageRole.user,
        content=body.content,
    )
    db.add(user_msg)
    await db.flush()

    # Invoke the agent layer
    try:
        response_text = await invoke_writer_agent(db, writer, body.content)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        logger.exception("Agent invocation failed for writer %s", writer_id)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate response. Please try again.",
        )

    # Persist assistant response
    assistant_msg = ChatMessage(
        writer_id=writer_id,
        role=MessageRole.assistant,
        content=response_text,
    )
    db.add(assistant_msg)
    await db.flush()
    await db.refresh(assistant_msg)

    return ChatMessageResponse.model_validate(assistant_msg)


@router.post("/{writer_id}/message/stream", status_code=200)
async def send_message_stream(
    writer_id: int,
    body: ChatMessageCreate,
    current_user: Annotated[User, Depends(get_current_user)],
) -> StreamingResponse:
    """Stream the writer agent response via Server-Sent Events.

    Does NOT use Depends(get_db) — manages its own short-lived sessions.
    The LLM call can take 10-30s; holding an SQLite connection open that
    long blocks all other writes.
    """
    # Short-lived session: auth check, load writer, persist user message
    async with async_session() as db:
        writer = await get_writer(db, writer_id=writer_id, user_id=current_user.id)
        user_msg = ChatMessage(
            writer_id=writer_id,
            role=MessageRole.user,
            content=body.content,
        )
        db.add(user_msg)
        await db.commit()

    async def event_generator():
        full_response = ""
        try:
            async for chunk in stream_writer_agent(writer, body.content):
                if isinstance(chunk, dict):
                    yield f"data: {json.dumps(chunk)}\n\n"
                else:
                    full_response += chunk
                    yield f"data: {json.dumps({'token': chunk})}\n\n"

            # Short-lived session: persist assistant response
            async with async_session() as save_db:
                assistant_msg = ChatMessage(
                    writer_id=writer_id,
                    role=MessageRole.assistant,
                    content=full_response,
                )
                save_db.add(assistant_msg)
                await save_db.commit()
                await save_db.refresh(assistant_msg)

            yield f"data: {json.dumps({'done': True, 'message_id': assistant_msg.id})}\n\n"
        except RuntimeError as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        except Exception:
            logger.exception("Streaming failed for writer %s", writer_id)
            yield f"data: {json.dumps({'error': 'Failed to generate response. Please try again.'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{writer_id}/history", response_model=list[ChatMessageResponse])
async def get_history(
    writer_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ChatMessageResponse]:
    """Return the full chat history for a writer."""
    # Verify writer belongs to user
    await get_writer(db, writer_id=writer_id, user_id=current_user.id)

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.writer_id == writer_id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = result.scalars().all()
    return [ChatMessageResponse.model_validate(m) for m in messages]


@router.post("/{writer_id}/brief", response_model=BriefResponse)
async def generate_brief_endpoint(
    writer_id: int,
    body: BriefRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BriefResponse:
    """Parse a free-text request into a structured Studio brief."""
    writer = await get_writer(db, writer_id=writer_id, user_id=current_user.id)
    try:
        return await generate_brief(writer, body.message)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        logger.exception("Brief generation failed for writer %s", writer_id)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate brief. Please try again.",
        )


@router.post("/{writer_id}/studio/stream", status_code=200)
async def studio_stream(
    writer_id: int,
    body: StudioStreamRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> StreamingResponse:
    """Stream a full Studio writing session (outline → draft → refine) via SSE.

    Does NOT use Depends(get_db) — the service manages its own short-lived
    sessions.  The LLM pipeline can take 30-90s; holding SQLite open that
    long blocks all other writes.

    Piece saving is handled inside stream_studio_session; this generator
    only forwards tokens and event dicts to the client.
    """
    # Short-lived session: auth check + load writer
    async with async_session() as db:
        writer = await get_writer(db, writer_id=writer_id, user_id=current_user.id)

    brief = body.brief

    async def event_generator():
        try:
            async for chunk in stream_studio_session(writer, brief):
                if isinstance(chunk, dict):
                    yield f"data: {json.dumps(chunk)}\n\n"
                else:
                    yield f"data: {json.dumps({'token': chunk})}\n\n"

            yield f"data: {json.dumps({'done': True})}\n\n"
        except RuntimeError as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        except Exception:
            logger.exception("Studio streaming failed for writer %s", writer_id)
            yield f"data: {json.dumps({'error': 'Failed to generate content. Please try again.'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
