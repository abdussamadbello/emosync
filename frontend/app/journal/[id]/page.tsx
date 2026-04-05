"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ChevronLeft, Edit2, Trash2, X, Check } from "lucide-react";
import { get_token } from "@/lib/api";
import {
  get_journal_entry,
  update_journal_entry,
  delete_journal_entry,
  type JournalEntry,
} from "@/lib/journal-api";

const TAG_OPTIONS = ["grief", "progress", "trigger", "gratitude", "reflection", "therapy"];

function mood_color(score: number | null): string {
  if (score === null) return "bg-muted text-muted-foreground";
  if (score >= 8) return "bg-green-500/10 text-green-600";
  if (score >= 5) return "bg-yellow-500/10 text-yellow-600";
  return "bg-red-500/10 text-red-600";
}

function format_date(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export default function JournalEntryPage() {
  const router = useRouter();
  const params = useParams();
  const id = params.id as string;

  const [entry, setEntry] = useState<JournalEntry | null>(null);
  const [is_loading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [token, setToken] = useState("");

  // Edit state
  const [is_editing, setIsEditing] = useState(false);
  const [edit_title, setEditTitle] = useState("");
  const [edit_content, setEditContent] = useState("");
  const [edit_mood, setEditMood] = useState<number | null>(null);
  const [edit_tags, setEditTags] = useState<string[]>([]);
  const [is_saving, setIsSaving] = useState(false);

  // Delete state
  const [show_delete_confirm, setShowDeleteConfirm] = useState(false);
  const [is_deleting, setIsDeleting] = useState(false);

  useEffect(() => {
    const t = get_token();
    if (!t) {
      router.replace("/auth/login");
      return;
    }
    setToken(t);
    load_entry(t);
  }, [id, router]);

  async function load_entry(t: string) {
    setIsLoading(true);
    setError("");
    try {
      const data = await get_journal_entry(t, id);
      setEntry(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load entry.");
    } finally {
      setIsLoading(false);
    }
  }

  function start_edit() {
    if (!entry) return;
    setEditTitle(entry.title ?? "");
    setEditContent(entry.content);
    setEditMood(entry.mood_score);
    setEditTags(entry.tags ?? []);
    setIsEditing(true);
    setError("");
  }

  function cancel_edit() {
    setIsEditing(false);
    setError("");
  }

  function toggle_tag(tag: string) {
    setEditTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  }

  async function handle_save() {
    if (!edit_content.trim()) {
      setError("Content cannot be empty.");
      return;
    }
    setIsSaving(true);
    setError("");
    try {
      const updated = await update_journal_entry(token, id, {
        title: edit_title.trim() || undefined,
        content: edit_content.trim(),
        mood_score: edit_mood ?? undefined,
        tags: edit_tags.length > 0 ? edit_tags : undefined,
      });
      setEntry(updated);
      setIsEditing(false);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save changes.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handle_delete() {
    setIsDeleting(true);
    setError("");
    try {
      await delete_journal_entry(token, id);
      router.push("/journal");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to delete entry.");
      setIsDeleting(false);
      setShowDeleteConfirm(false);
    }
  }

  if (is_loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <p className="text-sm text-muted-foreground">Loading entry…</p>
      </div>
    );
  }

  if (!entry && !is_loading) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background">
        <p className="text-sm text-muted-foreground">Entry not found.</p>
        <Button asChild variant="outline" size="sm">
          <Link href="/journal">Back to Journal</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background px-4 py-8">
      <div className="mx-auto max-w-2xl">
        {/* Back nav */}
        <div className="mb-6 flex items-center justify-between">
          <Button variant="ghost" size="sm" asChild className="text-muted-foreground">
            <Link href="/journal">
              <ChevronLeft className="mr-1 size-4" />
              Journal
            </Link>
          </Button>
          {!is_editing && (
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={start_edit} className="gap-1.5 text-muted-foreground">
                <Edit2 className="size-4" />
                Edit
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowDeleteConfirm(true)}
                className="gap-1.5 text-destructive hover:bg-destructive/10 hover:text-destructive"
              >
                <Trash2 className="size-4" />
                Delete
              </Button>
            </div>
          )}
        </div>

        {error && (
          <p className="mb-4 rounded-lg bg-destructive/10 px-3 py-2 text-xs text-destructive">
            {error}
          </p>
        )}

        {/* Delete confirmation */}
        {show_delete_confirm && (
          <div className="mb-4 rounded-xl border border-destructive/30 bg-destructive/5 p-4">
            <p className="mb-3 text-sm font-medium text-destructive">
              Delete this journal entry? This cannot be undone.
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowDeleteConfirm(false)}
                disabled={is_deleting}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handle_delete}
                disabled={is_deleting}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                {is_deleting ? "Deleting…" : "Yes, delete"}
              </Button>
            </div>
          </div>
        )}

        <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
          {!is_editing && entry ? (
            /* View mode */
            <div className="flex flex-col gap-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h1 className="text-lg font-semibold text-foreground">
                    {entry.title ?? "Untitled entry"}
                  </h1>
                  <p className="text-xs text-muted-foreground">{format_date(entry.created_at)}</p>
                </div>
                {entry.mood_score !== null && (
                  <span
                    className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${mood_color(entry.mood_score)}`}
                  >
                    Mood {entry.mood_score}/10
                  </span>
                )}
              </div>

              <div className="prose prose-sm max-w-none text-foreground/90">
                {entry.content.split("\n").map((line, i) => (
                  <p key={i} className={line === "" ? "my-2" : "my-0"}>
                    {line || "\u00A0"}
                  </p>
                ))}
              </div>

              {entry.tags && entry.tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {entry.tags.map((tag) => (
                    <span
                      key={tag}
                      className="rounded-full bg-muted px-2.5 py-0.5 text-xs text-muted-foreground"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ) : (
            /* Edit mode */
            <div className="flex flex-col gap-5">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-semibold">Edit Entry</h2>
                <button
                  onClick={cancel_edit}
                  className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                >
                  <X className="size-4" />
                </button>
              </div>

              {/* Title */}
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-foreground">
                  Title <span className="text-muted-foreground">(optional)</span>
                </label>
                <input
                  type="text"
                  value={edit_title}
                  onChange={(e) => setEditTitle(e.target.value)}
                  placeholder="Entry title…"
                  className="rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/30"
                />
              </div>

              {/* Content */}
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-foreground">Content</label>
                <textarea
                  value={edit_content}
                  onChange={(e) => setEditContent(e.target.value)}
                  rows={8}
                  className="rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/30 resize-none"
                />
              </div>

              {/* Mood */}
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium text-foreground">
                  Mood score <span className="text-muted-foreground">(optional)</span>
                </label>
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>Very low</span>
                  <span className="text-base font-semibold text-foreground">
                    {edit_mood !== null ? `${edit_mood}/10` : "—"}
                  </span>
                  <span>Very good</span>
                </div>
                <input
                  type="range"
                  min={1}
                  max={10}
                  value={edit_mood ?? 5}
                  onChange={(e) => setEditMood(Number(e.target.value))}
                  className="w-full accent-primary"
                />
                {edit_mood !== null ? (
                  <button
                    type="button"
                    onClick={() => setEditMood(null)}
                    className="self-end text-xs text-muted-foreground underline-offset-2 hover:underline"
                  >
                    Clear
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => setEditMood(5)}
                    className="self-start text-xs text-primary underline-offset-2 hover:underline"
                  >
                    Add mood score
                  </button>
                )}
              </div>

              {/* Tags */}
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-foreground">Tags</label>
                <div className="flex flex-wrap gap-2">
                  {TAG_OPTIONS.map((tag) => (
                    <button
                      key={tag}
                      type="button"
                      onClick={() => toggle_tag(tag)}
                      className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                        edit_tags.includes(tag)
                          ? "border-primary bg-primary/5 font-medium text-foreground"
                          : "border-border text-muted-foreground hover:border-primary/50"
                      }`}
                    >
                      {tag}
                    </button>
                  ))}
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-3 pt-1">
                <Button variant="outline" onClick={cancel_edit} className="flex-1" disabled={is_saving}>
                  <X className="mr-1.5 size-4" />
                  Cancel
                </Button>
                <Button onClick={handle_save} disabled={is_saving} className="flex-1">
                  <Check className="mr-1.5 size-4" />
                  {is_saving ? "Saving…" : "Save Changes"}
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
