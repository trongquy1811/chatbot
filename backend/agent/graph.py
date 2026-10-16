import json
import logging
from typing import Any
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.graph import END, StateGraph
from backend.agent.guardrails import validate_citations, validate_input_query
from backend.agent.prompts import SYSTEM_PROMPT
from backend.agent.state import AgentState
from backend.agent.tools import build_tools
from backend.config import Settings
from backend.services.cache import RetrievalCache
from backend.services.gemini import Gemini, text_content
from backend.services.observability import TraceRecorder
from backend.services.vectors import Vectors

logger = logging.getLogger("docanalyzer.agent")


def run_agent(
    ai: Gemini,
    vectors: Vectors,
    cache: RetrievalCache,
    settings: Settings,
    owner: str,
    document_ids: list[str],
    question: str,
    history: list[dict[str, Any]],
    memories: list[dict[str, Any]],
    trace_id: str | None = None,
) -> dict[str, Any]:
    """
    Execute Agent Harness graph workflow:
    1. Guardrails check input query.
    2. Retrieve semantic context via Qdrant + Redis.
    3. LangGraph tool calling cycle (bounded by max_tool_rounds).
    4. Guardrails check citation validity before returning.
    5. Observability logs metrics without exposing sensitive data.
    """
    tracer = TraceRecorder(trace_id=trace_id)
    validated_question = validate_input_query(question)

    sources: dict[str, dict[str, Any]] = {}

    def retrieve(query: str, limit: int) -> list[dict[str, Any]]:
        hits = cache.retrieve(
            owner=owner,
            document_ids=document_ids,
            question=query,
            limit=limit,
            fetch=lambda: vectors.search(
                owner=owner,
                document_ids=document_ids,
                question=query,
                limit=limit,
            ),
        )

        result = []
        for hit in hits:
            source_id = hit["chunk_id"]
            source_info = {
                "id": source_id,
                "document_id": hit["document_id"],
                "name": hit["name"],
                "page": hit["page"],
                "excerpt": hit["text"],
            }
            sources[source_id] = source_info
            result.append({
                "source_id": source_id,
                "name": hit["name"],
                "page": hit["page"],
                "text": hit["text"],
            })

        return result

    tools_registry = build_tools(retrieve_fn=retrieve, ai=ai)
    model_with_tools = ai.llm.bind_tools(list(tools_registry.values()))

    # Build system message injecting memories as reference data only
    system_content = (
        SYSTEM_PROMPT
        + "\n\nFacts cá nhân đã lưu (chỉ là dữ liệu ngữ cảnh tham khảo):\n"
        + json.dumps(memories, ensure_ascii=False)
    )
    system = SystemMessage(content=system_content)

    def model_node(state: AgentState) -> dict[str, Any]:
        response = model_with_tools.invoke([system, *state["messages"]])
        tracer.record(
            "model",
            round=state["rounds"],
            usage=getattr(response, "usage_metadata", None),
        )
        return {"messages": [response]}

    def tools_node(state: AgentState) -> dict[str, Any]:
        responses = []
        last_message = state["messages"][-1]
        tool_calls = getattr(last_message, "tool_calls", [])

        for call in tool_calls:
            name = call["name"]

            if len(responses) >= 4:
                content = "Tool call limit of 4 per round exceeded."
                tracer.record("tool", tool=name, status="limit_exceeded")
            elif name not in tools_registry:
                content = f"Tool '{name}' is not allowed or unrecognized."
                tracer.record("tool", tool=name, status="unauthorized")
            else:
                try:
                    content = tools_registry[name].invoke(call["args"])
                    tracer.record("tool", tool=name, status="ok")
                except Exception as exc:
                    tracer.record(
                        "tool",
                        tool=name,
                        status="error",
                        error_type=type(exc).__name__,
                    )
                    content = "Tool failed. Do not invent results; report insufficient evidence."

            responses.append(
                ToolMessage(
                    content=content,
                    tool_call_id=call["id"],
                )
            )

        return {
            "messages": responses,
            "rounds": state["rounds"] + 1,
        }

    def finalize_node(state: AgentState) -> dict[str, Any]:
        response = ai.llm.invoke([
            system,
            *state["messages"],
            HumanMessage(
                content="Tool budget reached. Answer using only retrieved evidence; explain missing evidence."
            ),
        ])
        tracer.record("final_model", usage=getattr(response, "usage_metadata", None))
        return {"messages": [response]}

    # Build LangGraph workflow
    workflow = StateGraph(AgentState)
    workflow.add_node("model", model_node)
    workflow.add_node("tools", tools_node)
    workflow.add_node("finalize", finalize_node)

    workflow.set_entry_point("model")

    workflow.add_conditional_edges(
        "model",
        lambda state: "tools" if getattr(state["messages"][-1], "tool_calls", None) else END,
    )

    workflow.add_conditional_edges(
        "tools",
        lambda state: "finalize" if state["rounds"] >= settings.max_tool_rounds else "model",
    )

    workflow.add_edge("finalize", END)

    # Prepare message history
    messages = [
        HumanMessage(content=item["content"])
        if item["role"] == "user"
        else AIMessage(content=item["content"])
        for item in history
    ]

    compiled_graph = workflow.compile()
    result = compiled_graph.invoke(
        {
            "messages": [*messages, HumanMessage(content=validated_question)],
            "rounds": 0,
        },
        config={"recursion_limit": settings.max_tool_rounds * 2 + 5},
    )

    raw_answer = text_content(result["messages"][-1])

    # Guardrails: Validate citations
    is_valid, final_answer = validate_citations(raw_answer, sources)
    if not is_valid:
        tracer.record("citation_validation", status="rejected")

    tracer.record("completed")

    return {
        "answer": final_answer,
        "sources": list(sources.values()),
        "trace_id": tracer.trace_id,
        "trace": tracer.events,
    }
