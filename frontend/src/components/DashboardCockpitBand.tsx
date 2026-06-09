"use client";

/**
 * DashboardCockpitBand — compact top section of the dashboard.
 *
 * Shows:
 * - Practice loop position as a RoundLabJourneyRail
 * - XP, level, and feedback report count as mono stats
 *
 * Replaces the old "Your practice loop" TrainingLoopMap card.
 */

import RoundLabJourneyRail from "./RoundLabJourneyRail";
import type { ProgressSummary } from "@/types";

function deriveRailIndex(p: ProgressSummary): number {
  if (p.speech_count === 0)          return -1; // nothing started
  if (p.feedback_ready_count === 0)  return 0;  // recorded, waiting for flow
  if (p.drill_attempts_count === 0)  return 1;  // flow done, drill next
  if (p.speech_count < 2)            return 2;  // drilled, re-record next
  if (p.feedback_ready_count < 2)    return 3;  // re-recorded, improvement pending
  return 4;                                      // full loop complete
}

interface StatPillProps {
  value: number | string;
  label: string;
}

function StatPill({ value, label }: StatPillProps) {
  return (
    <div className="flex flex-col items-center gap-0.5">
      <span
        className="text-xl font-bold leading-none tabular-nums text-ink"
        style={{ fontFamily: "var(--font-jetbrains-mono)" }}
      >
        {value}
      </span>
      <span className="section-stamp">{label}</span>
    </div>
  );
}

interface Props {
  progress: ProgressSummary;
}

export default function DashboardCockpitBand({ progress }: Props) {
  const railIndex = deriveRailIndex(progress);

  return (
    <div className="cockpit-band rounded-lg border border-hairline bg-surface-1 px-5 py-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:gap-6">
        {/* Rail — takes up available space */}
        <div className="flex min-w-0 flex-1 flex-col gap-2.5">
          <span className="section-stamp">
            Practice loop
            {progress.speech_count > 0 && (
              <span
                className="ml-2 rounded-[2px] border border-hairline px-1.5 py-0.5 text-[8px] font-semibold tabular-nums text-ink-faint"
                style={{ fontFamily: "var(--font-jetbrains-mono)" }}
              >
                Rep {progress.speech_count}
              </span>
            )}
          </span>
          <RoundLabJourneyRail activeIndex={railIndex} showLabels />
        </div>

        {/* Stats divider */}
        <div className="hidden h-10 w-px bg-hairline sm:block" />

        {/* Stats — compact mono stats panel */}
        <div className="flex items-center gap-5 sm:shrink-0">
          <StatPill value={progress.xp}                  label="XP"       />
          <div className="h-6 w-px bg-hairline" />
          <StatPill value={progress.level}               label="Level"    />
          <div className="h-6 w-px bg-hairline" />
          <StatPill value={progress.feedback_ready_count} label="Reports" />
        </div>
      </div>
    </div>
  );
}
