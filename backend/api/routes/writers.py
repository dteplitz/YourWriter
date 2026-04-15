from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.auth import get_current_user
from backend.db.database import get_db
from backend.db.models import User, WriterPiece
from backend.schemas.session import WriterSessionsSummaryResponse
from backend.schemas.studio import PieceResponse
from backend.schemas.writer import WriterCreate, WriterResponse, WriterUpdate, WriterWithIdentity
from backend.schemas.identity import IdentityResponse
from backend.schemas.writer_initialization import (
    WriterCreateFromPreviewRequest,
    WriterInitializationPreviewResponse,
    WriterInitializationRequest,
)
from backend.services.session_query_service import get_writer_sessions_summary
from backend.services.writer_initialization_service import (
    create_writer_from_preview,
    generate_writer_preview,
)
from backend.services.writer_service import (
    create_writer,
    delete_writer,
    get_writer,
    get_writers,
    update_writer,
)

router = APIRouter(prefix="/writers", tags=["writers"])


@router.get("", response_model=list[WriterResponse])
async def list_writers(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[WriterResponse]:
    """Return all writers belonging to the current user."""
    writers = await get_writers(db, user_id=current_user.id)
    return [WriterResponse.model_validate(w) for w in writers]


@router.post("", response_model=WriterResponse, status_code=201)
async def create_writer_endpoint(
    body: WriterCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WriterResponse:
    """Create a new writer with a default identity."""
    writer = await create_writer(
        db,
        user_id=current_user.id,
        name=body.name,
        purpose=body.purpose,
        style_description=body.style_description,
    )
    return WriterResponse.model_validate(writer)


@router.post("/initialize-preview", response_model=WriterInitializationPreviewResponse)
async def initialize_writer_preview_endpoint(
    body: WriterInitializationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> WriterInitializationPreviewResponse:
    """Generate an initial writer profile preview from free-text description."""
    _ = current_user
    return await generate_writer_preview(body.description)


@router.post("/from-preview", response_model=WriterResponse, status_code=201)
async def create_writer_from_preview_endpoint(
    body: WriterCreateFromPreviewRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WriterResponse:
    """Create a new writer from a previously generated initialization preview."""
    writer = await create_writer_from_preview(
        db,
        user_id=current_user.id,
        body=body,
    )
    return WriterResponse.model_validate(writer)


@router.get("/{writer_id}", response_model=WriterWithIdentity)
async def get_writer_endpoint(
    writer_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WriterWithIdentity:
    """Return a single writer including its latest identity."""
    writer = await get_writer(db, writer_id=writer_id, user_id=current_user.id)
    response = WriterWithIdentity.model_validate(writer)
    if writer.identities:
        latest = max(writer.identities, key=lambda i: i.version)
        response.identity = IdentityResponse.model_validate(latest)
    return response


@router.put("/{writer_id}", response_model=WriterResponse)
async def update_writer_endpoint(
    writer_id: int,
    body: WriterUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WriterResponse:
    """Update a writer's name and/or purpose."""
    writer = await update_writer(
        db, writer_id=writer_id, user_id=current_user.id, name=body.name, purpose=body.purpose
    )
    return WriterResponse.model_validate(writer)


@router.delete("/{writer_id}", status_code=204)
async def delete_writer_endpoint(
    writer_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Delete a writer and all associated data."""
    await delete_writer(db, writer_id=writer_id, user_id=current_user.id)


@router.get("/{writer_id}/pieces", response_model=list[PieceResponse])
async def list_pieces(
    writer_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[PieceResponse]:
    """Return all pieces (discography) for a writer."""
    await get_writer(db, writer_id=writer_id, user_id=current_user.id)

    result = await db.execute(
        select(WriterPiece)
        .where(WriterPiece.writer_id == writer_id)
        .order_by(WriterPiece.created_at.desc())
    )
    pieces = result.scalars().all()
    return [PieceResponse.model_validate(p) for p in pieces]


@router.get("/{writer_id}/sessions/summary", response_model=WriterSessionsSummaryResponse)
async def get_writer_sessions_summary_endpoint(
    writer_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WriterSessionsSummaryResponse:
    return await get_writer_sessions_summary(
        db,
        writer_id=writer_id,
        user_id=current_user.id,
    )


@router.get("/{writer_id}/pieces/{piece_id}", response_model=PieceResponse)
async def get_piece(
    writer_id: int,
    piece_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PieceResponse:
    """Return a single piece by ID, verifying writer ownership."""
    await get_writer(db, writer_id=writer_id, user_id=current_user.id)

    result = await db.execute(
        select(WriterPiece).where(
            WriterPiece.id == piece_id,
            WriterPiece.writer_id == writer_id,
        )
    )
    piece = result.scalar_one_or_none()
    if piece is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Piece not found",
        )
    return PieceResponse.model_validate(piece)
