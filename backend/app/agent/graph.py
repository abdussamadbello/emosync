"""LangGraph orchestration: Historian → Specialist → Anchor pipeline."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agent.nodes.anchor import anchor_node
from app.agent.nodes.historian import historian_node
from app.agent.nodes.specialist import specialist_node
from app.agent.state import AgentState

_graph_builder = StateGraph(AgentState)

_graph_builder.add_node("historian", historian_node)
_graph_builder.add_node("specialist", specialist_node)
_graph_builder.add_node("anchor", anchor_node)

_graph_builder.set_entry_point("historian")
_graph_builder.add_edge("historian", "specialist")
_graph_builder.add_edge("specialist", "anchor")
_graph_builder.add_edge("anchor", END)

grief_coach_graph = _graph_builder.compile()
