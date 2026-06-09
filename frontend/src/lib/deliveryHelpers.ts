/**
 * Pure helpers for delivery metrics display.
 * All functions are deterministic and free of side effects.
 */

import type { DeliveryMetrics, PacingBand } from "@/types";

// ── Pacing band ────────────────────────────────────────────────────────────────

export interface PacingBandDisplay {
  label: string;
  colorClass: string;
  hint: string;
}

export function getPacingBandDisplay(band: PacingBand | null | undefined): PacingBandDisplay {
  switch (band) {
    case "too_slow":
      return {
        label: "Too slow",
        colorClass: "text-warn",
        hint: "Speaking slowly can lose judge attention and reduce speech time efficiency.",
      };
    case "too_fast":
      return {
        label: "Too fast",
        colorClass: "text-danger",
        hint: "Fast pacing makes warrants harder to follow for lay judges and harder to flow for flow judges.",
      };
    case "steady":
      return {
        label: "Steady",
        colorClass: "text-ok",
        hint: "Your pace is in the judge-friendly range (110–180 WPM). Keep it consistent under pressure.",
      };
    default:
      return {
        label: "Unknown",
        colorClass: "text-ink-faint",
        hint: "No speech duration available — add duration when uploading to enable pacing analysis.",
      };
  }
}

// ── Clarity flag labels ────────────────────────────────────────────────────────

export interface FlagDisplay {
  label: string;
  description: string;
  severity: "warn" | "danger" | "info";
}

const FLAG_DISPLAY: Record<string, FlagDisplay> = {
  too_fast: {
    label: "Speaking too fast",
    description: "Pacing above 180 WPM — warrants may not land for lay judges.",
    severity: "danger",
  },
  too_slow: {
    label: "Speaking too slowly",
    description: "Pacing below 110 WPM — consider tightening your argument structure.",
    severity: "warn",
  },
  many_fillers: {
    label: "High filler word rate",
    description: "More than 5% of your words are fillers (um, uh, like, you know). Fillers reduce judge confidence.",
    severity: "danger",
  },
  repetitive_wording: {
    label: "Repetitive phrasing",
    description: "Several 2–4 word phrases appear 3+ times. Repetition wastes limited speech time.",
    severity: "warn",
  },
  long_sentences: {
    label: "Long sentences",
    description: "More than 40% of sentences exceed 30 words. Long sentences are hard to flow.",
    severity: "warn",
  },
  very_short_speech: {
    label: "Very short speech",
    description: "Speech is under 75 words — too short for full debate analysis.",
    severity: "info",
  },
};

export function getFlagDisplay(flag: string): FlagDisplay {
  return FLAG_DISPLAY[flag] ?? {
    label: flag.replace(/_/g, " "),
    description: "",
    severity: "info",
  };
}

// ── Score color ────────────────────────────────────────────────────────────────

export function deliveryScoreColor(score: number | null | undefined): string {
  if (score === null || score === undefined) return "text-ink-faint";
  if (score >= 75) return "text-ok";
  if (score >= 50) return "text-warn";
  return "text-danger";
}

// ── WPM format ─────────────────────────────────────────────────────────────────

export function formatWpm(wpm: number | null | undefined): string {
  if (wpm === null || wpm === undefined) return "—";
  return `${Math.round(wpm)} WPM`;
}

// ── Filler word display ────────────────────────────────────────────────────────

export function formatFillerBreakdown(json: Record<string, number> | null | undefined): Array<{ word: string; count: number }> {
  if (!json) return [];
  return Object.entries(json)
    .map(([word, count]) => ({ word, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 6);
}

// ── Coach note ─────────────────────────────────────────────────────────────────

/**
 * Generate a contextual coach note that ties delivery to debate impact.
 * Returns null if no significant issue is found.
 */
export function deriveDeliveryCoachNote(metrics: DeliveryMetrics): string | null {
  const flags = metrics.clarity_flags_json ?? [];
  const wpm = metrics.words_per_minute;
  const fillerCount = metrics.filler_word_count ?? 0;
  const wordCount = metrics.word_count ?? 1;
  const fillerRate = fillerCount / wordCount;

  if (flags.includes("too_fast") && wpm) {
    return `You're speaking at ${Math.round(wpm)} WPM — flow judges may miss warrants at this pace. Slow down around impact explanation to help the ballot land.`;
  }
  if (flags.includes("many_fillers") && fillerCount > 0) {
    return `${fillerCount} filler words detected (${(fillerRate * 100).toFixed(0)}% of words). Fillers signal hesitation and reduce judge confidence in your arguments.`;
  }
  if (flags.includes("repetitive_wording")) {
    const phrases = metrics.repeated_phrases_json ?? [];
    const top = phrases[0];
    if (top) {
      return `"${top.phrase}" appears ${top.count} times — repetition wastes limited PF speech time and can feel unprepared to flow judges.`;
    }
    return "Several phrases are repeated more than 3 times — repetition wastes limited speech time.";
  }
  if (flags.includes("too_slow") && wpm) {
    return `At ${Math.round(wpm)} WPM, judges may lose focus before you reach your impact. Try tightening your warrant structure.`;
  }
  if (flags.includes("long_sentences")) {
    return "Several sentences are very long — try breaking them into judge-flowable units (one idea per sentence).";
  }
  if (metrics.delivery_score !== null && metrics.delivery_score !== undefined && metrics.delivery_score >= 80) {
    return "Strong delivery — pacing, clarity, and filler rate are all in good shape for this judge type.";
  }
  return null;
}

// ── Delivery focus text (for dashboard card) ────────────────────────────────

export function deriveDeliveryFocus(metrics: DeliveryMetrics): string | null {
  const flags = metrics.clarity_flags_json ?? [];
  if (flags.includes("too_fast")) return "Slow down warrants";
  if (flags.includes("many_fillers")) return "Reduce filler words";
  if (flags.includes("repetitive_wording")) return "Avoid repeated phrases";
  if (flags.includes("long_sentences")) return "Shorten long sentences";
  if (flags.includes("too_slow")) return "Tighten argument structure";
  return null;
}

// ── Timeline segment color ─────────────────────────────────────────────────────

export function segmentFlagColor(flags: string[]): string {
  if (flags.includes("high_fillers") && flags.includes("repetitive")) return "border-danger/30 bg-danger/5";
  if (flags.includes("high_fillers")) return "border-warn/30 bg-warn/5";
  if (flags.includes("repetitive")) return "border-lav/20 bg-lav/5";
  return "border-hairline bg-surface-1";
}
