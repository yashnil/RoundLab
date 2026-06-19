"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Target, TrendingUp, Calendar, Flag, ArrowRight, CheckCircle2, Circle, Sparkles } from "lucide-react";
import AppShell from "@/components/shell/AppShell";
import EmptyState from "@/components/EmptyState";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { createClient } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import {
  deriveCurrentFocus, deriveSkillLevels, derivePracticeCoverage, deriveMilestones,
  deriveWeeklyPlan, drillEffectivenessNote, progressDataState,
} from "@/lib/progressModel";
import { deriveRecentActivity } from "@/lib/dashboardActivity";
import type { ProgressSummary, Speech } from "@/types";

function SectionTitle({ icon: Icon, children }: { icon: typeof Target; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2">
      <Icon size={15} className="text-ink-subtle" aria-hidden />
      <h2 className="text-heading text-ink">{children}</h2>
    </div>
  );
}

export default function ProgressPage() {
  const router = useRouter();
  const [progress, setProgress] = useState<ProgressSummary | null>(null);
  const [speeches, setSpeeches] = useState<Speech[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    createClient().auth.getUser()
      .then(async ({ data }) => {
        if (!data.user) { router.replace("/login"); return; }
        const [p, s] = await Promise.all([
          apiFetch<ProgressSummary>(`/users/${data.user.id}/progress`),
          apiFetch<Speech[]>(`/speeches?user_id=${data.user.id}`),
        ]);
        setProgress(p); setSpeeches(s);
      })
      .catch(() => setErr("We couldn't load your progress. Refresh to try again."))
      .finally(() => setLoading(false));
  }, [router]);

  const state = progressDataState(progress);
  const focus = deriveCurrentFocus(progress);
  const skills = deriveSkillLevels(progress);
  const coverage = derivePracticeCoverage(speeches);
  const milestones = deriveMilestones(progress, speeches);
  const plan = deriveWeeklyPlan(progress, speeches);
  const rhythm = deriveRecentActivity(speeches, 5);

  return (
    <AppShell maxWidth="full" bare>
      <div className="mx-auto flex max-w-4xl flex-col gap-6 px-4 py-7 sm:px-6">
        <div className="flex flex-col gap-1">
          <span className="section-stamp">Progress</span>
          <h1 className="text-title text-ink">Your development</h1>
          <p className="text-sm text-ink-subtle">How you&apos;re improving — and what to train next.</p>
        </div>

        {loading ? (
          <div className="flex flex-col gap-4">
            {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-32 w-full rounded-xl" />)}
          </div>
        ) : err ? (
          <Card><CardContent className="py-8 text-center text-sm text-danger">{err}</CardContent></Card>
        ) : state === "empty" ? (
          <EmptyState
            Icon={TrendingUp}
            title="Your progress starts with one speech."
            description="Record or upload a PF speech. After your first report, this page tracks your skills, coverage, and a weekly plan."
            action={{ label: "Start your first practice", href: "/session" }}
          />
        ) : (
          <>
            {state === "sparse" && (
              <div className="rounded-lg border border-lav/20 bg-lav/5 px-4 py-3 text-xs leading-relaxed text-ink-subtle">
                You have one analyzed report so far. Trends and drill effectiveness unlock with a second — practice another speech to fill them in.
              </div>
            )}

            {/* Current focus */}
            {focus && (
              <Card>
                <CardContent className="flex flex-col gap-3 px-5 py-5">
                  <SectionTitle icon={Target}>Current focus</SectionTitle>
                  <div className="flex flex-wrap items-end justify-between gap-2">
                    <div>
                      <p className="text-lg font-semibold text-ink">{focus.skill}</p>
                      <p className="text-xs text-ink-subtle">{focus.reason}</p>
                    </div>
                    <span className="font-mono text-sm tabular-nums text-ink-faint">{focus.score.toFixed(1)}/20</span>
                  </div>
                  {focus.lowConfidence && (
                    <p className="text-[11px] text-ink-faint">Based on limited data — keep practicing to confirm this focus.</p>
                  )}
                  <Link href={focus.href} className="inline-flex w-fit items-center gap-1 rounded-lg bg-lav px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-lav-hi">
                    Practice this <ArrowRight size={12} aria-hidden />
                  </Link>
                </CardContent>
              </Card>
            )}

            {/* Skill levels */}
            {skills.length > 0 && (
              <Card>
                <CardContent className="flex flex-col gap-3 px-5 py-5">
                  <SectionTitle icon={TrendingUp}>Skill levels</SectionTitle>
                  <div className="flex flex-col gap-2.5">
                    {skills.map((s) => {
                      const pct = Math.round((s.score / s.max) * 100);
                      const tone = pct >= 70 ? "bg-ok" : pct >= 50 ? "bg-warn" : "bg-danger";
                      return (
                        <div key={s.key} className="flex items-center gap-3">
                          <span className="w-32 shrink-0 text-xs text-ink-subtle">{s.label}</span>
                          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-hairline">
                            <div className={`h-full rounded-full ${tone}`} style={{ width: `${pct}%` }} />
                          </div>
                          <span className="w-12 shrink-0 text-right font-mono text-[11px] tabular-nums text-ink-faint">{s.score.toFixed(1)}/{s.max}</span>
                        </div>
                      );
                    })}
                  </div>
                  <p className="text-[11px] text-ink-faint">Current averages across your analyzed speeches.</p>
                </CardContent>
              </Card>
            )}

            {/* Practice coverage */}
            <Card>
              <CardContent className="flex flex-col gap-3 px-5 py-5">
                <SectionTitle icon={Calendar}>Practice coverage</SectionTitle>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
                  {coverage.map((c) => (
                    <div key={c.type} className={`flex flex-col items-center gap-1 rounded-lg border px-2 py-3 text-center ${c.practiced ? "border-ok/25 bg-ok/5" : "border-hairline bg-surface-1"}`}>
                      <span className="text-xs font-medium text-ink">{c.label}</span>
                      <span className={`text-[11px] tabular-nums ${c.practiced ? "text-ok" : "text-ink-faint"}`}>
                        {c.practiced ? `${c.count} done` : "Not yet"}
                      </span>
                    </div>
                  ))}
                </div>
                <p className="text-[11px] text-ink-faint">{drillEffectivenessNote(progress)}</p>
              </CardContent>
            </Card>

            {/* Weekly plan */}
            <Card>
              <CardContent className="flex flex-col gap-3 px-5 py-5">
                <div className="flex items-center justify-between">
                  <SectionTitle icon={Sparkles}>This week&apos;s plan</SectionTitle>
                  <span className="rounded-full border border-lav/25 bg-lav/10 px-2 py-0.5 text-[10px] font-medium text-lav">Generated</span>
                </div>
                <ul className="flex flex-col gap-2">
                  {plan.map((item) => (
                    <li key={item.id}>
                      <Link href={item.href} className="group flex items-center gap-3 rounded-lg border border-hairline bg-surface-1 px-3 py-2.5 transition-colors hover:border-hairline-strong">
                        <span className="flex min-w-0 flex-1 flex-col">
                          <span className="text-sm font-medium text-ink">{item.label}</span>
                          <span className="text-xs text-ink-subtle">{item.detail}</span>
                        </span>
                        <ArrowRight size={13} className="shrink-0 text-ink-faint transition-colors group-hover:text-lav" aria-hidden />
                      </Link>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>

            {/* Milestones */}
            <Card>
              <CardContent className="flex flex-col gap-3 px-5 py-5">
                <SectionTitle icon={Flag}>Milestones</SectionTitle>
                <ul className="flex flex-col gap-2">
                  {milestones.map((m) => (
                    <li key={m.id} className="flex items-center gap-2.5">
                      {m.done
                        ? <CheckCircle2 size={15} className="shrink-0 text-ok" aria-hidden />
                        : <Circle size={15} className="shrink-0 text-ink-faint" aria-hidden />}
                      <span className={`text-sm ${m.done ? "text-ink-subtle line-through" : "text-ink"}`}>{m.label}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>

            {/* Practice rhythm */}
            {rhythm.length > 0 && (
              <Card>
                <CardContent className="flex flex-col gap-3 px-5 py-5">
                  <SectionTitle icon={Calendar}>Recent practice</SectionTitle>
                  <ul className="flex flex-col gap-1.5">
                    {rhythm.map((a) => (
                      <li key={a.id}>
                        <Link href={a.href} className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 text-xs transition-colors hover:bg-surface-2">
                          <span className="truncate text-ink-muted">{a.action}</span>
                          <span className="shrink-0 text-ink-faint">{new Date(a.date).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
