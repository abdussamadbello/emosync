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
