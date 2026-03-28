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

## Backend development (without Docker for the app)

With Postgres running via Compose (`docker compose up db`):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+asyncpg://emosync:emosync@localhost:5432/emosync
export DATABASE_URL_SYNC=postgresql://emosync:emosync@localhost:5432/emosync
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Repository

`git@github.com:abdussamadbello/emosync.git`
