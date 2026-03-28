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

### 5.3 Suggested repo layout (illustrative)

```text
backend/
  app/
    main.py
    api/
    core/
    models/
    services/
  alembic/          # or chosen migration tool
  tests/
  Dockerfile
docker-compose.yml
.github/workflows/
```

### 5.4 Dependencies on other roles

- **Lead Agent:** Needs stable request/response/stream contract from your HTTP layer.
- **Multimodal:** Needs WebSocket URL scheme, auth, and message framing documented in OpenAPI or a short `docs/streaming.md`.
- **Frontend:** Needs CORS, cookie vs bearer auth decision, and deployed API base URL per environment.
- **MCP:** Historian may run in-process or sidecar; you document network boundaries (localhost vs internal Docker network) and env vars for MCP host/port.

### 5.5 Risks to track

- pgvector operator compatibility with your chosen Postgres image/version.
- Streaming timeouts behind reverse proxies (nginx, cloud load balancers).
- PII in logs — redact message bodies in production logs by policy.

---

## 6. Next actions (group)

1. Add this file to the repo root (or `docs/execution.md`) and link it from README.  
2. Schedule a 30-minute “contract” meeting: chat API + streaming + DB entities on a whiteboard.  
3. Open GitHub Issues per milestone with owners matching the table in §2.  
4. Backend track: open PR with Compose + empty FastAPI + migrations scaffold as M1.

---

## 7. Current scaffold (this repo)

- **M1 started:** `backend/` FastAPI app, Alembic + pgvector, `docker-compose.yml`, CI workflow.
- Local run: see [README.md](README.md).

---

*Last updated: 2026-03-28*
