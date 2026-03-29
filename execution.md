# EmoSync — Execution Plan

**Repository:** [git@github.com:abdussamadbello/emosync.git](https://github.com/abdussamadbello/emosync)  
**Purpose:** Turn the PRD into sequenced work, interfaces between roles, and concrete “done” criteria.

---

## 1. How we work

- **Vertical slice first:** One path end-to-end (text chat → backend → LLM stub → streamed reply) before polishing voice and full LangGraph.
- **Contracts over code:** Agree on API shapes (REST + WebSocket events), env vars, and DB tables early; stub implementations until integrations land.
- **Main branch stays runnable:** Docker Compose brings up API + Postgres; CI fails on lint/test/build regressions.
- **Security by default:** Secrets in env / secret manager only; no keys in repo; document what data leaves the device vs stays local (MCP / journals).

---

## 2. Roles, responsibilities, and deliverables

| Role | Primary focus | Key deliverables (repo artifacts) |
|------|----------------|-----------------------------------|
| **Lead Agent Engineer** | LangGraph orchestration, specialist nodes (CBT/ACT), prompts | `main.py` (or app entry), logic router, system prompts |
| **Multimodal Specialist** | STT/TTS, WebSockets, streaming sync | Whisper + ElevenLabs integration, audio buffer handling |
| **Backend & DevOps** | FastAPI, Postgres/pgvector, Docker, cloud | API gateway, database schema, migrations, CI/CD |
| **Frontend Architect** | Next.js App Router, voice orb, chat, state | App shell, visualizer, chat thread (note: Next.js typically uses `app/` or `page.tsx`, not `App.jsx` unless you standardize) |
| **MCP & Data Engineer** | MCP servers, local-first security | `mcp-calendar`, `mcp-journal`, semantic search over local markdown |

---

## 3. Milestones (suggested order)

1. **M0 — Repo & standards**  
   README, license, `.env.example`, branch strategy, code style (Python + TS), issue labels.

2. **M1 — Runnable backend + DB**  
   FastAPI app boots; health check; Postgres via Docker Compose; SQL migrations + pgvector extension; minimal schema (users/sessions/messages as needed).

3. **M2 — API gateway for chat**  
   REST (or SSE) endpoints for “send message / stream tokens”; auth placeholder (API key or session cookie); CORS for Next.js origin.

4. **M3 — Agent integration boundary**  
   Stable internal interface: `run_turn(user_id, conversation_id, payload) -> async stream`; Lead Agent plugs LangGraph behind this without rewriting HTTP layer.

5. **M4 — Multimodal path**  
   WebSocket (or dedicated routes) for audio chunks; STT → same internal `run_turn`; TTS stream back; Frontend consumes events.

6. **M5 — MCP in the loop**  
   Historian calls MCP tools; journal/calendar contracts documented; timeouts and failure modes defined.

7. **M6 — Production**  
   Deploy API + DB to chosen cloud; managed Postgres or container; secrets; observability (logs/metrics); backup policy.

---

## 4. Cross-role interfaces (agree once, change rarely)

- **HTTP:** Versioned paths (e.g. `/api/v1/...`); JSON errors with stable `code` + `message`.
- **Streaming:** Prefer SSE for text tokens unless bidirectional framing is required; WebSockets for audio duplex.
- **IDs:** UUIDs for `user_id`, `conversation_id`, `message_id`.
- **Webhooks / internal:** If async jobs appear later, document queue choice (or defer until M6).

---

## 5. Backend & DevOps — detailed execution (your track)

### 5.1 Scope

- FastAPI project layout (routers, services, settings, lifespan).
- PostgreSQL with **pgvector** for embeddings/RAG storage used by the product.
- **Dockerfile** for API + **docker-compose** for local API + Postgres (+ optional pgAdmin).
- **CI/CD:** lint + tests on PR; build image; deploy to staging/prod (GitHub Actions is a common default).

### 5.2 Deliverables checklist

| Deliverable | Definition of done |
|-------------|-------------------|
| **API gateway** | Routers mounted; middleware (CORS, request ID, error handler); `/health` and `/ready` (DB check); rate limiting or size limits documented |
| **Database schema** | Migrations checked in; extensions (`vector`) in migration; tables aligned with PRD (conversations, messages, embeddings metadata); indexes for hot paths |
| **Dockerization** | `docker compose up` starts stack; documented ports; non-root user in API image where practical |
| **CI/CD** | Pipeline on default branch + PRs; secrets via GitHub Environments; staging deploy automatic, prod manual or tagged |

### 5.3 Repo layout (current)

```text
backend/
  app/
    main.py               # FastAPI entry, middleware, exception handlers
    api/
      v1/
        health.py          # /health, /ready
        auth.py            # /auth/register, /auth/login, /auth/me
        chat.py            # /conversations, /messages, /messages/stream
        router.py          # Aggregates all v1 routers
      deps.py              # Dependency injection (API key, JWT auth)
    core/
      config.py            # Pydantic Settings from .env
      database.py          # SQLAlchemy async engine
      security.py          # bcrypt + JWT helpers
    models/                # SQLAlchemy ORM (user, conversation, message, embedding_chunk)
    schemas/               # Pydantic request/response models (auth, chat)
    services/
      chat_turn.py         # run_turn() — integration boundary for LangGraph
    agent/
      graph.py             # LangGraph grief-coach graph (Historian → Specialist → Anchor)
      state.py             # AgentState TypedDict
      prompts.py           # System prompts per node
      nodes/
        historian.py       # Context gathering (MCP stubs)
        specialist.py      # CBT/ACT/Narrative Therapy
        anchor.py          # Trauma-informed safety layer
  alembic/                 # Database migrations
  tests/                   # pytest (test_health, test_auth, test_chat, test_agent)
  Dockerfile
  requirements.txt
docker-compose.yml
.github/workflows/
  ci.yml                   # Ruff, Alembic, pytest, Docker build
  docker-publish.yml       # GHCR publish on push to main
```

### 5.4 Dependencies on other roles

- **Lead Agent:** ✅ Contract stable. LangGraph graph is wired behind `run_turn()` in `services/chat_turn.py`. HTTP/SSE layer unchanged.
- **Multimodal:** Needs WebSocket URL scheme, auth, and message framing documented in OpenAPI or a short `docs/streaming.md`.
- **Frontend:** CORS configured (`localhost:3000`). Auth is JWT bearer (`/auth/register` + `/auth/login`). Deployed API base URL per environment TBD.
- **MCP:** Historian node has stub MCP calls; wire real Calendar + Journal servers when M5 starts. Network boundaries (localhost vs internal Docker network) and env vars for MCP host/port still need documenting.

### 5.5 Risks to track

- pgvector operator compatibility with your chosen Postgres image/version.
- Streaming timeouts behind reverse proxies (nginx, cloud load balancers).
- PII in logs — redact message bodies in production logs by policy.

---

## 6. Next actions (group)

1. ~~Add this file to the repo root and link it from README.~~ **Done.**
2. ~~Backend track: Compose + FastAPI + migrations scaffold (M1).~~ **Done.**
3. ~~Chat API + SSE streaming + auth (M2/M2.5).~~ **Done.**
4. ~~Wire LangGraph agent pipeline behind `run_turn()` (M3).~~ **Done.**
5. Implement MCP Calendar + Journal servers and wire into Historian node (M5).
6. Add WebSocket routes for audio streaming; integrate Whisper STT + ElevenLabs TTS (M4).
7. Build Next.js frontend (Voice Orb UI, Chat Sidebar) consuming the `/api/v1` contract.
8. Deploy to cloud (managed Postgres, secrets, observability) and set up staging/prod environments (M6).

---

## 7. Current scaffold (this repo)

| Milestone | Status |
|-----------|--------|
| **M1** — Runnable backend + DB | **Done:** Compose + pgvector migration (`users`, `conversations`, `messages`, `embedding_chunks`), `/health`, `/ready`, CI. Second migration adds `email`, `password_hash`, `display_name` to users. |
| **M2** — API gateway for chat | **Done:** `POST/GET` conversations + messages, SSE stream for assistant tokens, stable JSON error shape. `GET /conversations` lists user conversations. |
| **M2.5** — User authentication | **Done:** JWT-based auth (`/auth/register`, `/auth/login`, `/auth/me`). bcrypt password hashing, `python-jose` JWT tokens, `email-validator` for input. Chat routes identify the current user via JWT. Optional `API_KEY` service auth still supported. |
| **M3** — Agent integration | **Done:** LangGraph grief-coach graph wired behind `run_turn()`. Three-node pipeline: Historian (context from MCP stubs) → Specialist (CBT/ACT/Narrative Therapy) → Anchor (trauma-informed safety). Activated by setting `GEMINI_API_KEY`; without it, a deterministic stub keeps CI and local dev working. |
| **M4** — Multimodal path | **Pending:** WebSocket / audio routes for STT (Whisper) and TTS (ElevenLabs). |
| **M5** — MCP in the loop | **Pending (stubs in place):** Historian node has placeholder MCP calls for Calendar + Journal servers. |
| **M6** — Production | **Partial:** GHCR publish on default branch; wire your host (Railway, Fly, Render, AWS, …) to pull `ghcr.io/<owner>/emosync-api` or trigger deploy. Staging URL + env still belong in your platform + GitHub Environments. |

Local run and HTTP details: [README.md](README.md).

---

*Last updated: 2026-03-29*
