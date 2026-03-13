from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.auth import create_access_token
from backend.db.database import get_db
from backend.schemas.user import Token, UserCreate, UserLogin, UserResponse
from backend.services.user_service import authenticate_user, create_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token, status_code=201)
async def register(
    body: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """Register a new user account and return a JWT for auto-login."""
    user = await create_user(db, email=body.email, password=body.password)
    token = create_access_token(data={"sub": user.email})
    return Token(access_token=token)


@router.post("/login", response_model=Token)
async def login(
    body: UserLogin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """Authenticate and return a JWT access token."""
    user = await authenticate_user(db, email=body.email, password=body.password)
    token = create_access_token(data={"sub": user.email})
    return Token(access_token=token)
