"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Mic, CheckCircle2, Target,
  MoreHorizontal, Trash2, ArrowUpRight, ArrowRight,
  Zap, Play, AlertTriangle, ChevronRight, Dumbbell,
} from "lucide-react";
import DeleteDialog from "@/components/DeleteDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  DropdownMenuRoot, DropdownMenuTrigger, DropdownMenuContent,
  DropdownMenuItem, DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { createClient } from "@/lib/supabase";
import { apiFetch, isBackendUnreachable } from "@/lib/api";
import { reducedSafe, staggerParent, staggerChild } from "@/lib/motion";
import { getSpeechStatusConfig } from "@/lib/debateHelpers";
import { motion } from "motion/react";
import FirstRunCommandCenter from "@/components/FirstRunCommandCenter";
import NextActionPanel from "@/components/dashboard/NextActionPanel";
import CoachingFocusCard from "@/components/dashboard/CoachingFocusCard";
import LoopStageCard from "@/components/dashboard/LoopStageCard";
import { DashboardSkeleton } from "@/components/dashboard/DashboardSkeleton";
import { deriveDashboardState } from "@/lib/dashboardModel";
import { deriveWorkoutProgress, getNextIncompleteStep } from "@/lib/workoutHelpers";
import NextMissionCard from "@/components/dashboard/NextMissionCard";
import { ContinueTrainingCard } from "@/components/training/ContinueTrainingCard";
import type { Speech, ProgressSummary, PilotSummary, Workout, StudentMission } from "@/types";

// ── Constants ─────────────────────────────────────────────────────────────────

const TYPE_LABEL: Record<string, string> = {
  constructive: "Constructive", rebuttal: "Rebuttal", summary: "Summary",
  final_focus: "Final Focus",  crossfire: "Crossfire",
};
const JUDGE_LABEL: Record<string, string> = {
  lay: "Lay", flow: "Flow", tech: "Tech", coach: "Coach",
};
const SKILL_LABELS: Record<string, string> = {
  weighing: "Impact Weighing", warranting: "Warranting", drops: "Drop Prevention",
  extensions: "Extensions", evidence: "Evidence Use", clash: "Clash",
  judge_adaptation: "Judge Adaptation", collapse: "Collapse Strategy", line_by_line: "Line-by-Line",
};
const SKILL_GRID = [
  { key: "clash",            label: "Clash",           icon: "⚔", max: 20 },
  { key: "weighing",         label: "Impact Weighing", icon: "⚖", max: 20 },
  { key: "extensions",       label: "Extensions",      icon: "↗", max: 20 },
  { key: "drops",            label: "Drop Prevention", icon: "🛡", max: 20 },
  { key: "judge_adaptation", label: "Judge Adapt.",    icon: "👁", max: 20 },
] as const;

type BV = "default" | "indigo" | "green" | "amber" | "red";

function speechBadge(s: Speech): { label: string; variant: BV } {
  const cfg = getSpeechStatusConfig(s.status);
  if (s.status === "pending" && s.audio_url) return { label: "Audio uploaded", variant: "default" };
  return { label: cfg.isProcessing ? `${cfg.label}…` : cfg.label, variant: cfg.badge as BV };
}
function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}
function fmtPercent(val: number | null) {
  return val === null ? "—" : `${Math.round(val * 100)}%`;
}

// ── Speech card ───────────────────────────────────────────────────────────────

const PIPELINE_STEPS = [
  { key: "audio",  label: "Audio" },
  { key: "tx",     label: "Transcript" },
  { key: "flow",   label: "Flow" },
  { key: "ballot", label: "Ballot" },
  { key: "drills", label: "Drills" },
];

function pipelineDone(s: Speech, key: string): boolean {
  if (key === "audio")  return !!s.audio_url;
  if (key === "tx")     return s.status !== "pending";
  if (key === "flow")   return s.status === "analyzing" || s.status === "done";
  if (key === "ballot") return s.status === "done";
  return false;
}

function SpeechCard({ s, onDelete }: { s: Speech; onDelete: (s: Speech) => void }) {
  const badge = speechBadge(s);
  const accentBorder =
    s.status === "done"           ? "border-l-ok/60"
    : s.status === "error"        ? "border-l-danger/60"
    : s.status === "analyzing"    ? "border-l-warn/60"
    : s.status === "transcribing" ? "border-l-lav/40"
    : "border-l-hairline";

  return (
    <Card className={`border-l-2 transition-colors duration-150 hover:border-hairline-strong ${accentBorder}`}>
      <CardContent className="flex items-center gap-4 px-5 py-4">
        <Link href={`/speech/${s.id}`} className="group flex min-w-0 flex-1 items-start gap-3.5">
          <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-hairline bg-surface-2 transition-colors group-hover:border-lav/30 group-hover:bg-lav/5">
            <Mic size={13} className="text-ink-faint transition-colors group-hover:text-lav" aria-hidden="true" />
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
            <div className="mt-1.5 flex items-center gap-0.5">
              {PIPELINE_STEPS.map((step, i, arr) => (
                <div key={step.key} className="flex items-center gap-0.5">
                  <div
                    title={step.label}
                    className={`h-1.5 rounded-full transition-colors ${pipelineDone(s, step.key) ? "w-5 bg-lav" : "w-3 bg-hairline"}`}
                  />
                  {i < arr.length - 1 && <div className="h-px w-0.5 bg-hairline" />}
                </div>
              ))}
              <span className="ml-1.5 text-xs text-ink-faint">{fmtDate(s.created_at)}</span>
            </div>
          </div>
        </Link>

        <div className="flex shrink-0 items-center gap-2">
          <Badge variant={badge.variant}>{badge.label}</Badge>
          <DropdownMenuRoot>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                onClick={(e) => e.preventDefault()}
                className="flex h-6 w-6 items-center justify-center rounded-md text-ink-faint transition-colors hover:bg-surface-2 hover:text-ink-subtle focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50"
                aria-label="Speech options"
              >
                <MoreHorizontal size={13} aria-hidden="true" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem asChild>
                <Link href={`/speech/${s.id}`} className="flex items-center gap-2">
                  <ArrowUpRight size={12} /> View flow report
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem destructive onSelect={() => onDelete(s)}>
                <Trash2 size={12} /> Delete session
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenuRoot>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const router = useRouter();

  const [userId,        setUserId]       = useState<string | null>(null);
  const [speeches,      setSpeeches]     = useState<Speech[]>([]);
  const [progress,      setProgress]     = useState<ProgressSummary | null>(null);
  const [pilotSummary,  setPilotSummary] = useState<PilotSummary | null>(null);
  const [latestWorkout, setLatestWorkout] = useState<Workout | null>(null);
  const [mission,       setMission]      = useState<StudentMission | null>(null);
  const [missionLoading, setMissionLoading] = useState(true);
  const [missionErr,    setMissionErr]   = useState("");
  const [nextTrainingAction, setNextTrainingAction] = useState<Record<string, unknown> | null>(null);
  const [trainingLoading, setTrainingLoading] = useState(true);
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

        const [speechesData, progressData] = await Promise.all([
          apiFetch<Speech[]>(`/speeches?user_id=${data.user.id}`),
          apiFetch<ProgressSummary>(`/users/${data.user.id}/progress`),
        ]);
        setSpeeches(speechesData);
        setProgress(progressData);

        try {
          const pilotData = await apiFetch<PilotSummary>(`/users/${data.user.id}/pilot-summary`);
          setPilotSummary(pilotData);
        } catch { /* non-critical */ }

        apiFetch<Workout[]>(`/workouts?user_id=${data.user.id}`)
          .then((ws) => { if (ws.length > 0) setLatestWorkout(ws[0]); })
          .catch(() => {});

        // Next Mission — non-blocking, shown as its own card
        apiFetch<StudentMission | null>(`/missions/next?user_id=${data.user.id}`)
          .then((m) => { setMission(m); })
          .catch(() => { setMissionErr("Mission unavailable"); })
          .finally(() => { setMissionLoading(false); });

        // Next Training Action — non-blocking, unified priority pipeline
        apiFetch<Record<string, unknown>>(`/training/next-action?user_id=${data.user.id}`)
          .then((action) => { setNextTrainingAction(action); })
          .catch(() => { setNextTrainingAction(null); })
          .finally(() => { setTrainingLoading(false); });
      })
      .catch((e) =>
        setErr(
          isBackendUnreachable(e)
            ? "Could not reach the server. Start the backend and refresh."
            : "Could not load your data. Please refresh and try again.",
        ),
      )
      .finally(() => setLoading(false));
  }, [router]);

  async function handleDelete() {
    if (!del || !userId) return;
    setDeleting(true);
    setDeleteErr("");
    try {
      await apiFetch(`/speeches/${del.id}?user_id=${userId}`, { method: "DELETE" });
      setSpeeches((p) => p.filter((s) => s.id !== del.id));
      const progressData = await apiFetch<ProgressSummary>(`/users/${userId}/progress`);
      setProgress(progressData);
      try {
        const pilotData = await apiFetch<PilotSummary>(`/users/${userId}/pilot-summary`);
        setPilotSummary(pilotData);
      } catch { /* non-critical */ }
      setDel(null);
    } catch (e: unknown) {
      setDeleteErr(e instanceof Error ? e.message : "Could not delete this session.");
    } finally { setDeleting(false); }
  }

  const state   = deriveDashboardState(speeches, progress);
  const stagger = reducedSafe(staggerParent(0.06, 0.03));
  const child   = reducedSafe(staggerChild);

  return (
    <>
      <motion.div
        className="mx-auto flex max-w-5xl flex-col gap-5 px-4 py-6 sm:px-6 sm:py-7"
        variants={stagger}
        initial="hidden"
        animate="show"
      >
        {/* Error */}
        {!loading && err && (
          <div role="alert" className="flex items-start gap-3 rounded-xl border border-danger/25 bg-danger/5 px-4 py-3">
            <AlertTriangle size={16} className="mt-0.5 shrink-0 text-danger" aria-hidden="true" />
            <p className="text-sm text-danger">{err}</p>
          </div>
        )}

        {/* Loading skeleton */}
        {loading && <DashboardSkeleton />}

        {!loading && (
          <>
            {/* 1. Next Best Action — dominant hero ───────────────────── */}
            <motion.div variants={child}>
              <NextActionPanel action={state.nextAction} />
            </motion.div>

            {/* 1b. Next Mission coaching card */}
            <motion.div variants={child}>
              <section aria-label="Next mission">
                <div className="mb-2 flex items-center gap-2">
                  <span className="text-eyebrow text-ink-subtle">Next mission</span>
                </div>
                <NextMissionCard
                  loading={missionLoading}
                  error={missionErr || null}
                  mission={mission}
                  hasSpeech={speeches.length > 0}
                />
              </section>
            </motion.div>

            {/* 1c. Continue Training CTA */}
            <motion.div variants={child}>
              <section aria-label="Training plan">
                <div className="mb-2 flex items-center gap-2">
                  <span className="text-eyebrow text-ink-subtle">Continue training</span>
                </div>
                <ContinueTrainingCard
                  nextAction={nextTrainingAction as Parameters<typeof ContinueTrainingCard>[0]["nextAction"]}
                  loading={trainingLoading}
                />
              </section>
            </motion.div>

            {/* 2. Recent speech insight — priority skill from latest data */}
            {state.showRecentInsight && progress && (
              <motion.div variants={child}>
                <CoachingFocusCard
                  skillAverages={progress.skill_averages}
                  feedbackReadyCount={progress.feedback_ready_count}
                />
              </motion.div>
            )}

            {/* New user: contextual first-run guide */}
            {state.userStage === "new-user" && (
              <motion.div variants={child}>
                <FirstRunCommandCenter userId={userId} />
              </motion.div>
            )}

            {/* Mid-funnel: has speech, no drills attempted yet */}
            {state.showMidFunnelGuide && progress && (
              <motion.div variants={child}>
                <MidFunnelGuide progress={progress} speeches={speeches} />
              </motion.div>
            )}

            {/* 3. Training loop stage ─────────────────────────────────── */}
            {progress && (
              <motion.div variants={child}>
                <LoopStageCard progress={progress} userStage={state.userStage} />
              </motion.div>
            )}

            {/* 4. Skill trajectory ────────────────────────────────────── */}
            {state.showSkillTrajectory && progress && (
              <motion.div variants={child}>
                <SkillTrajectorySection progress={progress} pilotSummary={pilotSummary} />
              </motion.div>
            )}

            {/* 5. Upcoming drills ─────────────────────────────────────── */}
            {state.showDrillQueue && progress && (
              <motion.div variants={child}>
                <DrillQueueSection
                  drills={progress.incomplete_drills}
                  workout={latestWorkout}
                />
              </motion.div>
            )}

            {/* 6. Speech history ──────────────────────────────────────── */}
            {state.showSpeechHistory && (
              <motion.div variants={child} className="flex flex-col gap-3">
                {state.hasPendingRecovery && <RecoveryBanner speeches={speeches} />}
                <SpeechHistorySection speeches={speeches} onDelete={setDel} />
              </motion.div>
            )}
          </>
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
    </>
  );
}

// ── Mid-funnel onboarding ─────────────────────────────────────────────────────

function MidFunnelGuide({
  progress,
  speeches,
}: {
  progress: ProgressSummary;
  speeches: Speech[];
}) {
  const hasFeedback  = progress.feedback_ready_count > 0;
  const latestDone   = speeches.find((s) => s.status === "done");
  const isProcessing = speeches.some((s) =>
    ["pending", "transcribing", "analyzing"].includes(s.status),
  );

  // Processing — show a subtle waiting hint
  if (isProcessing && !hasFeedback) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-hairline bg-surface-1 px-4 py-3">
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-lav/25 bg-lav/10" aria-hidden="true">
          <span className="h-2 w-2 motion-safe:animate-pulse rounded-full bg-lav" />
        </span>
        <p className="text-sm text-ink-subtle">
          Your speech is being analyzed — check back in a moment for your flow and ballot.
        </p>
      </div>
    );
  }

  // Feedback ready but no drills — the key conversion nudge
  if (hasFeedback && latestDone) {
    return (
      <div className="flex items-start gap-3 rounded-xl border border-lav/20 bg-lav/5 px-4 py-4">
        <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-lav/15" aria-hidden="true">
          <Target size={15} className="text-lav-hi" />
        </span>
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <p className="text-sm font-semibold text-ink">Ready to drill</p>
          <p className="text-sm text-ink-subtle">
            Your ballot is ready. Open your speech report to generate 3 targeted drills based on your actual weaknesses.
          </p>
        </div>
        <Button asChild size="sm" className="shrink-0">
          <Link href={`/speech/${latestDone.id}`}>
            Open report <ArrowRight size={12} aria-hidden="true" />
          </Link>
        </Button>
      </div>
    );
  }

  // First speech exists but still "pending" with no processing (edge: setup-only)
  return (
    <div className="flex items-start gap-3 rounded-xl border border-hairline bg-surface-1 px-4 py-3">
      <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-ok" aria-hidden="true" />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <p className="text-sm font-semibold text-ink">First session recorded</p>
        <p className="text-xs text-ink-subtle">
          Once analysis finishes, open the report and tap &ldquo;Generate Drills&rdquo; to start practicing.
        </p>
      </div>
      {latestDone && (
        <Link
          href={`/speech/${latestDone.id}`}
          className="shrink-0 text-xs font-medium text-lav transition-colors hover:text-lav-hi focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50 focus-visible:rounded"
        >
          View →
        </Link>
      )}
    </div>
  );
}

// ── Skill trajectory section ──────────────────────────────────────────────────

function SkillTrajectorySection({
  progress,
  pilotSummary,
}: {
  progress: ProgressSummary;
  pilotSummary: PilotSummary | null;
}) {
  const showTrends =
    pilotSummary?.skill_trends != null && progress.feedback_ready_count >= 2;

  return (
    <section aria-label="Skill trajectory" className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-eyebrow text-ink-subtle">Skill trajectory</span>
          <span className="rep-badge">
            avg · {progress.feedback_ready_count} speech{progress.feedback_ready_count !== 1 ? "es" : ""}
          </span>
        </div>
        <Link
          href="/progress"
          className="flex items-center gap-1 text-xs font-medium text-lav transition-colors hover:text-lav-hi focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50 focus-visible:rounded"
        >
          Full progress <ArrowRight size={11} aria-hidden="true" />
        </Link>
      </div>

      <Card>
        <CardContent className="grid grid-cols-1 gap-4 px-5 py-5 sm:grid-cols-2">
          {SKILL_GRID.map((skill) => {
            const value = (progress.skill_averages as Record<string, number> | null)?.[skill.key] ?? 0;
            const pct   = (value / skill.max) * 100;
            const barClass = pct >= 70 ? "bg-lav" : pct >= 50 ? "bg-warn" : "bg-danger";
            const trends = showTrends ? pilotSummary!.skill_trends : null;
            const trendVal = trends?.[skill.key as keyof typeof trends];
            const trendDir = trendVal?.trend === "improving" ? "up"
              : trendVal?.trend === "needs_attention" ? "down"
              : null;

            return (
              <div key={skill.key} className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-eyebrow text-ink-subtle">
                    <span aria-hidden="true">{skill.icon}</span>
                    {" "}{skill.label}
                    {trendDir === "up"   && <span className="ml-1 text-ok" aria-label="improving">↑</span>}
                    {trendDir === "down" && <span className="ml-1 text-danger" aria-label="declining">↓</span>}
                  </span>
                  <span className="font-mono text-xs font-bold tabular-nums text-ink">
                    {value.toFixed(1)}<span className="font-normal text-ink-faint">/{skill.max}</span>
                  </span>
                </div>
                <div
                  className="h-1.5 overflow-hidden rounded-full bg-hairline"
                  role="progressbar"
                  aria-valuenow={value}
                  aria-valuemin={0}
                  aria-valuemax={skill.max}
                  aria-label={skill.label}
                >
                  <div
                    className={`h-full rounded-full motion-safe:transition-all motion-safe:duration-700 ${barClass}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })}

          {progress.drill_completion_rate !== null && (
            <div className="flex flex-col gap-1.5 sm:col-span-2">
              <div className="flex items-center justify-between">
                <span className="text-eyebrow text-ink-subtle">Drill completion</span>
                <span className="font-mono text-xs font-bold text-ink">{fmtPercent(progress.drill_completion_rate)}</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-hairline">
                <div
                  className="h-full rounded-full bg-ok motion-safe:transition-all motion-safe:duration-700"
                  style={{ width: `${(progress.drill_completion_rate || 0) * 100}%` }}
                />
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </section>
  );
}

// ── Drill queue section ───────────────────────────────────────────────────────

function DrillQueueSection({
  drills,
  workout,
}: {
  drills: ProgressSummary["incomplete_drills"];
  workout: Workout | null;
}) {
  const next         = drills[0];
  const workoutNext  = workout && workout.status !== "completed" ? getNextIncompleteStep(workout) : null;
  const workoutProg  = workout && workout.status !== "completed" ? deriveWorkoutProgress(workout) : null;

  return (
    <section aria-label="Upcoming drills" className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <Zap size={14} className="text-lav" aria-hidden="true" />
        <h2 className="text-heading text-ink">Upcoming drills</h2>
        {drills.length > 1 && <span className="rep-badge">{drills.length}</span>}
      </div>

      <Card className="border-lav/20 bg-lav/5">
        <CardContent className="flex flex-col gap-4 px-5 py-5">
          {/* Primary drill */}
          <div className="flex items-start justify-between gap-3">
            <div className="flex min-w-0 flex-1 flex-col gap-1">
              <p className="truncate text-sm font-semibold text-ink">{next.title}</p>
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="rounded-full border border-lav/25 bg-lav/10 px-2 py-0.5 text-[10px] font-semibold text-lav">
                  {SKILL_LABELS[next.skill_target] ?? next.skill_target}
                </span>
                <span className="text-[10px] capitalize text-ink-faint">{next.difficulty}</span>
                {next.speech_title && (
                  <span className="text-[10px] text-ink-faint">From: {next.speech_title}</span>
                )}
              </div>
            </div>
            <Button asChild size="sm" className="shrink-0 gap-1.5">
              <Link href={`/drills/${next.id}`}>
                Open workspace <ArrowRight size={11} aria-hidden="true" />
              </Link>
            </Button>
          </div>

          {/* Additional drills */}
          {drills.length > 1 && (
            <div className="flex flex-col gap-1 border-t border-lav/10 pt-3">
              <p className="mb-1 text-xs font-medium text-ink-subtle">Also queued:</p>
              {drills.slice(1, 4).map((d) => (
                <Link
                  key={d.id}
                  href={`/drills/${d.id}`}
                  className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 text-xs text-ink-subtle transition-colors hover:bg-lav/5 hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50"
                >
                  <span className="truncate">{d.title}</span>
                  <span className="shrink-0 capitalize text-ink-faint">{d.status.replace("_", " ")}</span>
                </Link>
              ))}
              {drills.length > 4 && (
                <p className="px-2 text-xs text-ink-faint">+{drills.length - 4} more</p>
              )}
            </div>
          )}

          {/* Workout context — compact secondary row */}
          {workoutProg && workoutNext && workout && (
            <div className="flex items-center justify-between gap-3 border-t border-lav/10 pt-3">
              <div className="flex min-w-0 items-center gap-2">
                <Dumbbell size={13} className="shrink-0 text-lav" aria-hidden="true" />
                <span className="truncate text-xs text-ink-subtle">
                  Today&apos;s prep: {workoutProg.completed}/{workoutProg.total} done · {workoutNext.title}
                </span>
              </div>
              <Link
                href={`/speech/${workout.speech_id}`}
                className="shrink-0 flex items-center gap-0.5 text-[10px] font-medium text-lav hover:underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-lav/50"
              >
                Continue <ChevronRight size={10} aria-hidden="true" />
              </Link>
            </div>
          )}
        </CardContent>
      </Card>
    </section>
  );
}

// ── Recovery banner ───────────────────────────────────────────────────────────

function RecoveryBanner({ speeches }: { speeches: Speech[] }) {
  const stuck = speeches.filter(
    (s) => s.status === "error" || s.status === "transcribing" || s.status === "analyzing",
  );
  if (stuck.length === 0) return null;
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-start gap-3 rounded-xl border border-warn/25 bg-warn/5 px-4 py-3"
    >
      <AlertTriangle size={15} className="mt-0.5 shrink-0 text-warn" aria-hidden="true" />
      <div className="flex flex-1 flex-col gap-1.5">
        <p className="text-sm font-medium text-ink">
          {stuck.length === 1 ? "1 session needs attention" : `${stuck.length} sessions need attention`}
        </p>
        <div className="flex flex-col gap-1">
          {stuck.slice(0, 3).map((s) => (
            <Link
              key={s.id}
              href={`/speech/${s.id}`}
              className="flex items-center justify-between gap-2 rounded-md px-2 py-1 text-xs text-ink-subtle transition-colors hover:bg-warn/10 hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-warn/50"
            >
              <span className="truncate font-medium">{s.title}</span>
              <span className={`shrink-0 ${s.status === "error" ? "text-danger" : "text-warn"}`}>
                {s.status === "error" ? "Failed — retry" : "In progress"}
              </span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Speech history section ────────────────────────────────────────────────────

function SpeechHistorySection({
  speeches,
  onDelete,
}: {
  speeches: Speech[];
  onDelete: (s: Speech) => void;
}) {
  return (
    <section aria-label="Speech history" className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-eyebrow text-ink-subtle">Flow reports</span>
          <span className="rep-badge">{speeches.length}</span>
        </div>
        <Link
          href="/session"
          className="flex items-center gap-1 text-xs font-medium text-lav transition-colors hover:text-lav-hi focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50 focus-visible:rounded"
        >
          <Play size={10} aria-hidden="true" /> New session
        </Link>
      </div>
      <div className="flex flex-col gap-1.5">
        {speeches.map((s) => (
          <SpeechCard key={s.id} s={s} onDelete={onDelete} />
        ))}
      </div>
    </section>
  );
}

