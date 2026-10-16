from typing import Any
from pydantic import BaseModel, Field


# Fact Models
class Fact(BaseModel):
    key: str = Field(
        min_length=1,
        max_length=120,
        description="Stable lowercase key for one fact",
    )
    value: str = Field(
        min_length=1,
        max_length=1000,
        description="Fact value or preference",
    )


class Facts(BaseModel):
    facts: list[Fact] = Field(
        default_factory=list,
        max_length=10,
    )


# Document Models
class DocumentResponse(BaseModel):
    id: str
    name: str
    status: str
    chunks: int
    created_at: str | None = None


# Conversation & Message Models
class ConversationCreate(BaseModel):
    title: str = Field(
        default="New conversation",
        min_length=1,
        max_length=120,
    )


class ConversationResponse(BaseModel):
    id: str
    title: str


class MessageResponse(BaseModel):
    role: str
    content: str
    sources: list[dict[str, Any]] = Field(default_factory=list)


# Chat Models
class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    conversation_id: str = Field(min_length=1, max_length=36)
    document_ids: list[str] = Field(default_factory=list, max_length=30)
    remember: bool = False
    analyze_all_images: bool = False


class SourceItem(BaseModel):
    id: str
    document_id: str
    name: str
    page: int
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict[str, Any]]
    trace_id: str
    trace: list[dict[str, Any]]
    memory: dict[str, Any]


# Memory Models
class MemoryResponse(BaseModel):
    id: str
    key: str
    value: str
    pending_value: str | None = None
    version: int
    source_message_id: str


class ResolveMemoryRequest(BaseModel):
    accept: bool


# System Health
class HealthResponse(BaseModel):
    status: str
