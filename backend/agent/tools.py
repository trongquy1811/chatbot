import json
from collections.abc import Callable
from typing import Any
from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field
from backend.services.gemini import Gemini


class SearchArgs(BaseModel):
    query: str = Field(
        min_length=1,
        max_length=2000,
        description="Search query to locate relevant excerpts in authorized documents",
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=8,
        description="Maximum number of excerpts to retrieve",
    )


class ExtractArgs(BaseModel):
    query: str = Field(
        min_length=1,
        max_length=2000,
        description="Search query to find excerpts from which to extract structured facts",
    )


def build_tools(
    retrieve_fn: Callable[[str, int], list[dict[str, Any]]],
    ai: Gemini,
) -> dict[str, BaseTool]:
    """
    Build execution tools bound to the current request's retrieval context.
    """

    @tool(args_schema=SearchArgs)
    def search_documents(query: str, limit: int = 5) -> str:
        """Search authorized selected documents and return excerpts with source IDs."""
        hits = retrieve_fn(query, limit)
        return json.dumps(hits, ensure_ascii=False)

    @tool(args_schema=ExtractArgs)
    def extract_document_facts(query: str) -> str:
        """Extract key/value facts from relevant document excerpts without saving personal memory."""
        hits = retrieve_fn(query, 4)
        if not hits:
            return "No matching documents found."

        facts = ai.extract_facts(json.dumps(hits, ensure_ascii=False))

        return json.dumps(
            {
                "facts": [fact.model_dump() for fact in facts],
                "source_ids": [hit["source_id"] for hit in hits],
            },
            ensure_ascii=False,
        )

    tools_list = [search_documents, extract_document_facts]
    return {t.name: t for t in tools_list}
