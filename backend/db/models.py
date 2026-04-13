import enum
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key_encrypted: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    writers: Mapped[list["Writer"]] = relationship("Writer", back_populates="user", cascade="all, delete-orphan")


class Writer(Base):
    __tablename__ = "writers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    user: Mapped["User"] = relationship("User", back_populates="writers")
    identities: Mapped[list["WriterIdentity"]] = relationship(
        "WriterIdentity", back_populates="writer", cascade="all, delete-orphan"
    )
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="writer", cascade="all, delete-orphan"
    )
    evolution_logs: Mapped[list["EvolutionLog"]] = relationship(
        "EvolutionLog", back_populates="writer", cascade="all, delete-orphan"
    )
    pieces: Mapped[list["WriterPiece"]] = relationship(
        "WriterPiece", back_populates="writer", cascade="all, delete-orphan"
    )
    studio_sessions: Mapped[list["StudioSession"]] = relationship(
        "StudioSession", back_populates="writer", cascade="all, delete-orphan"
    )


class WriterIdentity(Base):
    __tablename__ = "writer_identities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    writer_id: Mapped[int] = mapped_column(ForeignKey("writers.id", ondelete="CASCADE"), nullable=False)
    personality: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    emotions: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    memories: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    topics: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    constraints: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    lifelong_objectives: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    writer: Mapped["Writer"] = relationship("Writer", back_populates="identities")


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    writer_id: Mapped[int] = mapped_column(ForeignKey("writers.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    writer: Mapped["Writer"] = relationship("Writer", back_populates="messages")


class WriterPiece(Base):
    __tablename__ = "writer_pieces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    writer_id: Mapped[int] = mapped_column(ForeignKey("writers.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    format: Mapped[str] = mapped_column(String(100), nullable=False, default="other")
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    writer: Mapped["Writer"] = relationship("Writer", back_populates="pieces")


class EvolutionLog(Base):
    __tablename__ = "evolution_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    writer_id: Mapped[int] = mapped_column(ForeignKey("writers.id", ondelete="CASCADE"), nullable=False)
    field_changed: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    writer: Mapped["Writer"] = relationship("Writer", back_populates="evolution_logs")


class StudioSession(Base):
    __tablename__ = "studio_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    writer_id: Mapped[int] = mapped_column(ForeignKey("writers.id", ondelete="CASCADE"), nullable=False)
    brief_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    lifecycle: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    # active | complete | imported | skipped | abandoned
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    writer: Mapped["Writer"] = relationship("Writer", back_populates="studio_sessions")
    takes: Mapped[list["StudioTake"]] = relationship(
        "StudioTake", back_populates="session", cascade="all, delete-orphan",
        order_by="StudioTake.take_number",
    )


class StudioTake(Base):
    __tablename__ = "studio_takes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("studio_sessions.id", ondelete="CASCADE"), nullable=False)
    take_number: Mapped[int] = mapped_column(Integer, nullable=False)
    iteration_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    session: Mapped["StudioSession"] = relationship("StudioSession", back_populates="takes")
