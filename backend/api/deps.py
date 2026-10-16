from collections.abc import Generator
from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session


def exclusive_operation(request: Request) -> Generator[None, None, None]:
    """
    Acquire non-blocking lock to prevent overlapping write or ingestion operations.
    Raises 409 Conflict if another operation is actively executing.
    """
    lock = getattr(request.app.state, "operation_lock", None)
    if lock is not None:
        acquired = lock.acquire(blocking=False)
        if not acquired:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Another write or AI operation is running; retry shortly",
            )
        try:
            yield
        finally:
            lock.release()
    else:
        yield


def get_owned_item(db: Session, model: type, item_id: str, identity: str):
    """Retrieve an item by ID, strictly verifying ownership."""
    item = db.scalar(
        select(model).where(
            model.id == item_id,
            model.owner == identity,
        )
    )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found or unauthorized",
        )
    return item
