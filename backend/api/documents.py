import logging
from pathlib import Path
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.api.deps import exclusive_operation, get_owned_item
from backend.auth import get_current_user
from backend.database import get_db
from backend.models import Document
from backend.schemas import DocumentResponse
from backend.services.ingestion import parse_document

logger = logging.getLogger("docanalyzer.api.documents")
router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "",
    response_model=DocumentResponse,
    dependencies=[Depends(exclusive_operation)],
)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    analyze_all_images: bool = False,
    identity: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload and ingest a document.
    Steps:
    1. Validate size and file format.
    2. Save initial document record in PostgreSQL.
    3. Extract text/images and compute chunks.
    4. Index embeddings into Qdrant.
    5. Update status to 'ready'.
    """
    cfg = request.app.state.cfg
    ai = request.app.state.ai
    vectors = request.app.state.vectors

    if ai is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chưa cấu hình GOOGLE_API_KEY trong file .env hoặc biến môi trường. Vui lòng thiết lập GOOGLE_API_KEY để xử lý tài liệu.",
        )

    filename = (file.filename or "document").replace("\\", "/")
    name = Path(filename).name[:255]

    content = await file.read(cfg.max_upload_mb * 1024 * 1024 + 1)

    if len(content) > cfg.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum upload size of {cfg.max_upload_mb} MB",
        )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    document = Document(
        owner=identity,
        name=name,
        status="processing",
    )
    db.add(document)
    db.commit()

    original_path = cfg.data_dir / "originals" / document.id
    original_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        chunks = parse_document(
            data=content,
            name=name,
            ai=ai,
            settings=cfg,
            analyze_all_images=analyze_all_images,
        )

        original_path.write_bytes(content)

        vectors.add(
            owner=identity,
            document_id=document.id,
            name=name,
            chunks=chunks,
        )

        document.status = "ready"
        document.chunks = len(chunks)
        db.commit()

    except Exception as exc:
        db.rollback()

        document = db.get(Document, document.id)
        if document:
            document.status = "failed"
            db.commit()

        original_path.unlink(missing_ok=True)

        try:
            vectors.delete(identity, document.id)
        except Exception:
            logger.warning("Failed cleanup of vectors after upload failure")

        if isinstance(exc, ValueError):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            )

        logger.error("Upload processing failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Document processing failed; inspect server logs",
        )

    return DocumentResponse(
        id=document.id,
        name=document.name,
        status=document.status,
        chunks=document.chunks,
        created_at=document.created_at,
    )


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    identity: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all documents belonging to current authenticated user."""
    rows = db.scalars(
        select(Document)
        .where(Document.owner == identity)
        .order_by(Document.created_at)
    )

    return [
        DocumentResponse(
            id=item.id,
            name=item.name,
            status=item.status,
            chunks=item.chunks,
            created_at=item.created_at,
        )
        for item in rows
    ]


@router.delete(
    "/{document_id}",
    dependencies=[Depends(exclusive_operation)],
)
def delete_document(
    request: Request,
    document_id: str,
    identity: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a document, its vector points, and underlying stored file."""
    document = get_owned_item(db, Document, document_id, identity)
    cfg = request.app.state.cfg
    vectors = request.app.state.vectors

    vectors.delete(identity, document.id)

    (cfg.data_dir / "originals" / document.id).unlink(missing_ok=True)

    db.delete(document)
    db.commit()

    return {"deleted": document_id}
