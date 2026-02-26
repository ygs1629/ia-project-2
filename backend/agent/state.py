from typing import Annotated
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """Estado que viaja por el grafo de LangGraph."""
    messages: Annotated[list, add_messages]