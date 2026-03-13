from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.auth import get_current_user
from backend.db.database import get_db
from backend.db.models import ChatMessage, MessageRole, User
from backend.schemas.chat import ChatMessageCreate, ChatMessageResponse
from backend.services.writer_service import get_writer

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/{writer_id}/message", response_model=ChatMessageResponse, status_code=201)
async def send_message(
    writer_id: int,
    body: ChatMessageCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ChatMessageResponse:
    """Save a user message and return a placeholder assistant response.

    The actual LLM-powered response will be handled by the agent layer
    in a later phase. For now this persists the user message and returns
    an echo-style assistant reply so the API contract is complete.
    """
    # Verify writer belongs to user
    await get_writer(db, writer_id=writer_id, user_id=current_user.id)

    # Persist user message
    user_msg = ChatMessage(
        writer_id=writer_id,
        role=MessageRole.user,
        content=body.content,
    )
    db.add(user_msg)
    await db.flush()

    # Placeholder assistant response (agent layer will replace this)
    assistant_msg = ChatMessage(
        writer_id=writer_id,
        role=MessageRole.assistant,
        content="[Agent response will be implemented in the agent layer]",
    )
    db.add(assistant_msg)
    await db.flush()
    await db.refresh(assistant_msg)

    return ChatMessageResponse.model_validate(assistant_msg)


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
