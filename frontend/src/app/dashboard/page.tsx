"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "motion/react";
import {
  Mic, CheckCircle2, Target,
  MoreHorizontal, Trash2, ArrowUpRight, ArrowRight,
  BookOpen, Zap, Users, Play, BarChart2, Dumbbell, ChevronRight,
} from "lucide-react";
import AppShell from "@/components/shell/AppShell";
import EmptyState from "@/components/EmptyState";
import DeleteDialog from "@/components/DeleteDialog";
import PilotChecklist from "@/components/PilotChecklist";
import SkillTrendCard from "@/components/SkillTrendCard";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  DropdownMenuRoot, DropdownMenuTrigger, DropdownMenuContent,
  DropdownMenuItem, DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { createClient } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import { staggerParent, staggerChild, cardHover } from "@/lib/motion";
import { getSpeechStatusConfig } from "@/lib/debateHelpers";
import DashboardMissionPanel, { DashboardMissionPanelSkeleton } from "@/components/DashboardMissionPanel";
import DashboardCockpitBand from "@/components/DashboardCockpitBand";
import FirstRunCommandCenter from "@/components/FirstRunCommandCenter";
import type { DeliveryMetrics, Speech, ProgressSummary, PilotSummary, Workout, BlockCoverageResponse } from "@/types";
import { deriveWorkoutProgress, getNextIncompleteStep } from "@/lib/workoutHelpers";
import NextActionPanel from "@/components/dashboard/NextActionPanel";
import QuickStartRow from "@/components/dashboard/QuickStartRow";
import PracticeRecipes from "@/components/dashboard/PracticeRecipes";
import CoachingFocusCard from "@/components/dashboard/CoachingFocusCard";
import RecentActivity from "@/components/dashboard/RecentActivity";
import { selectNextAction } from "@/lib/dashboardHelpers";
import { deriveDeliveryFocus, deliveryScoreColor, getPacingBandDisplay } from "@/lib/deliveryHelpers";
import { deriveBlockReadiness } from "@/lib/blockfileHelpers";

const TYPE_LABEL: Record<string, string> = {
  constructive: "Constructive", rebuttal: "Rebuttal", summary: "Summary",
  final_focus: "Final Focus",  crossfire: "Crossfire",
};
const JUDGE_LABEL: Record<string, string> = {
  lay: "Lay", flow: "Flow", tech: "Tech", coach: "Coach",
};

const SKILL_LABELS: Record<string, { label: string; variant: "indigo" | "green" | "amber" | "red" | "blue" | "violet" | "orange" | "default" }> = {
  weighing:         { label: "Impact Weighing",    variant: "indigo"  },
  warranting:       { label: "Warranting",         variant: "blue"    },
  drops:            { label: "Drop Prevention",    variant: "red"     },
  extensions:       { label: "Extensions",         variant: "green"   },
  evidence:         { label: "Evidence Use",       variant: "amber"   },
  clash:            { label: "Clash",              variant: "violet"  },
  judge_adaptation: { label: "Judge Adaptation",   variant: "orange"  },
  collapse:         { label: "Collapse Strategy",  variant: "indigo"  },
  line_by_line:     { label: "Line-by-Line",       variant: "blue"    },
};

type BV = "default" | "indigo" | "green" | "amber" | "red";

function speechStatus(s: Speech): { label: string; variant: BV } {
  const cfg = getSpeechStatusConfig(s.status);
  // Special case: audio uploaded but not yet transcribing
  if (s.status === "pending" && s.audio_url) {
    return { label: "Audio uploaded", variant: "default" };
  }
  return {
    label: cfg.isProcessing ? `${cfg.label}…` : cfg.label,
    variant: cfg.badge as BV,
  };
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short", day: "numeric", year: "numeric",
  });
}

function fmtPercent(val: number | null) {
  if (val === null) return "—";
  return `${Math.round(val * 100)}%`;
}

function SpeechCard({ s, onDelete }: { s: Speech; onDelete: (s: Speech) => void }) {
  const status = speechStatus(s);

  // Colored left-border accent based on status
  const accentBorder =
    s.status === "done"         ? "border-l-ok/60"
    : s.status === "error"      ? "border-l-danger/60"
    : s.status === "analyzing"  ? "border-l-warn/60"
    : s.status === "transcribing" ? "border-l-lav/40"
    : "border-l-hairline";

  const PIPELINE: Array<{ key: string; label: string; done: boolean; possible?: boolean }> = [
    { key: "audio",  label: "Audio",      done: !!s.audio_url },
    { key: "tx",     label: "Transcript", done: s.status !== "pending" },
    { key: "flow",   label: "Flow",       done: s.status === "analyzing" || s.status === "done" },
    { key: "ballot", label: "Ballot",     done: s.status === "done" },
    { key: "drills", label: "Drills",     done: false, possible: s.status === "done" },
  ];

  return (
    <motion.div
      variants={staggerChild}
      {...cardHover}
    >
      <Card className={`border-l-2 transition-colors duration-150 hover:border-hairline-strong ${accentBorder}`}>
        <CardContent className="flex items-center gap-4 px-5 py-4">
          <Link href={`/speech/${s.id}`} className="group flex min-w-0 flex-1 items-start gap-3.5">
            <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-hairline bg-surface-2 transition-colors group-hover:border-lav/30 group-hover:bg-lav/5">
              <Mic size={13} className="text-ink-faint transition-colors group-hover:text-lav" />
            </div>
            <div className="flex min-w-0 flex-col gap-0.5">
              <p className="truncate text-sm font-semibold text-ink transition-colors group-hover:text-lav-hi">
                {s.title}
              </p>
              <div className="flex flex-wrap items-center gap-x-2 gap-y-0">
                <span className="text-xs text-ink-subtle">{TYPE_LABEL[s.speech_type] ?? s.speech_type}</span>
                {s.side       && <span className="text-xs capitalize text-ink-faint">· {s.side}</span>}
                {s.judge_type && <span className="text-xs text-ink-faint">· {JUDGE_LABEL[s.judge_type]} judge</span>}
                {s.topic      && <span className="hidden truncate text-xs text-ink-faint sm:inline">· {s.topic}</span>}
              </div>
              {/* Pipeline dots with labels */}
              <div className="mt-1.5 flex items-center gap-0.5">
                {PIPELINE.map((step, i, arr) => (
                  <div key={step.key} className="flex items-center gap-0.5">
                    <div
                      title={step.label}
                      className={[
                        "h-1.5 rounded-full transition-colors",
                        step.done
                          ? "w-5 bg-lav"
                          : step.possible
                          ? "w-4 bg-lav/25"
                          : "w-3 bg-hairline",
                      ].join(" ")}
                    />
                    {i < arr.length - 1 && <div className="h-px w-0.5 bg-hairline" />}
                  </div>
                ))}
                <span className="ml-1.5 text-xs text-ink-faint">{fmtDate(s.created_at)}</span>
              </div>
            </div>
          </Link>

          <div className="flex shrink-0 items-center gap-2">
            <Badge variant={status.variant}>{status.label}</Badge>
            <DropdownMenuRoot>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  onClick={(e) => e.preventDefault()}
                  className="flex h-6 w-6 items-center justify-center rounded-md text-ink-faint transition-colors hover:bg-surface-2 hover:text-ink-subtle"
                >
                  <MoreHorizontal size={13} />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem asChild>
                  <Link href={`/speech/${s.id}`} className="flex items-center gap-2">
                    <ArrowUpRight size={12} />
                    View flow report
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem destructive onSelect={() => onDelete(s)}>
                  <Trash2 size={12} />
                  Delete session
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenuRoot>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

function SpeechSkeleton() {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 px-5 py-4">
        <Skeleton className="h-8 w-8 shrink-0 rounded-lg" />
        <div className="flex flex-1 flex-col gap-1.5">
          <Skeleton className="h-3.5 w-2/5" />
          <Skeleton className="h-3 w-1/4" />
        </div>
        <Skeleton className="h-5 w-24 rounded-full" />
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const [userId,        setUserId]       = useState<string | null>(null);
  const [speeches,      setSpeeches]     = useState<Speech[]>([]);
  const [progress,      setProgress]     = useState<ProgressSummary | null>(null);
  const [pilotSummary,  setPilotSummary] = useState<PilotSummary | null>(null);
  const [latestDelivery, setLatestDelivery] = useState<DeliveryMetrics | null>(null);
  const [latestWorkout, setLatestWorkout] = useState<Workout | null>(null);
  const [blockEntryCount, setBlockEntryCount] = useState(0);
  const [latestBlockCoverage, setLatestBlockCoverage] = useState<BlockCoverageResponse | null>(null);
  const [loading,       setLoading]      = useState(true);
  const [err,           setErr]          = useState("");
  const [del,           setDel]          = useState<Speech | null>(null);
  const [deleting,      setDeleting]     = useState(false);
  const [deleteErr,     setDeleteErr]    = useState("");

  useEffect(() => {
    createClient().auth.getUser()
      .then(async ({ data }) => {
        if (!data.user) { router.replace("/login"); return; }
        setUserId(data.user.id);

        // Fetch speeches, progress, and pilot summary in parallel
        const [speechesData, progressData] = await Promise.all([
          apiFetch<Speech[]>(`/speeches?user_id=${data.user.id}`),
          apiFetch<ProgressSummary>(`/users/${data.user.id}/progress`),
        ]);

        setSpeeches(speechesData);
        setProgress(progressData);

        // Pilot summary is best-effort — don't block the page if it fails
        try {
          const pilotData = await apiFetch<PilotSummary>(`/users/${data.user.id}/pilot-summary`);
          setPilotSummary(pilotData);
        } catch { /* non-critical */ }

        // Delivery metrics for the latest speech — best-effort
        if (speechesData.length > 0) {
          apiFetch<DeliveryMetrics>(`/speeches/${speechesData[0].id}/delivery-metrics?user_id=${data.user.id}`)
            .then(setLatestDelivery)
            .catch(() => {});
        }

        // Latest workout — best-effort
        apiFetch<Workout[]>(`/workouts?user_id=${data.user.id}`)
          .then((ws) => { if (ws.length > 0) setLatestWorkout(ws[0]); })
          .catch(() => {});

        // Block entries count — best-effort
        apiFetch<Array<unknown>>(`/block-entries?user_id=${data.user.id}`)
          .then((entries) => setBlockEntryCount(entries.length))
          .catch(() => {});

        // Block coverage for latest speech — best-effort
        if (speechesData.length > 0) {
          apiFetch<BlockCoverageResponse>(
            `/speeches/${speechesData[0].id}/block-coverage?user_id=${data.user.id}`,
          ).then(setLatestBlockCoverage).catch(() => {});
        }
      })
      .catch(() => setErr("Could not load your data. Please refresh and try again."))
      .finally(() => setLoading(false));
  }, [router]);

  async function handleDelete() {
    if (!del || !userId) return;
    setDeleting(true);
    setDeleteErr("");
    try {
      await apiFetch(`/speeches/${del.id}?user_id=${userId}`, { method: "DELETE" });
      setSpeeches((p) => p.filter((s) => s.id !== del.id));

      // Refresh progress
      const progressData = await apiFetch<ProgressSummary>(`/users/${userId}/progress`);
      setProgress(progressData);
      try {
        const pilotData = await apiFetch<PilotSummary>(`/users/${userId}/pilot-summary`);
        setPilotSummary(pilotData);
      } catch { /* non-critical */ }
      setDel(null);
    } catch (e: unknown) {
      setDeleteErr(e instanceof Error ? e.message : "Could not delete this session. Please refresh and try again.");
    }
    finally { setDeleting(false); }
  }

  return (
    <AppShell maxWidth="full" bare>
        <motion.div
          className="mx-auto flex max-w-6xl flex-col gap-5 px-4 py-6 sm:px-6 sm:py-7"
          variants={staggerParent(0.07, 0.05)}
          initial="hidden"
          animate="show"
        >
          {/* ── Cockpit band — practice loop position + stat pills ───── */}
          {!loading && progress && (
            <motion.div variants={staggerChild}>
              <DashboardCockpitBand progress={progress} />
            </motion.div>
          )}

          {/* ── Your next step — single most important action ──────── */}
          {!loading && (
            <motion.div variants={staggerChild}>
              <NextActionPanel
                action={selectNextAction({ speeches, progress, focusSkill: null })}
              />
            </motion.div>
          )}

          {/* ── Quick start — fast entry by speech type ─────────────── */}
          {!loading && (
            <motion.div variants={staggerChild}>
              <QuickStartRow />
            </motion.div>
          )}

          {/* ── Practice recipes — primed one-click configurations ──── */}
          {!loading && (
            <motion.div variants={staggerChild}>
              <PracticeRecipes />
            </motion.div>
          )}

          {/* ── Coaching focus — priority skill from real reports ────── */}
          {!loading && progress && (
            <motion.div variants={staggerChild}>
              <CoachingFocusCard
                skillAverages={progress.skill_averages}
                feedbackReadyCount={progress.feedback_ready_count}
              />
            </motion.div>
          )}

          {/* ── Recent activity — debate-native event stream ─────────── */}
          {!loading && speeches.length > 0 && (
            <motion.div variants={staggerChild}>
              <RecentActivity speeches={speeches} />
            </motion.div>
          )}

          {/* ── Mission Panel — supporting context, now below next step ── */}
          <motion.div variants={staggerChild}>
            {loading
              ? <DashboardMissionPanelSkeleton />
              : progress
              ? <DashboardMissionPanel progress={progress} latestSpeech={speeches[0] ?? null} />
              : null}
          </motion.div>

          {/* ── Delivery Focus Card — shows when latest speech has delivery metrics ── */}
          {!loading && latestDelivery && (() => {
            const focus = deriveDeliveryFocus(latestDelivery);
            const scoreColor = deliveryScoreColor(latestDelivery.delivery_score);
            const pacingDisplay = getPacingBandDisplay(latestDelivery.pacing_band);
            if (!focus && !latestDelivery.delivery_score) return null;
            return (
              <motion.div variants={staggerChild}>
                <Card className="border-hairline bg-surface-1">
                  <CardContent className="px-4 py-3">
                    <div className="flex items-start gap-3">
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-lav/10">
                        <Mic size={13} className="text-lav" />
                      </div>
                      <div className="flex flex-col gap-1 flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="section-stamp">Delivery focus</span>
                          {latestDelivery.delivery_score !== null && latestDelivery.delivery_score !== undefined && (
                            <span className={`text-xs font-semibold tabular-nums ${scoreColor}`}>
                              {latestDelivery.delivery_score}/100
                            </span>
                          )}
                          <span className={`text-[10px] font-medium ${pacingDisplay.colorClass}`}>
                            {pacingDisplay.label}
                            {latestDelivery.words_per_minute !== null && latestDelivery.words_per_minute !== undefined
                              ? ` · ${Math.round(latestDelivery.words_per_minute)} WPM` : ""}
                          </span>
                        </div>
                        {focus && (
                          <p className="text-xs font-medium text-ink">{focus}</p>
                        )}
                        {latestDelivery.filler_word_count !== null && latestDelivery.filler_word_count !== undefined && latestDelivery.filler_word_count > 0 && (
                          <p className="text-[11px] text-ink-faint">
                            {latestDelivery.filler_word_count} filler words detected in latest speech
                          </p>
                        )}
                      </div>
                      {speeches[0] && (
                        <Link
                          href={`/speech/${speeches[0].id}`}
                          className="shrink-0 text-[10px] text-lav font-medium hover:underline"
                        >
                          View report →
                        </Link>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            );
          })()}

          {/* ── Today's Prep — compact workout card ──────────────────────────────── */}
          {!loading && latestWorkout && latestWorkout.status !== "completed" && (() => {
            const prog = deriveWorkoutProgress(latestWorkout);
            const next = getNextIncompleteStep(latestWorkout);
            const speechId = latestWorkout.speech_id;
            return (
              <motion.div variants={staggerChild}>
                <Card className="border-hairline bg-surface-1">
                  <CardContent className="px-4 py-3">
                    <div className="flex items-start gap-3">
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-lav/10">
                        <Dumbbell size={13} className="text-lav" />
                      </div>
                      <div className="flex flex-col gap-0.5 flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="section-stamp">Today&apos;s prep</span>
                          <span className="text-[10px] text-ink-faint">
                            {prog.completed}/{prog.total} steps · {latestWorkout.estimated_minutes ?? "—"} min
                          </span>
                        </div>
                        <p className="text-xs font-medium text-ink truncate">{latestWorkout.title}</p>
                        {next && (
                          <p className="text-[11px] text-ink-faint truncate">Next: {next.title}</p>
                        )}
                      </div>
                      <Link
                        href={`/speech/${speechId}`}
                        className="shrink-0 flex items-center gap-0.5 text-[10px] text-lav font-medium hover:underline"
                      >
                        Continue <ChevronRight size={10} />
                      </Link>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            );
          })()}

          {/* Today's Prep CTA — when no active workout but latest speech is done */}
          {!loading && !latestWorkout && speeches[0]?.status === "done" && (
            <motion.div variants={staggerChild}>
              <Card className="border-hairline bg-surface-1">
                <CardContent className="px-4 py-3">
                  <div className="flex items-start gap-3">
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-lav/10">
                      <Dumbbell size={13} className="text-lav" />
                    </div>
                    <div className="flex flex-col gap-0.5 flex-1 min-w-0">
                      <span className="section-stamp">Today&apos;s prep</span>
                      <p className="text-xs text-ink-subtle">No workout yet — build one from your latest speech.</p>
                    </div>
                    <Link
                      href={`/speech/${speeches[0].id}`}
                      className="shrink-0 flex items-center gap-0.5 text-[10px] text-lav font-medium hover:underline"
                    >
                      Build workout <ChevronRight size={10} />
                    </Link>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Blockfile Readiness card — shown when user has block entries or coverage data */}
          {!loading && (blockEntryCount > 0 || latestBlockCoverage !== null) && (() => {
            const readiness = deriveBlockReadiness(blockEntryCount, latestBlockCoverage);
            const hasMissing = (latestBlockCoverage?.missing_count ?? 0) > 0;
            const hasPartial = (latestBlockCoverage?.partially_covered_count ?? 0) > 0;
            return (
              <motion.div variants={staggerChild}>
                <Card className="border-hairline bg-surface-1">
                  <CardContent className="px-4 py-3">
                    <div className="flex items-start gap-3">
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-surface-2 border border-hairline">
                        <BookOpen size={13} className={hasMissing ? "text-danger" : hasPartial ? "text-warn" : "text-ok"} />
                      </div>
                      <div className="flex flex-col gap-0.5 flex-1 min-w-0">
                        <span className="section-stamp">Block readiness</span>
                        <p className="text-xs font-semibold text-ink">
                          {readiness.totalEntries} block{readiness.totalEntries !== 1 ? "s" : ""}
                          {readiness.hasCoverage && latestBlockCoverage && (
                            <> · {latestBlockCoverage.covered_count}/{latestBlockCoverage.checks.length} covered</>
                          )}
                        </p>
                        {readiness.strongestGap && (
                          <p className="text-xs text-ink-subtle truncate">{readiness.strongestGap}</p>
                        )}
                      </div>
                      <div className="flex shrink-0 items-center gap-1">
                        {speeches[0] && (
                          <Link
                            href={`/speech/${speeches[0].id}#block-coverage`}
                            className="flex items-center gap-0.5 text-[10px] text-lav font-medium hover:underline"
                          >
                            Check <ChevronRight size={10} />
                          </Link>
                        )}
                        {blockEntryCount === 0 && (
                          <Link
                            href="/evidence"
                            className="flex items-center gap-0.5 text-[10px] text-lav font-medium hover:underline"
                          >
                            Upload <ChevronRight size={10} />
                          </Link>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            );
          })()}

          {/* Badges — shown separately below the mission panel */}
          {!loading && progress && progress.badges.length > 0 && (
            <motion.div variants={staggerChild}>
              <div className="flex flex-wrap items-center gap-2 px-1">
                <span className="section-stamp">Badges</span>
                {progress.badges.slice(0, 6).map((badge) => (
                  <div
                    key={badge.id}
                    title={`${badge.name}: ${badge.description}`}
                    className="flex h-7 w-7 items-center justify-center rounded-lg border border-hairline bg-surface-2 text-sm transition-colors hover:border-lav/30 hover:bg-lav/5"
                  >
                    {badge.icon}
                  </div>
                ))}
                {progress.badges.length > 6 && (
                  <span className="text-xs text-ink-faint">+{progress.badges.length - 6} more</span>
                )}
              </div>
            </motion.div>
          )}

          {/* ── Pilot Checklist — replaces the old onboarding card for returning users ── */}
          {!loading && progress && progress.drill_attempts_count > 0 && (
            <motion.div variants={staggerChild}>
              <Card className="border-lav/20 bg-lav/5">
                <CardContent className="px-5 py-5">
                  <div className="mb-3 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <BarChart2 size={13} className="text-lav" />
                      <span className="section-stamp" style={{ color: "var(--color-lav)" }}>Practice loop progress</span>
                    </div>
                    <Link href="/pilot" className="text-[10px] font-medium text-lav/70 transition-colors hover:text-lav">
                      View full analytics →
                    </Link>
                  </div>
                  <PilotChecklist progress={progress} pilot={pilotSummary} />
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* First-run command center — only shown when user has no speeches yet */}
          {!loading && progress && progress.speech_count === 0 && (
            <motion.div variants={staggerChild}>
              <FirstRunCommandCenter userId={userId} />
            </motion.div>
          )}

          {/* Onboarding Checklist — show only after first speech, until first drill is done */}
          {!loading && progress && progress.speech_count > 0 && progress.drill_attempts_count === 0 && (
            <motion.div variants={staggerChild}>
              <Card className="border-lav/20 bg-lav/5">
                <CardContent className="px-6 py-6">
                  <div className="mb-3 flex items-center gap-2">
                    <Play size={15} className="text-lav" />
                    <p className="text-sm font-semibold text-lav">Complete your first practice rep</p>
                  </div>
                  <p className="mb-5 text-sm leading-relaxed text-ink">
                    Record a PF speech → get your flow and judge ballot → practice targeted drills. Each drill attempt earns the most XP and drives real improvement.
                  </p>
                  <div className="mb-5 flex flex-col gap-2.5">
                    {[
                      { label: "Create a practice session", done: progress.speech_count > 0, icon: Mic },
                      { label: "Record a 45-90 second speech", done: speeches.some(s => s.audio_url), icon: Mic },
                      { label: "Get judge-style feedback", done: progress.feedback_ready_count > 0, icon: CheckCircle2 },
                      { label: "Complete one drill", done: progress.drill_attempts_count > 0, icon: Target },
                    ].map((step, i) => (
                      <div key={i} className="flex items-center gap-2.5">
                        {step.done ? (
                          <CheckCircle2 size={15} className="shrink-0 text-ok" />
                        ) : (
                          <div className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-lav/40 bg-lav/10">
                            <div className="h-1.5 w-1.5 rounded-full bg-lav/60" />
                          </div>
                        )}
                        <span className={`text-sm ${step.done ? "text-ink-subtle line-through" : "text-ink"}`}>
                          {step.label}
                        </span>
                      </div>
                    ))}
                  </div>
                  <div className="flex flex-col gap-2 sm:flex-row">
                    <Button asChild size="sm" className="gap-1.5">
                      <Link href="/session">
                        <Mic size={12} />
                        Start Practice Session
                      </Link>
                    </Button>
                    <Button asChild size="sm" variant="secondary" className="gap-1.5">
                      <Link href="/team">
                        <Users size={12} />
                        Join Team (Optional)
                      </Link>
                    </Button>
                  </div>
                  <div className="mt-4 rounded-lg border border-lav/10 bg-lav/5 px-3 py-2">
                    <p className="text-xs text-ink-muted">
                      <span className="font-medium text-ink-subtle">Privacy:</span> If you join a team, your coach can see your practice progress and feedback status. Your audio and transcripts stay private.
                    </p>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Error */}
          {!loading && err && (
            <motion.div variants={staggerChild}>
              <Card><CardContent className="py-8 text-center text-sm text-danger">{err}</CardContent></Card>
            </motion.div>
          )}

          {/* Empty state - only show if no onboarding card */}
          {!loading && speeches.length === 0 && progress && progress.drill_attempts_count > 0 && (
            <motion.div variants={staggerChild}>
              <EmptyState
                Icon={Mic}
                title="Your first practice speech starts the loop."
                description="Record or upload a PF speech. RoundLab will build a flow, generate a judge-style ballot, and create 3 targeted drills."
                action={{ label: "Start Practice Session", href: "/session" }}
                hint="Works with constructive, rebuttal, summary, or final focus."
              />
            </motion.div>
          )}

          {/* Assigned Drill Queue */}
          {!loading && progress && progress.incomplete_drills.length > 0 && (
            <motion.div variants={staggerChild}>
              <Card className="border-lav/20 bg-lav/5">
                <CardContent className="flex flex-col gap-4 px-5 py-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex flex-col gap-1">
                      <div className="flex items-center gap-2">
                        <Zap size={14} className="text-lav" />
                        <p className="text-eyebrow text-lav">Next Drill</p>
                      </div>
                      <p className="text-sm font-semibold text-ink">{progress.incomplete_drills[0].title}</p>
                      <div className="mt-1 flex flex-wrap items-center gap-2">
                        <Badge variant={(SKILL_LABELS[progress.incomplete_drills[0].skill_target]?.variant as "indigo") || "default"}>
                          {SKILL_LABELS[progress.incomplete_drills[0].skill_target]?.label || progress.incomplete_drills[0].skill_target}
                        </Badge>
                        <Badge variant="default" className="capitalize">{progress.incomplete_drills[0].difficulty}</Badge>
                        <span className="text-xs text-ink-subtle capitalize">{progress.incomplete_drills[0].status.replace("_", " ")}</span>
                        <span className="text-xs text-ink-faint">From: {progress.incomplete_drills[0].speech_title}</span>
                      </div>
                    </div>
                    <Button asChild size="sm" className="shrink-0 gap-1.5">
                      <Link href={`/drills/${progress.incomplete_drills[0].id}`}>
                        Open workspace
                        <ArrowRight size={11} />
                      </Link>
                    </Button>
                  </div>

                  {progress.incomplete_drills.length > 1 && (
                    <div className="flex flex-col gap-1.5 border-t border-lav/10 pt-3">
                      <p className="text-xs font-medium text-ink-subtle">Also assigned:</p>
                      {progress.incomplete_drills.slice(1, 4).map((d) => (
                        <Link
                          key={d.id}
                          href={`/drills/${d.id}`}
                          className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 text-xs text-ink-muted transition-colors hover:bg-lav/5 hover:text-ink"
                        >
                          <span className="truncate">{d.title}</span>
                          <span className="shrink-0 capitalize text-ink-faint">{d.status.replace("_", " ")}</span>
                        </Link>
                      ))}
                      {progress.incomplete_drills.length > 4 && (
                        <p className="text-xs text-ink-faint">+{progress.incomplete_drills.length - 4} more</p>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Skill breakdown */}
          {!loading && progress && progress.skill_averages && (
            <motion.div variants={staggerChild} className="flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <span className="section-stamp">Skill Breakdown</span>
                <span className="rep-badge">
                  avg · {progress.feedback_ready_count} speech{progress.feedback_ready_count !== 1 ? "es" : ""}
                </span>
              </div>
              <Card>
                <CardContent className="grid grid-cols-1 gap-4 px-5 py-5 sm:grid-cols-2">
                  {[
                    { key: "clash",            label: "Clash",            max: 20, icon: "⚔" },
                    { key: "weighing",         label: "Impact Weighing",  max: 20, icon: "⚖" },
                    { key: "extensions",       label: "Extensions",       max: 20, icon: "↗" },
                    { key: "drops",            label: "Drop Prevention",  max: 20, icon: "🛡" },
                    { key: "judge_adaptation", label: "Judge Adaptation", max: 20, icon: "👁" },
                  ].map((skill) => {
                    const value = progress.skill_averages![skill.key as keyof typeof progress.skill_averages];
                    const pct = (value / skill.max) * 100;
                    const barColor = pct >= 70 ? "bg-lav" : pct >= 50 ? "bg-warn" : "bg-danger";
                    return (
                      <div key={skill.key} className="flex flex-col gap-1.5">
                        <div className="flex items-center justify-between gap-2">
                          <span className="section-stamp">
                            <span aria-hidden>{skill.icon}</span>
                            {skill.label}
                          </span>
                          <span
                            className="text-xs font-bold tabular-nums text-ink"
                            style={{ fontFamily: "var(--font-jetbrains-mono)" }}
                          >
                            {value.toFixed(1)}<span className="font-normal text-ink-faint">/{skill.max}</span>
                          </span>
                        </div>
                        <div className="h-1.5 overflow-hidden rounded-full bg-hairline">
                          <motion.div
                            className={`h-full rounded-full ${barColor}`}
                            initial={{ width: 0 }}
                            animate={{ width: `${pct}%` }}
                            transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
                          />
                        </div>
                      </div>
                    );
                  })}
                  {progress.drill_completion_rate !== null && (
                    <div className="flex flex-col gap-1.5 sm:col-span-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-ink-subtle">Drill Completion Rate</span>
                        <span className="text-xs font-bold text-ink">{fmtPercent(progress.drill_completion_rate)}</span>
                      </div>
                      <div className="h-1.5 overflow-hidden rounded-full bg-hairline">
                        <motion.div
                          className="h-full rounded-full bg-ok"
                          initial={{ width: 0 }}
                          animate={{ width: `${(progress.drill_completion_rate || 0) * 100}%` }}
                          transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
                        />
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Skill Trend Cards — show when we have trend data and 2+ feedback reports */}
          {!loading && pilotSummary?.skill_trends && progress && progress.feedback_ready_count >= 2 && (
            <motion.div variants={staggerChild} className="flex flex-col gap-3">
              <div className="flex items-center justify-between gap-2">
                <span className="section-stamp">Skill Trends</span>
                <span className="rep-badge">vs previous speech</span>
              </div>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                {[
                  { key: "clash",            label: "Clash",           icon: "⚔", max: 20 },
                  { key: "weighing",         label: "Impact Weighing", icon: "⚖", max: 20 },
                  { key: "extensions",       label: "Extensions",      icon: "↗", max: 20 },
                  { key: "drops",            label: "Drop Prevention", icon: "🛡", max: 20 },
                  { key: "judge_adaptation", label: "Judge Adapt.",    icon: "👁", max: 20 },
                ].map(({ key, label, icon, max }) => {
                  const trend = pilotSummary.skill_trends![key as keyof typeof pilotSummary.skill_trends];
                  if (!trend || trend.trend === "no_data") return null;
                  return <SkillTrendCard key={key} label={label} icon={icon} max={max} trend={trend} />;
                })}
              </div>
            </motion.div>
          )}

          {/* Help state for drills */}
          {!loading && progress && progress.drills_assigned_count === 0 && progress.feedback_ready_count > 0 && (
            <motion.div variants={staggerChild}>
              <Card className="border-amber/20 bg-amber/5">
                <CardContent className="flex items-start gap-3 px-5 py-4">
                  <BookOpen size={14} className="mt-0.5 shrink-0 text-amber" />
                  <div className="flex flex-1 flex-col gap-1">
                    <p className="text-sm font-semibold text-ink">Generate drills to unlock personalized practice</p>
                    <p className="text-xs text-ink-subtle">
                      You have feedback on {progress.feedback_ready_count} speech{progress.feedback_ready_count !== 1 ? "es" : ""}. Open a session and click &ldquo;Generate Drills&rdquo; to get 3 personalized exercises targeting your weakest skills.
                    </p>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Skeleton list */}
          {loading && (
            <motion.div variants={staggerChild} className="flex flex-col gap-1.5">
              {Array.from({ length: 3 }).map((_, i) => <SpeechSkeleton key={i} />)}
            </motion.div>
          )}

          {/* Recovery banner — speeches stuck in error or still processing */}
          {!loading && speeches.some((s) => s.status === "error" || s.status === "transcribing" || s.status === "analyzing") && (
            <motion.div variants={staggerChild}>
              <div className="rounded-xl border border-warn/25 bg-warn/5 px-4 py-3 flex items-start gap-3">
                <span className="mt-0.5 shrink-0 text-warn text-sm">⚠</span>
                <div className="flex flex-1 flex-col gap-1.5">
                  <p className="text-sm font-medium text-ink">Some sessions need attention</p>
                  <div className="flex flex-col gap-1">
                    {speeches
                      .filter((s) => s.status === "error" || s.status === "transcribing" || s.status === "analyzing")
                      .slice(0, 3)
                      .map((s) => (
                        <Link
                          key={s.id}
                          href={`/speech/${s.id}`}
                          className="flex items-center justify-between gap-2 rounded-md px-2 py-1 text-xs text-ink-muted transition-colors hover:bg-warn/10 hover:text-ink"
                        >
                          <span className="truncate font-medium">{s.title}</span>
                          <span className={`shrink-0 ${s.status === "error" ? "text-danger" : "text-warn"} capitalize`}>
                            {s.status === "error" ? "Failed — retry" : "In progress"}
                          </span>
                        </Link>
                      ))}
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* Speech list */}
          {!loading && speeches.length > 0 && (
            <motion.section variants={staggerChild} className="flex flex-col gap-3">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="section-stamp">Flow Reports</span>
                  <span className="rep-badge">{speeches.length}</span>
                </div>
                <Link href="/session" className="flex items-center gap-1 text-xs font-medium text-lav transition-colors hover:text-lav-hi">
                  <Play size={10} />
                  New session
                </Link>
              </div>
              <motion.div
                className="flex flex-col gap-1.5"
                variants={staggerParent(0.05)}
                initial="hidden"
                animate="show"
              >
                {speeches.map((s) => (
                  <SpeechCard key={s.id} s={s} onDelete={setDel} />
                ))}
              </motion.div>
            </motion.section>
          )}
        </motion.div>

      <DeleteDialog
        open={del !== null}
        onOpenChange={(o) => { if (!o && !deleting) { setDel(null); setDeleteErr(""); } }}
        title="Delete session?"
        description={`"${del?.title}" will be permanently deleted along with its transcript, flow, feedback, and drills.`}
        onConfirm={handleDelete}
        isDeleting={deleting}
        error={deleteErr}
      />
    </AppShell>
  );
}
