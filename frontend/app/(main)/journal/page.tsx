"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Plus, BookOpen, Tag } from "lucide-react";
import { get_token, get_profile } from "@/lib/api";
import { list_journal_entries, type JournalEntry } from "@/lib/journal-api";

function mood_color(score: number | null): string {
  if (score === null) return "bg-muted text-muted-foreground";
  if (score >= 8) return "bg-green-500/10 text-green-600";
  if (score >= 5) return "bg-yellow-500/10 text-yellow-600";
  return "bg-red-500/10 text-red-600";
}

function format_date(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function JournalPage() {
  const router = useRouter();
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [is_loading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [token, setToken] = useState("");
  const [active_tag, setActiveTag] = useState<string | null>(null);

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
        return fetch_entries(t, null);
      })
      .catch(() => router.replace("/auth/login"));
  }, [router]);

  async function fetch_entries(t: string, tag: string | null) {
    setIsLoading(true);
    setError("");
    try {
      const data = await list_journal_entries(t, tag ? { tag } : undefined);
      data.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
      setEntries(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load journal entries.");
    } finally {
      setIsLoading(false);
    }
  }

  function handle_tag_filter(tag: string | null) {
    setActiveTag(tag);
    if (token) fetch_entries(token, tag);
  }

  const all_tags = Array.from(
    new Set(entries.flatMap((e) => e.tags ?? []))
  ).sort();

  if (is_loading && entries.length === 0) {
    return (
      <div className="flex items-center justify-center p-8">
        <p className="text-sm text-muted-foreground">Loading journal…</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8 p-8">
      <div className="mx-auto max-w-2xl w-full">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <BookOpen className="size-5 text-primary" />
            <h1 className="text-2xl font-semibold tracking-tight">Journal</h1>
          </div>
          <Button asChild size="sm">
            <Link href="/journal/new">
              <Plus className="mr-1.5 size-4" />
              New Entry
            </Link>
          </Button>
        </div>

        {/* Tag filter */}
        {all_tags.length > 0 && (
          <div className="mb-5 flex flex-wrap gap-2">
            <button
              onClick={() => handle_tag_filter(null)}
              className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                active_tag === null
                  ? "border-primary bg-primary/5 font-medium text-foreground"
                  : "border-border text-muted-foreground hover:border-primary/50"
              }`}
            >
              All
            </button>
            {all_tags.map((tag) => (
              <button
                key={tag}
                onClick={() => handle_tag_filter(tag)}
                className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                  active_tag === tag
                    ? "border-primary bg-primary/5 font-medium text-foreground"
                    : "border-border text-muted-foreground hover:border-primary/50"
                }`}
              >
                {tag}
              </button>
            ))}
          </div>
        )}

        {error && (
          <p className="mb-4 rounded-lg bg-destructive/10 px-3 py-2 text-xs text-destructive">
            {error}
          </p>
        )}

        {/* Entry list */}
        {entries.length === 0 && !is_loading ? (
          <div className="rounded-2xl border border-border bg-card p-10 text-center">
            <BookOpen className="mx-auto mb-3 size-8 text-muted-foreground/40" />
            <p className="text-[0.9375rem] font-medium text-muted-foreground">No journal entries yet</p>
            <p className="mt-1.5 text-sm text-muted-foreground">
              Writing about your feelings can help process grief.
            </p>
            <Button asChild className="mt-4" size="sm">
              <Link href="/journal/new">Write your first entry</Link>
            </Button>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {entries.map((entry) => (
              <Link key={entry.id} href={`/journal/${entry.id}`}>
                <div className="rounded-2xl border border-border bg-card p-5 shadow-sm transition-colors hover:border-primary/40 hover:bg-card/80">
                  <div className="mb-2.5 flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[0.9375rem] font-medium text-foreground">
                        {entry.title ?? "Untitled entry"}
                      </p>
                      <p className="text-xs text-muted-foreground">{format_date(entry.created_at)}</p>
                    </div>
                    {entry.mood_score !== null && (
                      <span
                        className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${mood_color(entry.mood_score)}`}
                      >
                        Mood {entry.mood_score}/10
                      </span>
                    )}
                  </div>
                  <p className="line-clamp-3 text-sm text-muted-foreground leading-relaxed">
                    {entry.content.slice(0, 150)}
                    {entry.content.length > 150 ? "…" : ""}
                  </p>
                  {entry.tags && entry.tags.length > 0 && (
                    <div className="mt-3 flex flex-wrap items-center gap-1.5">
                      <Tag className="size-3 text-muted-foreground/60" />
                      {entry.tags.map((tag) => (
                        <span
                          key={tag}
                          className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
