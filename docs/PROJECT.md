# EmoSync: Context-Aware Multimodal Grief Coach

## Project Overview

EmoSync is a privacy-first, hybrid AI coach for navigating grief and heartbreak. It combines real-time voice chat (via Gemini Live or ElevenLabs STT/TTS) and SSE-streamed text chat, grounded in the user's life events (Calendar) and reflections (Journals) through MCP servers and pgvector semantic search. Responses are shaped by CBT, ACT, and Narrative Therapy frameworks via a 3-node LangGraph agent pipeline.

**Status:** Functional prototype — backend API, agent pipeline, voice pipeline, ingestion, and Next.js frontend are all implemented and integrated.

---

## Core Features

| Feature | Description |
|---------|-------------|
| **Hybrid Interface** | Seamlessly switch between real-time voice and traditional text chat within the same conversation. |
| **Voice-First Empathy** | Two voice modes: Gemini Live (real-time bidirectional) or legacy ElevenLabs STT → LLM → TTS pipeline, with prosody-aware prompts for soothing output. |
| **MCP Calendar Server** | Identifies anniversaries, holidays, and significant dates to provide context-aware support. |
| **MCP Journal Server** | Semantic search over journal entries via pgvector embeddings to find evidence for CBT reframing. |
| **CBT Knowledge Base** | Ingested CBT PDF chunks stored as pgvector embeddings, retrieved by the Historian to ground therapy responses. |
| **Agentic Reasoning** | LangGraph-powered 3-node pipeline (Historian → Specialist → Anchor) for context-aware, therapy-informed, safety-validated responses. |
| **Stub Mode** | Full test and local dev support without any API keys — deterministic stub responses throughout. |

---

## Architecture

### High-Level Flow

```
User Input (Voice or Text)
        │
        ├── Text ──→ POST /conversations/{id}/messages/stream (SSE)
        │
        └── Voice ─→ WebSocket /voice/ws/{conversation_id}
                     │
                     ├── Gemini Live mode (real-time bidirectional)
                     └── Legacy mode (ElevenLabs STT → LLM → TTS)
                     │
                     ▼
              ┌─────────────────────────────────────────┐
              │         LangGraph Agent Pipeline         │
              │                                          │
              │  ┌──────────────┐  ┌─────────────────┐  │
              │  │  Historian    │  │ pgvector Search  │  │
              │  │  (Context)    │→ │ Journal entries  │  │
              │  │  temp=0.3     │  │ CBT PDF chunks   │  │
              │  └──────┬───────┘  └─────────────────┘  │
              │         ▼                                │
              │  ┌──────────────┐                        │
              │  │  Specialist   │  CBT/ACT/Narrative    │
              │  │  (Therapy)    │  Therapy frameworks    │
              │  │  temp=0.7     │                        │
              │  └──────┬───────┘                        │
              │         ▼                                │
              │  ┌──────────────┐                        │
              │  │  Anchor       │  Trauma-informed       │
              │  │  (Safety)     │  validation + prosody  │
              │  │  temp=0.3     │                        │
              │  └──────┬───────┘                        │
              └─────────┼────────────────────────────────┘
                        ▼
              ┌──────────────────────┐
              │  Text → SSE tokens    │
              │  Audio → TTS stream   │  (ElevenLabs or Gemini Live)
              └──────────────────────┘
```

### Agent Roles

| Agent | Model | Temp | Purpose |
|-------|-------|------|---------|
| **The Historian** | gemini-2.5-flash-lite | 0.3 | Embeds user message, runs parallel pgvector searches (journal + CBT chunks), assembles a contextual briefing with `date_insights` and `journal_insights`. |
| **The Specialist** | gemini-2.5-flash | 0.7 | Generates therapy-informed response using CBT, ACT, and Narrative Therapy frameworks, grounded in the Historian's briefing. Includes prosody hints for TTS. |
| **The Anchor** | gemini-2.5-flash | 0.3 | Safety & validation layer — checks for trauma-informed language, verifies no hallucinated context, ensures crisis resources on suicidal ideation, enforces emotional pacing. Falls back to Specialist response on timeout. |

---

## Technical Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 15 (App Router), Tailwind CSS, Web Audio API, Lucide React, Shadcn/ui |
| **Backend** | Python 3.11, FastAPI, LangGraph, SQLAlchemy (async) |
| **AI/LLM** | Gemini 2.5 Flash / Flash-Lite (agent nodes), Gemini Embeddings (768-dim) |
| **Voice** | Gemini Live (real-time bidirectional) or ElevenLabs (STT + TTS fallback) |
| **Database** | PostgreSQL 16 + pgvector (cosine similarity search) |
| **MCP** | Calendar + Journal servers (mock data, semantic journal search via pgvector) |
| **Ingestion** | PDF → chunk → embed → tag → pgvector pipeline for CBT knowledge base |
| **Infrastructure** | Docker Compose (local), GitHub Actions (CI/CD), GHCR (container registry) |

---

## Current Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| FastAPI backend scaffold | Done | CORS, middleware, error handling, request IDs, rate limiting |
| PostgreSQL + pgvector schema | Done | Users, conversations, messages, embedding_chunks (768-dim) |
| User authentication (JWT) | Done | Register, login, `/auth/me`; bcrypt + JWT (HS256) |
| REST/SSE chat API | Done | `/api/v1/conversations`, word-by-word SSE streaming |
| Docker Compose stack | Done | Postgres (pgvector:pg16) + API, one-command startup |
| CI/CD pipelines | Done | Ruff lint, Alembic check, pytest, Docker build, GHCR publish |
| LangGraph orchestration | Done | Historian → Specialist → Anchor pipeline; activated by `GEMINI_API_KEY` |
| Agent integration boundary | Done | `run_turn()` in `chat_turn.py`; stub fallback without API key |
| Voice pipeline (Gemini Live) | Done | Real-time bidirectional WebSocket bridge to Gemini Live API |
| Voice pipeline (Legacy) | Done | ElevenLabs STT → Agent → ElevenLabs TTS chain via WebSocket |
| MCP servers | Done | Calendar + Journal servers with mock data; journal has pgvector search |
| CBT ingestion pipeline | Done | PDF load → chunk → embed → tag → pgvector storage |
| Vector retrieval | Done | Historian queries CBT chunks + journal entries in parallel via pgvector |
| Next.js frontend | Done | Auth pages, chat view (SSE), sidebar, voice panel with audio visualisation |
| Cloud deployment | Pending | RDS, ECR, secrets, observability |

---

## API Reference

Base path: `/api/v1`

### Auth

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/auth/register` | Create account (email, password, display_name?) → JWT token |
| `POST` | `/auth/login` | Authenticate (email, password) → JWT token |
| `GET` | `/auth/me` | Current user profile (requires JWT bearer) |

### Chat (HTTP + SSE)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/conversations` | Create a conversation |
| `GET` | `/conversations` | List user's conversations (ordered by updated_at DESC) |
| `GET` | `/conversations/{id}/messages` | List messages in order (ASC) |
| `DELETE` | `/conversations/{id}` | Delete conversation + all messages (cascade) |
| `POST` | `/conversations/{id}/messages/stream` | Send message, receive SSE stream |

### Voice (WebSocket)

| Protocol | Path | Purpose |
|----------|------|---------|
| `WS` | `/voice/ws/{conversation_id}` | Full-duplex voice chat (auth via Bearer header or query param) |

**WebSocket client → server events:**

| Event Type | Payload | Description |
|------------|---------|-------------|
| `auth` | `{ "token": "<jwt>" }` | Authenticate the WebSocket session |
| `input_audio.append` | `{ "audio": "<base64 PCM>" }` | Stream audio chunk to server |
| `input_audio.commit` | `{}` | Finalize audio for legacy STT mode |

**WebSocket server → client events:**

| Event Type | Payload | Description |
|------------|---------|-------------|
| `session.ready` | `{ "provider": "gemini_live"\|"legacy", ... }` | Session initialized |
| `user.transcript` | `{ "text": "..." }` | Transcribed user speech |
| `assistant.text.delta` | `{ "text": "..." }` | Streaming assistant text fragment |
| `assistant.text.done` | `{ "text": "..." }` | Full assistant text |
| `output_audio.chunk` | `{ "audio": "<base64>" }` | TTS audio chunk |
| `output_audio.done` | `{}` | Audio stream complete |
| `turn.done` | `{}` | Full turn complete, ready for next input |
| `error` | `{ "code": "...", "message": "..." }` | Error event |

### Infrastructure

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Health check |
| `GET` | `/ready` | Readiness probe (includes DB check) |

### SSE Stream Events (Text Chat)

```
event: meta    → { "conversation_id", "user_message_id" }
event: token   → { "text": "<fragment>" }         (repeat, word-by-word)
event: done    → { "assistant_text": "<full>" }
event: error   → { "code", "message" }            (on failure)
```

### Authentication

Two auth mechanisms are available:

- **JWT (user auth):** Register via `/auth/register` or log in via `/auth/login` to get a JWT. Pass as `Authorization: Bearer <token>`.
- **API key (service auth):** If `API_KEY` env var is set, chat routes also accept `Authorization: Bearer <key>` or `X-API-Key: <key>`.
- **WebSocket auth:** Send `auth` event with JWT after connecting, or pass token as query param.

Health/ready endpoints are always open.

---

## Database Schema

```
users
├── id (UUID, PK)
├── email (varchar 320, unique, indexed)
├── password_hash (varchar 128)
├── display_name (varchar 256, nullable)
└── created_at (timestamptz)

conversations
├── id (UUID, PK)
├── user_id (UUID, FK → users)
├── title (varchar 512)
├── created_at (timestamptz)
└── updated_at (timestamptz)

messages
├── id (UUID, PK)
├── conversation_id (UUID, FK → conversations, CASCADE)
├── role ("user" | "assistant")
├── content (text)
└── created_at (timestamptz)

embedding_chunks
├── id (UUID, PK)
├── conversation_id (UUID, FK → conversations, nullable)
├── user_id (UUID, FK → users, nullable)
├── source_uri (varchar 2048)
├── source (varchar — "cbt_pdf", "journal", etc.)
├── content (text)
├── embedding (vector 768)            ← Gemini embeddings, 768 dimensions
├── extra_metadata (jsonb)
└── created_at (timestamptz)
```

---

## Data Flows

### Text Chat (SSE)

```
Frontend (chat_view.tsx)
  │  POST /conversations/{id}/messages/stream  { "message": "..." }
  ▼
Backend (chat.py:stream_message_turn)
  → Persist user message to DB
  → Load conversation_history (last 10 turns)
  → Create assistant message placeholder
  ▼
run_turn() (chat_turn.py)
  → No GEMINI_API_KEY? → return stub response
  → Otherwise: run_turn_full()
    → grief_coach_graph.ainvoke(initial_state)
      → Historian: embed message → parallel pgvector search → build briefing
      → Specialist: generate therapy response using briefing + history
      → Anchor: validate safety, strip prosody hint
    → Return (cleaned_text, prosody_hint)
  ▼
SSE streaming
  → "meta" event: conversation_id + user_message_id
  → "token" events: response streamed word-by-word
  → "done" event: full text, assistant message persisted to DB
```

### Voice Chat — Gemini Live Mode

```
Frontend (use_voice_chat.ts)
  │  WebSocket /voice/ws/{conversation_id}
  │  Send "auth" event with JWT
  ▼
Server opens Gemini Live bidirectional bridge
  → Send "session.ready" { provider: "gemini_live" }
  ▼
Client starts microphone (ScriptProcessor, 16kHz PCM)
  │  Continuous "input_audio.append" events (base64 PCM chunks)
  ▼
Gemini Live processes in real-time:
  → "user.transcript": what Gemini heard
  → "assistant.text.delta": streaming response text
  → "output_audio.chunk": synthesized audio (PCM)
  ▼
Client
  → Plays audio chunks in real-time (50ms lookahead buffer)
  → Reveals text synchronized with audio playback
  → "turn.done": persist turn to DB, restart listening
```

### Voice Chat — Legacy Mode (ElevenLabs Fallback)

```
Client captures audio (MediaRecorder, WebM/MP4)
  │  Silence detection: FFT 256-bin, 8dB threshold, 1.4s duration
  │  "input_audio.commit" on silence
  ▼
Server: ElevenLabs STT → transcript
  → "user.transcript" to client
  ▼
run_turn_full(transcript, history) → (text, prosody)
  → "assistant.text.delta" events (word-by-word)
  → ElevenLabs TTS → "output_audio.chunk" events (base64)
  → "output_audio.done", then "turn.done"
```

### CBT Ingestion Pipeline

```
main_ingest.py
  → Load PDF (backend/data/cbt.pdf)
  → Chunk text (1500 chars, 200 overlap)
  → Embed via Gemini Embeddings API (768-dim vectors)
  → Auto-tag chunks by CBT concept
  → Write to embedding_chunks table (pgvector)
```

### Vector Retrieval (used by Historian)

```
User message → Embed once (Gemini)
  ▼
Parallel pgvector queries:
  ├── Journal entries (source="journal", cosine distance)
  └── CBT PDF chunks (source="cbt_pdf", cosine distance)
  ▼
Score = 1 - cosine_distance (1.0 = perfect match)
  → Top-k results returned with content + score + metadata
  → Fed into Historian's briefing for Specialist
```

---

## Stub Mode & Fallback Behavior

| Component | Without API Key | Timeout Fallback |
|-----------|----------------|-----------------|
| **Agent pipeline** | Returns `"[stub assistant] Thanks for sharing. You said: {preview}"` | — |
| **Historian LLM** | Skipped (stub) | 30s → empty briefing |
| **Specialist LLM** | Skipped (stub) | 30s → generic fallback |
| **Anchor LLM** | Skipped (stub) | 30s → pass-through Specialist response |
| **Embeddings** | Skipped | Failure → empty results, no crash |
| **Voice STT/TTS** | Stub services (no audio) | — |
| **Chat stream** | — | 60s overall timeout → abort + error event |

---

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local dev without Docker)
- Node.js 18+ (for frontend)

### Quick Start

```bash
# Clone the repo
git clone git@github.com:abdussamadbello/emosync.git
cd emosync

# Copy env and start
cp .env.example .env
make up

# Verify
curl http://localhost:8000/api/v1/health
# → {"status":"ok"}
```

### Local Development (without Docker for the app)

```bash
# Start DB only
make db

# Backend
cd backend
uv sync
uv run python -m alembic upgrade head
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### Run Tests

```bash
# No API keys required — full stub mode
make test        # or: cd backend && uv run python -m pytest -q
make test-v      # verbose
```

---

## Project Structure

```
emosync/
├── docs/
│   ├── PROJECT.md                  ← You are here
│   └── VOICE_FRONTEND_INTEGRATION.md
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app, middleware, exception handlers
│   │   ├── api/v1/                 # Routes: health.py, auth.py, chat.py, voice.py
│   │   ├── api/deps.py             # Dependency injection (JWT auth, API key)
│   │   ├── core/                   # Config, database engine, security (JWT/bcrypt)
│   │   ├── models/                 # ORM: user, conversation, message, embedding_chunk
│   │   ├── schemas/                # Pydantic: auth.py, chat.py, voice.py
│   │   ├── services/
│   │   │   ├── chat_turn.py        # run_turn() — agent integration boundary (SSE)
│   │   │   ├── stt/                # STTService ABC + ElevenLabs impl + stub
│   │   │   ├── tts/                # TTSService ABC + ElevenLabs streaming impl + stub
│   │   │   └── realtime/           # VoiceOrchestrator + Gemini Live bridge
│   │   ├── agent/
│   │   │   ├── graph.py            # LangGraph grief-coach graph
│   │   │   ├── state.py            # AgentState TypedDict
│   │   │   ├── llm.py              # Shared LLM client configuration
│   │   │   ├── prompts.py          # System prompts for each node
│   │   │   └── nodes/              # historian.py, specialist.py, anchor.py
│   │   ├── ingestion/
│   │   │   ├── main_ingest.py      # CLI entry point for CBT PDF ingestion
│   │   │   ├── chunker.py          # Text chunking (1500 chars, 200 overlap)
│   │   │   ├── embedder.py         # Gemini embedding generation (768-dim)
│   │   │   ├── tagger.py           # Auto-tag by CBT concept
│   │   │   ├── writer.py           # Persist to pgvector
│   │   │   └── vector_retriever.py # Query pgvector, fetch context chunks
│   │   └── mcp/
│   │       ├── calendar/            # CalendarEvent schema, repo, service, mock data
│   │       └── journal/             # JournalEntry schema, repo, retriever, service
│   ├── alembic/                     # Database migrations (PostgreSQL + pgvector)
│   ├── tests/                       # pytest — 14 test files, full stub mode
│   ├── pyproject.toml               # Python dependencies (uv)
│   ├── uv.lock                      # Locked dependencies
│   └── Dockerfile                   # Multi-stage Python 3.11 image
├── frontend/
│   ├── app/                         # Next.js 15 App Router pages
│   │   ├── layout.tsx               # Root layout + theme provider + sidebar
│   │   ├── page.tsx                 # Landing page
│   │   ├── auth/                    # Login + register pages
│   │   └── c/[id]/page.tsx          # Chat conversation view (dynamic route)
│   ├── components/
│   │   ├── chat_view.tsx            # Message display + SSE text streaming
│   │   ├── sidebar.tsx              # Conversation list, new chat
│   │   └── voice_panel.tsx          # Voice controls + audio visualisation
│   ├── hooks/
│   │   ├── use_voice_chat.ts        # WebSocket voice orchestration hook
│   │   └── use-audio-recorder.ts    # Browser MediaRecorder API wrapper
│   └── lib/
│       ├── api.ts                   # HTTP client for /api/v1/* endpoints
│       └── sse.ts                   # EventSource SSE handler
├── docker-compose.yml               # Postgres (pgvector:pg16) + API
├── Makefile                         # Dev shortcuts (up, db, dev, test, lint, etc.)
└── README.md
```

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **SSE for text, WebSocket for voice** | SSE is simpler for one-way streaming; WebSocket enables full-duplex real-time audio. |
| **3-node agent pipeline** | Separates context gathering (Historian), therapy generation (Specialist), and safety validation (Anchor). Each can fail independently with graceful fallbacks. |
| **Word-by-word SSE streaming** | Better UX than waiting for full response; tokens appear as they're generated. |
| **Gemini Live as primary voice** | Real-time bidirectional audio with built-in TTS; ElevenLabs as fallback for environments without Gemini. |
| **pgvector cosine distance** | In-database similarity search — no Python roundtrip needed; scales to large embedding stores. |
| **Prosody hints in response text** | TTS can vary tone (slow, warm, measured) based on content without a separate emotion analysis step. |
| **Lazy conversation creation** | Only create backend conversation on first message — prevents empty conversations cluttering the sidebar. |
| **replaceState over router.push** | Prevents Next.js remount during SSE stream; keeps connection alive. |
| **Stub mode for all services** | Tests and local dev work with zero API keys — deterministic behavior everywhere. |

---

## Key Integration Points

**For Frontend devs:** The chat API is stable. Use `fetch()` with POST body for SSE streaming. CORS is configured for `localhost:3000`. Auth flow: call `/auth/register` or `/auth/login`, store the JWT in localStorage (`emosync_token`), pass as `Authorization: Bearer <token>`. Voice: connect WebSocket to `/voice/ws/{id}`, send `auth` event, then stream audio.

**For Agent engineers:** The LangGraph pipeline is wired behind `run_turn()` in `backend/app/services/chat_turn.py`. Set `GEMINI_API_KEY` to activate it. To modify agent behavior, edit prompts in `backend/app/agent/prompts.py` or node logic in `backend/app/agent/nodes/`. Each node has independent timeout + fallback behavior.

**For Data/MCP engineers:** The `embedding_chunks` table with pgvector is populated by the ingestion pipeline (`backend/app/ingestion/main_ingest.py`). The Historian queries it via `VectorRetriever`. Journal and Calendar MCP servers are in `backend/app/mcp/` with mock data — replace with real integrations as needed.
