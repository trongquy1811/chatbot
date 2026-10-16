import re
from typing import Any


class GuardrailViolation(Exception):
    """Raised when an input or output fails security guardrail checks."""
    pass


def validate_input_query(query: str, max_length: int = 4000) -> str:
    """Validate user input length and clean basic issues."""
    cleaned = query.strip()
    if not cleaned:
        raise GuardrailViolation("Question cannot be empty.")
    if len(cleaned) > max_length:
        raise GuardrailViolation(f"Question exceeds max allowed length of {max_length} characters.")
    return cleaned


def validate_citations(answer: str, valid_sources: dict[str, Any]) -> tuple[bool, str]:
    """
    Validate that every [source:<id>] cited by LLM corresponds to an authorized source chunk
    retrieved in the current execution turn.
    Returns (is_valid, sanitized_answer).
    """
    cited_ids = re.findall(r"\[source:([^\]]+)\]", answer)
    invalid_ids = [sid for sid in cited_ids if sid not in valid_sources]

    if invalid_ids:
        warning_msg = (
            "Không thể xác minh nguồn của câu trả lời này do chứa trích dẫn không hợp lệ. "
            "Vui lòng thử lại hoặc đặt câu hỏi cụ thể hơn."
        )
        return False, warning_msg

    return True, answer


def sanitize_reference_content(text: str) -> str:
    """
    Guardrail to ensure document content is treated strictly as reference data.
    Prefixes or neutralizes known prompt injection override patterns.
    """
    # Replace direct command overrides with inert text
    patterns = [
        (r"(?i)ignore (all )?previous instructions", "[REDACTED_INSTRUCTION]"),
        (r"(?i)system prompt override", "[REDACTED_INSTRUCTION]"),
        (r"(?i)you are now in developer mode", "[REDACTED_INSTRUCTION]"),
    ]
    sanitized = text
    for pattern, replacement in patterns:
        sanitized = re.sub(pattern, replacement, sanitized)
    return sanitized
