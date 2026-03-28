# EmoSync

Privacy-first, hybrid AI coach for navigating grief and heartbreak (see project PRD).

## Docs

- **[execution.md](execution.md)** — milestones, roles, interfaces, Backend & DevOps checklist.

## Quick start (local API + Postgres)

1. Copy environment file:

   ```bash
   cp .env.example .env
   ```

2. Start Postgres and API:

   ```bash
   docker compose up --build
   ```

3. Check health:

   - [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
   - [http://localhost:8000/api/v1/ready](http://localhost:8000/api/v1/ready) (includes DB check)
   - OpenAPI: [http://localhost:8000/docs](http://localhost:8000/docs)

## API contract (M2 — stable for Frontend / Agent)

All routes are under `/api/v1`. JSON errors use `{ "code", "message", "request_id" }` (validation responses also include `details`).

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/conversations` | Create a conversation; returns `{ id, created_at }`. Optional body: `{ "title"?, "user_id"? }`. |
| `GET` | `/conversations/{id}/messages` | List messages in order (user/assistant turns). |
| `POST` | `/conversations/{id}/messages/stream` | Send user text; response is **SSE** (`text/event-stream`). |

**Auth (placeholder):** If `API_KEY` is set in the environment, chat routes require `Authorization: Bearer <API_KEY>` or `X-API-Key: <API_KEY>`. Health and readiness stay unauthenticated for probes. With no `API_KEY`, chat routes are open (local dev only).

**SSE events** (each event has a JSON `data` payload):

- `meta` — `{ "conversation_id", "user_message_id" }` (IDs are UUID strings).
- `token` — `{ "text": "<fragment>" }` (many events; concatenate for the assistant reply).
- `done` — `{ "assistant_text": "<full text>" }` (assistant message is also persisted).
- `error` — `{ "code", "message" }` on failure after streaming started.

**Frontend streaming:** use `fetch()` with the request body and read the response body as a stream (EventSource only supports GET). Disable proxy buffering for SSE in production (see `X-Accel-Buffering: no` header on the response).

**Agent integration:** replace the stub in `backend/app/services/chat_turn.py` (`run_turn`) with LangGraph; the HTTP layer should keep calling `run_turn` only.

## CI/CD

- **CI** (`.github/workflows/ci.yml`): Ruff, Alembic upgrade, pytest, Docker build (no push).
- **Container registry** (`.github/workflows/docker-publish.yml`): on push to `main` / `master`, build `backend/Dockerfile` and push to `ghcr.io/<org>/emosync-api` (`latest` + SHA tags). Point your host at that image or mirror it.

**Migrations:** the API image runs `alembic upgrade head` before `uvicorn` (see `backend/Dockerfile`). For one-off jobs, run the same against `DATABASE_URL_SYNC`.

## Backend development (without Docker for the app)

**Python 3.11+ is required** (same as `backend/Dockerfile` and CI). macOS’s default `python3` is often **3.9**; SQLAlchemy then fails resolving types like `uuid.UUID | None` (`unsupported operand type(s) for '|'` / `MappedAnnotationError`). Use 3.11 via [uv](https://docs.astral.sh/uv/) (recommended) or another install.

With Postgres running via Compose (`docker compose up db`):

```bash
cd backend
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
export DATABASE_URL=postgresql+asyncpg://emosync:emosync@localhost:5432/emosync
export DATABASE_URL_SYNC=postgresql://emosync:emosync@localhost:5432/emosync
python -m alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`backend/.python-version` pins **3.11** so `uv venv` picks the right interpreter (uv can download it if missing). Always invoke tools as `python -m alembic` / `python -m pytest` so you use the venv’s Python.

If you prefer plain `venv` instead of uv: `python3.11 -m venv .venv` (after installing 3.11), then `pip install -r requirements.txt` as before.

## Repository

`git@github.com:abdussamadbello/emosync.git`
