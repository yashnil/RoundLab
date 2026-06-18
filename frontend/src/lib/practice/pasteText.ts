/**
 * Pasted-speech helpers — word count, speaking-time estimate, and minimum-content
 * guidance for the paste capture mode. Pure + tested so the paste UI stays honest
 * about what text-only analysis can and can't evaluate.
 */

/** Typical PF delivery rate. ~150 wpm → ~75 words ≈ 30 seconds. */
export const WORDS_PER_MINUTE = 150;

/** Minimum content for a meaningful analysis (~30 seconds of speech). */
export const MIN_WORDS = 75;

/** What text-only analysis cannot judge — surfaced verbatim in the paste UI. */
export const PASTE_DELIVERY_LIMITATION =
  "RoundLab can evaluate argument structure from pasted text, but it can't assess pacing, filler words, pauses, or vocal delivery without audio.";

export function wordCount(text: string): number {
  const trimmed = text.trim();
  return trimmed ? trimmed.split(/\s+/).length : 0;
}

/** Estimated speaking time, in whole seconds, at the PF delivery rate. */
export function estimateSpeakingSeconds(words: number): number {
  return Math.round((words / WORDS_PER_MINUTE) * 60);
}

/** Format whole seconds as m:ss. */
export function formatSpeakingTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = (seconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

export function meetsMinimum(text: string): boolean {
  return wordCount(text) >= MIN_WORDS;
}

export interface PasteStats {
  words: number;
  speakingTime: string;
  meetsMinimum: boolean;
  /** Words still needed to reach the minimum (0 once met). */
  wordsToMinimum: number;
}

export function derivePasteStats(text: string): PasteStats {
  const words = wordCount(text);
  return {
    words,
    speakingTime: formatSpeakingTime(estimateSpeakingSeconds(words)),
    meetsMinimum: words >= MIN_WORDS,
    wordsToMinimum: Math.max(0, MIN_WORDS - words),
  };
}
