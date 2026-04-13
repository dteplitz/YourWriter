from fastapi import APIRouter

from backend.api.routes import auth, chat, evolution, identity, sessions, writers

api_router = APIRouter(prefix="/api")

api_router.include_router(auth.router)
api_router.include_router(writers.router)
api_router.include_router(chat.router)
api_router.include_router(identity.router)
api_router.include_router(evolution.router)
api_router.include_router(sessions.router)
