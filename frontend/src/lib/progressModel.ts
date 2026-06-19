/**
 * Progress workspace model — turns the ProgressSummary + the student's speeches
 * into a development view: current focus, practice coverage, milestones, and a
 * generated weekly plan. Pure + tested. Honest about sparse data: we never
 * fabricate trends or claim a drill caused improvement without evidence.
 */

import type { ProgressSummary, SkillAverages, Speech, SpeechType } from "@/types";

const SKILL_LABELS: Record<keyof SkillAverages, string> = {
  clash: "Clash",
  weighing: "Impact weighing",
  extensions: "Extensions",
  drops: "Drop prevention",
  judge_adaptation: "Judge adaptation",
};

export interface CurrentFocus {
  skill: string;
  score: number;
  /** Why it's prioritized. */
  reason: string;
  /** Suggested practice deep-link. */
  href: string;
  /** True when there isn't enough data to be confident. */
  lowConfidence: boolean;
}

export function deriveCurrentFocus(p: ProgressSummary | null): CurrentFocus | null {
  if (!p?.skill_averages) return null;
  const entries = Object.entries(p.skill_averages) as [keyof SkillAverages, number][];
  if (entries.length === 0) return null;
  const [key, score] = entries.sort((a, b) => a[1] - b[1])[0];
  return {
    skill: SKILL_LABELS[key],
    score,
    reason: `Lowest scored dimension across ${p.feedback_ready_count} analyzed speech${p.feedback_ready_count !== 1 ? "es" : ""}.`,
    href: `/session?goal=${encodeURIComponent("Sharpen " + SKILL_LABELS[key].toLowerCase())}`,
    lowConfidence: p.feedback_ready_count < 2,
  };
}

export interface SkillLevel {
  key: string;
  label: string;
  score: number;
  max: number;
}

export function deriveSkillLevels(p: ProgressSummary | null): SkillLevel[] {
  if (!p?.skill_averages) return [];
  return (Object.keys(SKILL_LABELS) as (keyof SkillAverages)[]).map((k) => ({
    key: k,
    label: SKILL_LABELS[k],
    score: p.skill_averages![k],
    max: 20,
  }));
}

// ── Practice coverage ────────────────────────────────────────────────────────

const SPEECH_TYPES: SpeechType[] = ["constructive", "rebuttal", "summary", "final_focus", "crossfire"];
const TYPE_LABEL: Record<SpeechType, string> = {
  constructive: "Constructive", rebuttal: "Rebuttal", summary: "Summary",
  final_focus: "Final Focus", crossfire: "Crossfire",
};

export interface CoverageItem {
  type: SpeechType;
  label: string;
  count: number;
  practiced: boolean;
}

export function derivePracticeCoverage(speeches: Speech[]): CoverageItem[] {
  return SPEECH_TYPES.map((type) => {
    const count = speeches.filter((s) => s.speech_type === type).length;
    return { type, label: TYPE_LABEL[type], count, practiced: count > 0 };
  });
}

// ── Drill effectiveness (honest) ───────────────────────────────────────────────

export function drillEffectivenessNote(p: ProgressSummary | null): string {
  if (!p || p.drill_attempts_count === 0) return "No drill attempts yet — complete a drill to start tracking effect.";
  if (p.feedback_ready_count < 2) return "Not enough later speeches yet to measure whether drills moved your scores.";
  return "Re-record after a drill to see whether the targeted skill improved.";
}

// ── Milestones ─────────────────────────────────────────────────────────────────

export interface Milestone {
  id: string;
  label: string;
  done: boolean;
}

export function deriveMilestones(p: ProgressSummary | null, speeches: Speech[]): Milestone[] {
  const hasReRecord = speeches.some((s) => s.parent_speech_id);
  const typesPracticed = new Set(speeches.map((s) => s.speech_type));
  return [
    { id: "first-speech", label: "First practice speech", done: (p?.speech_count ?? 0) > 0 },
    { id: "first-report", label: "First analyzed report", done: (p?.feedback_ready_count ?? 0) > 0 },
    { id: "first-drill", label: "First completed drill", done: (p?.drills_completed_count ?? 0) > 0 },
    { id: "first-rerecord", label: "First re-record comparison", done: hasReRecord },
    { id: "all-types", label: "All core speech types practiced", done: SPEECH_TYPES.every((t) => typesPracticed.has(t)) },
  ];
}

// ── Weekly plan (generated, editable on the surface) ───────────────────────────

export interface PlanItem {
  id: string;
  label: string;
  detail: string;
  href: string;
}

export function deriveWeeklyPlan(p: ProgressSummary | null, speeches: Speech[]): PlanItem[] {
  const focus = deriveCurrentFocus(p);
  const coverage = derivePracticeCoverage(speeches);
  const neglected = coverage.find((c) => !c.practiced);
  const reRecordable = speeches.find((s) => s.status === "done" && !s.parent_speech_id);

  const plan: PlanItem[] = [];
  plan.push({
    id: "drill-1",
    label: "Two short drills",
    detail: focus ? `Target ${focus.skill.toLowerCase()}` : "Target your weakest skill",
    href: "/learn",
  });
  plan.push({
    id: "full-speech",
    label: "One full speech",
    detail: neglected ? `Try a ${neglected.label} — you haven't practiced it` : "Run a fresh constructive",
    href: `/session?type=${neglected?.type ?? "constructive"}`,
  });
  plan.push({
    id: "re-record",
    label: "One re-record",
    detail: reRecordable ? "Re-record a past speech and compare" : "After your next report, re-record to compare",
    href: reRecordable ? `/speech/${reRecordable.id}` : "/session",
  });
  plan.push({
    id: "evidence",
    label: "Optional: cut one card",
    detail: "Back your weakest contention with a fresh source",
    href: "/evidence",
  });
  return plan;
}

// ── Sparse-state classification ────────────────────────────────────────────────

export type ProgressDataState = "empty" | "sparse" | "ready";

export function progressDataState(p: ProgressSummary | null): ProgressDataState {
  if (!p || p.speech_count === 0) return "empty";
  if (p.feedback_ready_count < 2) return "sparse";
  return "ready";
}
