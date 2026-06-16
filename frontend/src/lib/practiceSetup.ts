/**
 * Practice-setup domain knowledge: debate-native guidance for the speech types
 * and judge types a Public Forum student picks before recording. Kept pure and
 * framework-free so the setup UI stays declarative and testable.
 */

import type { SpeechType, JudgeType } from "@/types";

export interface SpeechTypeInfo {
  label: string;
  /** One-line novice explanation of what this speech is for. */
  purpose: string;
  /** Typical speech length, in seconds, for the time target. */
  targetSeconds: number;
  /** Whether opponent/prior-speech context is useful for this speech. */
  opponentContextUseful: boolean;
}

export const SPEECH_TYPE_INFO: Record<SpeechType, SpeechTypeInfo> = {
  constructive: {
    label: "Constructive",
    purpose: "Build your case — lay out your contentions with claims, warrants, evidence, and impacts.",
    targetSeconds: 240,
    opponentContextUseful: false,
  },
  rebuttal: {
    label: "Rebuttal",
    purpose: "Answer your opponent — refute their contentions and defend your own.",
    targetSeconds: 240,
    opponentContextUseful: true,
  },
  summary: {
    label: "Summary",
    purpose: "Narrow the round — extend what matters, drop what doesn’t, and start weighing.",
    targetSeconds: 180,
    opponentContextUseful: true,
  },
  final_focus: {
    label: "Final Focus",
    purpose: "Crystallize the win — give the judge the clearest reason to vote for your side.",
    targetSeconds: 120,
    opponentContextUseful: true,
  },
  crossfire: {
    label: "Crossfire",
    purpose: "Question and answer — expose weaknesses and set up your later speeches.",
    targetSeconds: 180,
    opponentContextUseful: true,
  },
};

export interface JudgeTypeInfo {
  label: string;
  /** One-line explanation of what this judge cares about. */
  description: string;
}

export const JUDGE_TYPE_INFO: Record<JudgeType, JudgeTypeInfo> = {
  lay: {
    label: "Lay judge",
    description: "A non-expert. Rewards clear, persuasive speaking and big-picture impacts over jargon.",
  },
  flow: {
    label: "Flow judge",
    description: "Tracks every argument. Punishes dropped responses and weak extensions; rewards clean clash.",
  },
  tech: {
    label: "Tech judge",
    description: "Demands rigorous warrants, evidence quality, and explicit weighing between impacts.",
  },
  coach: {
    label: "Coach",
    description: "Full coaching lens — flags fixes and drill targets across every skill.",
  },
};

export const SPEECH_TYPE_ORDER: SpeechType[] = [
  "constructive",
  "rebuttal",
  "summary",
  "final_focus",
  "crossfire",
];

export const JUDGE_TYPE_ORDER: JudgeType[] = ["lay", "flow", "tech", "coach"];

function isSpeechType(value: string): value is SpeechType {
  return value in SPEECH_TYPE_INFO;
}

function isJudgeType(value: string): value is JudgeType {
  return value in JUDGE_TYPE_INFO;
}

export function getSpeechTypeInfo(type: string): SpeechTypeInfo | null {
  return isSpeechType(type) ? SPEECH_TYPE_INFO[type] : null;
}

export function getJudgeTypeInfo(type: string): JudgeTypeInfo | null {
  return isJudgeType(type) ? JUDGE_TYPE_INFO[type] : null;
}

/** Format a speech target as m:ss (e.g. 240 → "4:00"). */
export function formatSpeechTarget(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = (seconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

/** The CTA label for the setup form — debate-native, action-oriented. */
export function setupCtaLabel(isRerecord: boolean): string {
  return isRerecord ? "Start re-record" : "Open recorder";
}

// ── Smart defaults (last-used judge type) ────────────────────────────────────

export const LAST_JUDGE_KEY = "roundlab-last-judge";

export function readLastJudgeType(): string {
  if (typeof window === "undefined") return "";
  const v = window.localStorage.getItem(LAST_JUDGE_KEY);
  return v && isJudgeType(v) ? v : "";
}

export function rememberJudgeType(judge: string): void {
  if (typeof window === "undefined" || !isJudgeType(judge)) return;
  window.localStorage.setItem(LAST_JUDGE_KEY, judge);
}
