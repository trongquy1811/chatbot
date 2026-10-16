from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.api.deps import exclusive_operation, get_owned_item
from backend.auth import get_current_user
from backend.database import get_db
from backend.models import Memory
from backend.schemas import MemoryResponse, ResolveMemoryRequest
from backend.services.memory import delete_memory, resolve_memory

router = APIRouter(prefix="/memories", tags=["memories"])


@router.get("", response_model=list[MemoryResponse])
def list_memories(
    identity: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all long-term memories for the authenticated user."""
    rows = db.scalars(
        select(Memory).where(Memory.owner == identity)
    )

    return [
        MemoryResponse(
            id=item.id,
            key=item.key,
            value=item.value,
            pending_value=item.pending_value,
            version=item.version,
            source_message_id=item.source_message_id,
        )
        for item in rows
    ]


@router.post(
    "/{memory_id}/resolve",
    response_model=MemoryResponse,
    dependencies=[Depends(exclusive_operation)],
)
def resolve_memory_conflict(
    request: Request,
    memory_id: str,
    body: ResolveMemoryRequest,
    identity: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Resolve conflicting memory:
    - accept=True: commits pending_value to value, bumps version, updates vector store.
    - accept=False: discards pending_value, keeps existing value.
    """
    item = get_owned_item(db, Memory, memory_id, identity)
    vectors = getattr(request.app.state, "vectors", None)

    updated = resolve_memory(db, item, body.accept, vectors=vectors)

    return MemoryResponse(
        id=updated.id,
        key=updated.key,
        value=updated.value,
        pending_value=updated.pending_value,
        version=updated.version,
        source_message_id=updated.source_message_id,
    )


@router.delete(
    "/{memory_id}",
    dependencies=[Depends(exclusive_operation)],
)
def forget_memory(
    request: Request,
    memory_id: str,
    identity: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a memory item, all its revisions, and its vector embeddings."""
    item = get_owned_item(db, Memory, memory_id, identity)
    vectors = getattr(request.app.state, "vectors", None)

    deleted_id = delete_memory(db, item, vectors=vectors)
    return {"deleted": deleted_id}
