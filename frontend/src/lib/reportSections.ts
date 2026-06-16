/**
 * Speech report section model.
 *
 * The report is a long, anchored page (the existing `#drills` anchor is part of
 * this). This module defines the URL-addressable sections and which ones are
 * actually present for a given report, so the section nav, scroll-spy, and any
 * deep links all agree on one source of truth.
 */

export type ReportSectionId =
  | "overview"
  | "flow"
  | "drills"
  | "transcript";

export interface ReportSection {
  id: ReportSectionId;
  label: string;
  /** Short hint for tooltips / a11y. */
  hint: string;
}

/** Canonical render/nav order. */
export const REPORT_SECTIONS: ReportSection[] = [
  { id: "overview", label: "Overview", hint: "Verdict, ballot, and skills" },
  { id: "flow", label: "Flow", hint: "Claim, warrant, evidence, impact" },
  { id: "drills", label: "Drills", hint: "Practice built from this speech" },
  { id: "transcript", label: "Transcript", hint: "What you said, with timing" },
];

export interface ReportSectionFlags {
  hasFeedback: boolean;
  hasFlow: boolean;
  hasDrills: boolean;
  hasTranscript: boolean;
}

/** Only the sections that actually have content to show. */
export function availableSections(flags: ReportSectionFlags): ReportSection[] {
  return REPORT_SECTIONS.filter((s) => {
    switch (s.id) {
      case "overview":
        return flags.hasFeedback;
      case "flow":
        return flags.hasFlow;
      case "drills":
        return flags.hasDrills;
      case "transcript":
        return flags.hasTranscript;
    }
  });
}

/** Parse a section id from a URL hash (e.g. "#flow" → "flow"). */
export function sectionFromHash(hash: string | null | undefined): ReportSectionId | null {
  if (!hash) return null;
  const id = hash.replace(/^#/, "");
  return REPORT_SECTIONS.some((s) => s.id === id) ? (id as ReportSectionId) : null;
}
