"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Mic } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { createClient } from "@/lib/supabase";

type Mode = "signin" | "signup";

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [mode, setMode] = useState<Mode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  // Check for OAuth callback errors
  useEffect(() => {
    const oauthError = searchParams.get("error");
    if (oauthError === "oauth_callback_failed") {
      setError("Google sign-in did not complete. Please try again.");
    } else if (oauthError === "pkce_failed") {
      setError("Google sign-in failed (browser issue). Try email/password or a different browser.");
    } else if (oauthError === "oauth_failed") {
      setError("Google sign-in was cancelled or denied.");
    }
  }, [searchParams]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(""); setNotice(""); setLoading(true);
    const sb = createClient();
    try {
      if (mode === "signin") {
        const { error } = await sb.auth.signInWithPassword({ email, password });
        if (error) setError(error.message);
        else { router.push("/dashboard"); router.refresh(); }
      } else {
        const { error } = await sb.auth.signUp({ email, password });
        if (error) setError(error.message);
        else setNotice("Check your email for a confirmation link, then sign in.");
      }
    } catch (err) {
      setError(err instanceof TypeError
        ? "Could not reach Supabase. Check frontend/.env.local."
        : "An unexpected error occurred.");
    } finally { setLoading(false); }
  }

  function toggleMode() {
    setMode((m) => (m === "signin" ? "signup" : "signin"));
    setError(""); setNotice("");
  }

  async function handleGoogleSignIn() {
    setError(""); setNotice(""); setGoogleLoading(true);
    const sb = createClient();
    try {
      const { data, error } = await sb.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: `${window.location.origin}/auth/callback`,
          // Use PKCE flow (default for @supabase/ssr)
          // queryParams: {
          //   access_type: 'offline',
          //   prompt: 'consent',
          // },
        },
      });
      if (error) {
        setError(error.message);
        setGoogleLoading(false);
      }
      // If successful (data.url exists), user will be redirected to Google OAuth
      // Don't set googleLoading to false here - user is being redirected
    } catch (err) {
      setError(err instanceof TypeError
        ? "Could not reach Supabase. Check frontend/.env.local."
        : "An unexpected error occurred.");
      setGoogleLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-canvas px-4">
      <div className="w-full max-w-sm">

        {/* Brand */}
        <div className="mb-8 flex flex-col items-center gap-3 text-center">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-lav">
            <Mic size={16} className="text-white" />
          </div>
          <div className="flex flex-col gap-1">
            <h1 className="text-title text-ink">RoundLab</h1>
            <p className="text-sm text-ink-subtle">AI flow coach for Public Forum debaters</p>
          </div>
        </div>

        {/* Form card */}
        <Card>
          <CardContent className="px-5 py-5">
            <p className="mb-5 text-sm font-medium text-ink-muted">
              {mode === "signin" ? "Sign in to your account" : "Create an account"}
            </p>

            {/* Google sign-in */}
            <Button
              type="button"
              variant="secondary"
              onClick={handleGoogleSignIn}
              disabled={loading || googleLoading}
              className="mb-4 w-full gap-2"
            >
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M17.64 9.20443C17.64 8.56625 17.5827 7.95262 17.4764 7.36353H9V10.8449H13.8436C13.635 11.9699 13.0009 12.9231 12.0477 13.5613V15.8194H14.9564C16.6582 14.2526 17.64 11.9453 17.64 9.20443Z" fill="#4285F4"/>
                <path d="M8.99976 18C11.4298 18 13.467 17.1941 14.9561 15.8195L12.0475 13.5613C11.2416 14.1013 10.2107 14.4204 8.99976 14.4204C6.65567 14.4204 4.67158 12.8372 3.96385 10.71H0.957031V13.0418C2.43794 15.9831 5.48158 18 8.99976 18Z" fill="#34A853"/>
                <path d="M3.96409 10.7098C3.78409 10.1698 3.68182 9.59301 3.68182 8.99983C3.68182 8.40664 3.78409 7.82983 3.96409 7.28983V4.95801H0.957273C0.347727 6.17301 0 7.54755 0 8.99983C0 10.4521 0.347727 11.8266 0.957273 13.0416L3.96409 10.7098Z" fill="#FBBC05"/>
                <path d="M8.99976 3.57955C10.3211 3.57955 11.5075 4.03364 12.4402 4.92545L15.0216 2.34409C13.4629 0.891818 11.4257 0 8.99976 0C5.48158 0 2.43794 2.01682 0.957031 4.95818L3.96385 7.29C4.67158 5.16273 6.65567 3.57955 8.99976 3.57955Z" fill="#EA4335"/>
              </svg>
              {googleLoading ? "Connecting..." : "Continue with Google"}
            </Button>

            <div className="relative mb-4">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-hairline" />
              </div>
              <div className="relative flex justify-center text-xs">
                <span className="bg-surface-1 px-2 text-ink-faint">or continue with email</span>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <label htmlFor="email" className="text-xs font-medium text-ink-subtle">
                  Email
                </label>
                <Input
                  id="email" type="email" autoComplete="email" required
                  value={email} onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com" disabled={loading}
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label htmlFor="password" className="text-xs font-medium text-ink-subtle">
                  Password
                </label>
                <Input
                  id="password" type="password"
                  autoComplete={mode === "signin" ? "current-password" : "new-password"}
                  required value={password} onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••" disabled={loading} minLength={6}
                />
              </div>

              {error && (
                <p className="rounded-lg border border-danger/20 bg-danger/5 px-3 py-2 text-xs text-danger">
                  {error}
                </p>
              )}
              {notice && (
                <p className="rounded-lg border border-ok/20 bg-ok/5 px-3 py-2 text-xs text-ok">
                  {notice}
                </p>
              )}

              <Button type="submit" disabled={loading} className="mt-1 w-full">
                {loading ? "Please wait…" : mode === "signin" ? "Sign In" : "Create Account"}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Toggle */}
        <p className="mt-4 text-center text-xs text-ink-subtle">
          {mode === "signin" ? (
            <>Don&apos;t have an account?{" "}
              <button type="button" onClick={toggleMode} className="font-medium text-lav transition-colors hover:text-lav-hi">
                Sign up
              </button>
            </>
          ) : (
            <>Already have an account?{" "}
              <button type="button" onClick={toggleMode} className="font-medium text-lav transition-colors hover:text-lav-hi">
                Sign in
              </button>
            </>
          )}
        </p>
      </div>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <main className="flex min-h-screen items-center justify-center bg-canvas px-4">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-lav border-t-transparent" />
        </div>
      </main>
    }>
      <LoginContent />
    </Suspense>
  );
}
