# EmoSync Therapeutic Platform Expansion — Design Spec

**Date:** 2026-04-04
**Status:** Draft
**Scope:** Onboarding, Journal, Calendar, Treatment Plans, Assessments, Outcome Tracking, Dashboard

---

## 1. Overview

EmoSync currently operates as a chat-only grief coach — users send messages and receive AI-generated therapy-informed responses. This expansion transforms it into a **structured therapeutic platform** where the AI has persistent knowledge of the user's story, tracks measurable outcomes, and proactively coaches toward treatment goals.

### What changes

| Before | After |
|--------|-------|
| Cold start — AI knows nothing about the user | Onboarding collects grief context, preferences, baseline assessments |
| Chat only | Dashboard home + Journal + Calendar + Treatment Plan + Chat |
| Mock journal/calendar data | Real persistent data, user-created and AI-searchable |
| No outcome measurement | PHQ-9/GAD-7 screening, mood tracking, progress trends |
| Agent has no memory across sessions | Agent accesses profile, assessments, plans, moods via MCP tools |

### Build phases

1. **Phase 1 — Foundation & Onboarding:** New tables, onboarding wizard, route protection
2. **Phase 2 — Journal & Calendar:** CRUD endpoints + UI, auto-embedding, real MCP server integration
3. **Phase 3 — Treatment Plans & Outcomes:** Plan/goal CRUD, mood logging, periodic assessments, agent expansion
4. **Phase 4 — Dashboard & Polish:** Dashboard home, expanded sidebar, settings, score-aware escalation

---

## 2. Data Model

### 2.1 user_profiles

Extends the existing `users` table with a 1:1 profile for onboarding and preference data.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| user_id | UUID | FK → users, unique, not null | |
| grief_type | varchar | nullable | "loss", "breakup", "life_transition", "other" |
| grief_subject | text | nullable | Who/what they lost |
| grief_duration_months | int | nullable | How long ago |
| support_system | varchar | nullable | "strong", "some", "none" |
| prior_therapy | boolean | default false | |
| preferred_approaches | jsonb | default [] | e.g., ["cbt", "journaling", "mindfulness"] |
| onboarding_completed | boolean | default false | Gates access to main app |
| created_at | timestamptz | not null | |
| updated_at | timestamptz | not null | |

### 2.2 journal_entries

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| user_id | UUID | FK → users, not null | |
| title | varchar(256) | nullable | |
| content | text | not null | |
| mood_score | int | nullable, check 1-10 | Mood at time of writing |
| tags | jsonb | default [] | e.g., ["grief", "progress", "trigger"] |
| source | varchar | not null | "manual", "ai_suggested", "onboarding" |
| conversation_id | UUID | FK → conversations, nullable | If created from chat context |
| created_at | timestamptz | not null | |
| updated_at | timestamptz | not null | |

**On save:** Content is embedded via Gemini Embeddings API and written to `embedding_chunks` with `source="journal"` and `user_id` set, making it immediately searchable by the Historian.

### 2.3 calendar_events

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| user_id | UUID | FK → users, not null | |
| title | varchar(256) | not null | |
| date | date | not null | |
| event_type | varchar | not null | "anniversary", "birthday", "holiday", "therapy", "trigger", "milestone" |
| recurrence | varchar | nullable | "yearly", "monthly", "weekly", null |
| notes | text | nullable | |
| notify_agent | boolean | default true | Should the AI proactively mention this? |
| created_at | timestamptz | not null | |
| updated_at | timestamptz | not null | |

### 2.4 assessments

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| user_id | UUID | FK → users, not null | |
| instrument | varchar | not null | "phq9", "gad7", "pcl5" |
| responses | jsonb | not null | {"q1": 2, "q2": 1, ...} |
| total_score | int | not null | Computed from responses |
| severity | varchar | not null | "minimal", "mild", "moderate", "moderately_severe", "severe" |
| source | varchar | not null | "onboarding", "periodic", "ai_prompted" |
| created_at | timestamptz | not null | |

**Scoring rules:**
- PHQ-9 (0-27): minimal (0-4), mild (5-9), moderate (10-14), moderately severe (15-19), severe (20-27)
- GAD-7 (0-21): minimal (0-4), mild (5-9), moderate (10-14), severe (15-21)

### 2.5 treatment_plans

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| user_id | UUID | FK → users, not null | |
| title | varchar(256) | not null | |
| status | varchar | not null, default "active" | "active", "completed", "paused" |
| created_at | timestamptz | not null | |
| updated_at | timestamptz | not null | |

### 2.6 treatment_goals

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| plan_id | UUID | FK → treatment_plans, CASCADE | |
| description | text | not null | |
| target_date | date | nullable | |
| status | varchar | not null, default "not_started" | "not_started", "in_progress", "completed" |
| progress_notes | jsonb | default [] | [{"date": "...", "note": "..."}] |
| created_at | timestamptz | not null | |
| updated_at | timestamptz | not null | |

### 2.7 mood_logs

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| user_id | UUID | FK → users, not null | |
| score | int | not null, check 1-10 | |
| label | varchar | nullable | "anxious", "hopeful", "numb", "sad", "calm", etc. |
| notes | text | nullable | |
| source | varchar | not null | "check_in", "journal", "assessment", "onboarding" |
| created_at | timestamptz | not null | |

---

## 3. Onboarding Flow

### 3.1 Route protection

All app routes (`/`, `/c/[id]`, `/journal`, `/calendar`, `/plan`) redirect to `/onboarding` if `user_profiles.onboarding_completed = false`. The check runs on the frontend by querying `GET /api/v1/profile/me` after login.

### 3.2 Wizard steps

**Step 1 — Welcome & Context**
- grief_type: radio selector (Loss of someone, Breakup/divorce, Life transition, Other)
- grief_subject: optional free text ("Would you like to share more?")
- grief_duration_months: optional selector (Less than 1 month, 1-3, 3-6, 6-12, 1-2 years, 2+ years)

**Step 2 — Support & Preferences**
- support_system: radio (I have strong support, Some support, Not much support)
- prior_therapy: yes/no toggle
- preferred_approaches: multi-select checkboxes (Journaling, CBT exercises, Mindfulness, Just talking, Guided prompts)

**Step 3 — Baseline Assessments**
- PHQ-9: 9 questions, each with 4 radio options (Not at all=0, Several days=1, More than half the days=2, Nearly every day=3)
- GAD-7: 7 questions, same scale
- Questions presented in plain language, one section at a time
- Auto-scored on submission

**Step 4 — First Check-in & Summary**
- Mood score: 1-10 slider with emoji anchors
- Emotion label: optional tag selector (anxious, sad, numb, hopeful, calm, angry, other)
- Summary card: "Here's what I know about you" — shows grief type, support level, assessment scores
- "Start your first conversation" → sets `onboarding_completed = true`, redirects to `/`

### 3.3 API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/profile/me` | Get current user's profile (includes onboarding_completed) |
| PUT | `/api/v1/profile/me` | Update profile (used by each onboarding step) |
| POST | `/api/v1/assessments` | Submit assessment (PHQ-9 or GAD-7) |
| POST | `/api/v1/mood` | Log mood entry |
| POST | `/api/v1/profile/complete-onboarding` | Mark onboarding as done |

---

## 4. Journal

### 4.1 API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/journal` | Create journal entry |
| GET | `/api/v1/journal` | List entries (paginated, filterable by tags, date range) |
| GET | `/api/v1/journal/{id}` | Get single entry |
| PATCH | `/api/v1/journal/{id}` | Update entry |
| DELETE | `/api/v1/journal/{id}` | Delete entry |
| GET | `/api/v1/journal/search?q=...` | Semantic search via pgvector |

### 4.2 Auto-embedding on save

When a journal entry is created or updated:
1. Embed the content via Gemini Embeddings API (768-dim)
2. Upsert into `embedding_chunks` with `source="journal"`, `user_id`, and `source_uri=f"journal:{entry.id}"`
3. On delete: remove corresponding `embedding_chunks` rows

This makes new entries immediately available to the Historian's pgvector search.

### 4.3 Frontend

- `/journal` — List view with search bar (triggers semantic search), tag filter chips, date range picker
- `/journal/new` — Form: title, content (textarea), mood slider (1-10), tag multi-select, save button
- `/journal/[id]` — Detail view with edit/delete options
- Slide-out panel from chat: when user taps `[suggest:journal]` action button, a panel opens pre-filled with conversation context

---

## 5. Calendar

### 5.1 API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/calendar` | Create event |
| GET | `/api/v1/calendar` | List events (filterable by date range, type) |
| GET | `/api/v1/calendar/{id}` | Get single event |
| PATCH | `/api/v1/calendar/{id}` | Update event |
| DELETE | `/api/v1/calendar/{id}` | Delete event |

### 5.2 Recurrence handling

Events with `recurrence` set generate virtual instances. The query endpoint accepts a date range and returns both real events and computed recurrence instances within that range. Recurrence is simple: yearly (anniversaries), monthly, or weekly. No complex RRULE parsing.

### 5.3 Frontend

- `/calendar` — Monthly grid view, dots on event dates, color-coded by event_type
  - anniversary = purple, birthday = blue, therapy = teal, trigger = red, milestone = green, holiday = orange
- Click date → view events for that day + "Add event" button
- Event form modal: title, date, type dropdown, recurrence dropdown, notes, "Let AI know about this" toggle

---

## 6. Treatment Plans & Outcomes

### 6.1 Treatment plan API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/plans` | Create treatment plan |
| GET | `/api/v1/plans` | List plans (active first) |
| GET | `/api/v1/plans/{id}` | Get plan with goals |
| PATCH | `/api/v1/plans/{id}` | Update plan (title, status) |
| POST | `/api/v1/plans/{id}/goals` | Add goal to plan |
| PATCH | `/api/v1/goals/{id}` | Update goal (status, progress note) |
| DELETE | `/api/v1/goals/{id}` | Delete goal |

### 6.2 Assessment endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/assessments` | Submit assessment (shared with onboarding) |
| GET | `/api/v1/assessments` | List past assessments (ordered by date DESC) |
| GET | `/api/v1/assessments/latest?instrument=phq9` | Get most recent for instrument |

### 6.3 Mood log endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/mood` | Log mood (shared with onboarding) |
| GET | `/api/v1/mood` | List mood logs (paginated, date range) |
| GET | `/api/v1/mood/trend?days=14` | Aggregated trend data for charts |

### 6.4 Frontend

- `/plan` page:
  - Active plan card with title, status, progress bar (completed goals / total goals)
  - Goal list: each with description, status badge, target date, expandable progress notes
  - "Add Goal" button → inline form
  - "Take Assessment" button → modal with PHQ-9 or GAD-7 questionnaire
  - Assessment history table: date, instrument, score, severity badge
  - Mood trend sparkline (last 14 days)

- Chat integration:
  - `[suggest:goal_update]` → modal to update goal status + add progress note
  - `[suggest:assessment]` → assessment questionnaire modal
  - `[suggest:mood_check]` → quick mood slider modal

---

## 7. Data Access Patterns

Two distinct access patterns depending on whether the agent needs semantic search capabilities.

### 7.1 Architecture

```
Frontend (user)               Agent (Historian)
     │                             │
     ▼                             ├── MCP Tool Calls (semantic search)
 REST API endpoints                │   Journal: search, recent, get_by_id
 (Full CRUD for all domains)       │   Calendar: get_upcoming, get_triggers, get_by_date
     │                             │
     │                             └── Direct DB Queries (simple reads)
     │                                 Profile, Assessments, Treatment Plans,
     │                                 Mood Logs
     │                             │
     └──────────┬──────────────────┘
                ▼
       PostgreSQL tables
```

### 7.2 MCP servers (Journal + Calendar only)

Journal and Calendar use MCP because the agent needs **semantic search** (pgvector) and **recurrence expansion** — capabilities beyond simple CRUD reads.

**Journal MCP Server** (`backend/app/mcp/journal/`)

| Tool | Parameters | Returns |
|------|-----------|---------|
| `journal.search` | user_id, query (text), top_k | Semantically similar entries (service embeds query internally, then searches pgvector) |
| `journal.recent` | user_id, limit | Latest N journal entries |
| `journal.get_by_id` | entry_id | Single entry with full content |

**Calendar MCP Server** (`backend/app/mcp/calendar/`)

| Tool | Parameters | Returns |
|------|-----------|---------|
| `calendar.get_upcoming` | user_id, days | Events in next N days (includes recurrence instances) |
| `calendar.get_triggers` | user_id, days | Only anniversary/trigger type events nearby |
| `calendar.get_by_date` | user_id, date | Events on a specific date |

**Implementation pattern:**

```
backend/app/mcp/{domain}/
├── schema.py       # Pydantic models for tool inputs/outputs
├── service.py      # Service class with tool methods (async, queries DB)
├── repository.py   # SQLAlchemy queries (thin data access layer)
└── tools.py        # MCP tool definitions (name, description, parameters, handler)
```

### 7.3 Direct DB access (Profile, Assessments, Treatment Plans, Mood)

These domains are standard CRUD — the agent reads them via direct SQLAlchemy queries in the Historian node. No MCP layer needed.

**Profile** — `SELECT * FROM user_profiles WHERE user_id = :uid`
**Assessments** — `SELECT * FROM assessments WHERE user_id = :uid ORDER BY created_at DESC LIMIT 1`
**Treatment Plans** — `SELECT plan + goals WHERE user_id = :uid AND status = 'active'`
**Mood Logs** — `SELECT * FROM mood_logs WHERE user_id = :uid ORDER BY created_at DESC LIMIT :n`

These queries live in a shared repository module (`backend/app/services/therapeutic_context.py`) that the Historian imports and calls directly via `asyncio.gather`.

---

## 8. Agent Pipeline Changes

### 8.1 Expanded AgentState

```python
class AgentState(TypedDict, total=False):
    # Existing (unchanged)
    user_message: str
    conversation_id: str
    conversation_history: list[dict[str, str]]
    calendar_context: list[str]
    journal_context: list[str]
    historian_briefing: dict[str, str]
    specialist_response: str
    final_response: str

    # New fields
    user_profile: dict              # From profile.get MCP tool
    assessment_context: dict        # From assessment.get_latest MCP tool
    treatment_plan: dict            # From treatment.get_active_plan MCP tool
    recent_moods: list[dict]        # From mood.get_recent MCP tool
    upcoming_events: list[dict]     # From calendar.get_upcoming MCP tool
```

### 8.2 Historian changes

The Historian node expands from 2 parallel operations to 7:

```python
# MCP tool calls (semantic search / recurrence expansion)
journal_results = await mcp.call("journal.search", user_id=uid, query=msg)
events = await mcp.call("calendar.get_upcoming", user_id=uid, days=7)

# Direct pgvector query (static knowledge base)
cbt_results = await retriever.search(embedding, sources=("cbt_pdf",))

# Direct DB queries via therapeutic_context repository
profile = await therapeutic_ctx.get_profile(uid)
assessment = await therapeutic_ctx.get_latest_assessment(uid, "phq9")
plan = await therapeutic_ctx.get_active_plan(uid)
moods = await therapeutic_ctx.get_recent_moods(uid, limit=7)
```

All 7 calls run in parallel via `asyncio.gather`. The Historian's LLM prompt expands to include all this context in its briefing.

### 8.3 Specialist changes

System prompt additions:
- Reference user's assessment severity to calibrate approach intensity
- Mention active treatment goals when relevant ("Last time we discussed your goal to...")
- Acknowledge mood trends ("Your mood has been improving this week")
- Lean toward user's preferred approaches from onboarding
- Emit `[suggest:...]` tags when contextually appropriate:
  - `[suggest:journal]` — after emotional disclosure
  - `[suggest:mood_check]` — at end of session or when mood shift detected
  - `[suggest:assessment]` — when 2+ weeks since last assessment
  - `[suggest:goal_update]` — when user discusses progress on a known goal

### 8.4 Anchor changes

New safety checks added to system prompt:
- **Score-aware escalation:** If latest PHQ-9 ≥ 20 or GAD-7 ≥ 15, always include crisis resources (988 Suicide & Crisis Lifeline, Crisis Text Line)
- **Calendar sensitivity:** If an anniversary or trigger event is within 3 days, flag for extra-gentle tone
- **Prosody adaptation:** Severe assessment scores → default to `[speak slowly, gentle tone]`

---

## 9. Dashboard & Navigation

### 9.1 Updated route structure

| Route | Page | Auth | Onboarding |
|-------|------|------|------------|
| `/auth/login` | Login | No | No |
| `/auth/register` | Register | No | No |
| `/onboarding` | Onboarding wizard | Yes | Required if incomplete |
| `/` | Dashboard | Yes | Required |
| `/c/[id]` | Chat conversation | Yes | Required |
| `/journal` | Journal list | Yes | Required |
| `/journal/new` | New journal entry | Yes | Required |
| `/journal/[id]` | Journal detail/edit | Yes | Required |
| `/calendar` | Calendar view | Yes | Required |
| `/plan` | Treatment plan | Yes | Required |
| `/settings` | User settings | Yes | Required |

### 9.2 Sidebar expansion

The existing sidebar gains navigation sections above the conversation list:

```
┌─────────────────┐
│  EmoSync         │
│  ─────────────── │
│  Dashboard       │  ← new
│  Chat            │  ← existing (shows conversation list when active)
│  Journal         │  ← new
│  Calendar        │  ← new
│  My Plan         │  ← new
│  ─────────────── │
│  Settings        │  ← new
│  Sign Out        │
└─────────────────┘
```

### 9.3 Dashboard cards

Four cards in a responsive 2x2 grid:

1. **Mood Trend** — Sparkline of last 14 mood_logs, current score highlighted. Tap opens mood check-in modal.
2. **Treatment Plan** — Active plan title, progress bar (completed/total goals), next target date. Tap → `/plan`.
3. **Upcoming Events** — Next 3 calendar events within 7 days, trigger dates flagged. Tap → `/calendar`.
4. **Recent Journal** — Last 2-3 journal titles + dates. Tap → `/journal`.

Below cards: "Start a conversation" button → new chat or resume latest.

### 9.4 Chat action buttons

When the Specialist includes `[suggest:...]` tags, the frontend strips them from displayed text and renders action buttons below the message:

| Tag | Button Label | Action |
|-----|-------------|--------|
| `[suggest:journal]` | "Write in journal" | Opens slide-out panel, pre-filled with conversation context |
| `[suggest:mood_check]` | "How am I feeling?" | Opens mood slider modal |
| `[suggest:assessment]` | "Take a check-in" | Opens PHQ-9/GAD-7 modal |
| `[suggest:goal_update]` | "Update my goal" | Opens goal status update modal |

---

## 10. Testing Strategy

### Backend tests (pytest, stub mode)

| Area | Tests |
|------|-------|
| Onboarding API | Profile CRUD, onboarding completion, route protection |
| Journal API | Create, read, update, delete, search, auto-embedding |
| Calendar API | Create, read, update, delete, recurrence expansion |
| Assessment API | Submit, scoring logic (PHQ-9/GAD-7), severity calculation |
| Treatment Plan API | Plan CRUD, goal CRUD, progress notes |
| Mood API | Log, list, trend calculation |
| MCP tools | Each tool returns expected data shapes |
| Agent integration | Historian uses MCP tools, Specialist emits suggest tags, Anchor escalation |

### Frontend tests

- Onboarding wizard: step navigation, validation, submission
- Dashboard: renders cards with mock data
- Journal: CRUD flow, search
- Calendar: monthly view, event creation
- Chat action buttons: tag parsing, modal triggers

---

## 11. Phase Breakdown

### Phase 1 — Foundation & Onboarding
- Alembic migrations for all 7 new tables
- SQLAlchemy models for all new tables
- Pydantic schemas for all new entities
- Profile API endpoints (GET, PUT)
- Assessment API endpoints (POST, GET)
- Mood API endpoints (POST, GET)
- Onboarding completion endpoint
- PHQ-9 and GAD-7 scoring logic
- Onboarding wizard UI (4 steps)
- Route protection middleware (redirect to /onboarding)
- Tests for onboarding + profile + assessment scoring

### Phase 2 — Journal & Calendar
- Journal CRUD API endpoints
- Journal semantic search endpoint (pgvector)
- Journal auto-embedding on save (Gemini → embedding_chunks)
- Calendar CRUD API endpoints
- Calendar recurrence expansion logic
- Journal MCP server (search, recent, get_by_id tools)
- Calendar MCP server (get_upcoming, get_triggers, get_by_date tools)
- Replace Historian's mock data with real MCP tool calls
- Journal UI (list, create, edit, search, detail)
- Calendar UI (monthly grid, event form)
- Tests for journal + calendar CRUD + MCP tools

### Phase 3 — Treatment Plans & Outcomes
- Treatment plan + goal CRUD API endpoints
- Mood trend endpoint
- Therapeutic context repository (`backend/app/services/therapeutic_context.py`) for direct DB reads (profile, assessments, plans, moods)
- Expand Historian to call MCP tools (journal, calendar) + direct DB queries (profile, assessments, plans, moods)
- Expand Specialist prompt with assessment/plan/mood awareness
- Expand Anchor with score-aware escalation + calendar sensitivity
- Implement [suggest:...] tag system in Specialist
- Treatment plan UI (plan card, goal list, progress notes)
- Assessment modal (PHQ-9/GAD-7 questionnaire)
- Mood check-in modal
- Chat action buttons (parse tags, render buttons, trigger modals)
- Tests for plans + MCP tools + agent integration

### Phase 4 — Dashboard & Polish
- Dashboard page with 4 cards (mood trend, plan progress, upcoming events, recent journal)
- Expanded sidebar navigation
- Settings page (profile editing, preferences, approach selection)
- Journal slide-out panel from chat
- Data export (settings page)
- End-to-end flow tests
