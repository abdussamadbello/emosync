"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ChevronRight, ChevronLeft, Sparkles } from "lucide-react";
import { get_token, get_profile } from "@/lib/api";
import {
  update_profile,
  submit_assessment,
  log_mood,
  complete_onboarding,
} from "@/lib/onboarding-api";

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

const GAD7_QUESTIONS = [
  "Feeling nervous, anxious, or on edge",
  "Not being able to stop or control worrying",
  "Worrying too much about different things",
  "Trouble relaxing",
  "Being so restless that it's hard to sit still",
  "Becoming easily annoyed or irritable",
  "Feeling afraid, as if something awful might happen",
];

const ANSWER_OPTIONS = [
  { value: 0, label: "Not at all" },
  { value: 1, label: "Several days" },
  { value: 2, label: "More than half the days" },
  { value: 3, label: "Nearly every day" },
];

const EMOTION_LABELS = [
  "anxious",
  "sad",
  "numb",
  "hopeful",
  "calm",
  "angry",
  "other",
];

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [is_loading, setIsLoading] = useState(false);
  const [is_checking, setIsChecking] = useState(true);
  const [error, setError] = useState("");
  const [token, setToken] = useState("");

  const [grief_type, setGriefType] = useState("");
  const [grief_subject, setGriefSubject] = useState("");
  const [grief_duration, setGriefDuration] = useState<number | null>(null);

  const [support_system, setSupportSystem] = useState("");
  const [prior_therapy, setPriorTherapy] = useState(false);
  const [preferred_approaches, setPreferredApproaches] = useState<string[]>([]);

  const [phq9_responses, setPhq9Responses] = useState<Record<string, number>>({});
  const [gad7_responses, setGad7Responses] = useState<Record<string, number>>({});
  const [phq9_result, setPhq9Result] = useState<{ total_score: number; severity: string } | null>(null);
  const [gad7_result, setGad7Result] = useState<{ total_score: number; severity: string } | null>(null);

  const [mood_score, setMoodScore] = useState(5);
  const [mood_label, setMoodLabel] = useState("");

  useEffect(() => {
    const t = get_token();
    if (!t) {
      router.replace("/auth/login");
      return;
    }
    setToken(t);
    get_profile(t)
      .then((profile) => {
        if (profile.onboarding_completed) {
          router.replace("/");
        } else {
          setIsChecking(false);
        }
      })
      .catch(() => {
        router.replace("/auth/login");
      });
  }, [router]);

  if (is_checking) return null;

  async function handle_step1_next() {
    if (!grief_type) {
      setError("Please select what brings you here.");
      return;
    }
    setIsLoading(true);
    setError("");
    try {
      await update_profile(token, {
        grief_type,
        grief_subject: grief_subject || undefined,
        grief_duration_months: grief_duration ?? undefined,
      });
      setStep(2);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handle_step2_next() {
    if (!support_system) {
      setError("Please select your support level.");
      return;
    }
    setIsLoading(true);
    setError("");
    try {
      await update_profile(token, {
        support_system,
        prior_therapy,
        preferred_approaches,
      });
      setStep(3);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handle_step3_next() {
    const phq9_complete = PHQ9_QUESTIONS.every((_, i) => `q${i + 1}` in phq9_responses);
    const gad7_complete = GAD7_QUESTIONS.every((_, i) => `q${i + 1}` in gad7_responses);
    if (!phq9_complete || !gad7_complete) {
      setError("Please answer all questions before continuing.");
      return;
    }
    setIsLoading(true);
    setError("");
    try {
      const [phq9, gad7] = await Promise.all([
        submit_assessment(token, {
          instrument: "phq9",
          responses: phq9_responses,
          source: "onboarding",
        }),
        submit_assessment(token, {
          instrument: "gad7",
          responses: gad7_responses,
          source: "onboarding",
        }),
      ]);
      setPhq9Result({ total_score: phq9.total_score, severity: phq9.severity });
      setGad7Result({ total_score: gad7.total_score, severity: gad7.severity });
      setStep(4);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to submit assessments.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handle_finish() {
    setIsLoading(true);
    setError("");
    try {
      await log_mood(token, {
        score: mood_score,
        label: mood_label || undefined,
        source: "onboarding",
      });
      await complete_onboarding(token);
      router.push("/");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to complete onboarding.");
    } finally {
      setIsLoading(false);
    }
  }

  function toggle_approach(approach: string) {
    setPreferredApproaches((prev) =>
      prev.includes(approach)
        ? prev.filter((a) => a !== approach)
        : [...prev, approach]
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-lg">
        <div className="mb-8 flex flex-col items-center gap-3">
          <Link href="/" className="flex items-center gap-2.5">
            <Image src="/logo.png" alt="EmoSync" width={36} height={36} className="rounded-sm" />
            <span className="text-xl font-semibold tracking-tight">EmoSync</span>
          </Link>
          <p className="text-sm text-muted-foreground">Step {step} of 4</p>
          <div className="flex w-full max-w-xs gap-1.5">
            {[1, 2, 3, 4].map((s) => (
              <div
                key={s}
                className={`h-1.5 flex-1 rounded-full transition-colors ${
                  s <= step ? "bg-primary" : "bg-muted"
                }`}
              />
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
          {error && (
            <p className="mb-4 rounded-lg bg-destructive/10 px-3 py-2 text-xs text-destructive">
              {error}
            </p>
          )}

          {step === 1 && (
            <div className="flex flex-col gap-5">
              <div>
                <h2 className="text-lg font-semibold">What brings you to EmoSync?</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  This helps us understand how to support you best.
                </p>
              </div>
              <div className="flex flex-col gap-2">
                {[
                  { value: "loss", label: "Loss of someone" },
                  { value: "breakup", label: "Breakup or divorce" },
                  { value: "life_transition", label: "Life transition" },
                  { value: "other", label: "Something else" },
                ].map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setGriefType(opt.value)}
                    className={`rounded-lg border px-4 py-3 text-left text-sm transition-colors ${
                      grief_type === opt.value
                        ? "border-primary bg-primary/5 font-medium"
                        : "border-border hover:border-primary/50"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-foreground">
                  Would you like to share more? <span className="text-muted-foreground">(optional)</span>
                </label>
                <textarea
                  value={grief_subject}
                  onChange={(e) => setGriefSubject(e.target.value)}
                  placeholder="e.g., my grandmother, a relationship..."
                  rows={2}
                  className="rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/30"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-foreground">
                  How long ago? <span className="text-muted-foreground">(optional)</span>
                </label>
                <div className="flex flex-wrap gap-2">
                  {[
                    { value: 0, label: "Less than 1 month" },
                    { value: 2, label: "1–3 months" },
                    { value: 5, label: "3–6 months" },
                    { value: 9, label: "6–12 months" },
                    { value: 18, label: "1–2 years" },
                    { value: 30, label: "2+ years" },
                  ].map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => setGriefDuration(opt.value)}
                      className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                        grief_duration === opt.value
                          ? "border-primary bg-primary/5 font-medium"
                          : "border-border hover:border-primary/50"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
              <Button onClick={handle_step1_next} disabled={is_loading} className="w-full">
                {is_loading ? "Saving…" : "Continue"}
                {!is_loading && <ChevronRight className="ml-1 size-4" />}
              </Button>
            </div>
          )}

          {step === 2 && (
            <div className="flex flex-col gap-5">
              <div>
                <h2 className="text-lg font-semibold">Your support & preferences</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  We&apos;ll tailor our approach to what works for you.
                </p>
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium">Do you have people you can talk to?</label>
                <div className="flex flex-col gap-2">
                  {[
                    { value: "strong", label: "I have strong support" },
                    { value: "some", label: "Some support" },
                    { value: "none", label: "Not much support" },
                  ].map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => setSupportSystem(opt.value)}
                      className={`rounded-lg border px-4 py-3 text-left text-sm transition-colors ${
                        support_system === opt.value
                          ? "border-primary bg-primary/5 font-medium"
                          : "border-border hover:border-primary/50"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Have you done therapy before?</label>
                <button
                  type="button"
                  onClick={() => setPriorTherapy(!prior_therapy)}
                  className={`relative h-6 w-11 rounded-full transition-colors ${
                    prior_therapy ? "bg-primary" : "bg-muted"
                  }`}
                >
                  <span
                    className={`absolute left-0.5 top-0.5 size-5 rounded-full bg-white transition-transform ${
                      prior_therapy ? "translate-x-5" : ""
                    }`}
                  />
                </button>
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium">What sounds helpful?</label>
                <div className="flex flex-wrap gap-2">
                  {["Journaling", "CBT exercises", "Mindfulness", "Just talking", "Guided prompts"].map(
                    (approach) => (
                      <button
                        key={approach}
                        type="button"
                        onClick={() => toggle_approach(approach.toLowerCase())}
                        className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
                          preferred_approaches.includes(approach.toLowerCase())
                            ? "border-primary bg-primary/5 font-medium"
                            : "border-border hover:border-primary/50"
                        }`}
                      >
                        {approach}
                      </button>
                    )
                  )}
                </div>
              </div>
              <div className="flex gap-3">
                <Button variant="outline" onClick={() => setStep(1)} className="flex-1">
                  <ChevronLeft className="mr-1 size-4" /> Back
                </Button>
                <Button onClick={handle_step2_next} disabled={is_loading} className="flex-1">
                  {is_loading ? "Saving…" : "Continue"}
                  {!is_loading && <ChevronRight className="ml-1 size-4" />}
                </Button>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="flex flex-col gap-5">
              <div>
                <h2 className="text-lg font-semibold">Quick check-in</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Over the last 2 weeks, how often have you been bothered by the following?
                </p>
              </div>
              <div className="flex flex-col gap-3">
                <h3 className="text-sm font-medium text-muted-foreground">Part 1 of 2 — Mood</h3>
                {PHQ9_QUESTIONS.map((q, i) => (
                  <div key={`phq9-${i}`} className="flex flex-col gap-1.5">
                    <p className="text-sm">{q}</p>
                    <div className="flex gap-1">
                      {ANSWER_OPTIONS.map((opt) => (
                        <button
                          key={opt.value}
                          type="button"
                          onClick={() =>
                            setPhq9Responses((prev) => ({ ...prev, [`q${i + 1}`]: opt.value }))
                          }
                          className={`flex-1 rounded border px-1 py-1.5 text-xs transition-colors ${
                            phq9_responses[`q${i + 1}`] === opt.value
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
              <div className="flex flex-col gap-3">
                <h3 className="text-sm font-medium text-muted-foreground">Part 2 of 2 — Anxiety</h3>
                {GAD7_QUESTIONS.map((q, i) => (
                  <div key={`gad7-${i}`} className="flex flex-col gap-1.5">
                    <p className="text-sm">{q}</p>
                    <div className="flex gap-1">
                      {ANSWER_OPTIONS.map((opt) => (
                        <button
                          key={opt.value}
                          type="button"
                          onClick={() =>
                            setGad7Responses((prev) => ({ ...prev, [`q${i + 1}`]: opt.value }))
                          }
                          className={`flex-1 rounded border px-1 py-1.5 text-xs transition-colors ${
                            gad7_responses[`q${i + 1}`] === opt.value
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
              <div className="flex gap-3">
                <Button variant="outline" onClick={() => setStep(2)} className="flex-1">
                  <ChevronLeft className="mr-1 size-4" /> Back
                </Button>
                <Button onClick={handle_step3_next} disabled={is_loading} className="flex-1">
                  {is_loading ? "Submitting…" : "Continue"}
                  {!is_loading && <ChevronRight className="ml-1 size-4" />}
                </Button>
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="flex flex-col gap-5">
              <div>
                <h2 className="text-lg font-semibold">How are you feeling right now?</h2>
                <p className="mt-1 text-sm text-muted-foreground">One last check before we begin.</p>
              </div>
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>Very low</span>
                  <span className="text-lg font-semibold text-foreground">{mood_score}</span>
                  <span>Very good</span>
                </div>
                <input
                  type="range"
                  min={1}
                  max={10}
                  value={mood_score}
                  onChange={(e) => setMoodScore(Number(e.target.value))}
                  className="w-full accent-primary"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium">
                  What word fits? <span className="text-muted-foreground">(optional)</span>
                </label>
                <div className="flex flex-wrap gap-2">
                  {EMOTION_LABELS.map((label) => (
                    <button
                      key={label}
                      type="button"
                      onClick={() => setMoodLabel(mood_label === label ? "" : label)}
                      className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                        mood_label === label
                          ? "border-primary bg-primary/5 font-medium"
                          : "border-border hover:border-primary/50"
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="rounded-lg bg-muted/50 p-4 text-sm">
                <h3 className="mb-2 font-medium">Here&apos;s what I know about you</h3>
                <ul className="flex flex-col gap-1 text-muted-foreground">
                  <li>Reason: <span className="text-foreground">{grief_type.replace("_", " ")}</span></li>
                  <li>Support: <span className="text-foreground">{support_system}</span></li>
                  {phq9_result && (
                    <li>
                      PHQ-9: <span className="text-foreground">{phq9_result.total_score}/27 ({phq9_result.severity.replace("_", " ")})</span>
                    </li>
                  )}
                  {gad7_result && (
                    <li>
                      GAD-7: <span className="text-foreground">{gad7_result.total_score}/21 ({gad7_result.severity})</span>
                    </li>
                  )}
                </ul>
              </div>
              <div className="flex gap-3">
                <Button variant="outline" onClick={() => setStep(3)} className="flex-1">
                  <ChevronLeft className="mr-1 size-4" /> Back
                </Button>
                <Button onClick={handle_finish} disabled={is_loading} className="flex-1">
                  {is_loading ? (
                    <span className="flex items-center gap-2">
                      <Sparkles className="size-4 animate-spin" />
                      Starting…
                    </span>
                  ) : (
                    "Start your first conversation"
                  )}
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
