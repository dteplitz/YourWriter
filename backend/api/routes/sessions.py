import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.auth import get_current_user
from backend.db.database import get_db
from backend.db.models import User
from backend.schemas.session import (
    SessionAbandonResponse,
    SessionDetailResponse,
    SessionImportProposalResponse,
    SessionImportRequest,
    SessionImportResponse,
    SessionSkipResponse,
)
from backend.services.session_query_service import (
    SessionQueryError,
    abandon_session,
    get_session_detail,
)
from backend.services.session_import_service import (
    SessionImportError,
    apply_session_import,
    generate_import_proposal,
    skip_session_import,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session_detail_endpoint(
    session_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SessionDetailResponse:
    try:
        return await get_session_detail(
            db,
            session_id=session_id,
            user_id=current_user.id,
        )
    except SessionQueryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post("/{session_id}/abandon", response_model=SessionAbandonResponse)
async def abandon_session_endpoint(
    session_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SessionAbandonResponse:
    try:
        response = await abandon_session(
            db,
            session_id=session_id,
            user_id=current_user.id,
        )
        await db.commit()
        return response
    except SessionQueryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post("/{session_id}/import-proposal", response_model=SessionImportProposalResponse)
async def create_import_proposal(
    session_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
) -> SessionImportProposalResponse:
    try:
        return await generate_import_proposal(session_id=session_id, user_id=current_user.id)
    except SessionImportError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        logger.exception("Failed to generate import proposal for session %s", session_id)
        raise HTTPException(status_code=500, detail="Failed to generate import proposal. Please try again.")


@router.post("/{session_id}/import", response_model=SessionImportResponse)
async def import_session_changes(
    session_id: int,
    body: SessionImportRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> SessionImportResponse:
    try:
        return await apply_session_import(
            session_id=session_id,
            user_id=current_user.id,
            body=body,
        )
    except SessionImportError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        logger.exception("Failed to import session changes for session %s", session_id)
        raise HTTPException(status_code=500, detail="Failed to import session changes. Please try again.")


@router.post("/{session_id}/skip", response_model=SessionSkipResponse)
async def skip_session_changes(
    session_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
) -> SessionSkipResponse:
    try:
        return await skip_session_import(session_id=session_id, user_id=current_user.id)
    except SessionImportError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        logger.exception("Failed to skip session import for session %s", session_id)
        raise HTTPException(status_code=500, detail="Failed to skip session import. Please try again.")
