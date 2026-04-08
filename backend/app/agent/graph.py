"""LangGraph orchestration: Historian → Specialist → Anchor pipeline.

The graph runs Historian → Specialist as a compiled subgraph.  The Anchor
is invoked separately via ``stream_anchor()`` so its LLM output can be
streamed token-by-token to the client.  The full graph (including Anchor)
is still available as ``grief_coach_graph`` for non-streaming callers.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agent.nodes.anchor import anchor_node
from app.agent.nodes.historian import historian_node
from app.agent.nodes.specialist import specialist_node
from app.agent.state import AgentState

# --- Full graph (non-streaming, used by tests & voice pipeline) -----------
_graph_builder = StateGraph(AgentState)

_graph_builder.add_node("historian", historian_node)
_graph_builder.add_node("specialist", specialist_node)
_graph_builder.add_node("anchor", anchor_node)

_graph_builder.set_entry_point("historian")
_graph_builder.add_edge("historian", "specialist")
_graph_builder.add_edge("specialist", "anchor")
_graph_builder.add_edge("anchor", END)

grief_coach_graph = _graph_builder.compile()

# --- Pre-anchor graph (streaming: Historian → Specialist only) ------------
_pre_anchor_builder = StateGraph(AgentState)

_pre_anchor_builder.add_node("historian", historian_node)
_pre_anchor_builder.add_node("specialist", specialist_node)

_pre_anchor_builder.set_entry_point("historian")
_pre_anchor_builder.add_edge("historian", "specialist")
_pre_anchor_builder.add_edge("specialist", END)

pre_anchor_graph = _pre_anchor_builder.compile()
