"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ChevronLeft } from "lucide-react";
import { get_token, get_profile } from "@/lib/api";
import { create_journal_entry } from "@/lib/journal-api";

const TAG_OPTIONS = ["grief", "progress", "trigger", "gratitude", "reflection", "therapy"];

export default function NewJournalEntryPage() {
  const router = useRouter();
  const [token, setToken] = useState("");
  const [is_checking, setIsChecking] = useState(true);
  const [is_saving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [mood_score, setMoodScore] = useState<number | null>(null);
  const [selected_tags, setSelectedTags] = useState<string[]>([]);

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
        setIsChecking(false);
      })
      .catch(() => router.replace("/auth/login"));
  }, [router]);

  function toggle_tag(tag: string) {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  }

  async function handle_save() {
    if (!content.trim()) {
      setError("Content is required.");
      return;
    }
    setIsSaving(true);
    setError("");
    try {
      await create_journal_entry(token, {
        content: content.trim(),
        title: title.trim() || undefined,
        mood_score: mood_score ?? undefined,
        tags: selected_tags.length > 0 ? selected_tags : undefined,
      });
      router.push("/journal");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save entry.");
    } finally {
      setIsSaving(false);
    }
  }

  if (is_checking) return null;

  return (
    <div className="flex flex-col gap-6 p-8">
      <div className="mx-auto max-w-2xl w-full">
        {/* Back nav */}
        <div className="mb-6">
          <Button variant="ghost" size="sm" asChild className="text-muted-foreground">
            <Link href="/journal">
              <ChevronLeft className="mr-1 size-4" />
              Back to Journal
            </Link>
          </Button>
        </div>

        <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
          <h1 className="mb-5 text-lg font-semibold">New Journal Entry</h1>

          {error && (
            <p className="mb-4 rounded-lg bg-destructive/10 px-3 py-2 text-xs text-destructive">
              {error}
            </p>
          )}

          <div className="flex flex-col gap-5">
            {/* Title */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-foreground">
                Title <span className="text-muted-foreground">(optional)</span>
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Give this entry a title…"
                className="rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/30"
              />
            </div>

            {/* Content */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-foreground">
                What&apos;s on your mind? <span className="text-destructive">*</span>
              </label>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Write freely — this is just for you…"
                rows={8}
                className="rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/30 resize-none"
              />
            </div>

            {/* Mood score */}
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium text-foreground">
                Mood score <span className="text-muted-foreground">(optional)</span>
              </label>
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Very low</span>
                <span className="text-base font-semibold text-foreground">
                  {mood_score !== null ? `${mood_score}/10` : "—"}
                </span>
                <span>Very good</span>
              </div>
              <input
                type="range"
                min={1}
                max={10}
                value={mood_score ?? 5}
                onChange={(e) => setMoodScore(Number(e.target.value))}
                className="w-full accent-primary"
              />
              {mood_score !== null && (
                <button
                  type="button"
                  onClick={() => setMoodScore(null)}
                  className="self-end text-xs text-muted-foreground underline-offset-2 hover:underline"
                >
                  Clear
                </button>
              )}
              {mood_score === null && (
                <button
                  type="button"
                  onClick={() => setMoodScore(5)}
                  className="self-start text-xs text-primary underline-offset-2 hover:underline"
                >
                  Add mood score
                </button>
              )}
            </div>

            {/* Tags */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-foreground">
                Tags <span className="text-muted-foreground">(optional)</span>
              </label>
              <div className="flex flex-wrap gap-2">
                {TAG_OPTIONS.map((tag) => (
                  <button
                    key={tag}
                    type="button"
                    onClick={() => toggle_tag(tag)}
                    className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                      selected_tags.includes(tag)
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
              <Button variant="outline" asChild className="flex-1">
                <Link href="/journal">Cancel</Link>
              </Button>
              <Button onClick={handle_save} disabled={is_saving} className="flex-1">
                {is_saving ? "Saving…" : "Save Entry"}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
