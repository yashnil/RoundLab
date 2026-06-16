/**
 * Coaching-focus derivation: pick the student's current priority skill from
 * real report data (the lowest-scoring skill dimension) and explain why it
 * matters + what to practice. Pure + tested; never fabricates confidence.
 */

import type { SkillAverages } from "@/types";

export type SkillKey = keyof SkillAverages;

interface SkillMeta {
  label: string;
  /** Why this skill matters to a judge. */
  why: string;
  /** A concrete suggested activity. */
  suggestion: string;
}

export const SKILL_META: Record<SkillKey, SkillMeta> = {
  clash: {
    label: "Clash",
    why: "Judges reward direct engagement — answering your opponent’s actual arguments, not just repeating your own.",
    suggestion: "Practice a rebuttal that responds to each opposing contention by name.",
  },
  weighing: {
    label: "Weighing",
    why: "Comparative impact analysis tells the judge which argument matters most when both sides have offense.",
    suggestion: "Run a final focus that explicitly weighs your impact against theirs.",
  },
  extensions: {
    label: "Extensions",
    why: "Carrying arguments cleanly through the round keeps them on the judge’s flow and in the decision.",
    suggestion: "Practice a summary that extends your strongest contention with its warrant.",
  },
  drops: {
    label: "Coverage",
    why: "Dropped arguments are treated as conceded — judges flow them straight to the other side.",
    suggestion: "Drill answering every opposing contention in a rebuttal under time.",
  },
  judge_adaptation: {
    label: "Judge adaptation",
    why: "Different judges reward different things — adapting your emphasis wins close rounds.",
    suggestion: "Re-record this speech imagining a lay judge, then a flow judge.",
  },
};

export interface CoachingFocus {
  skill: SkillKey;
  label: string;
  score: number;
  why: string;
  suggestion: string;
}

/**
 * The priority skill is the lowest-scoring dimension. Returns null when there
 * isn't enough data (no skill averages, or no completed feedback yet).
 */
export function deriveCoachingFocus(
  skills: SkillAverages | null,
  feedbackReadyCount: number,
): CoachingFocus | null {
  if (!skills || feedbackReadyCount < 1) return null;

  const entries = (Object.keys(SKILL_META) as SkillKey[]).map((k) => ({
    skill: k,
    score: skills[k],
  }));

  // Lowest score is the weakness to focus on (ties resolved by SKILL_META order).
  let lowest = entries[0];
  for (const e of entries) {
    if (e.score < lowest.score) lowest = e;
  }

  const meta = SKILL_META[lowest.skill];
  return {
    skill: lowest.skill,
    label: meta.label,
    score: lowest.score,
    why: meta.why,
    suggestion: meta.suggestion,
  };
}
