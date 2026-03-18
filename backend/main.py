from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api.router import api_router
from backend.config import settings
from backend.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialise the database on startup."""
    await init_db()
    yield


app = FastAPI(
    title="YourWriter",
    description="Multi-user AI story writing platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


# Serve the React frontend — must come AFTER all API routes
if settings.is_production:
    app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str) -> FileResponse:
        return FileResponse("frontend/dist/index.html")
