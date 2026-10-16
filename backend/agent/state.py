from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """LangGraph state representation maintaining conversation messages and tool loop round counts."""
    messages: Annotated[list, add_messages]
    rounds: int
