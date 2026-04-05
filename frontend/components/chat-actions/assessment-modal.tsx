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
    if (!all_answered) { setError("Please answer all questions."); return; }
    setSaving(true); setError("");
    try {
      const result = await submit_assessment(token, { instrument: "phq9", responses, source: "ai_prompted" });
      onSaved({ total_score: result.total_score, severity: result.severity });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to submit.");
    } finally { setSaving(false); }
  }

  return (
    <div className="mt-2 rounded-xl border border-border bg-card p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium"><ClipboardCheck className="size-4 text-primary" /> Quick PHQ-9 check-in</div>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground"><X className="size-4" /></button>
      </div>
      <p className="mb-3 text-xs text-muted-foreground">Over the last 2 weeks, how often have you been bothered by:</p>
      <div className="flex max-h-64 flex-col gap-2.5 overflow-y-auto pr-1">
        {PHQ9_QUESTIONS.map((q, i) => (
          <div key={i} className="flex flex-col gap-1">
            <p className="text-xs">{q}</p>
            <div className="flex gap-1">
              {ANSWER_OPTIONS.map((opt) => (
                <button key={opt.value} type="button" onClick={() => setResponses((prev) => ({ ...prev, [`q${i + 1}`]: opt.value }))}
                  className={`flex-1 rounded border px-1 py-1 text-[10px] transition-colors ${responses[`q${i + 1}`] === opt.value ? "border-primary bg-primary/10 font-medium" : "border-border hover:border-primary/50"}`}>
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
