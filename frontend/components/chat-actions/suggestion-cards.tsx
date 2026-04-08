"use client";

import { Sparkles, Target } from "lucide-react";

// ── Types ────────────────────────────────────────────────────────────────────

export interface SuggestionData {
  micro_suggestion?: {
    title: string;
    framework: "cbt" | "act" | "narrative";
    description: string;
    rationale: string;
  } | null;
  plan_generation?: {
    title: string;
    goals: { description: string; target_date: string; framework: string }[];
  } | null;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

const FRAMEWORK_LABELS: Record<string, string> = {
  cbt: "CBT",
  act: "ACT",
  narrative: "Narrative",
};

// ── Cards ────────────────────────────────────────────────────────────────────

export function MicroSuggestionCard({
  suggestion,
}: {
  suggestion: NonNullable<SuggestionData["micro_suggestion"]>;
}) {
  return (
    <div className="mt-2 max-w-[85%] rounded-xl border border-primary/20 bg-primary/5 px-4 py-3 text-sm">
      <div className="flex items-center gap-2">
        <Sparkles className="size-3.5 text-primary" />
        <span className="font-medium text-foreground">{suggestion.title}</span>
        <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wider text-primary">
          {FRAMEWORK_LABELS[suggestion.framework] ?? suggestion.framework}
        </span>
      </div>
      <p className="mt-1.5 leading-relaxed text-foreground/90">
        {suggestion.description}
      </p>
      <p className="mt-1 text-xs italic text-muted-foreground">
        {suggestion.rationale}
      </p>
    </div>
  );
}

export function PlanGeneratedCard({
  plan,
}: {
  plan: NonNullable<SuggestionData["plan_generation"]>;
}) {
  return (
    <div className="mt-2 max-w-[85%] rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3 text-sm">
      <div className="flex items-center gap-2">
        <Target className="size-3.5 text-emerald-600 dark:text-emerald-400" />
        <span className="font-medium text-foreground">{plan.title}</span>
      </div>
      <p className="mt-1 text-foreground/80">
        {plan.goals.length} goal{plan.goals.length === 1 ? "" : "s"} created
        for your healing journey
      </p>
      <ul className="mt-2 space-y-1">
        {plan.goals.map((goal, i) => (
          <li
            key={i}
            className="flex items-start gap-1.5 text-xs text-foreground/70"
          >
            <span className="mt-0.5 size-1.5 shrink-0 rounded-full bg-emerald-500/40" />
            {goal.description}
          </li>
        ))}
      </ul>
      <p className="mt-2 text-[0.65rem] text-muted-foreground">
        You can edit or remove goals anytime.
      </p>
    </div>
  );
}
