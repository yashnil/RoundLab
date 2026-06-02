"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Mic } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { createClient } from "@/lib/supabase";

type Mode = "signin" | "signup";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

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
