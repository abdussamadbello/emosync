# AGENTS.md — EmoSync Agent Architecture

## Overview

EmoSync uses a LangGraph-based agentic pipeline to generate therapy-informed responses for grief and heartbreak support. The pipeline runs three sequential nodes, each backed by Gemini 1.5 Pro.

## Pipeline: Historian → Specialist → Anchor

```
User message + conversation history
        │
        ▼
┌──────────────┐
│  Historian    │  Gather context from MCP servers (calendar dates,
│  (temp=0.3)   │  journal entries). Currently stubbed — M5 pending.
└──────┬───────┘
       ▼
┌──────────────┐
│  Specialist   │  Apply CBT, ACT, and Narrative Therapy frameworks.
│  (temp=0.7)   │  Uses Historian context as evidence for reframing.
└──────┬───────┘
       ▼
┌──────────────┐
│  Anchor       │  Trauma-informed safety & validation layer.
│  (temp=0.3)   │  Ensures responses are emotionally safe.
└──────┬───────┘
       ▼
  Final response (streamed word-by-word via SSE)
```

## Agent State

Defined in `backend/app/agent/state.py` as a `TypedDict`:

| Field | Type | Set by |
|-------|------|--------|
| `user_message` | `str` | Input |
| `conversation_id` | `str` | Input |
| `conversation_history` | `list[dict[str, str]]` | Input |
| `calendar_context` | `list[str]` | Historian |
| `journal_context` | `list[str]` | Historian |
| `historian_briefing` | `dict` (`date_insights`, `journal_insights`) | Historian |
| `specialist_response` | `str` | Specialist |
| `final_response` | `str` | Anchor |

## Node details

### Historian (`backend/app/agent/nodes/historian.py`)

- **Purpose:** Pull context from MCP servers — calendar dates, journal entries, past reflections.
- **LLM:** Gemini 1.5 Pro, temperature 0.3
- **MCP status:** Stub calls (passes empty lists). Wire real Calendar + Journal servers for M5.
- **Output:** JSON with `date_insights` and `journal_insights` fields.
- **Fallback:** Returns safe default context if LLM fails.

### Specialist (`backend/app/agent/nodes/specialist.py`)

- **Purpose:** Apply therapy frameworks using Historian context as evidence.
- **LLM:** Gemini 1.5 Pro, temperature 0.7
- **Frameworks:**
  - **CBT:** Identify cognitive distortions, reframe with evidence
  - **ACT:** Psychological flexibility, values clarification
  - **Narrative Therapy:** Externalise problems, unique outcomes, resilience
- **Output:** Warm, conversational 2–4 paragraph response.
- **Constraints:** No diagnosis, no medication advice. Include crisis resources (988 Lifeline, Crisis Text Line) if suicidal ideation is detected.

### Anchor (`backend/app/agent/nodes/anchor.py`)

- **Purpose:** Trauma-informed safety and validation layer.
- **LLM:** Gemini 1.5 Pro, temperature 0.3
- **Checks:**
  - Validation before reframing (never skip acknowledgment)
  - No victim-blaming, toxic positivity, or minimising
  - Safety check for suicidal ideation (crisis resources)
  - Emotional pacing matched to user's energy
  - No hallucinated context (verify against Historian briefing)
  - Appends prosody hint at end (e.g. `[speak slowly, warm tone]`) — stripped before text streaming
- **Output:** Polished final response ready for the user.

## Integration boundary

The HTTP layer calls **only** `run_turn()` in `backend/app/services/chat_turn.py`. This function:

1. Checks if `GEMINI_API_KEY` is set
2. If yes → invokes `grief_coach_graph.ainvoke(initial_state)` (full pipeline)
3. If no → returns a deterministic stub (safe for CI / local dev)
4. Strips prosody hints from the final response
5. Streams word-by-word as an `AsyncIterator[str]`
6. Falls back to a safe empathetic message if the pipeline raises

## Graph definition

The graph is compiled in `backend/app/agent/graph.py`:

```python
historian → specialist → anchor → END
```

Linear pipeline (no conditional edges). All three nodes always run.

## Extending the pipeline

- **Add a new node:** Define it in `backend/app/agent/nodes/`, add fields to `AgentState`, register in `graph.py` with `add_node` + `add_edge`.
- **Modify prompts:** Edit `backend/app/agent/prompts.py`. Each node has its own system prompt.
- **Wire MCP servers:** Replace stub calls in `historian.py` with real MCP tool invocations. The state already has `calendar_context` and `journal_context` fields.
- **Add conditional routing:** Use `add_conditional_edges` in `graph.py` if you need to skip nodes or branch.

## Testing

Agent tests are in `backend/tests/test_agent.py`. They run without `GEMINI_API_KEY` (stub mode). To test the full pipeline locally, set the key in `.env` and run:

```bash
cd backend && python -m pytest tests/test_agent.py -q
```
