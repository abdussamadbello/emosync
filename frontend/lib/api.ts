/**
 * Base URL for all backend API requests.
 * Override with NEXT_PUBLIC_API_URL in .env.local for non-localhost setups.
 */
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Shape returned by /auth/register and /auth/login */
export interface TokenResponse {
  access_token: string;
  token_type: string;
}

/** Shape of a backend error response body */
interface ApiError {
  detail?: string;
  message?: string;
  code?: string;
}

/**
 * Calls the backend register endpoint and returns the token response.
 * Throws a human-readable Error on failure.
 */
export async function register_user(
  email: string,
  password: string,
  display_name: string
): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, display_name }),
  });

  if (!res.ok) {
    const body: ApiError = await res.json().catch(() => ({}));
    const msg =
      body.detail ??
      body.message ??
      `Registration failed (${res.status})`;
    throw new Error(msg);
  }

  return res.json() as Promise<TokenResponse>;
}

/** Shape returned by /auth/me */
export interface UserOut {
  id: string;
  email: string;
  display_name: string | null;
  created_at: string;
}

/**
 * Calls the backend login endpoint and returns the token response.
 * Throws a human-readable Error on failure.
 */
export async function login_user(
  email: string,
  password: string
): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const body: ApiError = await res.json().catch(() => ({}));
    const msg =
      body.detail ??
      body.message ??
      `Login failed (${res.status})`;
    throw new Error(msg);
  }

  return res.json() as Promise<TokenResponse>;
}

/**
 * Fetches the current user profile using the given JWT.
 * Throws a human-readable Error on failure.
 */
export async function get_current_user(token: string): Promise<UserOut> {
  const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch user profile (${res.status})`);
  }

  return res.json() as Promise<UserOut>;
}

/**
 * Persists the JWT access token in localStorage under "emosync_token".
 */
export function save_token(token: string): void {
  localStorage.setItem("emosync_token", token);
}

/**
 * Retrieves the stored JWT access token, or null if absent.
 */
export function get_token(): string | null {
  return localStorage.getItem("emosync_token");
}

/**
 * Removes the stored JWT access token (logout helper).
 */
export function clear_token(): void {
  localStorage.removeItem("emosync_token");
}

/**
 * Persists the user's display name in localStorage under "emosync_display_name".
 */
export function save_display_name(name: string): void {
  localStorage.setItem("emosync_display_name", name);
}

/**
 * Retrieves the stored display name, or null if absent.
 */
export function get_display_name(): string | null {
  return localStorage.getItem("emosync_display_name");
}

/**
 * Clears all auth-related data from localStorage.
 */
export function clear_auth(): void {
  localStorage.removeItem("emosync_token");
  localStorage.removeItem("emosync_display_name");
}

// ---------------------------------------------------------------------------
// Chat API
// ---------------------------------------------------------------------------

/** Shape of a conversation returned by the backend */
export interface ConversationOut {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

/** Shape of a message returned by the backend */
export interface MessageOut {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

/**
 * Creates a new conversation for the authenticated user.
 * Returns the conversation including its id.
 */
export async function create_conversation(
  token: string,
  title?: string
): Promise<ConversationOut> {
  const res = await fetch(`${API_BASE}/api/v1/conversations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ title: title ?? null }),
  });

  if (!res.ok) {
    const body: ApiError = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Failed to create conversation (${res.status})`);
  }

  return res.json() as Promise<ConversationOut>;
}

/**
 * Fetches all conversations for the authenticated user, newest first.
 */
export async function list_conversations(
  token: string
): Promise<ConversationOut[]> {
  const res = await fetch(`${API_BASE}/api/v1/conversations`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    const body: ApiError = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Failed to fetch conversations (${res.status})`);
  }

  return res.json() as Promise<ConversationOut[]>;
}

/**
 * Fetches all messages for a given conversation, oldest first.
 */
export async function list_messages(
  token: string,
  conversation_id: string
): Promise<MessageOut[]> {
  const res = await fetch(
    `${API_BASE}/api/v1/conversations/${conversation_id}/messages`,
    { headers: { Authorization: `Bearer ${token}` } }
  );

  if (!res.ok) {
    const body: ApiError = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Failed to fetch messages (${res.status})`);
  }

  return res.json() as Promise<MessageOut[]>;
}

/**
 * Opens an SSE stream for a chat turn.
 * Returns the raw Response so the caller can read the body as a stream.
 * Throws if the request itself fails (non-2xx before the stream starts).
 */
export async function stream_message(
  token: string,
  conversation_id: string,
  content: string
): Promise<Response> {
  const res = await fetch(
    `${API_BASE}/api/v1/conversations/${conversation_id}/messages/stream`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ content }),
    }
  );

  if (!res.ok) {
    const body: ApiError = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Stream request failed (${res.status})`);
  }

  return res;
}
