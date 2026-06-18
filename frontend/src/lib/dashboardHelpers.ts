/**
 * Dashboard next-action engine.
 *
 * Given the real data the dashboard already loads (speeches + progress summary),
 * deterministically pick the single most useful next step for the student. This
 * keeps the "what should I do next?" decision in one tested place instead of
 * scattered JSX conditionals.
 */

import type { Speech, ProgressSummary, SpeechType } from "@/types";

export type NextActionKind =
  | "retry-analysis"
  | "resume-analysis"
  | "finish-capture"
  | "recommended-drill"
  | "re-record"
  | "first-practice"
  | "keep-practicing";

/** Lucide icon name (kept as a string so this module stays render-agnostic). */
export type NextActionIcon =
  | "RotateCcw"
  | "Loader"
  | "Target"
  | "Repeat"
  | "Mic"
  | "TrendingUp";

export interface NextAction {
  kind: NextActionKind;
  /** Short eyebrow shown above the title. */
  eyebrow: string;
  title: string;
  /** One sentence on why this helps the student improve. */
  description: string;
  ctaLabel: string;
  href: string;
  icon: NextActionIcon;
  /** Optional secondary CTA (label + href). */
  secondary?: { label: string; href: string };
}

const PROCESSING_STATUSES = new Set(["pending", "transcribing", "analyzing"]);

function byNewest(a: Speech, b: Speech): number {
  return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
}

export function findFailedSpeech(speeches: Speech[]): Speech | null {
  return [...speeches].sort(byNewest).find((s) => s.status === "error") ?? null;
}

export function findInProgressSpeech(speeches: Speech[]): Speech | null {
  return (
    [...speeches].sort(byNewest).find((s) => PROCESSING_STATUSES.has(s.status)) ??
    null
  );
}

/**
 * A speech that was set up but never captured — status still `pending` with no
 * audio. The student abandoned mid-capture; their setup is saved and waiting.
 */
export function findUnfinishedCapture(speeches: Speech[]): Speech | null {
  return (
    [...speeches]
      .sort(byNewest)
      .find((s) => s.status === "pending" && !s.audio_url) ?? null
  );
}

/**
 * The newest completed *original* speech (not itself a re-record) that has NOT
 * already been improved on — the best candidate to re-record. Once a student
 * has re-recorded, we stop nudging that thread and encourage new material.
 */
export function findReRecordCandidate(speeches: Speech[]): Speech | null {
  const reRecordedParents = new Set(
    speeches.map((s) => s.parent_speech_id).filter(Boolean) as string[],
  );
  return (
    [...speeches]
      .sort(byNewest)
      .find(
        (s) =>
          s.status === "done" &&
          s.parent_speech_id === null &&
          !reRecordedParents.has(s.id),
      ) ?? null
  );
}

export interface NextActionInput {
  speeches: Speech[];
  progress: ProgressSummary | null;
  /** Focus skill label, if known (e.g. from skill averages). */
  focusSkill?: string | null;
}

export function selectNextAction({
  speeches,
  progress,
  focusSkill,
}: NextActionInput): NextAction {
  // 1. A failed analysis is the most urgent — the work exists but didn't finish.
  const failed = findFailedSpeech(speeches);
  if (failed) {
    return {
      kind: "retry-analysis",
      eyebrow: "Needs attention",
      title: "Finish analyzing your last speech",
      description:
        "Your recording is saved, but the analysis didn’t complete. Retry it — you won’t need to record again.",
      ctaLabel: "Retry analysis",
      href: `/speech/${failed.id}`,
      icon: "RotateCcw",
    };
  }

  // 2. A speech set up but never recorded — the setup is saved and waiting.
  //    (Checked before "in progress" because a pending speech with no audio is
  //    not actually analyzing — it's an abandoned capture.)
  const unfinished = findUnfinishedCapture(speeches);
  if (unfinished) {
    return {
      kind: "finish-capture",
      eyebrow: "Pick up where you left off",
      title: "Finish your unrecorded practice",
      description:
        "You set this speech up but haven’t recorded it yet. Your setup is saved — open the recorder and capture it.",
      ctaLabel: "Open recorder",
      href: `/speech/${unfinished.id}`,
      icon: "Mic",
      secondary: { label: "Start fresh", href: "/session" },
    };
  }

  // 3. An in-progress speech — let the student jump back to watch it finish.
  const inProgress = findInProgressSpeech(speeches);
  if (inProgress) {
    return {
      kind: "resume-analysis",
      eyebrow: "In progress",
      title: "Your speech is being analyzed",
      description:
        "Pick up where you left off and see your flow, ballot, and drills as soon as they’re ready.",
      ctaLabel: "Check progress",
      href: `/speech/${inProgress.id}`,
      icon: "Loader",
    };
  }

  // 4. A recommended drill targets the exact weakness from real feedback.
  const drill = progress?.incomplete_drills?.[0];
  if (drill) {
    return {
      kind: "recommended-drill",
      eyebrow: "Recommended drill",
      title: drill.title,
      description: `Targets ${formatSkill(drill.skill_target)} — the weakness your last ballot flagged. About 5 focused minutes.`,
      ctaLabel: "Start drill",
      href: `/drills/${drill.id}`,
      icon: "Target",
    };
  }

  // 4. Re-record a completed speech to close the coaching loop.
  const reRecord = findReRecordCandidate(speeches);
  if (reRecord) {
    return {
      kind: "re-record",
      eyebrow: "Close the loop",
      title: "Re-record to show improvement",
      description:
        "You’ve got feedback on this speech. Record it again to compare attempts and lock in the fix.",
      ctaLabel: "Re-record & compare",
      href: `/speech/${reRecord.id}`,
      icon: "Repeat",
      secondary: { label: "Start something new", href: "/session" },
    };
  }

  // 5. Brand-new student.
  if (speeches.length === 0) {
    return {
      kind: "first-practice",
      eyebrow: "Get started",
      title: "Record your first practice speech",
      description:
        "Give a 1–4 minute speech and RoundLab returns a flow, a judge-style ballot, and three drills built from it.",
      ctaLabel: "Record your first speech",
      href: "/session",
      icon: "Mic",
      secondary: { label: "See a sample report", href: "/demo" },
    };
  }

  // 6. Default — keep practicing, nudging toward the current focus skill.
  return {
    kind: "keep-practicing",
    eyebrow: "Keep building",
    title: focusSkill
      ? `Practice another speech to sharpen ${formatSkill(focusSkill)}`
      : "Practice another speech",
    description:
      "Consistent reps are what move your scores. Run another speech and keep the streak going.",
    ctaLabel: "Start a practice",
    href: "/session",
    icon: "TrendingUp",
  };
}

// ── Quick-start practice ─────────────────────────────────────────────────────

export interface QuickStartOption {
  type: SpeechType;
  label: string;
  /** Default speech length guidance, in minutes. */
  minutes: string;
}

export const QUICK_START_OPTIONS: QuickStartOption[] = [
  { type: "constructive", label: "Constructive", minutes: "4:00" },
  { type: "rebuttal", label: "Rebuttal", minutes: "4:00" },
  { type: "summary", label: "Summary", minutes: "3:00" },
  { type: "final_focus", label: "Final Focus", minutes: "2:00" },
  { type: "crossfire", label: "Crossfire", minutes: "3:00" },
];

/** Deep-link a quick-start choice into the practice setup flow. */
export function quickStartHref(type: SpeechType): string {
  return `/session?type=${type}`;
}

// ── Formatting ───────────────────────────────────────────────────────────────

export function formatSkill(skill: string): string {
  return skill
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (c) => c.toLowerCase())
    .trim();
}
