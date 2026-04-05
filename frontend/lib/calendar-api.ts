const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface CalendarEvent {
  id: string;
  user_id: string;
  title: string;
  date: string;
  event_type: string;
  recurrence: string | null;
  notes: string | null;
  notify_agent: boolean;
  created_at: string;
  updated_at: string;
}

function auth_headers(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

export async function list_calendar_events(
  token: string,
  params?: { from_date?: string; to_date?: string; event_type?: string }
): Promise<CalendarEvent[]> {
  const url = new URL(`${API_BASE}/api/v1/calendar`);
  if (params?.from_date) url.searchParams.set("from_date", params.from_date);
  if (params?.to_date) url.searchParams.set("to_date", params.to_date);
  if (params?.event_type) url.searchParams.set("event_type", params.event_type);
  const res = await fetch(url.toString(), { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error(`Failed to list events (${res.status})`);
  return res.json() as Promise<CalendarEvent[]>;
}

export async function create_calendar_event(
  token: string,
  data: {
    title: string;
    date: string;
    event_type: string;
    recurrence?: string;
    notes?: string;
    notify_agent?: boolean;
  }
): Promise<CalendarEvent> {
  const res = await fetch(`${API_BASE}/api/v1/calendar`, {
    method: "POST",
    headers: auth_headers(token),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to create event (${res.status})`);
  return res.json() as Promise<CalendarEvent>;
}

export async function update_calendar_event(
  token: string,
  id: string,
  data: {
    title?: string;
    date?: string;
    event_type?: string;
    recurrence?: string;
    notes?: string;
    notify_agent?: boolean;
  }
): Promise<CalendarEvent> {
  const res = await fetch(`${API_BASE}/api/v1/calendar/${id}`, {
    method: "PATCH",
    headers: auth_headers(token),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to update event (${res.status})`);
  return res.json() as Promise<CalendarEvent>;
}

export async function delete_calendar_event(token: string, id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/calendar/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`Failed to delete event (${res.status})`);
}
