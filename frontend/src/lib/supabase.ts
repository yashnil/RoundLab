import { createBrowserClient } from "@supabase/ssr";

// Call this inside Client Components to get a Supabase client with
// auth session management backed by cookies (required for App Router).
// Do not call at module level — createBrowserClient must run in the browser.
export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
}
