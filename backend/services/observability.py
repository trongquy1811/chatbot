import json
import logging
import time
from typing import Any
from uuid import uuid4

logger = logging.getLogger("docanalyzer.observability")


def generate_trace_id() -> str:
    """Generate a unique trace ID."""
    return str(uuid4())


class TraceRecorder:
    """
    Records request lifecycle events and execution times.
    Enforces privacy guardrails: never records raw tokens, API keys, or raw confidential texts.
    """

    def __init__(self, trace_id: str | None = None):
        self.trace_id = trace_id or generate_trace_id()
        self.started_at = time.monotonic()
        self.events: list[dict[str, Any]] = []

    def record(self, event: str, **fields: Any) -> dict[str, Any]:
        elapsed_ms = round((time.monotonic() - self.started_at) * 1000)

        # Sanitize sensitive keys
        safe_fields = {}
        for k, v in fields.items():
            if any(secret in k.lower() for secret in ["token", "key", "password", "secret", "auth"]):
                safe_fields[k] = "[REDACTED]"
            else:
                safe_fields[k] = v

        item = {
            "event": event,
            "elapsed_ms": elapsed_ms,
            **safe_fields,
        }
        self.events.append(item)

        log_payload = {
            "trace_id": self.trace_id,
            **item,
        }
        logger.info(json.dumps(log_payload, ensure_ascii=False))
        return item
