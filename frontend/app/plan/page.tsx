"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  ClipboardList,
  Plus,
  Trash2,
  ChevronDown,
  ChevronUp,
  TrendingUp,
  TrendingDown,
  Minus,
  CheckCircle2,
  Circle,
  Clock,
} from "lucide-react";
import { get_token, get_profile } from "@/lib/api";
import {
  list_plans,
  create_plan,
  add_goal,
  update_goal,
  delete_goal,
  list_assessments,
  get_mood_trend,
  type TreatmentPlan,
  type TreatmentGoal,
  type AssessmentResult,
  type MoodTrend,
} from "@/lib/plan-api";

// ── Helpers ───────────────────────────────────────────────────────────────────

function format_date(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function status_badge(status: string) {
  switch (status) {
    case "completed":
      return "bg-green-500/10 text-green-700 border-green-200";
    case "in_progress":
      return "bg-yellow-500/10 text-yellow-700 border-yellow-200";
    case "active":
      return "bg-blue-500/10 text-blue-700 border-blue-200";
    default:
      return "bg-muted text-muted-foreground border-border";
  }
}

function status_label(status: string): string {
  switch (status) {
    case "not_started": return "Not started";
    case "in_progress": return "In progress";
    case "completed": return "Completed";
    case "active": return "Active";
    default: return status.replace(/_/g, " ");
  }
}

function severity_badge(severity: string): string {
  switch (severity.toLowerCase()) {
    case "minimal":
    case "none":
      return "bg-green-500/10 text-green-700 border-green-200";
    case "mild":
      return "bg-yellow-500/10 text-yellow-700 border-yellow-200";
    case "moderate":
      return "bg-orange-500/10 text-orange-700 border-orange-200";
    case "moderately severe":
    case "severe":
      return "bg-red-500/10 text-red-700 border-red-200";
    default:
      return "bg-muted text-muted-foreground border-border";
  }
}

function GoalStatusIcon({ status }: { status: string }) {
  if (status === "completed") return <CheckCircle2 className="size-4 shrink-0 text-green-600" />;
  if (status === "in_progress") return <Clock className="size-4 shrink-0 text-yellow-600" />;
  return <Circle className="size-4 shrink-0 text-muted-foreground/50" />;
}

// ── Goal card ─────────────────────────────────────────────────────────────────

interface GoalCardProps {
  goal: TreatmentGoal;
  token: string;
  on_updated: (updated: TreatmentGoal) => void;
  on_deleted: (id: string) => void;
}

function GoalCard({ goal, token, on_updated, on_deleted }: GoalCardProps) {
  const [notes_open, setNotesOpen] = useState(false);
  const [progress_note, setProgressNote] = useState("");
  const [is_submitting, setIsSubmitting] = useState(false);
  const [is_deleting, setIsDeleting] = useState(false);
  const [error, setError] = useState("");

  async function handle_status_change(new_status: string) {
    setIsSubmitting(true);
    setError("");
    try {
      const updated = await update_goal(token, goal.id, { status: new_status });
      on_updated(updated);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to update goal.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handle_add_note() {
    if (!progress_note.trim()) return;
    setIsSubmitting(true);
    setError("");
    try {
      const updated = await update_goal(token, goal.id, { progress_note: progress_note.trim() });
      on_updated(updated);
      setProgressNote("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to add note.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handle_delete() {
    setIsDeleting(true);
    try {
      await delete_goal(token, goal.id);
      on_deleted(goal.id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to delete goal.");
      setIsDeleting(false);
    }
  }

  const notes = goal.progress_notes ?? [];

  return (
    <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
      {error && (
        <p className="mb-2 rounded-lg bg-destructive/10 px-2 py-1 text-xs text-destructive">{error}</p>
      )}
      <div className="flex items-start gap-3">
        <GoalStatusIcon status={goal.status} />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-foreground">{goal.description}</p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <span
              className={`rounded-full border px-2 py-0.5 text-xs ${status_badge(goal.status)}`}
            >
              {status_label(goal.status)}
            </span>
            {goal.target_date && (
              <span className="text-xs text-muted-foreground">
                Due {format_date(goal.target_date)}
              </span>
            )}
          </div>
        </div>
        <button
          onClick={handle_delete}
          disabled={is_deleting}
          title="Delete goal"
          className="shrink-0 rounded p-1 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive disabled:opacity-50"
        >
          <Trash2 className="size-4" />
        </button>
      </div>

      {/* Status actions */}
      <div className="mt-3 flex flex-wrap gap-2">
        {goal.status !== "in_progress" && (
          <button
            onClick={() => handle_status_change("in_progress")}
            disabled={is_submitting}
            className="rounded-lg border border-yellow-200 bg-yellow-500/5 px-2.5 py-1 text-xs font-medium text-yellow-700 transition-colors hover:bg-yellow-500/15 disabled:opacity-50"
          >
            Mark in progress
          </button>
        )}
        {goal.status !== "completed" && (
          <button
            onClick={() => handle_status_change("completed")}
            disabled={is_submitting}
            className="rounded-lg border border-green-200 bg-green-500/5 px-2.5 py-1 text-xs font-medium text-green-700 transition-colors hover:bg-green-500/15 disabled:opacity-50"
          >
            Mark completed
          </button>
        )}
        {goal.status !== "not_started" && (
          <button
            onClick={() => handle_status_change("not_started")}
            disabled={is_submitting}
            className="rounded-lg border border-border bg-muted/30 px-2.5 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted disabled:opacity-50"
          >
            Reset
          </button>
        )}
      </div>

      {/* Progress notes toggle */}
      <div className="mt-3 border-t border-border pt-3">
        <button
          onClick={() => setNotesOpen((v) => !v)}
          className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
        >
          {notes_open ? <ChevronUp className="size-3.5" /> : <ChevronDown className="size-3.5" />}
          Progress notes {notes.length > 0 ? `(${notes.length})` : ""}
        </button>

        {notes_open && (
          <div className="mt-2 space-y-2">
            {notes.length === 0 && (
              <p className="text-xs text-muted-foreground">No notes yet.</p>
            )}
            {notes.map((n, i) => (
              <div key={i} className="rounded-lg bg-muted/40 px-3 py-2">
                <p className="text-xs text-muted-foreground">{format_date(n.date)}</p>
                <p className="mt-0.5 text-xs text-foreground">{n.note}</p>
              </div>
            ))}
            <div className="flex gap-2 pt-1">
              <input
                type="text"
                value={progress_note}
                onChange={(e) => setProgressNote(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") void handle_add_note(); }}
                placeholder="Add a progress note…"
                className="flex-1 rounded-lg border border-input bg-transparent px-3 py-1.5 text-xs outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/30"
              />
              <Button
                size="sm"
                variant="outline"
                onClick={handle_add_note}
                disabled={is_submitting || !progress_note.trim()}
                className="text-xs"
              >
                Add
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function PlanPage() {
  const router = useRouter();
  const [token, setToken] = useState("");
  const [plans, setPlans] = useState<TreatmentPlan[]>([]);
  const [assessments, setAssessments] = useState<AssessmentResult[]>([]);
  const [mood_trend, setMoodTrend] = useState<MoodTrend | null>(null);
  const [is_loading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  // Create plan form
  const [show_create_form, setShowCreateForm] = useState(false);
  const [new_plan_title, setNewPlanTitle] = useState("");
  const [is_creating_plan, setIsCreatingPlan] = useState(false);

  // Add goal form
  const [show_goal_form, setShowGoalForm] = useState(false);
  const [goal_description, setGoalDescription] = useState("");
  const [goal_target_date, setGoalTargetDate] = useState("");
  const [is_adding_goal, setIsAddingGoal] = useState(false);

  const active_plan = plans.find((p) => p.status === "active") ?? plans[0] ?? null;

  const load_data = useCallback(async (t: string) => {
    setIsLoading(true);
    setError("");
    try {
      const [plans_data, assessments_data] = await Promise.all([
        list_plans(t),
        list_assessments(t).catch(() => [] as AssessmentResult[]),
      ]);
      setPlans(plans_data);
      setAssessments(assessments_data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load plan data.");
    }
    // Mood trend is optional — don't block the page
    get_mood_trend(t).then(setMoodTrend).catch(() => null);
    setIsLoading(false);
  }, []);

  useEffect(() => {
    const t = get_token();
    if (!t) {
      router.replace("/auth/login");
      return;
    }
    setToken(t);
    get_profile(t)
      .then((profile) => {
        if (!profile.onboarding_completed) {
          router.replace("/onboarding");
          return;
        }
        return load_data(t);
      })
      .catch(() => router.replace("/auth/login"));
  }, [router, load_data]);

  async function handle_create_plan() {
    if (!new_plan_title.trim()) return;
    setIsCreatingPlan(true);
    setError("");
    try {
      const plan = await create_plan(token, new_plan_title.trim());
      setPlans((prev) => [plan, ...prev]);
      setNewPlanTitle("");
      setShowCreateForm(false);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create plan.");
    } finally {
      setIsCreatingPlan(false);
    }
  }

  async function handle_add_goal() {
    if (!goal_description.trim() || !active_plan) return;
    setIsAddingGoal(true);
    setError("");
    try {
      const goal = await add_goal(token, active_plan.id, {
        description: goal_description.trim(),
        target_date: goal_target_date || undefined,
      });
      setPlans((prev) =>
        prev.map((p) =>
          p.id === active_plan.id ? { ...p, goals: [...p.goals, goal] } : p
        )
      );
      setGoalDescription("");
      setGoalTargetDate("");
      setShowGoalForm(false);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to add goal.");
    } finally {
      setIsAddingGoal(false);
    }
  }

  function handle_goal_updated(updated: TreatmentGoal) {
    setPlans((prev) =>
      prev.map((p) => ({
        ...p,
        goals: p.goals.map((g) => (g.id === updated.id ? updated : g)),
      }))
    );
  }

  function handle_goal_deleted(goal_id: string) {
    setPlans((prev) =>
      prev.map((p) => ({
        ...p,
        goals: p.goals.filter((g) => g.id !== goal_id),
      }))
    );
  }

  // Progress bar helpers
  const total_goals = active_plan?.goals.length ?? 0;
  const completed_goals = active_plan?.goals.filter((g) => g.status === "completed").length ?? 0;
  const progress_pct = total_goals > 0 ? Math.round((completed_goals / total_goals) * 100) : 0;

  function MoodDirectionIcon() {
    if (!mood_trend) return null;
    if (mood_trend.direction === "up") return <TrendingUp className="size-4 text-green-600" />;
    if (mood_trend.direction === "down") return <TrendingDown className="size-4 text-red-500" />;
    return <Minus className="size-4 text-muted-foreground" />;
  }

  if (is_loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <p className="text-sm text-muted-foreground">Loading your plan…</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background px-4 py-8">
      <div className="mx-auto max-w-2xl">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <ClipboardList className="size-5 text-primary" />
            <h1 className="text-xl font-semibold tracking-tight">My Plan</h1>
          </div>
          {!active_plan && !show_create_form && (
            <Button size="sm" onClick={() => setShowCreateForm(true)}>
              <Plus className="mr-1.5 size-4" />
              Create Plan
            </Button>
          )}
        </div>

        {error && (
          <p className="mb-4 rounded-lg bg-destructive/10 px-3 py-2 text-xs text-destructive">
            {error}
          </p>
        )}

        {/* Create plan form */}
        {show_create_form && (
          <div className="mb-6 rounded-xl border border-border bg-card p-4 shadow-sm">
            <h2 className="mb-3 text-sm font-semibold">Create a Treatment Plan</h2>
            <div className="flex gap-2">
              <input
                type="text"
                value={new_plan_title}
                onChange={(e) => setNewPlanTitle(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") void handle_create_plan(); }}
                placeholder="Plan title (e.g. 90-day grief recovery)"
                className="flex-1 rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/30"
              />
              <Button onClick={handle_create_plan} disabled={is_creating_plan || !new_plan_title.trim()} size="sm">
                {is_creating_plan ? "Creating…" : "Create"}
              </Button>
              <Button variant="outline" size="sm" onClick={() => { setShowCreateForm(false); setNewPlanTitle(""); }}>
                Cancel
              </Button>
            </div>
          </div>
        )}

        {/* No plan state */}
        {!active_plan && !show_create_form && (
          <div className="rounded-xl border border-border bg-card p-10 text-center">
            <ClipboardList className="mx-auto mb-3 size-8 text-muted-foreground/40" />
            <p className="text-sm font-medium text-muted-foreground">No treatment plan yet</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Create a plan to track your goals and progress.
            </p>
            <Button className="mt-4" size="sm" onClick={() => setShowCreateForm(true)}>
              <Plus className="mr-1.5 size-4" />
              Create Plan
            </Button>
          </div>
        )}

        {/* Active plan card */}
        {active_plan && (
          <div className="mb-6 rounded-xl border border-border bg-card p-5 shadow-sm">
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold text-foreground">{active_plan.title}</h2>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  Created {format_date(active_plan.created_at)}
                </p>
              </div>
              <span
                className={`shrink-0 rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${status_badge(active_plan.status)}`}
              >
                {status_label(active_plan.status)}
              </span>
            </div>

            {/* Progress bar */}
            {total_goals > 0 && (
              <div className="mb-4">
                <div className="mb-1.5 flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">
                    {completed_goals} of {total_goals} goals completed
                  </span>
                  <span className="text-xs font-medium text-foreground">{progress_pct}%</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary transition-all duration-500"
                    style={{ width: `${progress_pct}%` }}
                  />
                </div>
              </div>
            )}

            {/* Goal list */}
            <div className="space-y-3">
              {active_plan.goals.length === 0 && (
                <p className="text-xs text-muted-foreground">No goals yet. Add one below.</p>
              )}
              {active_plan.goals.map((goal) => (
                <GoalCard
                  key={goal.id}
                  goal={goal}
                  token={token}
                  on_updated={handle_goal_updated}
                  on_deleted={handle_goal_deleted}
                />
              ))}
            </div>

            {/* Add goal */}
            <div className="mt-4 border-t border-border pt-4">
              {!show_goal_form ? (
                <button
                  onClick={() => setShowGoalForm(true)}
                  className="flex items-center gap-1.5 text-xs font-medium text-primary transition-colors hover:text-primary/80"
                >
                  <Plus className="size-3.5" />
                  Add goal
                </button>
              ) : (
                <div className="space-y-2">
                  <input
                    type="text"
                    value={goal_description}
                    onChange={(e) => setGoalDescription(e.target.value)}
                    placeholder="Describe your goal…"
                    className="w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/30"
                  />
                  <div className="flex items-center gap-2">
                    <input
                      type="date"
                      value={goal_target_date}
                      onChange={(e) => setGoalTargetDate(e.target.value)}
                      className="rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none focus:border-ring focus:ring-2 focus:ring-ring/30"
                    />
                    <span className="text-xs text-muted-foreground">Target date (optional)</span>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      onClick={handle_add_goal}
                      disabled={is_adding_goal || !goal_description.trim()}
                    >
                      {is_adding_goal ? "Adding…" : "Add Goal"}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => { setShowGoalForm(false); setGoalDescription(""); setGoalTargetDate(""); }}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Mood trend */}
        {mood_trend && (
          <div className="mb-6 rounded-xl border border-border bg-card p-4 shadow-sm">
            <h2 className="mb-3 text-sm font-semibold tracking-tight">Mood Trend</h2>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <MoodDirectionIcon />
                <div>
                  <p className="text-2xl font-bold text-foreground">
                    {mood_trend.average.toFixed(1)}
                    <span className="ml-1 text-sm font-normal text-muted-foreground">/10</span>
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Average over {mood_trend.period_days} days
                    {" · "}{mood_trend.count} data point{mood_trend.count !== 1 ? "s" : ""}
                  </p>
                </div>
              </div>
              <span
                className={`ml-auto rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${
                  mood_trend.direction === "up"
                    ? "border-green-200 bg-green-500/10 text-green-700"
                    : mood_trend.direction === "down"
                    ? "border-red-200 bg-red-500/10 text-red-600"
                    : "bg-muted text-muted-foreground border-border"
                }`}
              >
                {mood_trend.direction === "up" ? "Improving" : mood_trend.direction === "down" ? "Declining" : "Stable"}
              </span>
            </div>
          </div>
        )}

        {/* Assessment history */}
        <div className="rounded-xl border border-border bg-card shadow-sm">
          <div className="border-b border-border px-4 py-3">
            <h2 className="text-sm font-semibold tracking-tight">Assessment History</h2>
          </div>
          {assessments.length === 0 ? (
            <div className="px-4 py-8 text-center">
              <p className="text-xs text-muted-foreground">No assessments recorded yet.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs font-medium text-muted-foreground">
                    <th className="px-4 py-2.5">Date</th>
                    <th className="px-4 py-2.5">Instrument</th>
                    <th className="px-4 py-2.5">Score</th>
                    <th className="px-4 py-2.5">Severity</th>
                  </tr>
                </thead>
                <tbody>
                  {assessments
                    .slice()
                    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
                    .map((a) => (
                      <tr key={a.id} className="border-b border-border/50 last:border-0">
                        <td className="px-4 py-2.5 text-xs text-muted-foreground">
                          {format_date(a.created_at)}
                        </td>
                        <td className="px-4 py-2.5 text-xs font-medium text-foreground">
                          {a.instrument.toUpperCase()}
                        </td>
                        <td className="px-4 py-2.5 text-xs font-semibold text-foreground">
                          {a.total_score}
                        </td>
                        <td className="px-4 py-2.5">
                          <span
                            className={`rounded-full border px-2 py-0.5 text-xs capitalize ${severity_badge(a.severity)}`}
                          >
                            {a.severity}
                          </span>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
