/**
 * Report presentation model — derives the Overview (executive diagnosis), the
 * Ballot (judge decision + coach translation), and the Skills workspace from a
 * FeedbackReport. Pure + tested so the report sections stay declarative and we
 * never fabricate data: every field is sourced from the report or omitted.
 */

import type { FeedbackReport, Speech } from "@/types";

// ── Overview ─────────────────────────────────────────────────────────────────

export interface OverviewModel {
  diagnosis: string;
  reason: string | null;
  strength: string | null;
  weakness: string | null;
  recommendedAction: string | null;
  limitations: string[];
  overallScore: number | null;
}

function isStale(fb: FeedbackReport): boolean {
  const v = fb.raw_feedback?.scoring_version;
  // Treat a missing or pre-v2 scoring version as stale (mirrors isReportStale).
  return !v || /^v?1/.test(v);
}

export function deriveOverview(fb: FeedbackReport, speech: Speech | null): OverviewModel {
  const rf = fb.raw_feedback;
  const topPriority = rf?.top_3_priorities?.[0] ?? null;
  const limitations: string[] = [];

  if (speech && !speech.audio_url) {
    limitations.push("Text input: pacing, filler, and vocal delivery weren't analyzed.");
  }
  if (rf?.regenerated_from_correction) {
    limitations.push("Regenerated from your flow correction.");
  }
  if (isStale(fb)) {
    limitations.push("Scored with an older rubric — regenerate for the latest scoring.");
  }
  for (const w of rf?.calibration_warnings ?? []) limitations.push(w);

  return {
    diagnosis: fb.summary?.trim() || "Your report is ready. Review the priority fix below.",
    reason: topPriority,
    strength: fb.strengths[0] ?? null,
    weakness: fb.weaknesses[0] ?? topPriority ?? null,
    recommendedAction: rf?.recommendations?.[0] ?? topPriority ?? null,
    limitations,
    overallScore: fb.overall_score,
  };
}

// ── Ballot ───────────────────────────────────────────────────────────────────

export interface BallotModel {
  votingIssue: string | null;
  decisionPath: string[];
  accepted: string[];
  unresolved: string[];
  weighing: string[];
  rfd: string | null;
  judgeAdaptation: string | null;
  coachWhy: string | null;
  coachFix: string | null;
  recommendations: string[];
}

export function deriveBallot(fb: FeedbackReport): BallotModel {
  const rf = fb.raw_feedback;
  const accepted = fb.strengths.slice(0, 3);
  const unresolved = rf?.dropped_or_undercovered_arguments ?? [];
  const weighing = rf?.weighing_diagnostics ?? [];
  const votingIssue = rf?.top_3_priorities?.[0] ?? fb.weaknesses[0] ?? null;

  // Build an honest decision path — only steps the data supports.
  const path: string[] = [];
  if (accepted.length > 0) path.push("Offense established");
  if (unresolved.length > 0) path.push("Key responses left undercovered");
  else if (accepted.length > 0) path.push("Responses largely handled");
  if (weighing.length > 0) path.push("Weighing left the comparison unresolved");
  else if ((fb.scores.weighing ?? 0) >= 14) path.push("Weighing resolved the comparison");
  if (votingIssue) path.push("Voting issue decided it");

  return {
    votingIssue,
    decisionPath: path,
    accepted,
    unresolved,
    weighing,
    rfd: rf?.decision_logic ?? null,
    judgeAdaptation: rf?.judge_adaptation_notes ?? null,
    coachWhy: rf?.decision_logic ?? fb.summary ?? null,
    coachFix: rf?.top_3_priorities?.[0] ?? fb.weaknesses[0] ?? null,
    recommendations: rf?.recommendations ?? [],
  };
}

// ── Skills ───────────────────────────────────────────────────────────────────

export type SkillGroup = "engagement" | "strategy" | "communication";
export type SkillBand = "strong" | "developing" | "weak";

export interface SkillInsight {
  key: string;
  label: string;
  score: number;
  max: number;
  group: SkillGroup;
  band: SkillBand;
  diagnostics: string[];
}

const SKILL_DEFS: { key: keyof FeedbackReport["scores"]; label: string; group: SkillGroup; diagKey?: string }[] = [
  { key: "clash", label: "Clash", group: "engagement" },
  { key: "extensions", label: "Extensions", group: "engagement" },
  { key: "drops", label: "Drop prevention", group: "engagement" },
  { key: "weighing", label: "Impact weighing", group: "strategy", diagKey: "weighing_diagnostics" },
  { key: "judge_adaptation", label: "Judge adaptation", group: "strategy" },
];

function band(score: number, max: number): SkillBand {
  const pct = score / max;
  if (pct >= 0.7) return "strong";
  if (pct >= 0.5) return "developing";
  return "weak";
}

export interface SkillsModel {
  priority: SkillInsight | null;
  insights: SkillInsight[];
}

export function deriveSkills(fb: FeedbackReport, deliveryScore?: number | null): SkillsModel {
  const rf = fb.raw_feedback;
  const insights: SkillInsight[] = SKILL_DEFS.map((d) => {
    const score = fb.scores[d.key] ?? 0;
    const diagnostics =
      d.diagKey === "weighing_diagnostics" ? rf?.weighing_diagnostics ?? [] : [];
    return { key: d.key, label: d.label, score, max: 20, group: d.group, band: band(score, 20), diagnostics };
  });

  // Attach warranting/evidence diagnostics to the most relevant engagement skill.
  const clash = insights.find((i) => i.key === "clash");
  if (clash) {
    clash.diagnostics = [
      ...(rf?.warranting_diagnostics ?? []),
      ...(rf?.evidence_diagnostics ?? []),
    ];
  }

  if (deliveryScore != null) {
    insights.push({
      key: "delivery",
      label: "Delivery",
      score: deliveryScore,
      max: 100,
      group: "communication",
      band: band(deliveryScore, 100),
      diagnostics: [],
    });
  }

  // Priority = lowest band, then lowest normalized score.
  const priority =
    [...insights].sort((a, b) => a.score / a.max - b.score / b.max)[0] ?? null;

  return { priority, insights };
}

export const SKILL_GROUP_LABELS: Record<SkillGroup, string> = {
  engagement: "Round engagement",
  strategy: "Strategy",
  communication: "Communication",
};
