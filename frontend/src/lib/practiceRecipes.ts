/**
 * Practice recipes — one-click training configurations for the dashboard.
 *
 * Each recipe is a real setup preset: it deep-links into /session with a speech
 * type (and, where useful, a judge lens, side, and a practice goal). Nothing here
 * is a dead button — every recipe opens the existing practice-setup flow primed.
 *
 * Kept pure + render-agnostic (icon names are strings) so it can be unit-tested
 * the way the rest of the dashboard model is.
 */

import type { SpeechType, JudgeType } from "@/types";

export type RecipeGroup = "full" | "quick";

/** Lucide icon name — resolved to a component at render time. */
export type RecipeIcon =
  | "Mic"
  | "Swords"
  | "Scale"
  | "Flag"
  | "Wrench"
  | "Gauge"
  | "Speech"
  | "Quote";

export interface PracticeRecipe {
  id: string;
  label: string;
  /** One line on what this rep trains. */
  blurb: string;
  /** Time estimate, m:ss. */
  minutes: string;
  group: RecipeGroup;
  icon: RecipeIcon;
  type: SpeechType;
  judge?: JudgeType;
  side?: "pro" | "con";
  /** A practice intention surfaced on the setup screen (guidance, not persisted). */
  goal?: string;
}

export const PRACTICE_RECIPES: PracticeRecipe[] = [
  // ── Full speeches ──────────────────────────────────────────────────────────
  {
    id: "full-constructive",
    label: "Full Constructive",
    blurb: "Build a complete case with warranted contentions.",
    minutes: "4:00",
    group: "full",
    icon: "Mic",
    type: "constructive",
    judge: "flow",
    goal: "Lay out every contention with claim, warrant, evidence, and impact.",
  },
  {
    id: "rebuttal-clash",
    label: "Rebuttal Clash Check",
    blurb: "Answer every opposing contention, line by line.",
    minutes: "4:00",
    group: "full",
    icon: "Swords",
    type: "rebuttal",
    judge: "flow",
    goal: "Respond to each opposing argument and defend your own.",
  },
  {
    id: "summary-collapse",
    label: "Summary Collapse",
    blurb: "Collapse to your best argument and start weighing.",
    minutes: "3:00",
    group: "full",
    icon: "Scale",
    type: "summary",
    judge: "flow",
    goal: "Drop what doesn't matter, extend what wins, and weigh.",
  },
  {
    id: "final-focus-voter",
    label: "Final Focus Voter",
    blurb: "Give the judge one clear reason to vote.",
    minutes: "2:00",
    group: "full",
    icon: "Flag",
    type: "final_focus",
    judge: "lay",
    goal: "Crystallize the single clearest reason your side wins.",
  },
  // ── Quick reps ───────────────────────────────────────────────────────────────
  {
    id: "warrant-repair",
    label: "30-Second Warrant Repair",
    blurb: "Rebuild one weak warrant with a clear because-statement.",
    minutes: "0:30",
    group: "quick",
    icon: "Wrench",
    type: "constructive",
    judge: "tech",
    goal: "Take one claim and explain exactly why it's true.",
  },
  {
    id: "weighing-sprint",
    label: "Weighing Sprint",
    blurb: "Weigh an impact on magnitude, probability, and timeframe.",
    minutes: "1:00",
    group: "quick",
    icon: "Gauge",
    type: "summary",
    judge: "tech",
    goal: "Compare your impact to the opponent's on all three axes.",
  },
  {
    id: "lay-explanation",
    label: "Lay Judge Explanation",
    blurb: "Explain your winning argument to a non-expert.",
    minutes: "1:30",
    group: "quick",
    icon: "Speech",
    type: "final_focus",
    judge: "lay",
    goal: "Make your best argument land with zero jargon.",
  },
  {
    id: "evidence-attribution",
    label: "Evidence Attribution Practice",
    blurb: "Cite each card with source and date as you extend.",
    minutes: "1:00",
    group: "quick",
    icon: "Quote",
    type: "rebuttal",
    judge: "tech",
    goal: "Name the source and year every time you reference a card.",
  },
];

/** Deep-link a recipe into the practice-setup flow with its presets applied. */
export function recipeHref(recipe: PracticeRecipe): string {
  const params = new URLSearchParams();
  params.set("type", recipe.type);
  if (recipe.judge) params.set("judge", recipe.judge);
  if (recipe.side) params.set("side", recipe.side);
  if (recipe.goal) params.set("goal", recipe.goal);
  return `/session?${params.toString()}`;
}

export function recipesByGroup(group: RecipeGroup): PracticeRecipe[] {
  return PRACTICE_RECIPES.filter((r) => r.group === group);
}
