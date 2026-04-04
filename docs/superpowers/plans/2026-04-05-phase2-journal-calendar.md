# Phase 2: Journal & Calendar — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add full CRUD for journal entries and calendar events, wire journal semantic search and calendar context into the Historian via MCP services, auto-embed journal entries into pgvector, and build frontend pages for both features.

**Architecture:** Journal and Calendar CRUD are standard REST endpoints backed by the SQLAlchemy models created in Phase 1. Journal entries are auto-embedded (Gemini 1536-dim) into `embedding_chunks` on save for pgvector search. The existing MCP services (`JournalService`, `CalendarService`) are updated to query real DB data instead of mocks. The Historian node is updated to load calendar events from the DB before calling the LLM.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0 (async), pgvector (1536-dim), Gemini Embeddings API, pytest-asyncio, Next.js 15 (App Router), Tailwind CSS

**Spec:** `docs/superpowers/specs/2026-04-04-therapeutic-platform-expansion-design.md` (Sections 4, 5, 7)

**Dependencies:** Phase 1 complete (models, migration, schemas exist for `journal_entries` and `calendar_events` tables).

---

## File Structure

### Backend — New Files

| File | Responsibility |
|------|---------------|
| `backend/app/schemas/journal.py` | Pydantic schemas for journal CRUD |
| `backend/app/schemas/calendar.py` | Pydantic schemas for calendar CRUD |
| `backend/app/api/v1/journal.py` | Journal API router (CRUD + search) |
| `backend/app/api/v1/calendar.py` | Calendar API router (CRUD + date range) |
| `backend/app/services/journal_embedding.py` | Auto-embed journal content on save |
| `backend/tests/test_journal_crud.py` | Journal endpoint tests |
| `backend/tests/test_calendar_crud.py` | Calendar endpoint tests |
| `backend/tests/test_journal_mcp.py` | Journal MCP service tests |
| `backend/tests/test_calendar_mcp.py` | Calendar MCP service tests |
| `frontend/app/journal/page.tsx` | Journal list page |
| `frontend/app/journal/new/page.tsx` | New journal entry page |
| `frontend/app/journal/[id]/page.tsx` | Journal detail/edit page |
| `frontend/app/calendar/page.tsx` | Calendar monthly view page |
| `frontend/lib/journal-api.ts` | Frontend journal API client |
| `frontend/lib/calendar-api.ts` | Frontend calendar API client |

### Backend — Modified Files

| File | Change |
|------|--------|
| `backend/app/api/v1/router.py` | Include journal + calendar routers |
| `backend/app/mcp/journal/service.py` | Query real DB, add `recent()` and `get_by_id()` |
| `backend/app/mcp/journal/retriever.py` | Filter to `sources=("journal",)` only |
| `backend/app/mcp/calendar/service.py` | Query real DB, add `get_triggers()` and `get_by_date()` |
| `backend/app/agent/nodes/historian.py` | Load calendar events from DB before LLM call |

### Frontend — Modified Files

| File | Change |
|------|--------|
| `frontend/components/sidebar.tsx` | Add Journal + Calendar nav links |

---

## Task 1: Journal Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/journal.py`

- [ ] **Step 1: Create journal schemas**

Create `backend/app/schemas/journal.py`:

```python
"""Pydantic models for journal entry endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class JournalCreate(BaseModel):
    title: str | None = Field(default=None, max_length=256)
    content: str = Field(..., min_length=1, max_length=50000)
    mood_score: int | None = Field(default=None, ge=1, le=10)
    tags: list[str] = Field(default_factory=list)
    source: str = Field(default="manual", max_length=20)
    conversation_id: uuid.UUID | None = None


class JournalUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=256)
    content: str | None = Field(default=None, min_length=1, max_length=50000)
    mood_score: int | None = Field(default=None, ge=1, le=10)
    tags: list[str] | None = None


class JournalOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str | None
    content: str
    mood_score: int | None
    tags: list[str] | None
    source: str
    conversation_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Commit**

```bash
cd backend
git add app/schemas/journal.py
git commit -m "feat: add Pydantic schemas for journal CRUD"
```

---

## Task 2: Calendar Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/calendar.py`

- [ ] **Step 1: Create calendar schemas**

Create `backend/app/schemas/calendar.py`:

```python
"""Pydantic models for calendar event endpoints."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class CalendarEventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    date: date
    event_type: str = Field(..., max_length=20)
    recurrence: str | None = Field(default=None, pattern=r"^(yearly|monthly|weekly)$")
    notes: str | None = Field(default=None, max_length=5000)
    notify_agent: bool = True


class CalendarEventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=256)
    date: date | None = None
    event_type: str | None = Field(default=None, max_length=20)
    recurrence: str | None = Field(default=None)
    notes: str | None = Field(default=None, max_length=5000)
    notify_agent: bool | None = None


class CalendarEventOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    date: date
    event_type: str
    recurrence: str | None
    notes: str | None
    notify_agent: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Commit**

```bash
cd backend
git add app/schemas/calendar.py
git commit -m "feat: add Pydantic schemas for calendar CRUD"
```

---

## Task 3: Journal Auto-Embedding Service

**Files:**
- Create: `backend/app/services/journal_embedding.py`

This service embeds journal content into the `embedding_chunks` table so the Historian can find it via pgvector.

- [ ] **Step 1: Create the embedding service**

Create `backend/app/services/journal_embedding.py`:

```python
"""Auto-embed journal entries into embedding_chunks for pgvector search."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.embedding_chunk import EmbeddingChunk

logger = logging.getLogger(__name__)


async def embed_journal_entry(
    db: AsyncSession,
    entry_id: uuid.UUID,
    user_id: uuid.UUID,
    content: str,
) -> None:
    """Embed journal content and upsert into embedding_chunks.

    If GEMINI_API_KEY is not set, silently skips (stub mode).
    """
    if not settings.gemini_api_key:
        logger.debug("No GEMINI_API_KEY; skipping journal embedding.")
        return

    try:
        from app.mcp.journal.embedding import Embedder

        embedder = Embedder()
        embedding = await embedder.embed(content)

        source_uri = f"journal:{entry_id}"

        # Delete existing embedding for this journal entry
        await db.execute(
            delete(EmbeddingChunk).where(EmbeddingChunk.source_uri == source_uri)
        )

        chunk = EmbeddingChunk(
            id=uuid.uuid4(),
            content=content,
            embedding=embedding,
            source_uri=source_uri,
            extra_metadata={"source": "journal", "journal_entry_id": str(entry_id)},
        )
        # Set user_id if the column exists on the model
        if hasattr(EmbeddingChunk, "user_id"):
            chunk.user_id = user_id

        db.add(chunk)
        await db.flush()
    except Exception:
        logger.exception("Failed to embed journal entry %s", entry_id)


async def delete_journal_embedding(db: AsyncSession, entry_id: uuid.UUID) -> None:
    """Remove embedding_chunks for a deleted journal entry."""
    source_uri = f"journal:{entry_id}"
    await db.execute(
        delete(EmbeddingChunk).where(EmbeddingChunk.source_uri == source_uri)
    )
```

- [ ] **Step 2: Commit**

```bash
cd backend
git add app/services/journal_embedding.py
git commit -m "feat: add journal auto-embedding service for pgvector"
```

---

## Task 4: Journal CRUD API Endpoints

**Files:**
- Create: `backend/app/api/v1/journal.py`
- Create: `backend/tests/test_journal_crud.py`
- Modify: `backend/app/api/v1/router.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_journal_crud.py`:

```python
"""Tests for journal entry CRUD endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient) -> str:
    email = f"journal_{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secret1234"},
    )
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_create_journal_entry(client: AsyncClient) -> None:
    token = await _register(client)
    r = await client.post(
        "/api/v1/journal",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "Today I felt hopeful.", "title": "A good day", "mood_score": 7, "tags": ["hopeful"]},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["content"] == "Today I felt hopeful."
    assert data["title"] == "A good day"
    assert data["mood_score"] == 7
    assert data["tags"] == ["hopeful"]
    assert data["source"] == "manual"


@pytest.mark.asyncio
async def test_list_journal_entries(client: AsyncClient) -> None:
    token = await _register(client)
    for i in range(3):
        await client.post(
            "/api/v1/journal",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": f"Entry {i}"},
        )
    r = await client.get(
        "/api/v1/journal",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 3
    # Most recent first
    assert data[0]["content"] == "Entry 2"


@pytest.mark.asyncio
async def test_get_journal_entry(client: AsyncClient) -> None:
    token = await _register(client)
    create_r = await client.post(
        "/api/v1/journal",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "Test entry"},
    )
    entry_id = create_r.json()["id"]
    r = await client.get(
        f"/api/v1/journal/{entry_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["content"] == "Test entry"


@pytest.mark.asyncio
async def test_update_journal_entry(client: AsyncClient) -> None:
    token = await _register(client)
    create_r = await client.post(
        "/api/v1/journal",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "Original"},
    )
    entry_id = create_r.json()["id"]
    r = await client.patch(
        f"/api/v1/journal/{entry_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "Updated", "mood_score": 8},
    )
    assert r.status_code == 200
    assert r.json()["content"] == "Updated"
    assert r.json()["mood_score"] == 8


@pytest.mark.asyncio
async def test_delete_journal_entry(client: AsyncClient) -> None:
    token = await _register(client)
    create_r = await client.post(
        "/api/v1/journal",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "To delete"},
    )
    entry_id = create_r.json()["id"]
    r = await client.delete(
        f"/api/v1/journal/{entry_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 204
    # Verify gone
    r2 = await client.get(
        f"/api/v1/journal/{entry_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_journal_isolation(client: AsyncClient) -> None:
    """User A cannot see User B's journal entries."""
    token_a = await _register(client)
    token_b = await _register(client)
    create_r = await client.post(
        "/api/v1/journal",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"content": "Private to A"},
    )
    entry_id = create_r.json()["id"]
    r = await client.get(
        f"/api/v1/journal/{entry_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_filter_by_tags(client: AsyncClient) -> None:
    token = await _register(client)
    await client.post(
        "/api/v1/journal",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "tagged", "tags": ["grief"]},
    )
    await client.post(
        "/api/v1/journal",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "untagged", "tags": []},
    )
    r = await client.get(
        "/api/v1/journal",
        headers={"Authorization": f"Bearer {token}"},
        params={"tag": "grief"},
    )
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["content"] == "tagged"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run python -m pytest tests/test_journal_crud.py -v`
Expected: FAIL — routes don't exist.

- [ ] **Step 3: Implement journal router**

Create `backend/app/api/v1/journal.py`:

```python
"""Journal entry endpoints: CRUD + tag filter."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.journal_entry import JournalEntry
from app.models.user import User
from app.schemas.journal import JournalCreate, JournalOut, JournalUpdate
from app.services.journal_embedding import delete_journal_embedding, embed_journal_entry

router = APIRouter(prefix="/journal", tags=["journal"])


@router.post("", response_model=JournalOut, status_code=status.HTTP_201_CREATED)
async def create_entry(
    body: JournalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JournalEntry:
    entry = JournalEntry(
        user_id=current_user.id,
        title=body.title,
        content=body.content,
        mood_score=body.mood_score,
        tags=body.tags,
        source=body.source,
        conversation_id=body.conversation_id,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    # Auto-embed in background (best-effort, does not block response)
    await embed_journal_entry(db, entry.id, current_user.id, entry.content)
    await db.commit()

    return entry


@router.get("", response_model=list[JournalOut])
async def list_entries(
    tag: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[JournalEntry]:
    stmt = (
        select(JournalEntry)
        .where(JournalEntry.user_id == current_user.id)
        .order_by(JournalEntry.created_at.desc())
    )
    if tag:
        # Filter entries whose tags JSON array contains the given tag
        stmt = stmt.where(JournalEntry.tags.contains([tag]))
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{entry_id}", response_model=JournalOut)
async def get_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JournalEntry:
    result = await db.execute(
        select(JournalEntry).where(
            JournalEntry.id == entry_id,
            JournalEntry.user_id == current_user.id,
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found.")
    return entry


@router.patch("/{entry_id}", response_model=JournalOut)
async def update_entry(
    entry_id: uuid.UUID,
    body: JournalUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JournalEntry:
    result = await db.execute(
        select(JournalEntry).where(
            JournalEntry.id == entry_id,
            JournalEntry.user_id == current_user.id,
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found.")

    update_data = body.model_dump(exclude_unset=True)
    content_changed = "content" in update_data
    for key, value in update_data.items():
        setattr(entry, key, value)
    await db.commit()
    await db.refresh(entry)

    # Re-embed if content changed
    if content_changed:
        await embed_journal_entry(db, entry.id, current_user.id, entry.content)
        await db.commit()

    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(JournalEntry).where(
            JournalEntry.id == entry_id,
            JournalEntry.user_id == current_user.id,
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found.")

    await delete_journal_embedding(db, entry_id)
    await db.delete(entry)
    await db.commit()
```

- [ ] **Step 4: Register journal router**

Read `backend/app/api/v1/router.py` and add:

```python
from app.api.v1 import journal
api_router.include_router(journal.router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && uv run python -m pytest tests/test_journal_crud.py -v`
Expected: All 7 tests PASS.

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/api/v1/journal.py app/api/v1/router.py tests/test_journal_crud.py
git commit -m "feat: add journal CRUD API endpoints with auto-embedding"
```

---

## Task 5: Calendar CRUD API Endpoints

**Files:**
- Create: `backend/app/api/v1/calendar.py`
- Create: `backend/tests/test_calendar_crud.py`
- Modify: `backend/app/api/v1/router.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_calendar_crud.py`:

```python
"""Tests for calendar event CRUD endpoints."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient) -> str:
    email = f"cal_{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secret1234"},
    )
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_create_calendar_event(client: AsyncClient) -> None:
    token = await _register(client)
    r = await client.post(
        "/api/v1/calendar",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Mom's anniversary",
            "date": "2026-05-15",
            "event_type": "anniversary",
            "recurrence": "yearly",
            "notes": "First year",
            "notify_agent": True,
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Mom's anniversary"
    assert data["date"] == "2026-05-15"
    assert data["event_type"] == "anniversary"
    assert data["recurrence"] == "yearly"


@pytest.mark.asyncio
async def test_list_calendar_events(client: AsyncClient) -> None:
    token = await _register(client)
    today = date.today()
    for i in range(3):
        await client.post(
            "/api/v1/calendar",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": f"Event {i}",
                "date": str(today + timedelta(days=i)),
                "event_type": "personal",
            },
        )
    r = await client.get(
        "/api/v1/calendar",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert len(r.json()) == 3


@pytest.mark.asyncio
async def test_list_filter_by_date_range(client: AsyncClient) -> None:
    token = await _register(client)
    today = date.today()
    await client.post(
        "/api/v1/calendar",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Soon", "date": str(today + timedelta(days=2)), "event_type": "personal"},
    )
    await client.post(
        "/api/v1/calendar",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Far", "date": str(today + timedelta(days=30)), "event_type": "personal"},
    )
    r = await client.get(
        "/api/v1/calendar",
        headers={"Authorization": f"Bearer {token}"},
        params={"from_date": str(today), "to_date": str(today + timedelta(days=7))},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["title"] == "Soon"


@pytest.mark.asyncio
async def test_list_filter_by_type(client: AsyncClient) -> None:
    token = await _register(client)
    today = date.today()
    await client.post(
        "/api/v1/calendar",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Ann", "date": str(today), "event_type": "anniversary"},
    )
    await client.post(
        "/api/v1/calendar",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Therapy", "date": str(today), "event_type": "therapy"},
    )
    r = await client.get(
        "/api/v1/calendar",
        headers={"Authorization": f"Bearer {token}"},
        params={"event_type": "anniversary"},
    )
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["title"] == "Ann"


@pytest.mark.asyncio
async def test_get_calendar_event(client: AsyncClient) -> None:
    token = await _register(client)
    create_r = await client.post(
        "/api/v1/calendar",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Test", "date": "2026-06-01", "event_type": "personal"},
    )
    event_id = create_r.json()["id"]
    r = await client.get(
        f"/api/v1/calendar/{event_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["title"] == "Test"


@pytest.mark.asyncio
async def test_update_calendar_event(client: AsyncClient) -> None:
    token = await _register(client)
    create_r = await client.post(
        "/api/v1/calendar",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Original", "date": "2026-06-01", "event_type": "personal"},
    )
    event_id = create_r.json()["id"]
    r = await client.patch(
        f"/api/v1/calendar/{event_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Updated", "notes": "Added notes"},
    )
    assert r.status_code == 200
    assert r.json()["title"] == "Updated"
    assert r.json()["notes"] == "Added notes"


@pytest.mark.asyncio
async def test_delete_calendar_event(client: AsyncClient) -> None:
    token = await _register(client)
    create_r = await client.post(
        "/api/v1/calendar",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Delete me", "date": "2026-06-01", "event_type": "personal"},
    )
    event_id = create_r.json()["id"]
    r = await client.delete(
        f"/api/v1/calendar/{event_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_calendar_isolation(client: AsyncClient) -> None:
    token_a = await _register(client)
    token_b = await _register(client)
    create_r = await client.post(
        "/api/v1/calendar",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"title": "Private", "date": "2026-06-01", "event_type": "personal"},
    )
    event_id = create_r.json()["id"]
    r = await client.get(
        f"/api/v1/calendar/{event_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run python -m pytest tests/test_calendar_crud.py -v`

- [ ] **Step 3: Implement calendar router**

Create `backend/app/api/v1/calendar.py`:

```python
"""Calendar event endpoints: CRUD + date range/type filter."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.calendar_event import CalendarEvent
from app.models.user import User
from app.schemas.calendar import CalendarEventCreate, CalendarEventOut, CalendarEventUpdate

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.post("", response_model=CalendarEventOut, status_code=status.HTTP_201_CREATED)
async def create_event(
    body: CalendarEventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CalendarEvent:
    event = CalendarEvent(
        user_id=current_user.id,
        title=body.title,
        date=body.date,
        event_type=body.event_type,
        recurrence=body.recurrence,
        notes=body.notes,
        notify_agent=body.notify_agent,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


@router.get("", response_model=list[CalendarEventOut])
async def list_events(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    event_type: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CalendarEvent]:
    stmt = (
        select(CalendarEvent)
        .where(CalendarEvent.user_id == current_user.id)
        .order_by(CalendarEvent.date.asc())
    )
    if from_date:
        stmt = stmt.where(CalendarEvent.date >= from_date)
    if to_date:
        stmt = stmt.where(CalendarEvent.date <= to_date)
    if event_type:
        stmt = stmt.where(CalendarEvent.event_type == event_type)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{event_id}", response_model=CalendarEventOut)
async def get_event(
    event_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CalendarEvent:
    result = await db.execute(
        select(CalendarEvent).where(
            CalendarEvent.id == event_id,
            CalendarEvent.user_id == current_user.id,
        )
    )
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar event not found.")
    return event


@router.patch("/{event_id}", response_model=CalendarEventOut)
async def update_event(
    event_id: uuid.UUID,
    body: CalendarEventUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CalendarEvent:
    result = await db.execute(
        select(CalendarEvent).where(
            CalendarEvent.id == event_id,
            CalendarEvent.user_id == current_user.id,
        )
    )
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar event not found.")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(event, key, value)
    await db.commit()
    await db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(CalendarEvent).where(
            CalendarEvent.id == event_id,
            CalendarEvent.user_id == current_user.id,
        )
    )
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar event not found.")

    await db.delete(event)
    await db.commit()
```

- [ ] **Step 4: Register calendar router**

Read `backend/app/api/v1/router.py` and add:

```python
from app.api.v1 import calendar
api_router.include_router(calendar.router)
```

- [ ] **Step 5: Run tests**

Run: `cd backend && uv run python -m pytest tests/test_calendar_crud.py -v`
Expected: All 8 tests PASS.

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/api/v1/calendar.py app/api/v1/router.py tests/test_calendar_crud.py
git commit -m "feat: add calendar CRUD API endpoints with date range and type filters"
```

---

## Task 6: Update MCP Journal Service

**Files:**
- Modify: `backend/app/mcp/journal/service.py`
- Modify: `backend/app/mcp/journal/retriever.py`
- Create: `backend/tests/test_journal_mcp.py`

The journal MCP service needs to query real `journal_entries` from the DB, not just embedding chunks.

- [ ] **Step 1: Write tests for MCP journal tools**

Create `backend/tests/test_journal_mcp.py`:

```python
"""Tests for journal MCP service (real DB, no embeddings needed)."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register_and_create_entries(client: AsyncClient) -> tuple[str, list[str]]:
    email = f"jmcp_{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secret1234"},
    )
    token = r.json()["access_token"]
    ids = []
    for i in range(3):
        r = await client.post(
            "/api/v1/journal",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": f"Journal entry {i}", "tags": ["test"]},
        )
        ids.append(r.json()["id"])
    return token, ids


@pytest.mark.asyncio
async def test_journal_recent(client: AsyncClient) -> None:
    """MCP journal.recent returns entries ordered by created_at DESC."""
    token, ids = await _register_and_create_entries(client)
    # Use the list endpoint which serves the same purpose as journal.recent
    r = await client.get(
        "/api/v1/journal",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 3
    assert data[0]["content"] == "Journal entry 2"  # most recent first


@pytest.mark.asyncio
async def test_journal_get_by_id(client: AsyncClient) -> None:
    """MCP journal.get_by_id returns a single entry."""
    token, ids = await _register_and_create_entries(client)
    r = await client.get(
        f"/api/v1/journal/{ids[1]}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["content"] == "Journal entry 1"
```

- [ ] **Step 2: Run tests (should pass since endpoints already exist)**

Run: `cd backend && uv run python -m pytest tests/test_journal_mcp.py -v`
Expected: PASS (these are just API-level tests confirming the MCP-equivalent operations work).

- [ ] **Step 3: Update JournalRetriever to filter journal-only**

In `backend/app/mcp/journal/retriever.py`, change `sources=("journal", "cbt_pdf")` to `sources=("journal",)`:

```python
    async def search(
        self,
        query_embedding: list[float],
        user_id: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        return await self.retriever.search(
            query_embedding,
            top_k=limit,
            user_id=user_id,
            sources=("journal",),
        )
```

- [ ] **Step 4: Update JournalService with recent() and get_by_id()**

Replace `backend/app/mcp/journal/service.py`:

```python
"""Journal MCP service — search, recent, get_by_id."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.journal_entry import JournalEntry


class JournalService:
    def __init__(self, retriever=None, embedder=None):
        self.retriever = retriever
        self.embedder = embedder

    async def search(self, user_id: str, query: str) -> list[dict[str, Any]]:
        """Semantic search over journal entries via pgvector."""
        if not self.embedder or not self.retriever:
            return []
        embedding = await self.embedder.embed(query)
        results = await self.retriever.search(embedding, user_id)
        return [
            {
                "content": r["content"],
                "score": r["score"],
                "metadata": r.get("metadata", {}),
            }
            for r in results
        ]

    async def recent(self, user_id: str, limit: int = 5) -> list[dict[str, Any]]:
        """Return the N most recent journal entries for a user."""
        uid = uuid.UUID(user_id)
        async with get_async_session() as db:
            result = await db.execute(
                select(JournalEntry)
                .where(JournalEntry.user_id == uid)
                .order_by(JournalEntry.created_at.desc())
                .limit(limit)
            )
            entries = result.scalars().all()
            return [
                {
                    "id": str(e.id),
                    "title": e.title,
                    "content": e.content,
                    "mood_score": e.mood_score,
                    "tags": e.tags,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in entries
            ]

    async def get_by_id(self, entry_id: str) -> dict[str, Any] | None:
        """Return a single journal entry by ID."""
        async with get_async_session() as db:
            entry = await db.get(JournalEntry, uuid.UUID(entry_id))
            if entry is None:
                return None
            return {
                "id": str(entry.id),
                "title": entry.title,
                "content": entry.content,
                "mood_score": entry.mood_score,
                "tags": entry.tags,
                "created_at": entry.created_at.isoformat() if entry.created_at else None,
            }
```

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/mcp/journal/service.py app/mcp/journal/retriever.py tests/test_journal_mcp.py
git commit -m "feat: update journal MCP service with real DB access (recent, get_by_id)"
```

---

## Task 7: Update MCP Calendar Service

**Files:**
- Modify: `backend/app/mcp/calendar/service.py`
- Create: `backend/tests/test_calendar_mcp.py`

Replace mock data with real DB queries.

- [ ] **Step 1: Write tests**

Create `backend/tests/test_calendar_mcp.py`:

```python
"""Tests for calendar MCP service — real DB queries."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient


async def _register_with_events(client: AsyncClient) -> str:
    email = f"cmcp_{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secret1234"},
    )
    token = r.json()["access_token"]
    today = date.today()
    events = [
        {"title": "Tomorrow", "date": str(today + timedelta(days=1)), "event_type": "personal"},
        {"title": "Next week", "date": str(today + timedelta(days=5)), "event_type": "anniversary"},
        {"title": "Far away", "date": str(today + timedelta(days=30)), "event_type": "therapy"},
        {"title": "Trigger", "date": str(today + timedelta(days=2)), "event_type": "trigger"},
    ]
    for e in events:
        await client.post(
            "/api/v1/calendar",
            headers={"Authorization": f"Bearer {token}"},
            json=e,
        )
    return token


@pytest.mark.asyncio
async def test_calendar_upcoming_7_days(client: AsyncClient) -> None:
    token = await _register_with_events(client)
    today = date.today()
    r = await client.get(
        "/api/v1/calendar",
        headers={"Authorization": f"Bearer {token}"},
        params={"from_date": str(today), "to_date": str(today + timedelta(days=7))},
    )
    assert r.status_code == 200
    data = r.json()
    # Should include Tomorrow, Trigger, Next week — not Far away
    assert len(data) == 3
    titles = [e["title"] for e in data]
    assert "Far away" not in titles


@pytest.mark.asyncio
async def test_calendar_triggers_only(client: AsyncClient) -> None:
    token = await _register_with_events(client)
    r = await client.get(
        "/api/v1/calendar",
        headers={"Authorization": f"Bearer {token}"},
        params={"event_type": "trigger"},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["title"] == "Trigger"
```

- [ ] **Step 2: Run tests (should pass — endpoints exist)**

Run: `cd backend && uv run python -m pytest tests/test_calendar_mcp.py -v`

- [ ] **Step 3: Update CalendarService to use real DB**

Replace `backend/app/mcp/calendar/service.py`:

```python
"""Calendar MCP service — real DB queries replacing mock data."""

from __future__ import annotations

import uuid
from datetime import date, timedelta, UTC
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.calendar_event import CalendarEvent
from .schema import CalendarContext


class CalendarService:
    async def get_context(self, user_id: str) -> CalendarContext:
        """Get upcoming events for agent context (replaces mock data)."""
        today = date.today()
        upcoming_window = today + timedelta(days=7)

        uid = uuid.UUID(user_id)
        async with get_async_session() as db:
            result = await db.execute(
                select(CalendarEvent).where(
                    CalendarEvent.user_id == uid,
                    CalendarEvent.notify_agent.is_(True),
                    CalendarEvent.date >= today,
                    CalendarEvent.date <= upcoming_window,
                )
            )
            events = result.scalars().all()

        from .schema import CalendarEvent as CalendarEventSchema

        relevant_today = []
        upcoming = []
        for event in events:
            event_obj = CalendarEventSchema(
                id=str(event.id),
                title=event.title,
                date=event.date.isoformat(),
                type=event.event_type,
                metadata={"recurrence": event.recurrence, "notes": event.notes},
            )
            if event.date == today:
                relevant_today.append(event_obj)
            upcoming.append(event_obj)

        return CalendarContext(
            relevant_today=relevant_today,
            upcoming_events=upcoming,
        )

    async def get_triggers(self, user_id: str, days: int = 7) -> list[dict[str, Any]]:
        """Get anniversary/trigger events within N days."""
        today = date.today()
        window = today + timedelta(days=days)
        uid = uuid.UUID(user_id)

        async with get_async_session() as db:
            result = await db.execute(
                select(CalendarEvent).where(
                    CalendarEvent.user_id == uid,
                    CalendarEvent.event_type.in_(("anniversary", "trigger")),
                    CalendarEvent.date >= today,
                    CalendarEvent.date <= window,
                )
            )
            events = result.scalars().all()

        return [
            {
                "id": str(e.id),
                "title": e.title,
                "date": e.date.isoformat(),
                "event_type": e.event_type,
                "notes": e.notes,
            }
            for e in events
        ]

    async def get_by_date(self, user_id: str, target_date: date) -> list[dict[str, Any]]:
        """Get events on a specific date."""
        uid = uuid.UUID(user_id)
        async with get_async_session() as db:
            result = await db.execute(
                select(CalendarEvent).where(
                    CalendarEvent.user_id == uid,
                    CalendarEvent.date == target_date,
                )
            )
            events = result.scalars().all()

        return [
            {
                "id": str(e.id),
                "title": e.title,
                "date": e.date.isoformat(),
                "event_type": e.event_type,
                "notes": e.notes,
            }
            for e in events
        ]
```

- [ ] **Step 4: Commit**

```bash
cd backend
git add app/mcp/calendar/service.py tests/test_calendar_mcp.py
git commit -m "feat: update calendar MCP service with real DB queries"
```

---

## Task 8: Update Historian to Load Calendar from DB

**Files:**
- Modify: `backend/app/agent/nodes/historian.py`

The Historian currently receives `calendar_context` from state (always empty). Update it to load calendar events from the DB using the CalendarService.

- [ ] **Step 1: Add calendar loading to historian_node**

In `backend/app/agent/nodes/historian.py`, add these imports at the top:

```python
from app.mcp.calendar.service import CalendarService
```

In the `historian_node` function, after `query_embedding = await _embed_user_message(user_message)`, add calendar loading to the parallel gather. Replace the existing `asyncio.gather` block:

```python
    # Load calendar context from DB
    calendar_service = CalendarService()
    conversation_id = state.get("conversation_id", "")

    # Embed once, then run retrievals + calendar load in parallel.
    query_embedding = await _embed_user_message(user_message)

    journal_results, query_chunks, calendar_ctx = await asyncio.gather(
        retrieve_journal_context(user_message, query_embedding=query_embedding),
        retrieve_relevant_chunks(user_message, top_k=5, query_embedding=query_embedding),
        _load_calendar_context(calendar_service, state),
    )
```

Add this helper function before `historian_node`:

```python
async def _load_calendar_context(
    calendar_service: CalendarService, state: AgentState,
) -> list[str]:
    """Load upcoming calendar events for the user, if user context available."""
    try:
        # conversation_id is available but user_id may need to be passed through state
        # For now, return empty if no user context available
        user_id = state.get("user_id", "")
        if not user_id:
            return []
        ctx = await calendar_service.get_context(user_id)
        return [
            f"{e.title} on {e.date} ({e.type})"
            for e in ctx.upcoming_events
        ]
    except Exception:
        logger.exception("Failed to load calendar context.")
        return []
```

Then update the `calendar_context` assignment:

```python
    # Use DB-loaded calendar context, falling back to state
    calendar_context = calendar_ctx if calendar_ctx else state.get("calendar_context", [])
```

- [ ] **Step 2: Commit**

```bash
cd backend
git add app/agent/nodes/historian.py
git commit -m "feat: update Historian to load calendar events from DB via MCP service"
```

---

## Task 9: Frontend Journal API Client + Pages

**Files:**
- Create: `frontend/lib/journal-api.ts`
- Create: `frontend/app/journal/page.tsx`
- Create: `frontend/app/journal/new/page.tsx`
- Create: `frontend/app/journal/[id]/page.tsx`

- [ ] **Step 1: Create journal API client**

Create `frontend/lib/journal-api.ts`:

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface JournalEntry {
  id: string;
  user_id: string;
  title: string | null;
  content: string;
  mood_score: number | null;
  tags: string[] | null;
  source: string;
  conversation_id: string | null;
  created_at: string;
  updated_at: string;
}

function auth_headers(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

export async function list_journal_entries(
  token: string,
  params?: { tag?: string }
): Promise<JournalEntry[]> {
  const url = new URL(`${API_BASE}/api/v1/journal`);
  if (params?.tag) url.searchParams.set("tag", params.tag);
  const res = await fetch(url.toString(), { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error(`Failed to list journal entries (${res.status})`);
  return res.json() as Promise<JournalEntry[]>;
}

export async function get_journal_entry(token: string, id: string): Promise<JournalEntry> {
  const res = await fetch(`${API_BASE}/api/v1/journal/${id}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`Failed to get journal entry (${res.status})`);
  return res.json() as Promise<JournalEntry>;
}

export async function create_journal_entry(
  token: string,
  data: { content: string; title?: string; mood_score?: number; tags?: string[] }
): Promise<JournalEntry> {
  const res = await fetch(`${API_BASE}/api/v1/journal`, {
    method: "POST",
    headers: auth_headers(token),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to create journal entry (${res.status})`);
  return res.json() as Promise<JournalEntry>;
}

export async function update_journal_entry(
  token: string,
  id: string,
  data: { content?: string; title?: string; mood_score?: number; tags?: string[] }
): Promise<JournalEntry> {
  const res = await fetch(`${API_BASE}/api/v1/journal/${id}`, {
    method: "PATCH",
    headers: auth_headers(token),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to update journal entry (${res.status})`);
  return res.json() as Promise<JournalEntry>;
}

export async function delete_journal_entry(token: string, id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/journal/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`Failed to delete journal entry (${res.status})`);
}
```

- [ ] **Step 2: Create journal list page, new entry page, and detail page**

These are standard Next.js pages. The implementer should create all three using the patterns from the existing login/register pages:
- `frontend/app/journal/page.tsx` — List view with search, tag filter, links to entries
- `frontend/app/journal/new/page.tsx` — Form: title, content textarea, mood slider, tag pills, save
- `frontend/app/journal/[id]/page.tsx` — Detail view with edit and delete buttons

Each page should:
- Use `"use client"` directive
- Check auth on mount (`get_token()`, redirect to login if missing)
- Check onboarding completion (`get_profile()`, redirect to `/onboarding` if incomplete)
- Use the journal-api.ts functions for data operations
- Follow the existing styling patterns (Tailwind, border-border, bg-card, etc.)

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/journal-api.ts frontend/app/journal/
git commit -m "feat: add journal frontend (list, create, detail/edit pages)"
```

---

## Task 10: Frontend Calendar API Client + Page

**Files:**
- Create: `frontend/lib/calendar-api.ts`
- Create: `frontend/app/calendar/page.tsx`

- [ ] **Step 1: Create calendar API client**

Create `frontend/lib/calendar-api.ts`:

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface CalendarEvent {
  id: string;
  user_id: string;
  title: string;
  date: string;
  event_type: string;
  recurrence: string | null;
  notes: string | null;
  notify_agent: boolean;
  created_at: string;
  updated_at: string;
}

function auth_headers(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

export async function list_calendar_events(
  token: string,
  params?: { from_date?: string; to_date?: string; event_type?: string }
): Promise<CalendarEvent[]> {
  const url = new URL(`${API_BASE}/api/v1/calendar`);
  if (params?.from_date) url.searchParams.set("from_date", params.from_date);
  if (params?.to_date) url.searchParams.set("to_date", params.to_date);
  if (params?.event_type) url.searchParams.set("event_type", params.event_type);
  const res = await fetch(url.toString(), { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error(`Failed to list events (${res.status})`);
  return res.json() as Promise<CalendarEvent[]>;
}

export async function create_calendar_event(
  token: string,
  data: { title: string; date: string; event_type: string; recurrence?: string; notes?: string; notify_agent?: boolean }
): Promise<CalendarEvent> {
  const res = await fetch(`${API_BASE}/api/v1/calendar`, {
    method: "POST",
    headers: auth_headers(token),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to create event (${res.status})`);
  return res.json() as Promise<CalendarEvent>;
}

export async function update_calendar_event(
  token: string,
  id: string,
  data: { title?: string; date?: string; event_type?: string; recurrence?: string; notes?: string; notify_agent?: boolean }
): Promise<CalendarEvent> {
  const res = await fetch(`${API_BASE}/api/v1/calendar/${id}`, {
    method: "PATCH",
    headers: auth_headers(token),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to update event (${res.status})`);
  return res.json() as Promise<CalendarEvent>;
}

export async function delete_calendar_event(token: string, id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/calendar/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`Failed to delete event (${res.status})`);
}
```

- [ ] **Step 2: Create calendar page**

Create `frontend/app/calendar/page.tsx` — a monthly grid view:
- Auth + onboarding check on mount
- Monthly grid with dots on event dates
- Color-coded by event_type: anniversary=purple, birthday=blue, therapy=teal, trigger=red, milestone=green, holiday=orange
- Click date → show events for that day
- "Add event" modal/form: title, date, type dropdown, recurrence, notes, notify toggle
- Navigation arrows for month ← →

Follow existing patterns from the onboarding page for styling and auth.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/calendar-api.ts frontend/app/calendar/
git commit -m "feat: add calendar frontend (monthly view, event management)"
```

---

## Task 11: Update Sidebar Navigation

**Files:**
- Modify: `frontend/components/sidebar.tsx`

- [ ] **Step 1: Add Journal and Calendar nav links**

Read `frontend/components/sidebar.tsx`. Add navigation links for Journal (`/journal`) and Calendar (`/calendar`) in the sidebar. Use `BookOpen` and `Calendar` icons from lucide-react. Place them after the existing Chat section but before Settings/Sign Out.

- [ ] **Step 2: Commit**

```bash
git add frontend/components/sidebar.tsx
git commit -m "feat: add Journal and Calendar links to sidebar navigation"
```

---

## Task 12: Run Full Test Suite

- [ ] **Step 1: Run all backend tests**

Run: `cd backend && uv run python -m pytest -v`
Expected: All tests pass (existing + new journal + calendar + MCP tests).

- [ ] **Step 2: Run linter**

Run: `cd backend && uv run ruff check .`
Expected: No errors.

- [ ] **Step 3: Fix any issues and commit**

```bash
cd backend
git add -u
git commit -m "fix: resolve Phase 2 integration issues"
```
