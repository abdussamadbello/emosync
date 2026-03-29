# CLAUDE.md — EmoSync

## Project overview

EmoSync is a privacy-first, hybrid AI grief coach. Python 3.11 + FastAPI backend with PostgreSQL (pgvector), LangGraph agent pipeline (Historian → Specialist → Anchor), JWT auth, SSE streaming. No frontend yet (planned Next.js).

## Repository layout

```
backend/
  app/
    main.py                  # FastAPI app, middleware, exception handlers
    api/v1/                  # Routes: health.py, auth.py, chat.py
    api/deps.py              # Dependency injection (JWT auth, API key)
    core/config.py           # Pydantic Settings from .env
    core/database.py         # SQLAlchemy async engine + session
    core/security.py         # bcrypt passwords, JWT tokens
    models/                  # ORM: user, conversation, message, embedding_chunk
    schemas/                 # Pydantic: auth.py, chat.py
    services/chat_turn.py    # run_turn() — integration boundary for agent
    agent/
      graph.py               # LangGraph grief-coach graph
      state.py               # AgentState TypedDict
      prompts.py             # System prompts
      nodes/                 # historian.py, specialist.py, anchor.py
  alembic/                   # Migrations (PostgreSQL + pgvector)
  tests/                     # pytest (test_health, test_auth, test_chat, test_agent)
  Dockerfile
  requirements.txt
docker-compose.yml           # Postgres (pgvector:pg16) + API
.github/workflows/
  ci.yml                     # Ruff lint, Alembic, pytest, Docker build
  docker-publish.yml         # GHCR publish on push to main
```

## Development commands

```bash
# Start full stack
docker compose up --build

# Start DB only (for local dev)
docker compose up db

# Local Python dev (from backend/)
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
export DATABASE_URL=postgresql+asyncpg://emosync:emosync@localhost:5432/emosync
export DATABASE_URL_SYNC=postgresql://emosync:emosync@localhost:5432/emosync
python -m alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Lint
cd backend && ruff check app tests

# Test
cd backend && python -m pytest -q

# New migration
cd backend && python -m alembic revision --autogenerate -m "description"
```

## Key conventions

- **Python 3.11+** required (union types use `X | None` syntax)
- All routes under `/api/v1`; versioned prefix
- JSON errors: `{ "code", "message", "request_id" }` (+ `details` for validation)
- UUIDs for all entity IDs
- Async throughout: SQLAlchemy async, asyncpg, FastAPI async handlers
- Alembic migrations checked in under `backend/alembic/versions/`
- Use `python -m alembic` / `python -m pytest` (not bare commands) to use the venv
- SSE streaming for chat responses (not WebSocket for text)
- Agent pipeline activated by `GEMINI_API_KEY` env var; without it, a deterministic stub is used
- `run_turn()` in `services/chat_turn.py` is the single integration boundary — the HTTP layer calls only this function
- Passwords hashed with bcrypt; auth tokens are JWT (HS256)
- No secrets in repo; use `.env` locally, GitHub Environments in CI

## Environment variables

See `.env.example`. Key ones:
- `DATABASE_URL` / `DATABASE_URL_SYNC` — async and sync Postgres connection strings
- `GEMINI_API_KEY` — enables LangGraph agent (optional, stub without it)
- `JWT_SECRET` — JWT signing key (default is insecure, change in prod)
- `API_KEY` — optional service-level auth for chat routes
- `CORS_ORIGINS` — comma-separated allowed origins

## Seed data

Run `python -m scripts.seed_users` from the repo root (with `DATABASE_URL` set and migrations applied) to create demo users. Credentials are in `scripts/seed_users.py`.
