from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.auth import get_current_user
from backend.db.database import get_db
from backend.db.models import User, WriterIdentity
from backend.schemas.evolution import RollbackResponse
from backend.schemas.identity import ConstraintsUpdate, IdentityResponse, IdentityUpdate
from backend.services.writer_service import get_writer

router = APIRouter(prefix="/writers", tags=["identity"])


async def _get_latest_identity(db: AsyncSession, writer_id: int) -> WriterIdentity:
    """Return the latest identity version for a writer, or raise 404."""
    result = await db.execute(
        select(WriterIdentity)
        .where(WriterIdentity.writer_id == writer_id)
        .order_by(WriterIdentity.version.desc())
        .limit(1)
    )
    identity = result.scalar_one_or_none()
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Identity not found for this writer",
        )
    return identity


@router.get("/{writer_id}/identity", response_model=IdentityResponse)
async def get_identity(
    writer_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> IdentityResponse:
    """Return the latest identity snapshot for a writer."""
    await get_writer(db, writer_id=writer_id, user_id=current_user.id)
    identity = await _get_latest_identity(db, writer_id)
    return IdentityResponse.model_validate(identity)


@router.put("/{writer_id}/identity", response_model=IdentityResponse)
async def update_identity(
    writer_id: int,
    body: IdentityUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> IdentityResponse:
    """Create a new identity version with the supplied updates.

    Only fields present in the request body are changed; others are
    carried forward from the current version.
    """
    await get_writer(db, writer_id=writer_id, user_id=current_user.id)
    current = await _get_latest_identity(db, writer_id)

    new_identity = WriterIdentity(
        writer_id=writer_id,
        personality=body.personality if body.personality is not None else current.personality,
        emotions=body.emotions if body.emotions is not None else current.emotions,
        memories=body.memories if body.memories is not None else current.memories,
        topics=body.topics if body.topics is not None else current.topics,
        constraints=current.constraints,  # constraints have their own endpoint
        lifelong_objectives=(
            body.lifelong_objectives if body.lifelong_objectives is not None else current.lifelong_objectives
        ),
        version=current.version + 1,
    )
    db.add(new_identity)
    await db.flush()
    await db.refresh(new_identity)
    return IdentityResponse.model_validate(new_identity)


@router.put("/{writer_id}/constraints", response_model=IdentityResponse)
async def update_constraints(
    writer_id: int,
    body: ConstraintsUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> IdentityResponse:
    """Create a new identity version with updated constraints."""
    await get_writer(db, writer_id=writer_id, user_id=current_user.id)
    current = await _get_latest_identity(db, writer_id)

    new_identity = WriterIdentity(
        writer_id=writer_id,
        personality=current.personality,
        emotions=current.emotions,
        memories=current.memories,
        topics=current.topics,
        constraints=body.constraints,
        lifelong_objectives=current.lifelong_objectives,
        version=current.version + 1,
    )
    db.add(new_identity)
    await db.flush()
    await db.refresh(new_identity)
    return IdentityResponse.model_validate(new_identity)


@router.post("/{writer_id}/identity/rollback", response_model=RollbackResponse)
async def rollback_identity(
    writer_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> RollbackResponse:
    """Crea nueva versión copiando la N-1. Append-only, nunca destruye historial."""
    await get_writer(db, writer_id=writer_id, user_id=current_user.id)

    # Cargar últimas 2 versiones
    result = await db.execute(
        select(WriterIdentity)
        .where(WriterIdentity.writer_id == writer_id)
        .order_by(WriterIdentity.version.desc())
        .limit(2)
    )
    versions = list(result.scalars().all())

    if len(versions) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No previous version to rollback to",
        )

    current, previous = versions[0], versions[1]

    new_identity = WriterIdentity(
        writer_id=writer_id,
        personality=previous.personality,
        emotions=previous.emotions,
        memories=previous.memories,
        topics=previous.topics,
        constraints=previous.constraints,
        lifelong_objectives=previous.lifelong_objectives,
        version=current.version + 1,
    )
    db.add(new_identity)
    await db.flush()
    await db.refresh(new_identity)

    return RollbackResponse(
        writer_id=writer_id,
        rolled_back_to_version=previous.version,
        new_version=new_identity.version,
        identity=IdentityResponse.model_validate(new_identity),
    )
