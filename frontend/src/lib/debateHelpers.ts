/**
 * Pure helper functions for debate data processing.
 * These are extracted here so they can be unit-tested independently of React.
 * All functions are side-effect-free and depend only on their arguments.
 */

import type { SkillAverages, DebateIssueType, DebateIssue, SpeechStatus, ProgressSummary, Speech, FeedbackReport, FeedbackScores, SpeechComparisonResult, ArgumentItem } from "@/types";

// ── Skill analysis ─────────────────────────────────────────────────────────────

const SKILL_LABELS: Record<keyof SkillAverages, string> = {
  clash:            "Clash",
  weighing:         "Impact Weighing",
  extensions:       "Extensions",
  drops:            "Drop Prevention",
  judge_adaptation: "Judge Adaptation",
};

/** Returns the lowest-scoring skill from skill_averages. */
export function deriveLowestSkill(
  avgs: SkillAverages,
): { key: keyof SkillAverages; value: number; label: string } | null {
  const entries = (Object.entries(avgs) as [keyof SkillAverages, number][])
    .filter(([, v]) => typeof v === "number" && !Number.isNaN(v));
  if (entries.length === 0) return null;
  const [key, value] = entries.reduce((min, cur) => (cur[1] < min[1] ? cur : min));
  return { key, value, label: SKILL_LABELS[key] };
}

/** Returns skill percentage (0-100). */
export function skillPercent(value: number, max = 20): number {
  return Math.round((Math.max(0, Math.min(max, value)) / max) * 100);
}

// ── Issue type mapping ─────────────────────────────────────────────────────────

/** Map issue_type strings to human-readable labels. */
export const ISSUE_TYPE_LABELS: Record<DebateIssueType, string> = {
  missing_warrant:   "Missing warrant",
  weak_evidence:     "Weak evidence",
  unclear_impact:    "Unclear impact",
  no_weighing:       "No impact weighing",
  dropped_argument:  "Dropped argument",
  weak_extension:    "Weak extension",
  no_clash:          "No clash",
  new_argument:      "New argument",
  organization:      "Organization issue",
  delivery:          "Delivery issue",
};

/** Map issue_type to severity color class. */
export function issueSeverityColor(severity: "low" | "medium" | "high"): string {
  if (severity === "high")   return "danger";
  if (severity === "medium") return "warn";
  return "ink-subtle";
}

// ── Duration formatting ────────────────────────────────────────────────────────

/** Format seconds into a human-readable string: "1m 30s" or "45s". */
export function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "—";
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins === 0) return `${secs}s`;
  if (secs === 0) return `${mins}m`;
  return `${mins}m ${secs}s`;
}

/** Format drill time_limit_seconds to a display string. */
export function formatDrillTimeLimit(seconds: number | null | undefined): string {
  if (seconds == null) return "—";
  return formatDuration(seconds);
}

// ── Speech status normalization ────────────────────────────────────────────────

export interface SpeechStatusConfig {
  label: string;
  color: "lav" | "ok" | "warn" | "danger" | "default";
  /** Badge variant for use with Badge component */
  badge: "indigo" | "green" | "amber" | "red" | "default";
  isTerminal: boolean;
  isProcessing: boolean;
}

const STATUS_CONFIGS: Record<string, SpeechStatusConfig> = {
  pending:      { label: "Pending",       color: "default", badge: "default", isTerminal: false, isProcessing: false },
  transcribing: { label: "Transcribing",  color: "lav",     badge: "indigo",  isTerminal: false, isProcessing: true  },
  analyzing:    { label: "Analyzing",     color: "warn",    badge: "amber",   isTerminal: false, isProcessing: true  },
  done:         { label: "Feedback ready",color: "ok",      badge: "green",   isTerminal: true,  isProcessing: false },
  error:        { label: "Error",         color: "danger",  badge: "red",     isTerminal: true,  isProcessing: false },
};

const FALLBACK_STATUS: SpeechStatusConfig = {
  label: "Unknown",
  color: "default",
  badge: "default",
  isTerminal: false,
  isProcessing: false,
};

/** Normalize a raw status string into a structured config object. */
export function getSpeechStatusConfig(status: string): SpeechStatusConfig {
  return STATUS_CONFIGS[status] ?? FALLBACK_STATUS;
}

/** Human-readable status label. */
export function getSpeechStatusLabel(status: string): string {
  return getSpeechStatusConfig(status).label;
}

/** Tailwind color token name for a status. */
export function getSpeechStatusColor(status: string): SpeechStatusConfig["color"] {
  return getSpeechStatusConfig(status).color;
}

// ── Issue extraction and ranking ───────────────────────────────────────────────

/** Extract the highest-severity issue from a structured_issues list. */
export function getPrimaryIssue(issues: DebateIssue[] | undefined): DebateIssue | null {
  if (!issues || issues.length === 0) return null;
  const order = { high: 0, medium: 1, low: 2 };
  return [...issues].sort((a, b) => (order[a.severity] ?? 3) - (order[b.severity] ?? 3))[0];
}

/** Return all argument labels affected by structured issues, deduplicated. */
export function getAffectedArgumentLabels(issues: DebateIssue[] | undefined): string[] {
  if (!issues || issues.length === 0) return [];
  const all = issues.flatMap((i) => i.affected_argument_labels);
  return [...new Set(all)];
}

/** Map a structured issue type to the matching drill recommendation type. */
export function mapIssueToDrillType(issueType: DebateIssueType): string {
  const MAP: Record<DebateIssueType, string> = {
    missing_warrant:   "warranting",
    weak_evidence:     "evidence",
    unclear_impact:    "weighing",
    no_weighing:       "weighing",
    dropped_argument:  "drops",
    weak_extension:    "extensions",
    no_clash:          "clash",
    new_argument:      "drops",
    organization:      "judge_adaptation",
    delivery:          "judge_adaptation",
  };
  return MAP[issueType] ?? "warranting";
}

/** Normalize a raw issue_type string — returns null if unrecognized. */
export function normalizeIssueType(raw: string): DebateIssueType | null {
  const VALID: Set<string> = new Set([
    "missing_warrant", "weak_evidence", "unclear_impact", "no_weighing",
    "dropped_argument", "weak_extension", "no_clash", "new_argument",
    "organization", "delivery",
  ]);
  return VALID.has(raw) ? (raw as DebateIssueType) : null;
}

/** Normalize a severity string — returns "medium" as safe default if unrecognized. */
export function normalizeSeverity(raw: string): "low" | "medium" | "high" {
  if (raw === "low" || raw === "high") return raw;
  return "medium";
}

// ── Coach margin note copy ─────────────────────────────────────────────────────

export interface CoachNoteConfig {
  note: string;
  type: "info" | "warn" | "strong";
}

const COACH_NOTES: Record<DebateIssueType, CoachNoteConfig> = {
  missing_warrant: {
    type: "warn",
    note: "Without a warrant, a judge can't evaluate WHY your claim is true. The argument can be conceded without ever being answered — state the mechanism linking the claim to the evidence.",
  },
  weak_evidence: {
    type: "warn",
    note: "Weak evidence is vulnerable to an evidence comparison turn. Cite the source and date, and explain what the study specifically proves — don't let your opponent define what it says.",
  },
  unclear_impact: {
    type: "warn",
    note: "Impact calculus requires magnitude, probability, and timeframe. Without a clear impact, a judge has nothing to weigh — winning the claim may still lose the round.",
  },
  no_weighing: {
    type: "warn",
    note: "Impact weighing is the last argument a judge processes before voting. If you don't compare your impact to opponent offense explicitly, the judge decides — and they often default to whoever was clearest.",
  },
  dropped_argument: {
    type: "warn",
    note: "Many judges treat a dropped argument as conceded. Even a thin 'non-unique' or 'this doesn't apply because' protects the ballot. Silence reads as agreement on the flow.",
  },
  weak_extension: {
    type: "info",
    note: "Extending an argument requires the claim, warrant, and impact — not just the label. 'Extend our first contention' gives a judge nothing to carry forward without the substance.",
  },
  no_clash: {
    type: "warn",
    note: "Without direct clash, you're debating past each other. Name the opponent argument before answering it — this shows the judge exactly where your offense beats theirs.",
  },
  new_argument: {
    type: "warn",
    note: "Late-round new arguments are typically barred — a judge won't evaluate a claim the opponent had no chance to answer. Use later speeches to extend, weigh, and collapse.",
  },
  organization: {
    type: "info",
    note: "Clear signposting prevents mis-flows. Explicitly name each contention and transition: 'moving to my second contention on economic harm' keeps the judge's flow synchronized with yours.",
  },
  delivery: {
    type: "info",
    note: "Slow down on impacts — speed is acceptable for warrants, but impacts need to land clearly. Lay judges especially decide based on what they understood, not what was technically said.",
  },
};

/**
 * Returns the debate-native coach note copy for a given structured issue type.
 * Returns null if the issue type is unrecognized.
 */
export function getCoachNote(issueType: DebateIssueType): CoachNoteConfig | null {
  return COACH_NOTES[issueType] ?? null;
}

/**
 * Derives the most impactful issue type from an argument map's issue strings.
 * Used to surface a relevant coach note when only heuristic issues are available
 * (no structured_issues from the v2+ report schema).
 * Checks in priority order: warrant → evidence → impact → weighing → drop → extension → clash.
 */
export function deriveFlowCoachNoteType(
  args: Array<{ issues: string[] }>,
): DebateIssueType | null {
  if (!args || args.length === 0) return null;
  const argsWithIssues = args.filter((a) => a.issues.length > 0);
  if (argsWithIssues.length === 0) return null;

  const blob = argsWithIssues.flatMap((a) => a.issues).join(" ").toLowerCase();
  if (blob.includes("warrant"))                                   return "missing_warrant";
  if (blob.includes("evidence") || blob.includes("unsupported")) return "weak_evidence";
  if (blob.includes("impact"))                                    return "unclear_impact";
  if (blob.includes("weigh"))                                     return "no_weighing";
  if (blob.includes("drop"))                                      return "dropped_argument";
  if (blob.includes("extension") || blob.includes("extend"))     return "weak_extension";
  if (blob.includes("clash"))                                     return "no_clash";
  return null;
}

// ── Issue-to-keyword mapping (for heuristic fallback) ─────────────────────────

/** Derive an issue keyword from a priority/weakness string. */
export function priorityToIssueKeyword(text: string): string | null {
  const t = text.toLowerCase();
  if (t.includes("warrant"))                                  return "warrant";
  if (t.includes("evidence") || t.includes("unsupported"))   return "evidence";
  // "weigh" before "impact" — weighing mentions often include the word "impact"
  if (t.includes("weigh"))                                    return "weigh";
  if (t.includes("impact"))                                   return "impact";
  if (t.includes("drop"))                                     return "drop";
  if (t.includes("extension") || t.includes("extend"))       return "extension";
  if (t.includes("clash"))                                    return "clash";
  return null;
}

// ── Practice next-action helper ────────────────────────────────────────────────

export type PracticeNextActionState =
  | "start_first_speech"
  | "open_report"
  | "wait_for_analysis"
  | "generate_drills"
  | "start_drill"
  | "continue_drill"
  | "re_record"
  | "view_improvement";

export interface PracticeNextAction {
  state: PracticeNextActionState;
  /** 0-indexed TrainingLoopMap step: 0=Speech, 1=Report, 2=Drill, 3=Re-record, 4=Improvement */
  loopStep: 0 | 1 | 2 | 3 | 4;
  title: string;
  description: string;
  primaryLabel: string;
  primaryHref: string;
  secondaryLabel?: string;
  secondaryHref?: string;
}

/**
 * Derives the single most-important next action for the student.
 * Pure function — testable without React.
 */
export function derivePracticeNextAction(
  progress: ProgressSummary | null,
  latestSpeech: Speech | null,
): PracticeNextAction {
  if (!progress || progress.speech_count === 0) {
    return {
      state: "start_first_speech",
      loopStep: 0,
      title: "Record your first practice speech",
      description: "Speak for 30–90 seconds. RoundLab builds a flow, generates a judge ballot, and assigns targeted drills.",
      primaryLabel: "Start practice session",
      primaryHref: "/session",
    };
  }

  if (progress.feedback_ready_count === 0) {
    const isProcessing =
      latestSpeech?.status === "transcribing" || latestSpeech?.status === "analyzing";
    if (isProcessing) {
      return {
        state: "wait_for_analysis",
        loopStep: 1,
        title: "Analysis in progress",
        description: "RoundLab is building your flow and judge ballot — usually 30–60 seconds.",
        primaryLabel: "Open session",
        primaryHref: latestSpeech ? `/speech/${latestSpeech.id}` : "/dashboard",
      };
    }
    return {
      state: "open_report",
      loopStep: 1,
      title: "Open your speech report",
      description: "Your flow and judge ballot are ready. Review your arguments and generate targeted drills.",
      primaryLabel: "Open flow report",
      primaryHref: latestSpeech ? `/speech/${latestSpeech.id}` : "/dashboard",
    };
  }

  if (progress.drills_assigned_count === 0) {
    return {
      state: "generate_drills",
      loopStep: 2,
      title: "Generate your personalized drills",
      description: "Open your speech report and click Generate Drills to get 3 targeted exercises.",
      primaryLabel: "Open flow report",
      primaryHref: latestSpeech ? `/speech/${latestSpeech.id}` : "/dashboard",
    };
  }

  if (progress.incomplete_drills.length > 0) {
    const next = progress.incomplete_drills[0];
    const isFirstDrill = progress.drill_attempts_count === 0;
    return {
      state: isFirstDrill ? "start_drill" : "continue_drill",
      loopStep: 2,
      title: isFirstDrill
        ? `Start your first drill`
        : `Continue: ${next.title}`,
      description: isFirstDrill
        ? `${next.title} — targeting ${next.skill_target.replace(/_/g, " ")}`
        : `Targeting ${next.skill_target.replace(/_/g, " ")} · ${next.difficulty}`,
      primaryLabel: "Open drill workspace",
      primaryHref: `/drills/${next.id}`,
      secondaryLabel:
        progress.incomplete_drills.length > 1
          ? `+${progress.incomplete_drills.length - 1} more drill${progress.incomplete_drills.length - 1 !== 1 ? "s" : ""} assigned`
          : undefined,
      secondaryHref:
        progress.incomplete_drills.length > 1 && latestSpeech
          ? `/speech/${latestSpeech.id}#drills`
          : undefined,
    };
  }

  // Check if the latest speech is a deliberate re-record (has parent_speech_id)
  if (latestSpeech?.parent_speech_id) {
    if (latestSpeech.status === "transcribing" || latestSpeech.status === "analyzing") {
      return {
        state: "wait_for_analysis",
        loopStep: 3,
        title: "Re-record is being analyzed",
        description: "Your new speech is being processed. The improvement comparison will appear when ready.",
        primaryLabel: "Open session",
        primaryHref: `/speech/${latestSpeech.id}`,
      };
    }
    if (latestSpeech.status === "done") {
      return {
        state: "view_improvement",
        loopStep: 4,
        title: "View your improvement comparison",
        description: "Your re-recorded speech is analyzed. See how your drill work paid off.",
        primaryLabel: "View improvement report",
        primaryHref: `/speech/${latestSpeech.id}`,
      };
    }
  }

  if (progress.speech_count < 2) {
    return {
      state: "re_record",
      loopStep: 3,
      title: "Re-record your speech to track improvement",
      description: "You've worked through your drills. Record the same speech again to see how your score changes.",
      primaryLabel: "Start re-record session",
      primaryHref: "/session",
      secondaryLabel: "Back to dashboard",
      secondaryHref: "/dashboard",
    };
  }

  return {
    state: "view_improvement",
    loopStep: 4,
    title: "View your improvement",
    description: "Compare your latest flow report to previous rounds to see skill growth.",
    primaryLabel: "Open latest report",
    primaryHref: latestSpeech ? `/speech/${latestSpeech.id}` : "/dashboard",
  };
}

// ── Speech comparison helper ───────────────────────────────────────────────────

/** Maps drill skill_target to the feedback_report score dimension it most affects. */
const SKILL_TO_SCORE_DIM: Partial<Record<string, keyof FeedbackScores>> = {
  weighing: "weighing",
  warranting: "clash",
  drops: "drops",
  extensions: "extensions",
  evidence: "drops",
  clash: "clash",
  judge_adaptation: "judge_adaptation",
  collapse: "extensions",
  line_by_line: "drops",
};

type PartialFeedback = Pick<FeedbackReport, "overall_score" | "scores" | "weaknesses"> | null;

/**
 * Computes a deterministic improvement comparison between two feedback reports.
 * Pure function — no API calls, no side effects.
 * Used for testing and as a client-side fallback if the backend endpoint is unavailable.
 */
export function compareSpeeches(
  originalFeedback: PartialFeedback,
  newFeedback: PartialFeedback,
  drillSkillTarget: string | null,
): SpeechComparisonResult {
  const origScore = originalFeedback?.overall_score ?? null;
  const newScore  = newFeedback?.overall_score ?? null;
  const overallDelta = origScore !== null && newScore !== null ? newScore - origScore : null;

  const scoreDim = drillSkillTarget ? (SKILL_TO_SCORE_DIM[drillSkillTarget] ?? null) : null;
  const origSkillScore: number | null = (scoreDim !== null && originalFeedback?.scores != null)
    ? originalFeedback.scores[scoreDim]
    : null;
  const newSkillScore: number | null = (scoreDim !== null && newFeedback?.scores != null)
    ? newFeedback.scores[scoreDim]
    : null;
  const skillDelta = origSkillScore !== null && newSkillScore !== null
    ? newSkillScore - origSkillScore
    : null;

  // Build summary
  const parts: string[] = [];
  if (overallDelta !== null) {
    if (overallDelta > 5) parts.push(`Strong improvement — overall score up ${overallDelta} points after the drill.`);
    else if (overallDelta > 0) parts.push(`Score improved by ${overallDelta} point${overallDelta !== 1 ? "s" : ""} after the drill.`);
    else if (overallDelta === 0) parts.push("Score held steady — your drill work is consolidating.");
    else parts.push(`Score dipped by ${Math.abs(overallDelta)} — that can happen while internalizing new technique.`);
  }
  if (drillSkillTarget && skillDelta !== null && overallDelta !== null) {
    const label = drillSkillTarget.replace(/_/g, " ");
    if (skillDelta > 0) parts.push(`Your ${label} score also improved by ${skillDelta}.`);
    else if (skillDelta < 0) parts.push(`Your ${label} score slipped — focus there next.`);
  } else if (drillSkillTarget && skillDelta !== null) {
    const dir = skillDelta > 0 ? "improved" : skillDelta === 0 ? "held steady" : "dipped";
    parts.push(`Your ${drillSkillTarget.replace(/_/g, " ")} ${dir} after the drill.`);
  }
  const summary = parts.length > 0 ? parts.join(" ") : "Report comparison is ready — compare the two to see what changed.";

  const stillNeedsWork = newFeedback?.weaknesses?.[0] ?? null;

  let nextAction: string;
  if (overallDelta !== null && overallDelta >= 5) nextAction = "Great progress — consider moving to the next skill drill.";
  else if (overallDelta !== null && overallDelta > 0) nextAction = "Keep practicing — one more rep of this drill will reinforce the skill.";
  else nextAction = "Record another drill rep, then re-record the speech to track improvement.";

  return {
    has_parent: true,
    parent_speech_id: null,
    source_drill_id: null,
    source_drill_skill: drillSkillTarget,
    original_overall_score: origScore,
    new_overall_score: newScore,
    overall_delta: overallDelta,
    original_skill_score: origSkillScore,
    new_skill_score: newSkillScore,
    skill_delta: skillDelta,
    summary,
    still_needs_work: stillNeedsWork,
    next_action: nextAction,
  };
}

// ── Argument display label derivation ─────────────────────────────────────────

const TYPE_LABEL_PREFIX: Record<string, string> = {
  offense: "ARG", defense: "DEF", weighing: "WGH", response: "RSP", unclear: "ARG",
};

/**
 * Derives a structured display label from an ArgumentItem.
 * Parses existing `label` for known prefixes (C1, NC2, A1, etc.).
 * Returns { prefix, ordinal, title } where structuredLabel = "${prefix} · Arg ${ordinal}".
 *
 * Examples:
 *   "C1 - Economic Growth" → { prefix: "C1", ordinal: 1, title: "Economic Growth" }
 *   "Economic Growth" (offense, first offense arg) → { prefix: "ARG", ordinal: 1, title: "Economic Growth" }
 */
export function deriveArgumentDisplayLabel(
  arg: ArgumentItem,
  _index: number,
  allArgs: ArgumentItem[],
): { prefix: string; ordinal: number; title: string } {
  const match = arg.label.match(/^([A-Za-z]+\d*)\s*[-–—·:]\s*/);
  if (match) {
    const raw = match[1].toUpperCase();
    const title = arg.label.slice(match[0].length).trim() || arg.label;
    const samePrefix = allArgs.filter((a) => {
      const m = a.label.match(/^([A-Za-z]+\d*)\s*[-–—·:]\s*/);
      return m ? m[1].toUpperCase() === raw : false;
    });
    const ordinal = samePrefix.indexOf(arg) + 1;
    return { prefix: raw, ordinal: Math.max(1, ordinal), title };
  }
  const typeKey = TYPE_LABEL_PREFIX[arg.argument_type] ?? "ARG";
  const sameType = allArgs.filter((a) => (TYPE_LABEL_PREFIX[a.argument_type] ?? "ARG") === typeKey);
  const ordinal = sameType.indexOf(arg) + 1;
  return { prefix: typeKey, ordinal: Math.max(1, ordinal), title: arg.label };
}
