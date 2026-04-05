# Phase 4: Dashboard & Polish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the root page with a dashboard showing mood trend, treatment plan progress, upcoming calendar events, and recent journal entries. Add a settings page for profile editing. Update sidebar with Dashboard and Settings links.

**Architecture:** Dashboard is a client component that fetches data from existing endpoints on mount. Settings page reads/writes the profile API. The root `/` route changes from ChatView to Dashboard. Chat moves to a dedicated `/chat` route.

**Tech Stack:** Next.js 15 (App Router), Tailwind CSS, Shadcn/ui

**Spec:** `docs/superpowers/specs/2026-04-04-therapeutic-platform-expansion-design.md` (Section 9)

---

## Task 1: Dashboard Page

**Files:**
- Create: `frontend/app/dashboard/page.tsx`
- Modify: `frontend/app/page.tsx`

- [ ] **Step 1: Create dashboard page**

Create `frontend/app/dashboard/page.tsx` — a "use client" page with 4 cards in a 2x2 responsive grid:

1. **Mood Trend** — calls `GET /api/v1/mood/trend` via plan-api.ts `get_mood_trend()`. Shows average score (large number), direction arrow (up=green, down=red, stable=gray), period. Links to mood check-in.

2. **Treatment Plan** — calls `GET /api/v1/plans` via plan-api.ts `list_plans()`. Shows active plan title, progress bar (completed goals / total goals), next target date. Links to `/plan`.

3. **Upcoming Events** — calls `GET /api/v1/calendar` with from_date=today, to_date=today+7 via calendar-api.ts. Shows next 3 events with date and type badge. Links to `/calendar`.

4. **Recent Journal** — calls `GET /api/v1/journal` via journal-api.ts. Shows last 3 entry titles + dates. Links to `/journal`.

Below cards: "Start a conversation" button linking to `/chat`.

Auth + onboarding check on mount (get_token, get_profile).

Use existing API client functions from `journal-api.ts`, `calendar-api.ts`, `plan-api.ts`.

Styling: responsive grid (`grid grid-cols-1 md:grid-cols-2 gap-4`), each card is `rounded-xl border border-border bg-card p-5`.

- [ ] **Step 2: Update root page to redirect to dashboard**

Replace `frontend/app/page.tsx`:

```tsx
import { redirect } from "next/navigation";

export default function Home() {
  redirect("/dashboard");
}
```

- [ ] **Step 3: Move chat to /chat route**

Create `frontend/app/chat/page.tsx`:

```tsx
import { ChatView } from "@/components/chat_view";

export default function ChatPage() {
  return <ChatView />;
}
```

Ensure `/c/[id]/page.tsx` still works (it already imports ChatView directly, no change needed).

- [ ] **Step 4: Commit**

```bash
git add frontend/app/dashboard/ frontend/app/page.tsx frontend/app/chat/
git commit -m "feat: add dashboard page with mood/plan/events/journal cards"
```

---

## Task 2: Settings Page

**Files:**
- Create: `frontend/app/settings/page.tsx`

- [ ] **Step 1: Create settings page**

Create `frontend/app/settings/page.tsx` — a "use client" page for profile editing:

- Auth + onboarding check on mount
- Loads profile via `get_profile()`
- Editable fields: grief_type (dropdown), grief_subject (textarea), support_system (radio), prior_therapy (toggle), preferred_approaches (multi-select checkboxes)
- Display name field (from user, read-only or editable)
- Assessment scores display (latest PHQ-9 and GAD-7 from `GET /api/v1/assessments/latest`)
- "Save Changes" button → calls `update_profile()` from onboarding-api.ts
- "Sign Out" button → clears auth, redirects to login

Uses existing API functions from `api.ts` and `onboarding-api.ts`.

- [ ] **Step 2: Commit**

```bash
git add frontend/app/settings/
git commit -m "feat: add settings page (profile editing, preferences, sign out)"
```

---

## Task 3: Update Sidebar Navigation

**Files:**
- Modify: `frontend/components/sidebar.tsx`

- [ ] **Step 1: Add Dashboard, Chat, and Settings links**

Read `frontend/components/sidebar.tsx`. Add:
- **Dashboard** link at the top (using `LayoutDashboard` icon, href="/dashboard")
- **Chat** link (using `MessageCircle` icon, href="/chat") — replaces or supplements the existing conversation-list behavior
- **Settings** link near the bottom (using `Settings` icon, href="/settings")
- **Sign Out** button at the very bottom (using `LogOut` icon) — calls `clear_auth()` from api.ts, redirects to `/auth/login`

The sidebar should now have this order:
1. Dashboard
2. Chat (with conversation list when expanded)
3. Journal
4. Calendar
5. My Plan
6. ---separator---
7. Settings
8. Sign Out

- [ ] **Step 2: Commit**

```bash
git add frontend/components/sidebar.tsx
git commit -m "feat: update sidebar with Dashboard, Chat, Settings, and Sign Out links"
```

---

## Task 4: Run Full Test Suite + Final Verification

- [ ] **Step 1: Run all backend tests**

Run: `cd backend && uv run python -m pytest -q`

- [ ] **Step 2: Verify git log**

Run: `git log --oneline -30` to see the full implementation history.

- [ ] **Step 3: Commit any fixes**

```bash
git add -u && git commit -m "fix: resolve Phase 4 integration issues"
```
