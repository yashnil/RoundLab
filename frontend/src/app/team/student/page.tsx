"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Mic, ClipboardList, ExternalLink } from "lucide-react";
import AppShell from "@/components/shell/AppShell";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { createClient } from "@/lib/supabase";
import { fetchStudentProfile, RECIPIENT_STATE_LABEL, RECIPIENT_STATE_TONE } from "@/lib/assignments";
import type { CoachStudentProfile } from "@/types";

const TONE_CLS: Record<"ink" | "warn" | "ok" | "danger" | "lav", string> = {
  ink: "border-hairline bg-surface-2 text-ink-subtle",
  warn: "border-warn/30 bg-warn/10 text-warn",
  ok: "border-ok/30 bg-ok/10 text-ok",
  danger: "border-danger/30 bg-danger/10 text-danger",
  lav: "border-lav/30 bg-lav/10 text-lav",
};

export default function StudentProfilePage() {
  const router = useRouter();
  const [profile, setProfile] = useState<CoachStudentProfile | null>(null);
  const [teamId, setTeamId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    const params = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : null;
    const tid = params?.get("team") ?? null;
    const sid = params?.get("id") ?? null;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time URL init, hydration-safe
    setTeamId(tid);
    createClient().auth.getUser()
      .then(async ({ data }) => {
        if (!data.user) { router.replace("/login"); return; }
        if (!tid || !sid) { setErr("Missing student or team."); return; }
        setProfile(await fetchStudentProfile(tid, sid));
      })
      .catch(() => setErr("Could not load this student. You may not have coach access."))
      .finally(() => setLoading(false));
  }, [router]);

  const nextAction =
    !profile ? null
    : profile.assignments.some((a) => a.status === "ready_for_review") ? "Review their submitted work"
    : profile.assignments.some((a) => a.status === "assigned") ? "Waiting on an assigned practice"
    : profile.feedback_ready_count === 0 ? "Encourage a first practice"
    : "Assign a targeted drill or re-record";

  return (
    <AppShell maxWidth="full" bare>
      <div className="mx-auto flex max-w-2xl flex-col gap-5 px-4 py-8 sm:px-6">
        <Link href="/team" className="flex w-fit items-center gap-1 text-xs text-ink-subtle transition-colors hover:text-ink">
          <ArrowLeft size={12} aria-hidden /> Back to team
        </Link>

        {loading ? (
          <Skeleton className="h-48 w-full rounded-xl" />
        ) : err ? (
          <p className="rounded-lg border border-danger/20 bg-danger/5 px-4 py-3 text-sm text-danger">{err}</p>
        ) : profile ? (
          <>
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-full border border-hairline bg-surface-2 text-sm font-semibold text-ink-subtle">
                {(profile.display_name || "S").charAt(0).toUpperCase()}
              </div>
              <div>
                <h1 className="text-title text-ink">{profile.display_name || "Student"}</h1>
                <p className="text-xs text-ink-subtle">{profile.speech_count} speeches · {profile.feedback_ready_count} analyzed</p>
              </div>
            </div>

            {/* Suggested next action */}
            {nextAction && (
              <Card className="border-lav/20 bg-lav/5">
                <CardContent className="px-4 py-3">
                  <p className="text-eyebrow text-lav">Suggested next action</p>
                  <p className="text-sm font-medium text-ink">{nextAction}</p>
                  {teamId && (
                    <Link href={`/team/assign?team=${teamId}`} className="mt-1 inline-block text-xs font-medium text-lav hover:underline">
                      Create an assignment →
                    </Link>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Assignments */}
            <Card>
              <CardContent className="flex flex-col gap-3 px-5 py-4">
                <span className="flex items-center gap-1.5 text-eyebrow text-ink-subtle"><ClipboardList size={12} aria-hidden /> Assignments</span>
                {profile.assignments.length === 0 ? (
                  <p className="text-xs text-ink-faint">No assignments yet.</p>
                ) : (
                  <ul className="flex flex-col gap-1.5">
                    {profile.assignments.map((a) => (
                      <li key={a.recipient_id} className="flex items-center justify-between gap-2 rounded-lg border border-hairline bg-surface-1 px-3 py-2">
                        <span className="truncate text-sm text-ink">{a.title}</span>
                        <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold ${TONE_CLS[RECIPIENT_STATE_TONE[a.status]]}`}>
                          {RECIPIENT_STATE_LABEL[a.status]}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>

            {/* Recent reports */}
            <Card>
              <CardContent className="flex flex-col gap-3 px-5 py-4">
                <span className="flex items-center gap-1.5 text-eyebrow text-ink-subtle"><Mic size={12} aria-hidden /> Recent reports</span>
                {profile.speeches.length === 0 ? (
                  <p className="text-xs text-ink-faint">No speeches yet.</p>
                ) : (
                  <ul className="flex flex-col gap-1.5">
                    {profile.speeches.map((s) => (
                      <li key={s.id}>
                        <Link href={`/speech/${s.id}`} className="flex items-center justify-between gap-2 rounded-lg border border-hairline bg-surface-1 px-3 py-2 transition-colors hover:border-hairline-strong">
                          <span className="flex min-w-0 flex-col">
                            <span className="truncate text-sm text-ink">{s.title}</span>
                            <span className="text-[11px] capitalize text-ink-faint">{s.speech_type.replace("_", " ")} · {s.status}</span>
                          </span>
                          <ExternalLink size={13} className="shrink-0 text-ink-faint" aria-hidden />
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </>
        ) : null}
      </div>
    </AppShell>
  );
}
