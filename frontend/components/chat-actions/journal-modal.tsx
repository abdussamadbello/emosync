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
    if (!content.trim()) { setError("Content is required."); return; }
    setSaving(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/v1/journal`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          title: title || undefined, content, mood_score: mood_score ?? undefined,
          tags, source: "ai_suggested", conversation_id: conversationId || undefined,
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
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground"><X className="size-4" /></button>
      </div>
      <input type="text" placeholder="Title (optional)" value={title} onChange={(e) => setTitle(e.target.value)}
        className="mb-2 w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/30" />
      <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={4}
        className="mb-2 w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/30" />
      <div className="mb-2 flex flex-col gap-1.5">
        <label className="text-xs text-muted-foreground">Mood (optional)</label>
        <div className="flex items-center gap-2">
          <input type="range" min={1} max={10} value={mood_score ?? 5} onChange={(e) => setMoodScore(Number(e.target.value))} className="flex-1 accent-primary" />
          <span className="w-6 text-center text-sm font-medium">{mood_score ?? "—"}</span>
        </div>
      </div>
      <div className="mb-3 flex flex-wrap gap-1.5">
        {TAG_OPTIONS.map((tag) => (
          <button key={tag} type="button" onClick={() => toggle_tag(tag)}
            className={`rounded-full border px-2.5 py-1 text-xs transition-colors ${tags.includes(tag) ? "border-primary bg-primary/5 font-medium" : "border-border hover:border-primary/50"}`}>
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
