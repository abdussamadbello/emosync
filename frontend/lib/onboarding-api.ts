/**
 * API client for onboarding-related endpoints.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface ProfileUpdate {
  grief_type?: string;
  grief_subject?: string;
  grief_duration_months?: number;
  support_system?: string;
  prior_therapy?: boolean;
  preferred_approaches?: string[];
}

interface AssessmentSubmission {
  instrument: "phq9" | "gad7";
  responses: Record<string, number>;
  source: string;
}

interface AssessmentResult {
  id: string;
  instrument: string;
  total_score: number;
  severity: string;
  source: string;
  created_at: string;
}

interface MoodSubmission {
  score: number;
  label?: string;
  source: string;
}

function auth_headers(token: string): Record<string, string> {
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
}

export async function update_profile(
  token: string,
  data: ProfileUpdate
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/profile/me`, {
    method: "PUT",
    headers: auth_headers(token),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Profile update failed (${res.status})`);
}

export async function submit_assessment(
  token: string,
  data: AssessmentSubmission
): Promise<AssessmentResult> {
  const res = await fetch(`${API_BASE}/api/v1/assessments`, {
    method: "POST",
    headers: auth_headers(token),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Assessment submit failed (${res.status})`);
  return res.json() as Promise<AssessmentResult>;
}

export async function log_mood(
  token: string,
  data: MoodSubmission
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/mood`, {
    method: "POST",
    headers: auth_headers(token),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Mood log failed (${res.status})`);
}

export async function complete_onboarding(token: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/profile/complete-onboarding`, {
    method: "POST",
    headers: auth_headers(token),
  });
  if (!res.ok) throw new Error(`Complete onboarding failed (${res.status})`);
}
