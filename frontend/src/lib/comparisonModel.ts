/**
 * Comparison presentation model — turns a SpeechComparisonResult into named,
 * dimension-labeled change items so an improvement receipt leads with *what
 * changed*, not a single score delta. Pure + tested.
 *
 * We never claim improvement from the overall score alone: each change is tied
 * to a specific dimension (targeted skill, delivery, filler, pace), and a
 * declining or unchanged result is reported just as plainly as an improvement.
 */

import type { SpeechComparisonResult } from "@/types";

export type ChangeTone = "improved" | "declined" | "steady" | "info";

export interface ChangeItem {
  /** Dimension name, e.g. "Impact weighing", "Filler words". */
  label: string;
  /** Before → after detail string. */
  detail: string;
  tone: ChangeTone;
}

function humanize(skill: string): string {
  const s = skill.replace(/[_-]+/g, " ").trim();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function toneFromDelta(delta: number | null | undefined, higherIsBetter = true): ChangeTone {
  if (delta === null || delta === undefined || delta === 0) return "steady";
  const better = higherIsBetter ? delta > 0 : delta < 0;
  return better ? "improved" : "declined";
}

function ba(before: number | null | undefined, after: number | null | undefined, suffix = ""): string | null {
  if ((before === null || before === undefined) && (after === null || after === undefined)) return null;
  const b = before === null || before === undefined ? "—" : `${before}${suffix}`;
  const a = after === null || after === undefined ? "—" : `${after}${suffix}`;
  return `${b} → ${a}`;
}

/** Named change items, targeted skill first, then delivery behaviors. */
export function deriveComparisonChanges(c: SpeechComparisonResult): ChangeItem[] {
  const items: ChangeItem[] = [];

  // Targeted skill leads — this is what the drill aimed at.
  if (c.source_drill_skill && c.skill_delta !== null) {
    const detail = ba(c.original_skill_score, c.new_skill_score, "/20");
    if (detail) {
      items.push({ label: humanize(c.source_drill_skill), detail, tone: toneFromDelta(c.skill_delta) });
    }
  }

  // Filler words — fewer is better.
  if (c.filler_delta !== null && c.filler_delta !== undefined) {
    const detail = ba(c.original_filler_count, c.new_filler_count);
    if (detail) {
      items.push({ label: "Filler words", detail, tone: toneFromDelta(c.filler_delta, false) });
    }
  }

  // Speaking pace — direction isn't inherently good/bad, so report as info.
  if (c.wpm_delta !== null && c.wpm_delta !== undefined && (c.original_wpm || c.new_wpm)) {
    const detail = ba(c.original_wpm, c.new_wpm, " WPM");
    if (detail) items.push({ label: "Speaking pace", detail, tone: "info" });
  }

  // Delivery score.
  if (c.delivery_score_delta !== null && c.delivery_score_delta !== undefined) {
    const detail = ba(c.original_delivery_score, c.new_delivery_score, "/100");
    if (detail) {
      items.push({ label: "Delivery", detail, tone: toneFromDelta(c.delivery_score_delta) });
    }
  }

  return items;
}

/** Supporting (demoted) score chips — overall ballot + targeted skill. */
export interface ScoreChip {
  label: string;
  before: number | null;
  after: number | null;
  delta: number | null;
  suffix: string;
}

export function supportingScores(c: SpeechComparisonResult): ScoreChip[] {
  const chips: ScoreChip[] = [];
  if (c.original_overall_score !== null || c.new_overall_score !== null) {
    chips.push({
      label: "Overall ballot",
      before: c.original_overall_score,
      after: c.new_overall_score,
      delta: c.overall_delta,
      suffix: "/100",
    });
  }
  return chips;
}

/** True when there's at least one concrete improved/declined change to show. */
export function hasMeaningfulChange(c: SpeechComparisonResult): boolean {
  return deriveComparisonChanges(c).some((i) => i.tone === "improved" || i.tone === "declined");
}
