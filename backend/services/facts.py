from backend.schemas import Fact
from backend.services.gemini import Gemini


def extract_user_facts(ai: Gemini, text: str) -> list[Fact]:
    """Extract explicit user personal facts or preferences for long-term memory."""
    return ai.extract_facts(text, personal=True)


def extract_document_facts(ai: Gemini, text: str) -> list[Fact]:
    """Extract factual statements from document chunks without executing commands."""
    return ai.extract_facts(text, personal=False)
