.PHONY: help up down build db \
        migrate migrate-new migrate-down \
        install install-fe dev dev-fe dev-all \
        lint lint-fix lint-fe \
        test test-v test-agent \
        seed ingest

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Docker ────────────────────────────────────────────────────────────────────

up: ## Start full stack (Postgres + API)
	docker compose up --build

down: ## Stop all containers
	docker compose down

build: ## Build Docker images without starting
	docker compose build

db: ## Start only the database container
	docker compose up db

# ── Install ───────────────────────────────────────────────────────────────────

install: ## Create venv and install Python dependencies
	cd backend && uv sync

install-fe: ## Install frontend Node dependencies
	cd frontend && npm install

# ── Local dev ─────────────────────────────────────────────────────────────────

dev: ## Run FastAPI with hot reload on :8000 (requires DB + .env)
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-fe: ## Run Next.js dev server on :3000
	cd frontend && npm run dev

dev-all: ## Start backend + frontend together (no Docker; requires .env set)
	@set -e; \
	trap 'kill 0' INT TERM; \
	(cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000) & \
	(cd frontend && npm run dev) & \
	wait

# ── Database ──────────────────────────────────────────────────────────────────

migrate: ## Apply all pending Alembic migrations
	cd backend && uv run python -m alembic upgrade head

migrate-new: ## Generate a new migration (usage: make migrate-new MSG="description")
	cd backend && uv run python -m alembic revision --autogenerate -m "$(MSG)"

migrate-down: ## Downgrade one Alembic revision
	cd backend && uv run python -m alembic downgrade -1

# ── Quality ───────────────────────────────────────────────────────────────────

lint: ## Run Ruff linter on backend
	cd backend && uv run ruff check app tests

lint-fix: ## Run Ruff linter with auto-fix
	cd backend && uv run ruff check --fix app tests

lint-fe: ## Run ESLint on frontend
	cd frontend && npm run lint

# ── Tests ─────────────────────────────────────────────────────────────────────

test: ## Run full pytest suite (stub mode, no API keys required)
	cd backend && uv run python -m pytest -q

test-v: ## Run pytest with verbose output
	cd backend && uv run python -m pytest -v

test-agent: ## Run agent-specific tests only
	cd backend && uv run python -m pytest tests/test_agent.py tests/test_agent_errors.py tests/test_historian.py tests/test_historian_parsing.py -v

# ── Seed & Ingestion ──────────────────────────────────────────────────────────

seed: ## Seed demo users into the database
	cd backend && uv run python -m scripts.seed_users

ingest: ## Ingest a PDF document (usage: make ingest FILE=path/to/doc.pdf)
	cd backend && uv run python -m app.ingestion.main_ingest --file $(FILE)
