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
          const incomplete = active.goals.filter((g) => g.status !== "completed");
          setGoals(incomplete);
          if (incomplete.length > 0) { setSelectedGoal(incomplete[0].id); setNewStatus(incomplete[0].status); }
        }
      })
      .catch(() => setError("Failed to load goals."))
      .finally(() => setLoading(false));
  }, [token]);

  async function handle_save() {
    if (!selected_goal || !progress_note.trim()) { setError("Select a goal and add a note."); return; }
    setSaving(true); setError("");
    try {
      await update_goal(token, selected_goal, { status: new_status || undefined, progress_note });
      onSaved();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to update.");
    } finally { setSaving(false); }
  }

  if (loading) return <div className="mt-2 rounded-xl border border-border bg-card p-4 text-sm text-muted-foreground">Loading goals…</div>;
  if (goals.length === 0) return (
    <div className="mt-2 rounded-xl border border-border bg-card p-4">
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">No active goals to update.</span>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground"><X className="size-4" /></button>
      </div>
    </div>
  );

  return (
    <div className="mt-2 rounded-xl border border-border bg-card p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium"><Target className="size-4 text-primary" /> Update goal progress</div>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground"><X className="size-4" /></button>
      </div>
      <select value={selected_goal} onChange={(e) => { setSelectedGoal(e.target.value); const g = goals.find((g) => g.id === e.target.value); if (g) setNewStatus(g.status); }}
        className="mb-2 w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none focus:border-ring focus:ring-2 focus:ring-ring/30">
        {goals.map((g) => <option key={g.id} value={g.id}>[{g.status.replace("_"," ")}] {g.description.slice(0, 60)}</option>)}
      </select>
      <div className="mb-2 flex gap-2">
        {["not_started", "in_progress", "completed"].map((s) => (
          <button key={s} onClick={() => setNewStatus(s)}
            className={`flex-1 rounded-lg border px-2 py-1.5 text-xs transition-colors ${new_status === s ? "border-primary bg-primary/5 font-medium" : "border-border hover:border-primary/50"}`}>
            {s.replace("_", " ")}
          </button>
        ))}
      </div>
      <textarea placeholder="What progress did you make?" value={progress_note} onChange={(e) => setProgressNote(e.target.value)} rows={2}
        className="mb-2 w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/30" />
      {error && <p className="mb-2 text-xs text-destructive">{error}</p>}
      <Button onClick={handle_save} disabled={saving} size="sm" className="w-full">{saving ? "Saving…" : "Update goal"}</Button>
    </div>
  );
}
