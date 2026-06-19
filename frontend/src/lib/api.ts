import { createClient } from "@/lib/supabase";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  // Attach the Supabase access token so endpoints that authenticate the caller
  // can derive identity from the verified JWT (others simply ignore it).
  const headers = new Headers(options?.headers);
  try {
    const { data } = await createClient().auth.getSession();
    const token = data.session?.access_token;
    if (token && !headers.has("Authorization")) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  } catch {
    // No session available — the request proceeds unauthenticated.
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
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
