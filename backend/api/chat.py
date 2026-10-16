import json
import logging
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.agent.graph import run_agent
from backend.api.deps import exclusive_operation, get_owned_item
from backend.auth import get_current_user
from backend.database import get_db
from backend.models import Conversation, Document, Memory, Message
from backend.schemas import ChatRequest, ChatResponse
from backend.services.memory import merge_facts

logger = logging.getLogger("docanalyzer.api.chat")
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "",
    response_model=ChatResponse,
    dependencies=[Depends(exclusive_operation)],
)
def chat_endpoint(
    request: Request,
    body: ChatRequest,
    identity: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Main Chat Q&A Endpoint powered by Agent Harness:
    1. Authenticate user and verify conversation ownership.
    2. Validate that all selected documents are ready and owned by user.
    3. Retrieve recent history (Redis session with automatic PostgreSQL fallback).
    4. Fetch active personal memories for user.
    5. Run LangGraph Agent workflow with semantic search and citation guardrails.
    6. Persist user and assistant messages to database & session store.
    7. If remember=True, extract personal facts, resolve conflicts, and sync memories.
    """
    # 1. Verify conversation
    get_owned_item(db, Conversation, body.conversation_id, identity)

    # 2. Verify selected documents
    document_ids = list(dict.fromkeys(body.document_ids))
    for doc_id in document_ids:
        doc = get_owned_item(db, Document, doc_id, identity)
        if doc.status != "ready":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Selected document '{doc.name}' is not ready (status: {doc.status})",
            )

    # 3. Retrieve short-term history via sessions service (Redis with PG fallback)
    session_store = getattr(request.app.state, "sessions_store", None)
    if session_store:
        history = session_store.get_history(db, body.conversation_id, limit=12)
    else:
        rows = list(
            db.scalars(
                select(Message)
                .where(Message.conversation_id == body.conversation_id)
                .order_by(Message.created_at.desc(), Message.id.desc())
                .limit(12)
            )
        )[::-1]
        history = [{"role": m.role, "content": m.content} for m in rows]

    # 4. Fetch user's active memories
    memories = list(
        db.scalars(
            select(Memory)
            .where(Memory.owner == identity)
            .limit(50)
        )
    )

    trace_id = str(uuid4())
    cfg = request.app.state.cfg
    ai = request.app.state.ai
    vectors = request.app.state.vectors
    cache = request.app.state.cache

    if ai is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chưa cấu hình GOOGLE_API_KEY trong file .env hoặc biến môi trường. Vui lòng thiết lập GOOGLE_API_KEY để sử dụng dịch vụ AI.",
        )

    # 5. Run Agent Harness
    try:
        result = run_agent(
            ai=ai,
            vectors=vectors,
            cache=cache,
            settings=cfg,
            owner=identity,
            document_ids=document_ids,
            question=body.question,
            history=history,
            memories=[{"key": m.key, "value": m.value} for m in memories],
            trace_id=trace_id,
        )
    except Exception as exc:
        logger.error("Agent failed [trace_id=%s]: %s", trace_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "AI service execution failed; retry later",
                "trace_id": trace_id,
            },
        )

    # 6. Save messages to DB
    user_message = Message(
        conversation_id=body.conversation_id,
        role="user",
        content=body.question,
    )
    assistant_message = Message(
        conversation_id=body.conversation_id,
        role="assistant",
        content=result["answer"],
        sources_json=json.dumps(result["sources"], ensure_ascii=False),
    )
    db.add_all([user_message, assistant_message])
    db.commit()

    # Update session cache if present
    if session_store:
        session_store.append_messages(
            body.conversation_id,
            [
                {"role": "user", "content": body.question, "sources": []},
                {
                    "role": "assistant",
                    "content": result["answer"],
                    "sources": result["sources"],
                },
            ],
        )

    # 7. Memorize personal facts if requested
    result["memory"] = {"status": "disabled"}

    if body.remember:
        try:
            facts = ai.extract_facts(body.question, personal=True)
            merge_res = merge_facts(
                db=db,
                owner=identity,
                facts=facts,
                source_message_id=user_message.id,
                vectors=vectors,
            )
            result["memory"] = {
                "status": "processed",
                **merge_res,
            }
        except Exception as exc:
            db.rollback()
            logger.warning("Memory extraction failed [trace_id=%s]: %s", trace_id, exc)
            result["memory"] = {
                "status": "failed",
                "message": "Answer saved; memory update encountered an issue",
            }

    return ChatResponse(**result)
