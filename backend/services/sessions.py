import json
import logging
from typing import Any
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.models import Message

logger = logging.getLogger("docanalyzer.sessions")


class SessionStore:
    """
    Manages short-term conversation context and history.
    Uses Redis for rapid cache retrieval with automatic fallback to PostgreSQL.
    Rule: 'Redis lỗi thì lấy lịch sử từ PostgreSQL'.
    """

    def __init__(self, redis_client: Redis | None = None):
        self.redis = redis_client

    def _redis_key(self, conversation_id: str) -> str:
        return f"session:{conversation_id}:messages"

    def get_history(
        self,
        db: Session,
        conversation_id: str,
        limit: int = 12,
    ) -> list[dict[str, Any]]:
        """
        Fetch recent conversation messages.
        Attempts Redis first; falls back cleanly to PostgreSQL on cache miss or Redis error.
        """
        if self.redis:
            try:
                cached_data = self.redis.get(self._redis_key(conversation_id))
                if cached_data:
                    messages = json.loads(cached_data)
                    return messages[-limit:]
            except (RedisError, Exception) as exc:
                logger.warning(
                    "Redis session read failed (%s); falling back to PostgreSQL",
                    type(exc).__name__,
                )

        # Fallback to PostgreSQL
        rows = list(
            db.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.desc(), Message.id.desc())
                .limit(limit)
            )
        )[::-1]

        history = [
            {
                "role": msg.role,
                "content": msg.content,
                "sources": json.loads(msg.sources_json) if msg.sources_json else [],
            }
            for msg in rows
        ]

        # Populate Redis cache if possible
        if self.redis and history:
            try:
                self.redis.setex(
                    self._redis_key(conversation_id),
                    3600,  # 1 hour TTL
                    json.dumps(history, ensure_ascii=False),
                )
            except (RedisError, Exception):
                logger.warning("Redis session write failed")

        return history

    def append_messages(
        self,
        conversation_id: str,
        new_messages: list[dict[str, Any]],
    ) -> None:
        """Update Redis session cache if available."""
        if not self.redis:
            return

        try:
            cached_data = self.redis.get(self._redis_key(conversation_id))
            messages = json.loads(cached_data) if cached_data else []
            messages.extend(new_messages)
            # Keep last 50
            messages = messages[-50:]
            self.redis.setex(
                self._redis_key(conversation_id),
                3600,
                json.dumps(messages, ensure_ascii=False),
            )
        except (RedisError, Exception):
            logger.warning("Redis session update failed")
