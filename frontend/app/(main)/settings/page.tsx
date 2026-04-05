"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Settings, LogOut, Save } from "lucide-react";
import { get_token, get_profile, clear_auth, type UserProfile } from "@/lib/api";
import { update_profile } from "@/lib/onboarding-api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface AssessmentResult {
  id: string;
  instrument: string;
  total_score: number;
  severity: string;
  source: string;
  created_at: string;
}

async function fetch_latest_assessment(
  token: string,
  instrument: string
): Promise<AssessmentResult | null> {
  const res = await fetch(
    `${API_BASE}/api/v1/assessments/latest?instrument=${instrument}`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  );
  if (!res.ok) return null;
  return res.json() as Promise<AssessmentResult>;
}

const GRIEF_TYPE_OPTIONS = [
  { value: "loss", label: "Loss of someone" },
  { value: "breakup", label: "Breakup or divorce" },
  { value: "life_transition", label: "Life transition" },
  { value: "other", label: "Something else" },
];

const SUPPORT_SYSTEM_OPTIONS = [
  { value: "strong", label: "I have strong support" },
  { value: "some", label: "Some support" },
  { value: "none", label: "Not much support" },
];

const APPROACH_OPTIONS = [
  { value: "journaling", label: "Journaling" },
  { value: "cbt exercises", label: "CBT exercises" },
  { value: "mindfulness", label: "Mindfulness" },
  { value: "just talking", label: "Just talking" },
  { value: "guided prompts", label: "Guided prompts" },
];

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

export default function SettingsPage() {
  const router = useRouter();
  const [token, setToken] = useState("");
  const [is_checking, setIsChecking] = useState(true);
  const [is_loading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Profile fields
  const [grief_type, setGriefType] = useState("");
  const [grief_subject, setGriefSubject] = useState("");
  const [support_system, setSupportSystem] = useState("");
  const [prior_therapy, setPriorTherapy] = useState(false);
  const [preferred_approaches, setPreferredApproaches] = useState<string[]>([]);

  // Assessments (read-only)
  const [phq9, setPhq9] = useState<AssessmentResult | null>(null);
  const [gad7, setGad7] = useState<AssessmentResult | null>(null);

  const load_profile = useCallback(
    async (t: string, profile: UserProfile) => {
      setGriefType(profile.grief_type ?? "");
      setGriefSubject(profile.grief_subject ?? "");
      setSupportSystem(profile.support_system ?? "");
      setPriorTherapy(profile.prior_therapy ?? false);
      setPreferredApproaches(profile.preferred_approaches ?? []);

      // Load assessments in parallel — non-blocking
      const [phq9_data, gad7_data] = await Promise.all([
        fetch_latest_assessment(t, "phq9"),
        fetch_latest_assessment(t, "gad7"),
      ]);
      setPhq9(phq9_data);
      setGad7(gad7_data);
    },
    []
  );

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
        return load_profile(t, profile);
      })
      .catch(() => router.replace("/auth/login"))
      .finally(() => setIsChecking(false));
  }, [router, load_profile]);

  function toggle_approach(value: string) {
    setPreferredApproaches((prev) =>
      prev.includes(value) ? prev.filter((a) => a !== value) : [...prev, value]
    );
  }

  async function handle_save() {
    setIsLoading(true);
    setError("");
    setSuccess("");
    try {
      await update_profile(token, {
        grief_type: grief_type || undefined,
        grief_subject: grief_subject || undefined,
        support_system: support_system || undefined,
        prior_therapy,
        preferred_approaches,
      });
      setSuccess("Settings saved successfully.");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save settings.");
    } finally {
      setIsLoading(false);
    }
  }

  function handle_sign_out() {
    clear_auth();
    router.replace("/auth/login");
  }

  if (is_checking) return null;

  return (
    <div className="flex flex-col gap-6 p-8">
      <div className="mx-auto max-w-xl w-full">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Settings className="size-5 text-primary" />
            <h1 className="text-xl font-semibold tracking-tight">Settings</h1>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={handle_sign_out}
            className="gap-2 text-muted-foreground hover:text-destructive"
          >
            <LogOut className="size-4" />
            Sign Out
          </Button>
        </div>

        {/* Feedback banners */}
        {error && (
          <p className="mb-4 rounded-lg bg-destructive/10 px-3 py-2 text-xs text-destructive">
            {error}
          </p>
        )}
        {success && (
          <p className="mb-4 rounded-lg bg-green-500/10 px-3 py-2 text-xs text-green-700">
            {success}
          </p>
        )}

        {/* Profile form */}
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
          <h2 className="mb-5 text-sm font-semibold text-foreground">Profile &amp; Preferences</h2>

          <div className="flex flex-col gap-5">
            {/* Grief type */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-foreground">
                What brings you to EmoSync?
              </label>
              <select
                value={grief_type}
                onChange={(e) => setGriefType(e.target.value)}
                className="rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none focus:border-ring focus:ring-2 focus:ring-ring/30"
              >
                <option value="">Select…</option>
                {GRIEF_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Grief subject */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-foreground">
                Would you like to share more?{" "}
                <span className="text-muted-foreground font-normal">(optional)</span>
              </label>
              <textarea
                value={grief_subject}
                onChange={(e) => setGriefSubject(e.target.value)}
                placeholder="e.g., my grandmother, a relationship…"
                rows={2}
                className="rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/30"
              />
            </div>

            {/* Support system */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-foreground">
                Do you have people you can talk to?
              </label>
              <div className="flex flex-col gap-2">
                {SUPPORT_SYSTEM_OPTIONS.map((opt) => (
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

            {/* Prior therapy toggle */}
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-foreground">
                Have you done therapy before?
              </label>
              <button
                type="button"
                onClick={() => setPriorTherapy((v) => !v)}
                aria-pressed={prior_therapy}
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

            {/* Preferred approaches */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-foreground">
                What sounds helpful?
              </label>
              <div className="flex flex-wrap gap-2">
                {APPROACH_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => toggle_approach(opt.value)}
                    className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
                      preferred_approaches.includes(opt.value)
                        ? "border-primary bg-primary/5 font-medium"
                        : "border-border hover:border-primary/50"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-6 border-t border-border pt-5">
            <Button onClick={handle_save} disabled={is_loading} className="w-full gap-2">
              <Save className="size-4" />
              {is_loading ? "Saving…" : "Save Changes"}
            </Button>
          </div>
        </div>

        {/* Assessment scores (read-only) */}
        {(phq9 ?? gad7) && (
          <div className="mt-5 rounded-xl border border-border bg-card p-5 shadow-sm">
            <h2 className="mb-4 text-sm font-semibold text-foreground">Latest Assessment Scores</h2>
            <div className="flex flex-col gap-3">
              {phq9 && (
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-foreground">PHQ-9 (Depression)</p>
                    <p className="text-xs text-muted-foreground">
                      Score: <span className="font-semibold text-foreground">{phq9.total_score}/27</span>
                    </p>
                  </div>
                  <span
                    className={`rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${severity_badge(phq9.severity)}`}
                  >
                    {phq9.severity.replace(/_/g, " ")}
                  </span>
                </div>
              )}
              {phq9 && gad7 && <div className="border-t border-border/60" />}
              {gad7 && (
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-foreground">GAD-7 (Anxiety)</p>
                    <p className="text-xs text-muted-foreground">
                      Score: <span className="font-semibold text-foreground">{gad7.total_score}/21</span>
                    </p>
                  </div>
                  <span
                    className={`rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${severity_badge(gad7.severity)}`}
                  >
                    {gad7.severity.replace(/_/g, " ")}
                  </span>
                </div>
              )}
            </div>
            <p className="mt-3 text-xs text-muted-foreground">
              These scores are read-only. Complete a new assessment to update them.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
