# EmoSync: Context-Aware Multimodal Grief Coach

## Project Overview

EmoSync is a privacy-first, hybrid AI coach for navigating grief and heartbreak. It integrates Voice and Text Chat with the Model Context Protocol (MCP) to ground conversations in the user's actual life events (Calendar) and reflections (Journals), applying CBT, ACT, and Narrative Therapy frameworks.

**Status:** Prototype (Backend scaffold complete, agent + frontend integration in progress)

---

## Core Features

| Feature | Description |
|---------|-------------|
| **Hybrid Interface** | Seamlessly switch between real-time voice and traditional text chat. |
| **Voice-First Empathy** | Low-latency STT/TTS with "prosody-aware" system prompts for soothing output. |
| **MCP Calendar Server** | Identifies anniversaries, holidays, and significant dates to provide context-aware support. |
| **MCP Journal Server** | Semantic search over private local Markdown/Text files to find evidence for CBT reframing. |
| **Agentic Reasoning** | LangGraph-powered multi-agent pipeline (Historian, Specialist, Anchor) for therapy-informed responses. |

---

## Architecture

### High-Level Flow

```
User Input (Voice or Text)
        │
        ▼
┌──────────────────┐
│  Voice → Whisper  │   (STT if voice input)
│  Text → Direct    │
└────────┬─────────┘
         ▼
┌──────────────────────────────────────┐
│         LangGraph Agentic Router     │
│                                      │
│  ┌────────────┐  ┌──────────────┐   │
│  │ Historian   │→ │ MCP Servers  │   │
│  │ (Context)   │  │ Calendar +   │   │
│  │             │  │ Journal      │   │
│  └─────┬──────┘  └──────────────┘   │
│        ▼                             │
│  ┌────────────┐                      │
│  │ Specialist  │  CBT/ACT protocols  │
│  │ (Therapy)   │  + MCP evidence     │
│  └─────┬──────┘                      │
│        ▼                             │
│  ┌────────────┐                      │
│  │ Anchor      │  Trauma-informed    │
│  │ (Safety)    │  validation layer   │
│  └─────┬──────┘                      │
└────────┼─────────────────────────────┘
         ▼
┌──────────────────┐
│  Text → Chat UI   │
│  Audio → TTS out   │   (ElevenLabs)
└──────────────────┘
```

### Agent Roles

| Agent | Purpose |
|-------|---------|
| **The Historian** | Pulls context from MCP servers — calendar dates, journal entries, past reflections. |
| **The Specialist** | Applies CBT/ACT protocols (e.g., Thought Records, cognitive defusion) using context as evidence. |
| **The Anchor** | Ensures all responses are validating, trauma-informed, and emotionally safe. |

---

## Technical Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 14, Tailwind CSS, Web Audio API, Lucide React |
| **Backend** | Python 3.11, FastAPI, LangGraph, LangChain |
| **AI/LLM** | Gemini 1.5 Pro (multimodal), Whisper (STT), ElevenLabs (TTS) |
| **Database** | PostgreSQL + pgvector (RAG / semantic search) |
| **MCP Storage** | Local filesystem (Markdown/Text journals, calendar data) |
| **Infrastructure** | Docker Compose (local), GitHub Actions (CI/CD), GHCR (container registry) |

---

## Current Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| FastAPI backend scaffold | Done | CORS, auth, error handling, request IDs |
| PostgreSQL + pgvector schema | Done | Users, conversations, messages, embedding_chunks |
| REST/SSE chat API | Done | `/api/v1/conversations`, streaming with SSE |
| Docker Compose stack | Done | Postgres + API, one-command startup |
| CI/CD pipelines | Done | Lint, test, build, publish to GHCR |
| Agent integration boundary | Done | `run_turn()` stub ready for LangGraph |
| LangGraph orchestration | Pending | Historian / Specialist / Anchor nodes |
| Voice pipeline (STT/TTS) | Pending | Whisper + ElevenLabs integration |
| MCP servers | Pending | Calendar + Journal tool contracts |
| Next.js frontend | Pending | Voice Orb UI, Chat Sidebar |
| Cloud deployment | Pending | RDS, ECR, secrets, observability |

---

## Team Roles & Deliverables

| Role | Primary Responsibilities | Key Deliverables |
|------|--------------------------|------------------|
| **Lead Agent Engineer** | LangGraph orchestration, specialist node logic (CBT/ACT), prompt engineering | `main.py` logic router, system prompts, agent nodes |
| **Multimodal Specialist** | Audio pipeline (STT/TTS), WebSockets, real-time streaming sync | Whisper/ElevenLabs integration, audio buffer |
| **Backend & DevOps** | FastAPI structure, PostgreSQL/pgvector, Dockerization, cloud deploy | API gateway, database schema, CI/CD |
| **Frontend Architect** | Next.js App Router, Voice Orb UI, Chat Sidebar, state management | App components, audio visualizer, chat thread |
| **MCP & Data Engineer** | MCP server implementation, calendar/journal contracts, semantic search | MCP tool definitions, pgvector queries, data pipeline |

---

## API Reference (Stable)

Base path: `/api/v1`

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/conversations` | Create a conversation |
| `GET` | `/conversations/{id}/messages` | List messages in order |
| `POST` | `/conversations/{id}/messages/stream` | Send message, receive SSE stream |
| `GET` | `/health` | Health check |
| `GET` | `/ready` | Readiness probe (includes DB check) |

### SSE Stream Events

```
event: meta    → { "conversation_id", "user_message_id" }
event: token   → { "text": "<fragment>" }         (repeat)
event: done    → { "assistant_text": "<full>" }
event: error   → { "code", "message" }            (on failure)
```

### Auth

When `API_KEY` env var is set, chat routes require `Authorization: Bearer <key>` or `X-API-Key: <key>`. Health/ready endpoints are always open.

---

## Database Schema

```
users
├── id (UUID, PK)
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
├── conversation_id (UUID, FK → conversations)
├── source_uri (varchar 2048)
├── content (text)
├── embedding (vector 1536)
├── extra_metadata (jsonb)
└── created_at (timestamptz)
```

---

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local dev without Docker)

### Quick Start

```bash
# Clone the repo
git clone git@github.com:abdussamadbello/emosync.git
cd emosync

# Copy env and start
cp .env.example .env
docker compose up --build

# Verify
curl http://localhost:8000/api/v1/health
# → {"status":"ok"}
```

### Local Development (without Docker for the app)

```bash
# Start DB only
docker compose up db

# Set up Python env
cd backend
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt

# Configure
export DATABASE_URL=postgresql+asyncpg://emosync:emosync@localhost:5432/emosync
export DATABASE_URL_SYNC=postgresql://emosync:emosync@localhost:5432/emosync

# Run migrations and start
python -m alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Run Tests

```bash
cd backend
python -m pytest -q
```

---

## Project Structure

```
emosync/
├── docs/
│   └── PROJECT.md              ← You are here
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI application entry
│   │   ├── api/v1/             # Route handlers (health, chat)
│   │   ├── core/               # Config, database engine
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic request/response models
│   │   └── services/           # Business logic (chat_turn.py → LangGraph hook)
│   ├── alembic/                # Database migrations
│   ├── tests/                  # pytest test suite
│   ├── Dockerfile              # Multi-stage Python 3.11 image
│   └── requirements.txt        # Python dependencies
├── docker-compose.yml          # Local Postgres + API stack
├── execution.md                # Detailed milestone plan
└── README.md                   # Quick-start guide
```

---

## Key Integration Points

**For Frontend devs:** The chat API is stable. Use `fetch()` with POST body for SSE streaming. CORS is configured for `localhost:3000`.

**For Agent engineers:** Replace the stub in `backend/app/services/chat_turn.py` (`run_turn` function). The HTTP/SSE layer stays unchanged.

**For MCP engineers:** The `embedding_chunks` table with pgvector is ready for semantic search. Wire MCP tool outputs into the `extra_metadata` JSON column.
