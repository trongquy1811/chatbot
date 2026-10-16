import logging
from typing import Any
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from backend.models import Memory, MemoryRevision
from backend.schemas import Fact
from backend.services.vectors import Vectors

logger = logging.getLogger("docanalyzer.memory")


def merge_facts(
    db: Session,
    owner: str,
    facts: list[Fact],
    source_message_id: str,
    vectors: Vectors | None = None,
) -> dict[str, int]:
    """
    Merge newly extracted user facts into long-term memory.
    Enforces the core rule:
    - If a new fact conflicts with an existing one, it does NOT overwrite immediately;
      it enters a 'pending_value' state waiting for explicit user confirmation.
    - PostgreSQL is the source of truth.
    - Qdrant only indexes accepted memories.
    """
    result = {
        "added": 0,
        "unchanged": 0,
        "conflicts": 0,
    }

    for fact in facts:
        key = " ".join(fact.key.lower().split())
        if not key:
            continue

        # Check existing memory for owner
        query = select(Memory).where(Memory.owner == owner, Memory.key == key)
        # with_for_update() is PostgreSQL/MySQL specific; handle gracefully if sqlite
        bind = db.get_bind()
        if bind and bind.dialect.name != "sqlite":
            query = query.with_for_update()

        memory = db.scalar(query)

        if memory is None:
            memory = Memory(
                owner=owner,
                key=key,
                value=fact.value,
                source_message_id=source_message_id,
                version=1,
            )
            db.add(memory)
            db.flush()

            revision = MemoryRevision(
                memory_id=memory.id,
                value=memory.value,
                source_message_id=source_message_id,
                version=1,
            )
            db.add(revision)

            # Sync confirmed new memory to vector database
            if vectors:
                try:
                    vectors.index_memory(owner, memory.id, memory.key, memory.value)
                except Exception as exc:
                    logger.warning("Failed to index memory in vector store: %s", exc)

            result["added"] += 1

        elif memory.value.strip().casefold() == fact.value.strip().casefold():
            result["unchanged"] += 1

        else:
            # Memory conflict: retain old value until user explicitly resolves it.
            memory.pending_value = fact.value
            memory.pending_source_id = source_message_id
            result["conflicts"] += 1

    db.commit()
    return result


def resolve_memory(
    db: Session,
    memory: Memory,
    accept: bool,
    vectors: Vectors | None = None,
) -> Memory:
    """
    Resolve a pending conflicting memory update based on user confirmation.
    """
    if accept and memory.pending_value is not None:
        memory.value = memory.pending_value
        memory.source_message_id = memory.pending_source_id or memory.source_message_id
        memory.version += 1

        db.add(
            MemoryRevision(
                memory_id=memory.id,
                value=memory.value,
                source_message_id=memory.source_message_id,
                version=memory.version,
            )
        )

        if vectors:
            try:
                vectors.index_memory(memory.owner, memory.id, memory.key, memory.value)
            except Exception as exc:
                logger.warning("Failed to sync resolved memory to vector store: %s", exc)

    # Clear pending state
    memory.pending_value = None
    memory.pending_source_id = None
    db.commit()
    return memory


def delete_memory(
    db: Session,
    memory: Memory,
    vectors: Vectors | None = None,
) -> str:
    """
    Delete a memory record, its revisions, and its vector representation.
    """
    memory_id = memory.id
    owner = memory.owner

    db.execute(
        delete(MemoryRevision).where(MemoryRevision.memory_id == memory_id)
    )
    db.delete(memory)
    db.commit()

    if vectors:
        try:
            vectors.delete_memory(owner, memory_id)
        except Exception as exc:
            logger.warning("Failed to delete memory from vector store: %s", exc)

    return memory_id
