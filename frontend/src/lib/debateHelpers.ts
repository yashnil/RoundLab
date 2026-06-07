/**
 * Pure helper functions for debate data processing.
 * These are extracted here so they can be unit-tested independently of React.
 * All functions are side-effect-free and depend only on their arguments.
 */

import type { SkillAverages, DebateIssueType, DebateIssue, SpeechStatus } from "@/types";

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
