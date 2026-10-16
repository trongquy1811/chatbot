from collections.abc import Callable
import hashlib
import json
import logging
from typing import Any
from redis import Redis
from redis.exceptions import RedisError

logger = logging.getLogger("docanalyzer.cache")


class RetrievalCache:
    """Redis cache for semantic search / retrieval results."""

    def __init__(self, url: str | None = None):
        self.client = (
            Redis.from_url(
                url,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
            if url
            else None
        )

    def retrieve(
        self,
        owner: str,
        document_ids: list[str],
        question: str,
        limit: int,
        fetch: Callable[[], list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        """
        Retrieve cached semantic search results if available; otherwise call fetch() and cache.
        Cached by user and document IDs to prevent data leakage.
        """
        payload = json.dumps(
            [owner, sorted(document_ids), question, limit],
            ensure_ascii=False,
        )
        key = "retrieval:v1:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()

        if self.client:
            try:
                cached = self.client.get(key)
                if cached:
                    return json.loads(cached)
            except (RedisError, ValueError, Exception):
                logger.warning("cache_read_unavailable")

        result = fetch()

        if self.client:
            try:
                self.client.setex(
                    key,
                    120,
                    json.dumps(result, ensure_ascii=False),
                )
            except (RedisError, Exception):
                logger.warning("cache_write_unavailable")

        return result
