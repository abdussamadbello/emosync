const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface TreatmentGoal {
  id: string;
  plan_id: string;
  description: string;
  target_date: string | null;
  status: string;
  progress_notes: Array<{ date: string; note: string }> | null;
  created_at: string;
  updated_at: string;
}

export interface TreatmentPlan {
  id: string;
  user_id: string;
  title: string;
  status: string;
  goals: TreatmentGoal[];
  created_at: string;
  updated_at: string;
}

export interface MoodTrend {
  average: number;
  direction: string;
  count: number;
  period_days: number;
}

export interface AssessmentResult {
  id: string;
  instrument: string;
  total_score: number;
  severity: string;
  source: string;
  created_at: string;
}

function auth_headers(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

export async function list_plans(token: string): Promise<TreatmentPlan[]> {
  const res = await fetch(`${API_BASE}/api/v1/plans`, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error(`Failed to list plans (${res.status})`);
  return res.json() as Promise<TreatmentPlan[]>;
}

export async function get_plan(token: string, id: string): Promise<TreatmentPlan> {
  const res = await fetch(`${API_BASE}/api/v1/plans/${id}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error(`Failed to get plan (${res.status})`);
  return res.json() as Promise<TreatmentPlan>;
}

export async function create_plan(token: string, title: string): Promise<TreatmentPlan> {
  const res = await fetch(`${API_BASE}/api/v1/plans`, {
    method: "POST", headers: auth_headers(token), body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error(`Failed to create plan (${res.status})`);
  return res.json() as Promise<TreatmentPlan>;
}

export async function update_plan(token: string, id: string, data: { title?: string; status?: string }): Promise<TreatmentPlan> {
  const res = await fetch(`${API_BASE}/api/v1/plans/${id}`, {
    method: "PATCH", headers: auth_headers(token), body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to update plan (${res.status})`);
  return res.json() as Promise<TreatmentPlan>;
}

export async function add_goal(token: string, plan_id: string, data: { description: string; target_date?: string }): Promise<TreatmentGoal> {
  const res = await fetch(`${API_BASE}/api/v1/plans/${plan_id}/goals`, {
    method: "POST", headers: auth_headers(token), body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to add goal (${res.status})`);
  return res.json() as Promise<TreatmentGoal>;
}

export async function update_goal(token: string, goal_id: string, data: { status?: string; progress_note?: string }): Promise<TreatmentGoal> {
  const res = await fetch(`${API_BASE}/api/v1/goals/${goal_id}`, {
    method: "PATCH", headers: auth_headers(token), body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to update goal (${res.status})`);
  return res.json() as Promise<TreatmentGoal>;
}

export async function delete_goal(token: string, goal_id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/goals/${goal_id}`, {
    method: "DELETE", headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`Failed to delete goal (${res.status})`);
}

export async function get_mood_trend(token: string, days: number = 14): Promise<MoodTrend> {
  const res = await fetch(`${API_BASE}/api/v1/mood/trend?days=${days}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`Failed to get mood trend (${res.status})`);
  return res.json() as Promise<MoodTrend>;
}

export async function list_assessments(token: string): Promise<AssessmentResult[]> {
  const res = await fetch(`${API_BASE}/api/v1/assessments`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`Failed to list assessments (${res.status})`);
  return res.json() as Promise<AssessmentResult[]>;
}
