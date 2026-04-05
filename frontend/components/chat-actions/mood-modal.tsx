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
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ score, label: label || undefined, source: "check_in" }),
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
        <input type="range" min={1} max={10} value={score} onChange={(e) => setScore(Number(e.target.value))} className="w-full accent-primary" />
      </div>
      <div className="mb-3 flex flex-wrap gap-1.5">
        {EMOTION_LABELS.map((l) => (
          <button key={l} type="button" onClick={() => setLabel(label === l ? "" : l)}
            className={`rounded-full border px-2.5 py-1 text-xs transition-colors ${label === l ? "border-primary bg-primary/5 font-medium" : "border-border hover:border-primary/50"}`}>
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
