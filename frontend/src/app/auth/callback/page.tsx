"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase";

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        const code = searchParams.get("code");
        const errorParam = searchParams.get("error");
        const errorDescription = searchParams.get("error_description");

        // Handle OAuth errors from Supabase
        if (errorParam) {
          console.error("OAuth error from Supabase:", errorParam, errorDescription);
          setError(errorDescription || "Authentication failed");
          setTimeout(() => router.replace("/login?error=oauth_failed"), 2000);
          return;
        }

        if (!code) {
          console.error("No code in OAuth callback");
          router.replace("/login?error=oauth_callback_failed");
          return;
        }

        const supabase = createClient();

        // Exchange the code for a session
        const { data, error: exchangeError } = await supabase.auth.exchangeCodeForSession(code);

        if (exchangeError) {
          console.error("Code exchange error:", exchangeError);
          // Check if it's a PKCE-specific error
          if (exchangeError.message?.includes("code verifier")) {
            router.replace("/login?error=pkce_failed");
          } else {
            router.replace("/login?error=oauth_callback_failed");
          }
          return;
        }

        if (!data?.session) {
          console.error("No session after code exchange");
          router.replace("/login?error=oauth_callback_failed");
          return;
        }

        // Success - session is now stored in cookies
        router.replace("/dashboard");
      } catch (err) {
        console.error("Unexpected callback error:", err);
        setError("An unexpected error occurred during sign-in.");
        setTimeout(() => router.replace("/login?error=oauth_callback_failed"), 2000);
      }
    };

    handleCallback();
  }, [router, searchParams]);

  return (
    <div className="flex flex-col items-center gap-4">
      {error ? (
        <>
          <p className="text-sm text-danger">{error}</p>
          <p className="text-xs text-ink-faint">Redirecting to login...</p>
        </>
      ) : (
        <>
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-lav border-t-transparent" />
          <p className="text-sm text-ink-subtle">Completing sign-in...</p>
        </>
      )}
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-canvas px-4">
      <Suspense fallback={
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-lav border-t-transparent" />
          <p className="text-sm text-ink-subtle">Loading...</p>
        </div>
      }>
        <AuthCallbackContent />
      </Suspense>
    </main>
  );
}
