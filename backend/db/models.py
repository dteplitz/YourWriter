import enum
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.sqlite import JSON
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
