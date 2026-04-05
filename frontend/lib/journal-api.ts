const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface JournalEntry {
  id: string;
  user_id: string;
  title: string | null;
  content: string;
  mood_score: number | null;
  tags: string[] | null;
  source: string;
  conversation_id: string | null;
  created_at: string;
  updated_at: string;
}

function auth_headers(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

export async function list_journal_entries(
  token: string,
  params?: { tag?: string }
): Promise<JournalEntry[]> {
  const url = new URL(`${API_BASE}/api/v1/journal`);
  if (params?.tag) url.searchParams.set("tag", params.tag);
  const res = await fetch(url.toString(), { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error(`Failed to list journal entries (${res.status})`);
  return res.json() as Promise<JournalEntry[]>;
}

export async function get_journal_entry(token: string, id: string): Promise<JournalEntry> {
  const res = await fetch(`${API_BASE}/api/v1/journal/${id}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`Failed to get journal entry (${res.status})`);
  return res.json() as Promise<JournalEntry>;
}

export async function create_journal_entry(
  token: string,
  data: { content: string; title?: string; mood_score?: number; tags?: string[] }
): Promise<JournalEntry> {
  const res = await fetch(`${API_BASE}/api/v1/journal`, {
    method: "POST",
    headers: auth_headers(token),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to create journal entry (${res.status})`);
  return res.json() as Promise<JournalEntry>;
}

export async function update_journal_entry(
  token: string,
  id: string,
  data: { content?: string; title?: string; mood_score?: number; tags?: string[] }
): Promise<JournalEntry> {
  const res = await fetch(`${API_BASE}/api/v1/journal/${id}`, {
    method: "PATCH",
    headers: auth_headers(token),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to update journal entry (${res.status})`);
  return res.json() as Promise<JournalEntry>;
}

export async function delete_journal_entry(token: string, id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/journal/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`Failed to delete journal entry (${res.status})`);
}
