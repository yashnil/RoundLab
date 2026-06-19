import { createClient } from "@/lib/supabase";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const supabase = createClient();
  const callerSetAuth = new Headers(options?.headers).has("Authorization");

  async function send(token: string | null): Promise<Response> {
    const headers = new Headers(options?.headers);
    if (token && !callerSetAuth) headers.set("Authorization", `Bearer ${token}`);
    return fetch(`${API_BASE}${path}`, { ...options, headers });
  }

  // Attach the current Supabase access token so endpoints that authenticate the
  // caller can derive identity from the verified JWT (others ignore it).
  let token: string | null = null;
  try {
    token = (await supabase.auth.getSession()).data.session?.access_token ?? null;
  } catch {
    // No session — request proceeds unauthenticated.
  }

  let res = await send(token);

  // On a 401 with a token, the access token is likely stale: refresh the session
  // once and retry before surfacing the error.
  if (res.status === 401 && token && !callerSetAuth) {
    try {
      const refreshed = (await supabase.auth.refreshSession()).data.session?.access_token ?? null;
      if (refreshed && refreshed !== token) {
        res = await send(refreshed);
      }
    } catch {
      // Refresh failed — fall through to the original 401.
    }
  }

  if (!res.ok) {
    let message = `API error ${res.status} on ${path}`;
    try {
      const body = await res.json();
      if (body?.detail) message = String(body.detail);
    } catch {
      // response body wasn't JSON — keep the default message
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}
