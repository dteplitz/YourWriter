import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.auth import get_current_user
from backend.db.database import get_db
from backend.db.models import ChatMessage, MessageRole, User
from backend.schemas.chat import ChatMessageCreate, ChatMessageResponse
from backend.services.chat_service import invoke_writer_agent, stream_writer_agent
from backend.services.writer_service import get_writer

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
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StreamingResponse:
    """Stream the writer agent response via Server-Sent Events."""
    writer = await get_writer(db, writer_id=writer_id, user_id=current_user.id)

    # Persist user message
    user_msg = ChatMessage(
        writer_id=writer_id,
        role=MessageRole.user,
        content=body.content,
    )
    db.add(user_msg)
    await db.flush()

    async def event_generator():
        full_response = ""
        try:
            async for chunk in stream_writer_agent(db, writer, body.content):
                full_response += chunk
                yield f"data: {json.dumps({'token': chunk})}\n\n"

            # Persist the complete assistant response
            assistant_msg = ChatMessage(
                writer_id=writer_id,
                role=MessageRole.assistant,
                content=full_response,
            )
            db.add(assistant_msg)
            await db.flush()
            await db.refresh(assistant_msg)

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
