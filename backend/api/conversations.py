import json
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.api.deps import get_owned_item
from backend.auth import get_current_user
from backend.database import get_db
from backend.models import Conversation, Message
from backend.schemas import (
    ConversationCreate,
    ConversationResponse,
    MessageResponse,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationResponse)
def create_conversation(
    body: ConversationCreate,
    identity: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new conversation."""
    item = Conversation(
        owner=identity,
        title=body.title,
    )
    db.add(item)
    db.commit()

    return ConversationResponse(id=item.id, title=item.title)


@router.get("", response_model=list[ConversationResponse])
def list_conversations(
    identity: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all conversations for the authenticated user."""
    rows = db.scalars(
        select(Conversation)
        .where(Conversation.owner == identity)
        .order_by(Conversation.created_at.desc())
    )

    return [
        ConversationResponse(id=item.id, title=item.title)
        for item in rows
    ]


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
def get_conversation_messages(
    conversation_id: str,
    identity: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve full history of messages in a conversation."""
    get_owned_item(db, Conversation, conversation_id, identity)

    rows = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at, Message.id)
    )

    return [
        MessageResponse(
            role=item.role,
            content=item.content,
            sources=json.loads(item.sources_json) if item.sources_json else [],
        )
        for item in rows
    ]
