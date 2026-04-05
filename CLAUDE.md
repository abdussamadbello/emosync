# CLAUDE.md — EmoSync

## Project overview

EmoSync is a privacy-first, hybrid AI grief coach. Python 3.11 + FastAPI backend with PostgreSQL (pgvector), LangGraph agent pipeline (Historian → Specialist → Anchor), JWT auth, SSE streaming for text chat, and WebSocket-based real-time voice (STT → Agent → TTS). Next.js 15 frontend is live with auth, chat, and voice panel.

## Repository layout

```
backend/
  app/
    main.py                     # FastAPI app, middleware, exception handlers
    api/v1/                     # Routes: health.py, auth.py, chat.py, voice.py
    api/deps.py                 # Dependency injection (JWT auth, API key)
    core/config.py              # Pydantic Settings from .env
    core/database.py            # SQLAlchemy async engine + session
    core/security.py            # bcrypt passwords, JWT tokens
    core/vector_store.py        # LocalVectorStore (JSON-based, cosine similarity)
    models/                     # ORM: user, conversation, message, embedding_chunk
    schemas/                    # Pydantic: auth.py, chat.py, voice.py
    services/
      chat_turn.py              # run_turn() — agent integration boundary (SSE)
      audio/buffer.py           # AudioBuffer for WebSocket audio frames
      stt/                      # STTService ABC + ElevenLabs impl + stub
      tts/                      # TTSService ABC + ElevenLabs streaming impl + stub
      realtime/
        orchestrator.py         # VoiceOrchestrator: STT → Agent → TTS chain
        session.py              # Per-WebSocket session state
    agent/
      graph.py                  # LangGraph grief-coach graph
      state.py                  # AgentState TypedDict
      prompts.py                # System prompts for each node
      nodes/                    # historian.py, specialist.py, anchor.py
    ingestion/
      pipeline.py               # Load → Chunk → Embed → Store orchestration
      pdf_loader.py             # PDF text extraction
      chunker.py                # Text chunking (optional semantic split)
      embedder.py               # Gemini embedding generation
      tagger.py                 # Auto-tag documents by topic/intent
      writer.py                 # Persist to LocalVectorStore / pgvector
      vector_retriever.py       # Query vector store, fetch context chunks
      main_ingest.py            # CLI entry point
    mcp/
      calendar/                 # CalendarEvent schema, repository, service, mock data
      journal/                  # JournalEntry schema, repository, retriever, service, mock data
  alembic/                      # Migrations (PostgreSQL + pgvector)
  tests/                        # pytest — see Testing section below
  Dockerfile
  requirements.txt
frontend/
  app/                          # Next.js 15 App Router pages
    layout.tsx                  # Root layout + theme provider + sidebar
    page.tsx                    # Landing page
    auth/login/page.tsx         # Login form
    auth/register/page.tsx      # Registration form
    c/[id]/page.tsx             # Chat conversation view (dynamic route)
  components/
    chat_view.tsx               # Message display + SSE text streaming
    sidebar.tsx                 # Conversation list, new chat
    voice_panel.tsx             # Voice controls + audio visualisation
    ui/button.tsx               # Shadcn/ui Button
  hooks/
    use_voice_chat.ts           # WebSocket voice orchestration hook
    use-audio-recorder.ts       # Browser MediaRecorder API wrapper
  lib/
    api.ts                      # HTTP client for /api/v1/* endpoints
    sse.ts                      # EventSource SSE handler
    mock-audio-service.ts       # Stub audio for development
docker-compose.yml              # Postgres (pgvector:pg16) + API
Makefile                        # Dev shortcuts (see below)
.github/workflows/
  ci.yml                        # Ruff lint, Alembic, pytest, Docker build
  docker-publish.yml            # GHCR publish on push to main
```

## Development commands

```bash
# ── Docker ──────────────────────────────
make up              # Start full stack (Postgres + API)
make db              # Start only the database container
make down            # Stop all containers

# ── Local Python dev ─────────────────────
make install         # Create venv and install dependencies
make dev             # Run FastAPI with hot reload on :8000

# ── Database ─────────────────────────────
make migrate                    # Apply all Alembic migrations
make migrate-new MSG="desc"     # Generate a new migration
make migrate-down               # Downgrade one revision

# ── Quality ──────────────────────────────
make lint            # Ruff linter
make lint-fix        # Ruff with auto-fix
make test            # pytest (stub mode, no GEMINI_API_KEY required)
make test-v          # pytest verbose

# ── Seed ─────────────────────────────────
make seed            # Seed demo users into the database
```

Or run raw commands from `backend/`:

```bash
uv sync
uv run python -m alembic upgrade head
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Key conventions

- **Python 3.11+** required (union types use `X | None` syntax)
- All routes under `/api/v1`; versioned prefix
- JSON errors: `{ "code", "message", "request_id" }` (+ `details` for validation)
- UUIDs for all entity IDs
- Async throughout: SQLAlchemy async, asyncpg, FastAPI async handlers
- Alembic migrations checked in under `backend/alembic/versions/`
- Backend dependencies are defined in `backend/pyproject.toml` and locked in `backend/uv.lock`
- Prefer `uv run python -m alembic` / `uv run python -m pytest` so commands execute in the synced project environment
- **Text chat:** SSE streaming via `/api/v1/chat/conversations/{id}/turns`
- **Voice chat:** WebSocket at `/api/v1/voice/ws/{conversation_id}` — binary audio in, text+audio out
- Agent pipeline activated by `GEMINI_API_KEY` env var; without it, a deterministic stub is used
- `run_turn()` in `services/chat_turn.py` is the single text-chat integration boundary
- Voice pipeline: `VoiceOrchestrator.stream_transcript_turn()` chains STT → `run_turn()` → TTS
- Passwords hashed with bcrypt; auth tokens are JWT (HS256)
- No secrets in repo; use `.env` locally, GitHub Environments in CI

## Environment variables

See `.env.example`. Key ones:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Async Postgres connection string (`postgresql+asyncpg://...`) |
| `DATABASE_URL_SYNC` | Sync string for Alembic (`postgresql://...`) |
| `GEMINI_API_KEY` | Enables LangGraph agent (optional; stub without it) |
| `JWT_SECRET` | JWT signing key — **change in prod** |
| `API_KEY` | Optional service-level auth for chat routes |
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `ELEVENLABS_API_KEY` | Enables ElevenLabs STT + TTS (optional; stub without it) |
| `ELEVENLABS_VOICE_ID` | ElevenLabs voice to use for TTS output |
| `ELEVENLABS_MODEL_ID` | ElevenLabs TTS model (default: `eleven_turbo_v2_5`) |
| `VOICE_OUTPUT_FORMAT` | Audio format for TTS chunks (default: `mp3_22050_32`) |

## Testing

Tests live in `backend/tests/`. Run without any API keys (full stub mode):

| File | Coverage |
|---|---|
| `test_health.py` | Health probe |
| `test_auth.py` | Register, login, token refresh |
| `test_auth_ratelimit.py` | Auth rate limiting |
| `test_chat.py` | SSE streaming, conversation history |
| `test_agent.py` | Full agent pipeline (stub) |
| `test_agent_errors.py` | Agent error handling + fallbacks |
| `test_historian.py` | Historian MCP stub calls |
| `test_historian_parsing.py` | Historian JSON parsing edge cases |
| `test_ingestion.py` | PDF → chunk → embed pipeline |
| `test_vector_query.py` | LocalVectorStore cosine search |
| `test_mcp.py` | Calendar + Journal MCP mock calls |
| `test_voice_edges.py` | Voice WebSocket edge cases, auth, buffer overflow |
| `test_voice_orchestrator.py` | STT → Agent → TTS chain |

## Seed data

Run `python -m scripts.seed_users` from the repo root (with `DATABASE_URL` set and migrations applied) to create demo users. Credentials are in `scripts/seed_users.py`.
