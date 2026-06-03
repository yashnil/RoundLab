import { createBrowserClient } from "@supabase/ssr";

// Call this inside Client Components to get a Supabase client with
// auth session management backed by cookies (required for App Router).
// Do not call at module level — createBrowserClient must run in the browser.
export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get(name: string) {
          // Get cookie from document.cookie in browser
          if (typeof document === 'undefined') return undefined;
          const value = `; ${document.cookie}`;
          const parts = value.split(`; ${name}=`);
          if (parts.length === 2) return parts.pop()?.split(';').shift();
          return undefined;
        },
        set(name: string, value: string, options: any) {
          // Set cookie via document.cookie in browser
          if (typeof document === 'undefined') return;
          let cookieStr = `${name}=${value}`;
          if (options?.maxAge) cookieStr += `; max-age=${options.maxAge}`;
          if (options?.path) cookieStr += `; path=${options.path}`;
          if (options?.domain) cookieStr += `; domain=${options.domain}`;
          if (options?.sameSite) cookieStr += `; samesite=${options.sameSite}`;
          if (options?.secure) cookieStr += '; secure';
          document.cookie = cookieStr;
        },
        remove(name: string, options: any) {
          // Remove cookie by setting max-age to 0
          if (typeof document === 'undefined') return;
          let cookieStr = `${name}=; max-age=0`;
          if (options?.path) cookieStr += `; path=${options.path}`;
          if (options?.domain) cookieStr += `; domain=${options.domain}`;
          document.cookie = cookieStr;
        },
      },
    }
  );
}

// Dev-only: log whether the required env vars are present and show the host.
// Removed automatically in production builds (NODE_ENV === 'production').
if (process.env.NODE_ENV === "development") {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  let host = "(not set)";
  try {
    if (url) host = new URL(url).host;
  } catch {
    host = "(invalid URL)";
  }
  console.log(
    "[supabase] NEXT_PUBLIC_SUPABASE_URL present:", !!url, "| host:", host,
  );
  console.log("[supabase] NEXT_PUBLIC_SUPABASE_ANON_KEY present:", !!key);
}
