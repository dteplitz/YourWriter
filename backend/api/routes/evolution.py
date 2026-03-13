from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.auth import get_current_user
from backend.db.database import get_db
from backend.db.models import EvolutionLog, User
from backend.schemas.evolution import EvolutionLogResponse
from backend.services.writer_service import get_writer

router = APIRouter(prefix="/writers", tags=["evolution"])


@router.get("/{writer_id}/evolution", response_model=list[EvolutionLogResponse])
async def get_evolution_log(
    writer_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[EvolutionLogResponse]:
    """Return the evolution history for a writer, newest first."""
    await get_writer(db, writer_id=writer_id, user_id=current_user.id)

    result = await db.execute(
        select(EvolutionLog)
        .where(EvolutionLog.writer_id == writer_id)
        .order_by(EvolutionLog.created_at.desc())
    )
    logs = result.scalars().all()
    return [EvolutionLogResponse.model_validate(log) for log in logs]
