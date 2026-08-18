"""LangGraph adapter with a dependency-free fallback for offline demos."""

from __future__ import annotations

from typing import TypedDict

from .agent import agent


class AgentState(TypedDict):
    session_id: str
    user_id: str
    message: str
    response: dict


def _agent_node(state: AgentState) -> AgentState:
    state["response"] = agent.handle(
        session_id=state["session_id"],
        user_id=state["user_id"],
        message=state["message"],
    )
    return state


try:
    from langgraph.graph import END, START, StateGraph

    _builder = StateGraph(AgentState)
    _builder.add_node("booking_agent", _agent_node)
    _builder.add_edge(START, "booking_agent")
    _builder.add_edge("booking_agent", END)
    _graph = _builder.compile()
except ImportError:
    _graph = None


def run_agent(session_id: str, user_id: str, message: str) -> dict:
    state: AgentState = {
        "session_id": session_id,
        "user_id": user_id,
        "message": message,
        "response": {},
    }
    if _graph is None:
        return _agent_node(state)["response"]
    return _graph.invoke(state)["response"]
