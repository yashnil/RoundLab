"use client";

import { formatRecorderClock } from "@/lib/recorder";
import { cn } from "@/lib/utils";

interface RecordingTimerProps {
  ms: number;
  /** Pulse the dot while actively recording. */
  active?: boolean;
  className?: string;
}

/**
 * Large, stable recording clock. Marked aria-hidden so screen readers aren't
 * spammed with a new time every tick — recording status is announced
 * separately via a live region in the recorder.
 */
export default function RecordingTimer({ ms, active, className }: RecordingTimerProps) {
  return (
    <div className={cn("flex items-center gap-2", className)} aria-hidden="true">
      {active && (
        <span className="relative flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full rounded-full bg-danger/60 motion-safe:animate-ping" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-danger" />
        </span>
      )}
      <span className="font-mono text-3xl font-semibold tabular-nums tracking-tight text-ink">
        {formatRecorderClock(ms)}
      </span>
    </div>
  );
}
