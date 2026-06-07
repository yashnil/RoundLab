"use client";

/**
 * ReportVerdictPanel — Two-column above-fold panel for completed speech reports.
 *
 * Left:  Score ring / Grade / Summary / Mini dimension bars / Biggest Issue (with argument chain)
 * Right: Speech metadata / Judge mode selector / Next action CTAs
 *
 * Immediately answers: "What happened? What cost me the round? What do I do now?"
 */

import { motion, useMotionValue, useTransform, animate } from "motion/react";
import { useEffect } from "react";
import { ArrowRight, ChevronRight, RefreshCw, Target } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import JudgeModeSelector, { type JudgeViewMode } from "@/components/JudgeModeSelector";
import { EASE } from "@/lib/motion";
import type { DebateIssue, Drill, FeedbackReport, FeedbackScores, Speech } from "@/types";

// ── Animated count-up ──────────────────────────────────────────────────────────

function AnimatedScore({ score }: { score: number }) {
  const mv = useMotionValue(0);
  const display = useTransform(mv, (v) => Math.round(v).toString());
  useEffect(() => {
    const ctrl = animate(mv, score, { duration: 1.2, delay: 0.2, ease: EASE });
    return ctrl.stop;
  }, [mv, score]);
  return <motion.span>{display}</motion.span>;
}

// ── Grade config ───────────────────────────────────────────────────────────────

function resolveGrade(score: number | null) {
  if (score === null) return { grade: "Not scored", ring: "border-hairline-strong", glow: "" };
  if (score >= 90) return { grade: "Tournament-Ready",        ring: "border-ok",    glow: "oklch(0.620 0.170 145 / 0.30)" };
  if (score >= 80) return { grade: "Strong",                  ring: "border-ok",    glow: "oklch(0.620 0.170 145 / 0.25)" };
  if (score >= 70) return { grade: "Solid",                   ring: "border-lav",   glow: "oklch(0.510 0.156 278 / 0.30)" };
  if (score >= 60) return { grade: "Developing",              ring: "border-lav",   glow: "oklch(0.510 0.156 278 / 0.25)" };
  if (score >= 50) return { grade: "Flawed but Complete",     ring: "border-warn",  glow: "oklch(0.750 0.155 74 / 0.25)"  };
  if (score >= 40) return { grade: "Needs Foundation",        ring: "border-warn",  glow: "oklch(0.750 0.155 74 / 0.20)"  };
  return                  { grade: "Severely Underdeveloped", ring: "border-danger", glow: "oklch(0.640 0.215 25 / 0.20)" };
}

// ── Mini dimension bar row ─────────────────────────────────────────────────────

const DIM_LABELS: Record<keyof FeedbackScores, string> = {
  clash:            "Clash",
  weighing:         "Weighing",
  extensions:       "Extensions",
  drops:            "Drops",
  judge_adaptation: "Judge",
};

function dimColor(val: number): string {
  if (val >= 16) return "bg-ok";
  if (val >= 12) return "bg-lav";
  if (val >= 8)  return "bg-warn";
  return "bg-danger";
}

function MiniScoreBars({ scores }: { scores: FeedbackScores }) {
  return (
    <div className="mt-4 grid grid-cols-5 gap-2">
      {(Object.keys(DIM_LABELS) as (keyof FeedbackScores)[]).map((key) => {
        const val = scores[key] ?? 0;
        const pct = Math.round((Math.max(0, Math.min(20, val)) / 20) * 100);
        return (
          <div key={key} className="flex flex-col items-center gap-1">
            <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-surface-3">
              <motion.div
                className={`absolute inset-y-0 left-0 rounded-full ${dimColor(val)}`}
                initial={{ width: 0 }}
                animate={{ width: `${pct}%` }}
                transition={{ duration: 0.8, delay: 0.5, ease: EASE }}
              />
            </div>
            <span className="text-[9px] font-medium text-ink-faint leading-none">
              {DIM_LABELS[key]}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ── Argument chain — issue evidence visual ─────────────────────────────────────

function ArgumentChain({ labels, color }: { labels: string[]; color: "danger" | "warn" }) {
  if (labels.length === 0) return null;
  return (
    <div className={`rounded-lg border border-${color}/15 bg-${color}/5 px-3 py-2`}>
      <p className={`mb-1.5 text-[9px] font-semibold uppercase tracking-wider text-${color}/60`}>
        Found in your flow
      </p>
      <div className="flex flex-wrap items-center gap-1">
        {labels.map((label, i) => (
          <span key={i} className="flex items-center gap-1">
            {i > 0 && <ChevronRight size={9} className={`shrink-0 text-${color}/35`} />}
            <span className={`rounded border border-${color}/20 bg-${color}/10 px-2 py-0.5 text-[10px] font-medium text-ink-muted`}>
              {label}
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}

// ── Top issue card (compact but rich) ─────────────────────────────────────────

function TopIssueCard({
  issue,
  priorities,
}: {
  issue?: DebateIssue | null;
  priorities?: string[];
}) {
  const title          = issue?.title          ?? priorities?.[0] ?? null;
  const recommendation = issue?.recommendation ?? null;
  const whyItMatters   = issue?.why_it_matters ?? null;
  const severity       = issue?.severity       ?? "medium";
  const color: "danger" | "warn" = severity === "high" ? "danger" : "warn";
  const affectedLabels = issue?.affected_argument_labels?.slice(0, 4) ?? [];

  if (!title) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.25, ease: EASE }}
      className={`rounded-xl border border-${color}/25 bg-${color}/5`}
      style={{
        boxShadow: severity === "high"
          ? "0 0 24px -8px oklch(0.640 0.215 25 / 0.15)"
          : "0 0 20px -8px oklch(0.750 0.155 74 / 0.12)",
      }}
    >
      {/* Header */}
      <div className={`flex items-center justify-between gap-2 border-b border-${color}/15 px-4 py-2`}>
        <div className="flex items-center gap-2">
          <span className={`h-1.5 w-1.5 shrink-0 rounded-full bg-${color} analysis-step-active`} />
          <p className={`text-eyebrow text-${color}`}>Round-Losing Issue</p>
        </div>
        <span className={`rounded-full border border-${color}/20 bg-${color}/10 px-2 py-0.5 text-[10px] font-semibold capitalize text-${color}`}>
          {severity}
        </span>
      </div>

      <div className="flex flex-col gap-2.5 px-4 py-3">
        {/* Issue title */}
        <p className="text-sm font-semibold leading-snug text-ink">{title}</p>

        {/* Argument chain — where this issue appears */}
        <ArgumentChain labels={affectedLabels} color={color} />

        {/* Why it costs you rounds */}
        {whyItMatters && (
          <p className="text-xs leading-relaxed text-ink-muted">{whyItMatters}</p>
        )}

        {/* Recommendation */}
        {recommendation && (
          <div className={`flex items-start gap-2 rounded-lg border border-${color}/15 bg-surface-1 px-3 py-2`}>
            <ArrowRight size={10} className={`mt-0.5 shrink-0 text-${color}`} />
            <p className="text-xs leading-relaxed text-ink-muted">{recommendation}</p>
          </div>
        )}
      </div>
    </motion.div>
  );
}

// ── Metadata chip ──────────────────────────────────────────────────────────────

function MetaChip({ label }: { label: string }) {
  return (
    <span className="rounded-full border border-hairline bg-surface-2 px-2.5 py-1 text-xs font-medium capitalize text-ink-subtle">
      {label}
    </span>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

interface ReportVerdictPanelProps {
  speech: Speech;
  feedback: FeedbackReport;
  drills: Drill[];
  judgeViewMode: JudgeViewMode;
  onJudgeModeChange: (m: JudgeViewMode) => void;
  onStartNewAttempt: () => void;
  overallScore: number | null;
}

const TYPE_LABEL: Record<string, string> = {
  constructive: "Constructive", rebuttal: "Rebuttal",
  summary: "Summary", final_focus: "Final Focus", crossfire: "Crossfire",
};

export default function ReportVerdictPanel({
  speech,
  feedback,
  drills,
  judgeViewMode,
  onJudgeModeChange,
  onStartNewAttempt,
  overallScore,
}: ReportVerdictPanelProps) {
  const { grade, ring, glow } = resolveGrade(overallScore);

  // Top structured issue (prefer high-severity v2+)
  const topIssue =
    feedback.raw_feedback?.structured_issues?.find((i) => i.severity === "high")
    ?? feedback.raw_feedback?.structured_issues?.[0]
    ?? null;

  // Drill state
  const assignedDrills = drills.filter((d) => d.status === "assigned");
  const allDone        = drills.length > 0 && drills.every((d) => d.status !== "assigned");

  // Format duration
  const dur = speech.duration_seconds;
  const durLabel = dur
    ? dur < 60 ? `${dur}s` : `${Math.floor(dur / 60)}:${String(dur % 60).padStart(2, "0")}`
    : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: EASE }}
      className="grid grid-cols-1 gap-3 lg:grid-cols-[1fr_260px]"
    >

      {/* ── Left: Score + Grade + Dimension bars + Biggest Issue ──────────── */}
      <div
        className="beam-top overflow-hidden rounded-2xl border border-lav/20 bg-gradient-to-br from-lav/5 via-surface-1 to-surface-1 p-5"
        style={{ boxShadow: `0 0 60px -16px ${glow || "oklch(0.510 0.156 278 / 0.20)"}` }}
      >
        {/* Score ring + grade */}
        <div className="flex items-center gap-5">
          <div className="relative shrink-0">
            <div className={`absolute inset-0 rounded-full opacity-20 blur-md ${ring.replace("border-", "bg-")}`} />
            <div className={`relative flex h-20 w-20 flex-col items-center justify-center rounded-full border-[3px] bg-canvas ${ring}`}>
              <span className="text-3xl font-bold leading-none tracking-tight text-ink">
                {overallScore !== null ? <AnimatedScore score={overallScore} /> : "—"}
              </span>
              <span className="mt-0.5 text-[10px] text-ink-faint">/100</span>
            </div>
          </div>

          <div className="flex min-w-0 flex-col gap-1.5">
            <p className="text-heading text-ink">{grade}</p>
            {feedback.summary && (
              <p className="text-sm leading-relaxed text-ink-subtle line-clamp-3">
                {feedback.summary}
              </p>
            )}
          </div>
        </div>

        {/* Mini dimension score bars */}
        {feedback.scores && <MiniScoreBars scores={feedback.scores} />}

        {/* Biggest issue with argument chain */}
        <div className="mt-4">
          <TopIssueCard
            issue={topIssue}
            priorities={feedback.raw_feedback?.top_3_priorities}
          />
        </div>
      </div>

      {/* ── Right: Metadata + Judge Lens + CTAs ───────────────────────────── */}
      <div className="flex flex-col gap-3">

        {/* Speech metadata */}
        <div className="rounded-2xl border border-hairline bg-surface-1 p-4">
          <p className="mb-2 text-eyebrow text-ink-faint">Speech details</p>
          <div className="flex flex-wrap items-center gap-1.5">
            <MetaChip label={TYPE_LABEL[speech.speech_type] ?? speech.speech_type} />
            {speech.side       && <MetaChip label={speech.side} />}
            {speech.judge_type && <MetaChip label={`${speech.judge_type} judge`} />}
            {durLabel          && <MetaChip label={durLabel} />}
          </div>
          {speech.topic && (
            <p className="mt-2 text-xs leading-relaxed text-ink-faint">
              <span className="font-medium text-ink-subtle">Resolution:</span> {speech.topic}
            </p>
          )}
        </div>

        {/* Judge lens selector */}
        <div className="rounded-2xl border border-hairline bg-surface-1 p-4">
          <JudgeModeSelector value={judgeViewMode} onChange={onJudgeModeChange} />
        </div>

        {/* Next step CTA */}
        <div className="flex flex-col gap-2 rounded-2xl border border-hairline bg-surface-1 p-4">
          <p className="text-eyebrow text-ink-faint">Next step</p>

          {assignedDrills.length > 0 ? (
            <>
              <p className="text-xs font-semibold text-ink">
                {assignedDrills.length} drill{assignedDrills.length > 1 ? "s" : ""} waiting
              </p>
              <p className="text-[11px] text-ink-faint leading-relaxed line-clamp-2">
                {assignedDrills[0]?.title}
              </p>
              <Button asChild size="sm" className="w-full gap-1.5">
                <a href="#drills">
                  <Target size={12} />
                  Start drill
                </a>
              </Button>
            </>
          ) : allDone ? (
            <>
              <p className="text-xs text-ok">✓ All drills completed</p>
              <Button size="sm" onClick={onStartNewAttempt} className="w-full gap-1.5">
                <RefreshCw size={12} />
                New Attempt
              </Button>
            </>
          ) : drills.length === 0 ? (
            <>
              <p className="text-xs text-ink-subtle">Generate drills to start practicing</p>
              <Button asChild size="sm" variant="secondary" className="w-full">
                <a href="#drills">Generate Drills</a>
              </Button>
            </>
          ) : (
            <Button size="sm" onClick={onStartNewAttempt} className="w-full gap-1.5">
              <RefreshCw size={12} /> New Attempt
            </Button>
          )}

          <Link
            href="/dashboard"
            className="flex items-center justify-center gap-1 text-xs text-ink-faint transition-colors hover:text-ink"
          >
            Back to dashboard <ArrowRight size={10} />
          </Link>
        </div>

      </div>
    </motion.div>
  );
}
