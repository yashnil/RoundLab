"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase";
import { DiagnosticIntake } from "@/components/training/DiagnosticIntake";
import { startDiagnostic, completeDiagnostic } from "@/lib/trainingApi";
import type { ExperienceLevel } from "@/types/training";
import { CheckCircle } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function DiagnosticPage() {
  const router = useRouter();
  const [authLoading, setAuthLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    createClient()
      .auth.getUser()
      .then(({ data }) => {
        if (!data.user) router.replace("/login?next=/diagnostic");
      })
      .catch(() => router.replace("/login?next=/diagnostic"))
      .finally(() => setAuthLoading(false));
  }, [router]);

  async function handleComplete(level: ExperienceLevel, intakeData: Record<string, unknown>) {
    setSubmitting(true);
    setErr("");
    try {
      const { diagnostic_id } = await startDiagnostic({
        experience_level: level,
        intake_data: intakeData,
      });
      await completeDiagnostic({ diagnostic_id });
      setDone(true);
    } catch {
      setErr("Could not save diagnostic. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (authLoading) {
    return (
      <div className="max-w-xl mx-auto px-4 py-8 text-[13px] text-ink-subtle">Loading…</div>
    );
  }

  if (done) {
    return (
      <div className="max-w-xl mx-auto px-4 py-8 text-center space-y-4">
        <div className="w-14 h-14 rounded-full bg-ok/10 flex items-center justify-center mx-auto">
          <CheckCircle size={28} className="text-ok" aria-hidden />
        </div>
        <h1 className="text-xl font-bold text-ink">Diagnostic complete</h1>
        <p className="text-[13px] text-ink-subtle">
          Your training plan and starting mastery profile are ready.
        </p>
        <Link href="/training">
          <Button className="px-6">View Training Plan →</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-canvas">
      {err && (
        <div className="max-w-xl mx-auto px-4 pt-4">
          <p className="text-[12px] text-danger">{err}</p>
        </div>
      )}
      <DiagnosticIntake onComplete={handleComplete} loading={submitting} />
    </div>
  );
}
