from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)


def uid() -> str:
    return str(uuid4())


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=uid
    )
    owner: Mapped[str] = mapped_column(String(200), index=True)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        String(20), default="processing"
    )
    chunks: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str] = mapped_column(
        String(40), default=now
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=uid
    )
    owner: Mapped[str] = mapped_column(String(200), index=True)
    title: Mapped[str] = mapped_column(
        String(120), default="New conversation"
    )
    created_at: Mapped[str] = mapped_column(
        String(40), default=now
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=uid
    )
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    sources_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[str] = mapped_column(
        String(40), default=now
    )


class Memory(Base):
    __tablename__ = "memories"

    __table_args__ = (
        UniqueConstraint(
            "owner", "key", name="uq_memory_owner_key"
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=uid
    )
    owner: Mapped[str] = mapped_column(String(200), index=True)
    key: Mapped[str] = mapped_column(String(120))
    value: Mapped[str] = mapped_column(Text)

    pending_value: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    source_message_id: Mapped[str] = mapped_column(String(36))
    pending_source_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1)


class MemoryRevision(Base):
    __tablename__ = "memory_revisions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=uid
    )
    memory_id: Mapped[str] = mapped_column(
        ForeignKey("memories.id"), index=True
    )
    value: Mapped[str] = mapped_column(Text)
    source_message_id: Mapped[str] = mapped_column(String(36))
    version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[str] = mapped_column(
        String(40), default=now
    )
