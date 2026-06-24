// Pass 16 — Round simulation model and helpers

import type {
  ArgumentFlowStatus,
  CrossfireExchange,
  RoundArgument,
  RoundDecision,
  RoundPhaseType,
  RoundSide,
  RoundSimulation,
  RoundSimulationConfig,
  RoundSpeech,
  RoundStatus,
} from "@/types/round";

// ── Phase metadata ────────────────────────────────────────────────────────────

export const PHASE_LABELS: Record<RoundPhaseType, string> = {
  first_constructive: "First Constructive",
  second_constructive: "Second Constructive",
  first_crossfire: "First Crossfire",
  first_rebuttal: "First Rebuttal",
  second_rebuttal: "Second Rebuttal",
  grand_crossfire: "Grand Crossfire",
  first_summary: "First Summary",
  second_summary: "Second Summary",
  final_crossfire: "Final Crossfire",
  first_final_focus: "First Final Focus",
  second_final_focus: "Second Final Focus",
  judge_deliberation: "Judge Deliberation",
  completed: "Round Complete",
};

export const FULL_PHASE_ORDER: RoundPhaseType[] = [
  "first_constructive",
  "second_constructive",
  "first_crossfire",
  "first_rebuttal",
  "second_rebuttal",
  "grand_crossfire",
  "first_summary",
  "second_summary",
  "final_crossfire",
  "first_final_focus",
  "second_final_focus",
  "judge_deliberation",
  "completed",
];

export const SHORTENED_PHASE_ORDER: RoundPhaseType[] = [
  "first_constructive",
  "second_constructive",
  "first_crossfire",
  "first_rebuttal",
  "second_rebuttal",
  "first_summary",
  "second_summary",
  "first_final_focus",
  "second_final_focus",
  "judge_deliberation",
  "completed",
];

export const CROSSFIRE_PHASES = new Set<RoundPhaseType>([
  "first_crossfire",
  "grand_crossfire",
  "final_crossfire",
]);

export const SPEECH_PHASES = new Set<RoundPhaseType>([
  "first_constructive",
  "second_constructive",
  "first_rebuttal",
  "second_rebuttal",
  "first_summary",
  "second_summary",
  "first_final_focus",
  "second_final_focus",
]);

// ── Phase utilities ───────────────────────────────────────────────────────────

export function getPhaseOrder(format: string): RoundPhaseType[] {
  if (format === "shortened") return SHORTENED_PHASE_ORDER;
  return FULL_PHASE_ORDER;
}

export function nextPhase(current: RoundPhaseType, format: string): RoundPhaseType | null {
  const order = getPhaseOrder(format);
  const idx = order.indexOf(current);
  if (idx < 0 || idx + 1 >= order.length) return null;
  return order[idx + 1];
}

export function phaseProgress(current: RoundPhaseType, format: string): number {
  const order = getPhaseOrder(format);
  const idx = order.indexOf(current);
  if (idx < 0) return 0;
  return Math.round((idx / (order.length - 1)) * 100);
}

export function isCrossfire(phase: RoundPhaseType): boolean {
  return CROSSFIRE_PHASES.has(phase);
}

export function isSpeechPhase(phase: RoundPhaseType): boolean {
  return SPEECH_PHASES.has(phase);
}

// ── Flow argument helpers ─────────────────────────────────────────────────────

export const ARGUMENT_STATUS_LABELS: Record<ArgumentFlowStatus, string> = {
  introduced: "Introduced",
  answered: "Answered",
  conceded: "Conceded",
  extended: "Extended",
  underextended: "Underextended",
  dropped: "Dropped",
  turned: "Turned",
  mitigated: "Mitigated",
  outweighed: "Outweighed",
  new_in_late_speech: "Late Argument",
  unresolved: "Unresolved",
  live: "Live",
};

export const ARGUMENT_STATUS_COLORS: Record<ArgumentFlowStatus, string> = {
  introduced: "text-sky-600",
  answered: "text-amber-600",
  conceded: "text-red-600",
  extended: "text-emerald-600",
  underextended: "text-amber-500",
  dropped: "text-red-700 font-semibold",
  turned: "text-purple-600",
  mitigated: "text-orange-500",
  outweighed: "text-rose-600",
  new_in_late_speech: "text-red-500 italic",
  unresolved: "text-slate-500",
  live: "text-emerald-700 font-semibold",
};

export function getProArguments(args: RoundArgument[]): RoundArgument[] {
  return args.filter((a) => a.side === "pro");
}

export function getConArguments(args: RoundArgument[]): RoundArgument[] {
  return args.filter((a) => a.side === "con");
}

export function getSurvivingOffense(args: RoundArgument[], side: RoundSide): RoundArgument[] {
  const surviving: ArgumentFlowStatus[] = ["live", "extended", "introduced", "unresolved"];
  return args.filter((a) => a.side === side && surviving.includes(a.status) && a.is_offense);
}

export function getDroppedArguments(args: RoundArgument[]): RoundArgument[] {
  return args.filter((a) => a.status === "dropped");
}

// ── Decision helpers ──────────────────────────────────────────────────────────

export function winnerLabel(decision: RoundDecision): string {
  return decision.winner === "pro" ? "Pro (Affirmative)" : "Con (Negative)";
}

export function speakerPoints(decision: RoundDecision, side: RoundSide): number {
  return decision.speaker_points[side] ?? 27.0;
}

// ── Time formatting ───────────────────────────────────────────────────────────

export function formatSeconds(s: number): string {
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${String(sec).padStart(2, "0")}`;
}

// ── Default config ────────────────────────────────────────────────────────────

export function defaultRoundConfig(overrides?: Partial<RoundSimulationConfig>): RoundSimulationConfig {
  return {
    format: "full",
    student_side: "pro",
    speaking_order: "first",
    speaker_role: "first",
    judge_type: "flow",
    opponent_difficulty: "jv",
    resolution: "",
    coaching_hints_enabled: true,
    pauses_allowed: true,
    practice_mode_overrides: [],
    constructive_time: 240,
    rebuttal_time: 240,
    summary_time: 180,
    final_focus_time: 120,
    crossfire_time: 180,
    prep_time: 120,
    approved_card_ids: [],
    approved_blockfile_ids: [],
    approved_frontline_ids: [],
    source_scope: "personal",
    evidence_testing_mode: false,
    ...overrides,
  };
}

// ── Speech type labels ────────────────────────────────────────────────────────

export function speechTypeLabel(phase: RoundPhaseType): string {
  const map: Partial<Record<RoundPhaseType, string>> = {
    first_constructive: "Constructive",
    second_constructive: "Constructive",
    first_rebuttal: "Rebuttal",
    second_rebuttal: "Rebuttal",
    first_summary: "Summary",
    second_summary: "Summary",
    first_final_focus: "Final Focus",
    second_final_focus: "Final Focus",
  };
  return map[phase] ?? "Speech";
}
