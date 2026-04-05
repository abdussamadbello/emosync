# Chat Therapeutic Actions — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make chat conversations directly create therapeutic data — inline mood check-in, journal save from conversation context, goal progress update, and assessment prompting — all without leaving the chat view.

**Architecture:** Replace the current `SuggestButton` (which just links to other pages) with inline modal components that POST to existing API endpoints. Each modal is a small self-contained component rendered inside chat_view.tsx. The conversation context (last assistant message + user message) is passed to the journal modal as pre-filled content. No backend changes needed — all existing endpoints work.

**Tech Stack:** Next.js 15, React (useState), Tailwind CSS, existing API clients

---

## File Structure

### Frontend — New Files

| File | Responsibility |
|------|---------------|
| `frontend/components/chat-actions/mood-modal.tsx` | Inline mood check-in (1-10 slider + label) |
| `frontend/components/chat-actions/journal-modal.tsx` | Journal save with pre-filled conversation context |
| `frontend/components/chat-actions/goal-modal.tsx` | Goal status update + progress note |
| `frontend/components/chat-actions/assessment-modal.tsx` | PHQ-9 / GAD-7 questionnaire |

### Frontend — Modified Files

| File | Change |
|------|--------|
| `frontend/components/chat_view.tsx` | Replace SuggestButton with inline action modals |

---

## Task 1: Mood Check-In Modal

**Files:**
- Create: `frontend/components/chat-actions/mood-modal.tsx`

- [ ] **Step 1: Create the mood modal component**

Create `frontend/components/chat-actions/mood-modal.tsx`:

```tsx
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { SmilePlus, X } from "lucide-react";

const EMOTION_LABELS = ["anxious", "sad", "numb", "hopeful", "calm", "angry"];
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface MoodModalProps {
  token: string;
  onClose: () => void;
  onSaved: () => void;
}

export function MoodModal({ token, onClose, onSaved }: MoodModalProps) {
  const [score, setScore] = useState(5);
  const [label, setLabel] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handle_save() {
    setSaving(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/v1/mood`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          score,
          label: label || undefined,
          source: "check_in",
        }),
      });
      if (!res.ok) throw new Error(`Failed (${res.status})`);
      onSaved();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save mood.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mt-2 rounded-xl border border-border bg-card p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium">
          <SmilePlus className="size-4 text-primary" />
          How are you feeling right now?
        </div>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
          <X className="size-4" />
        </button>
      </div>

      <div className="mb-3 flex flex-col gap-1.5">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>Very low</span>
          <span className="text-base font-semibold text-foreground">{score}</span>
          <span>Very good</span>
        </div>
        <input
          type="range"
          min={1}
          max={10}
          value={score}
          onChange={(e) => setScore(Number(e.target.value))}
          className="w-full accent-primary"
        />
      </div>

      <div className="mb-3 flex flex-wrap gap-1.5">
        {EMOTION_LABELS.map((l) => (
          <button
            key={l}
            type="button"
            onClick={() => setLabel(label === l ? "" : l)}
            className={`rounded-full border px-2.5 py-1 text-xs transition-colors ${
              label === l
                ? "border-primary bg-primary/5 font-medium"
                : "border-border hover:border-primary/50"
            }`}
          >
            {l}
          </button>
        ))}
      </div>

      {error && <p className="mb-2 text-xs text-destructive">{error}</p>}

      <Button onClick={handle_save} disabled={saving} size="sm" className="w-full">
        {saving ? "Saving…" : "Log mood"}
      </Button>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/chat-actions/mood-modal.tsx
git commit -m "feat: add inline mood check-in modal for chat"
```

---

## Task 2: Journal Save Modal

**Files:**
- Create: `frontend/components/chat-actions/journal-modal.tsx`

- [ ] **Step 1: Create the journal modal component**

Create `frontend/components/chat-actions/journal-modal.tsx`:

```tsx
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { BookOpen, X } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TAG_OPTIONS = ["grief", "progress", "trigger", "gratitude", "reflection", "therapy"];

interface JournalModalProps {
  token: string;
  context: string;
  conversationId: string | null;
  onClose: () => void;
  onSaved: () => void;
}

export function JournalModal({ token, context, conversationId, onClose, onSaved }: JournalModalProps) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState(context);
  const [mood_score, setMoodScore] = useState<number | null>(null);
  const [tags, setTags] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function toggle_tag(tag: string) {
    setTags((prev) => (prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]));
  }

  async function handle_save() {
    if (!content.trim()) {
      setError("Content is required.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/v1/journal`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: title || undefined,
          content,
          mood_score: mood_score ?? undefined,
          tags,
          source: "ai_suggested",
          conversation_id: conversationId || undefined,
        }),
      });
      if (!res.ok) throw new Error(`Failed (${res.status})`);
      onSaved();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mt-2 rounded-xl border border-border bg-card p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium">
          <BookOpen className="size-4 text-primary" />
          Save to journal
        </div>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
          <X className="size-4" />
        </button>
      </div>

      <input
        type="text"
        placeholder="Title (optional)"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        className="mb-2 w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/30"
      />

      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        rows={4}
        className="mb-2 w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/30"
      />

      <div className="mb-2 flex flex-col gap-1.5">
        <label className="text-xs text-muted-foreground">Mood (optional)</label>
        <div className="flex items-center gap-2">
          <input
            type="range"
            min={1}
            max={10}
            value={mood_score ?? 5}
            onChange={(e) => setMoodScore(Number(e.target.value))}
            className="flex-1 accent-primary"
          />
          <span className="w-6 text-center text-sm font-medium">{mood_score ?? "—"}</span>
        </div>
      </div>

      <div className="mb-3 flex flex-wrap gap-1.5">
        {TAG_OPTIONS.map((tag) => (
          <button
            key={tag}
            type="button"
            onClick={() => toggle_tag(tag)}
            className={`rounded-full border px-2.5 py-1 text-xs transition-colors ${
              tags.includes(tag)
                ? "border-primary bg-primary/5 font-medium"
                : "border-border hover:border-primary/50"
            }`}
          >
            {tag}
          </button>
        ))}
      </div>

      {error && <p className="mb-2 text-xs text-destructive">{error}</p>}

      <Button onClick={handle_save} disabled={saving} size="sm" className="w-full">
        {saving ? "Saving…" : "Save journal entry"}
      </Button>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/chat-actions/journal-modal.tsx
git commit -m "feat: add inline journal save modal for chat"
```

---

## Task 3: Goal Update Modal

**Files:**
- Create: `frontend/components/chat-actions/goal-modal.tsx`

- [ ] **Step 1: Create the goal update modal component**

Create `frontend/components/chat-actions/goal-modal.tsx`:

```tsx
"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Target, X } from "lucide-react";
import { list_plans, update_goal, type TreatmentGoal } from "@/lib/plan-api";

interface GoalModalProps {
  token: string;
  onClose: () => void;
  onSaved: () => void;
}

export function GoalModal({ token, onClose, onSaved }: GoalModalProps) {
  const [goals, setGoals] = useState<TreatmentGoal[]>([]);
  const [selected_goal, setSelectedGoal] = useState<string>("");
  const [new_status, setNewStatus] = useState<string>("");
  const [progress_note, setProgressNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    list_plans(token)
      .then((plans) => {
        const active = plans.find((p) => p.status === "active");
        if (active) {
          setGoals(active.goals.filter((g) => g.status !== "completed"));
          if (active.goals.length > 0) {
            setSelectedGoal(active.goals[0].id);
            setNewStatus(active.goals[0].status);
          }
        }
      })
      .catch(() => setError("Failed to load goals."))
      .finally(() => setLoading(false));
  }, [token]);

  async function handle_save() {
    if (!selected_goal || !progress_note.trim()) {
      setError("Select a goal and add a note.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await update_goal(token, selected_goal, {
        status: new_status || undefined,
        progress_note,
      });
      onSaved();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to update.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="mt-2 rounded-xl border border-border bg-card p-4 text-sm text-muted-foreground">
        Loading goals…
      </div>
    );
  }

  if (goals.length === 0) {
    return (
      <div className="mt-2 rounded-xl border border-border bg-card p-4">
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">No active goals to update.</span>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="size-4" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mt-2 rounded-xl border border-border bg-card p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Target className="size-4 text-primary" />
          Update goal progress
        </div>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
          <X className="size-4" />
        </button>
      </div>

      <select
        value={selected_goal}
        onChange={(e) => {
          setSelectedGoal(e.target.value);
          const g = goals.find((g) => g.id === e.target.value);
          if (g) setNewStatus(g.status);
        }}
        className="mb-2 w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none focus:border-ring focus:ring-2 focus:ring-ring/30"
      >
        {goals.map((g) => (
          <option key={g.id} value={g.id}>
            [{g.status}] {g.description.slice(0, 60)}
          </option>
        ))}
      </select>

      <div className="mb-2 flex gap-2">
        {["not_started", "in_progress", "completed"].map((s) => (
          <button
            key={s}
            onClick={() => setNewStatus(s)}
            className={`flex-1 rounded-lg border px-2 py-1.5 text-xs transition-colors ${
              new_status === s
                ? "border-primary bg-primary/5 font-medium"
                : "border-border hover:border-primary/50"
            }`}
          >
            {s.replace("_", " ")}
          </button>
        ))}
      </div>

      <textarea
        placeholder="What progress did you make?"
        value={progress_note}
        onChange={(e) => setProgressNote(e.target.value)}
        rows={2}
        className="mb-2 w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/30"
      />

      {error && <p className="mb-2 text-xs text-destructive">{error}</p>}

      <Button onClick={handle_save} disabled={saving} size="sm" className="w-full">
        {saving ? "Saving…" : "Update goal"}
      </Button>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/chat-actions/goal-modal.tsx
git commit -m "feat: add inline goal update modal for chat"
```

---

## Task 4: Assessment Modal

**Files:**
- Create: `frontend/components/chat-actions/assessment-modal.tsx`

- [ ] **Step 1: Create the assessment modal component**

Create `frontend/components/chat-actions/assessment-modal.tsx`:

```tsx
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ClipboardCheck, X } from "lucide-react";
import { submit_assessment } from "@/lib/onboarding-api";

const PHQ9_QUESTIONS = [
  "Little interest or pleasure in doing things",
  "Feeling down, depressed, or hopeless",
  "Trouble falling or staying asleep, or sleeping too much",
  "Feeling tired or having little energy",
  "Poor appetite or overeating",
  "Feeling bad about yourself — or that you are a failure",
  "Trouble concentrating on things",
  "Moving or speaking slowly, or being fidgety/restless",
  "Thoughts that you would be better off dead, or of hurting yourself",
];

const ANSWER_OPTIONS = [
  { value: 0, label: "Not at all" },
  { value: 1, label: "Several days" },
  { value: 2, label: "More days" },
  { value: 3, label: "Nearly every day" },
];

interface AssessmentModalProps {
  token: string;
  onClose: () => void;
  onSaved: (result: { total_score: number; severity: string }) => void;
}

export function AssessmentModal({ token, onClose, onSaved }: AssessmentModalProps) {
  const [responses, setResponses] = useState<Record<string, number>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const all_answered = PHQ9_QUESTIONS.every((_, i) => `q${i + 1}` in responses);

  async function handle_submit() {
    if (!all_answered) {
      setError("Please answer all questions.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const result = await submit_assessment(token, {
        instrument: "phq9",
        responses,
        source: "ai_prompted",
      });
      onSaved({ total_score: result.total_score, severity: result.severity });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to submit.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mt-2 rounded-xl border border-border bg-card p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium">
          <ClipboardCheck className="size-4 text-primary" />
          Quick PHQ-9 check-in
        </div>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
          <X className="size-4" />
        </button>
      </div>

      <p className="mb-3 text-xs text-muted-foreground">
        Over the last 2 weeks, how often have you been bothered by:
      </p>

      <div className="flex max-h-64 flex-col gap-2.5 overflow-y-auto pr-1">
        {PHQ9_QUESTIONS.map((q, i) => (
          <div key={i} className="flex flex-col gap-1">
            <p className="text-xs">{q}</p>
            <div className="flex gap-1">
              {ANSWER_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setResponses((prev) => ({ ...prev, [`q${i + 1}`]: opt.value }))}
                  className={`flex-1 rounded border px-1 py-1 text-[10px] transition-colors ${
                    responses[`q${i + 1}`] === opt.value
                      ? "border-primary bg-primary/10 font-medium"
                      : "border-border hover:border-primary/50"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      {error && <p className="mt-2 text-xs text-destructive">{error}</p>}

      <Button onClick={handle_submit} disabled={saving || !all_answered} size="sm" className="mt-3 w-full">
        {saving ? "Submitting…" : "Submit check-in"}
      </Button>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/chat-actions/assessment-modal.tsx
git commit -m "feat: add inline PHQ-9 assessment modal for chat"
```

---

## Task 5: Wire Modals into Chat View

**Files:**
- Modify: `frontend/components/chat_view.tsx`

This is the key task — replace `SuggestButton` (which just links to pages) with modals that open inline below the message and POST to the API.

- [ ] **Step 1: Replace SuggestButton with inline action system**

In `frontend/components/chat_view.tsx`:

1. Remove the old `SuggestButton` component and its `Link` import (if only used for that).

2. Add imports for the new modals:

```tsx
import { MoodModal } from "@/components/chat-actions/mood-modal";
import { JournalModal } from "@/components/chat-actions/journal-modal";
import { GoalModal } from "@/components/chat-actions/goal-modal";
import { AssessmentModal } from "@/components/chat-actions/assessment-modal";
```

3. Add state for tracking which message has an open modal:

```tsx
const [active_action, setActiveAction] = useState<{
  message_index: number;
  type: string;
} | null>(null);
```

4. Add a helper to get the current auth token:

```tsx
function get_auth_token(): string {
  return get_token() ?? "";
}
```

5. Replace the `SuggestButton` rendering with action buttons that toggle modals. Where the current code renders:

```tsx
{msg.role === "assistant" && parse_suggest_tag(msg.content).suggest && (
  <SuggestButton suggest={parse_suggest_tag(msg.content).suggest!} />
)}
```

Replace with:

```tsx
{msg.role === "assistant" && parse_suggest_tag(msg.content).suggest && (
  <>
    {active_action?.message_index === idx && active_action.type === parse_suggest_tag(msg.content).suggest ? (
      // Render the open modal
      <>
        {active_action.type === "mood_check" && (
          <MoodModal
            token={get_auth_token()}
            onClose={() => setActiveAction(null)}
            onSaved={() => setActiveAction(null)}
          />
        )}
        {active_action.type === "journal" && (
          <JournalModal
            token={get_auth_token()}
            context={msg.content.slice(0, 500)}
            conversationId={active_conversation_id}
            onClose={() => setActiveAction(null)}
            onSaved={() => setActiveAction(null)}
          />
        )}
        {active_action.type === "goal_update" && (
          <GoalModal
            token={get_auth_token()}
            onClose={() => setActiveAction(null)}
            onSaved={() => setActiveAction(null)}
          />
        )}
        {active_action.type === "assessment" && (
          <AssessmentModal
            token={get_auth_token()}
            onClose={() => setActiveAction(null)}
            onSaved={() => setActiveAction(null)}
          />
        )}
      </>
    ) : (
      // Render the action button
      <ChatActionButton
        suggest={parse_suggest_tag(msg.content).suggest!}
        onClick={() =>
          setActiveAction({
            message_index: idx,
            type: parse_suggest_tag(msg.content).suggest!,
          })
        }
      />
    )}
  </>
)}
```

6. Replace the `SuggestButton` component with `ChatActionButton`:

```tsx
function ChatActionButton({ suggest, onClick }: { suggest: string; onClick: () => void }) {
  const label =
    suggest === "journal"
      ? "Write in journal"
      : suggest === "goal_update"
      ? "Update my goal"
      : suggest === "assessment"
      ? "Take a check-in"
      : "How am I feeling?";
  const Icon = suggest === "journal" ? BookOpen : suggest === "goal_update" ? Target : suggest === "assessment" ? ClipboardCheck : SmilePlus;
  return (
    <button
      onClick={onClick}
      className="mt-2 inline-flex items-center gap-1.5 rounded-lg border border-primary/30 bg-primary/5 px-3 py-1.5 text-xs font-medium text-primary transition-colors hover:bg-primary/10"
    >
      <Icon className="size-3.5" />
      {label}
    </button>
  );
}
```

7. Add missing icon imports (SmilePlus, ClipboardCheck) from lucide-react if not already imported.

8. The `idx` variable should come from the `.map()` callback — check that the message list rendering provides it. The current code likely uses `.map((msg, idx) => ...)` or similar — use that index.

9. `active_conversation_id` is the current conversation ID state variable — read the file to find its actual name (likely `active_conversation` or the ID extracted from the URL).

- [ ] **Step 2: Verify the rendering**

Run the frontend dev server and:
1. Chat with the AI until it emits a `[suggest:...]` tag
2. Click the action button
3. The modal should appear inline below the message
4. Fill it out and submit
5. The modal should close on success

- [ ] **Step 3: Commit**

```bash
git add frontend/components/chat_view.tsx
git commit -m "feat: wire inline therapeutic action modals into chat view"
```

---

## Task 6: Test Full Flow

- [ ] **Step 1: Run backend tests to verify nothing broke**

Run: `cd backend && uv run python -m pytest tests/test_mood.py tests/test_journal_crud.py tests/test_plans.py tests/test_assessments.py -q`

- [ ] **Step 2: Manual E2E test**

1. Login as Alice (alice@example.com / password123)
2. Start a conversation
3. Share something emotional → AI should respond with `[suggest:journal]` or `[suggest:mood_check]`
4. Click the action button → modal opens inline
5. Submit → data saved to DB
6. Check `/journal` or `/plan` to verify the data appears

- [ ] **Step 3: Commit any fixes**

```bash
git add -u && git commit -m "fix: resolve chat action integration issues"
```
