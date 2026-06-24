"use client";

import { useEffect, useRef, useState } from "react";
import { formatSeconds } from "@/lib/roundModel";
import type { RoundPhaseType, RoundSide } from "@/types/round";

interface Props {
  phase: RoundPhaseType;
  phaseLabel: string;
  studentSpeaksNow: boolean;
  studentSide: RoundSide;
  timeLimitSeconds: number;
  /** ISO timestamp when the current phase started on the server. Anchors the timer. */
  phaseStartedAt?: string;
  status: string;
  coachingHint?: string;
}

/**
 * Compute elapsed seconds from a server-supplied start time, capped at the limit.
 * Falls back to 0 if the timestamp is missing or unparseable.
 */
function elapsedFromServer(phaseStartedAt: string | undefined): number {
  if (!phaseStartedAt) return 0;
  const start = Date.parse(phaseStartedAt);
  if (Number.isNaN(start)) return 0;
  return Math.max(0, Math.floor((Date.now() - start) / 1000));
}

export function RoundPhaseHeader({
  phase,
  phaseLabel,
  studentSpeaksNow,
  studentSide,
  timeLimitSeconds,
  phaseStartedAt,
  status,
  coachingHint,
}: Props) {
  // Initialise elapsed from server anchor if available, else 0
  const [elapsed, setElapsed] = useState(() => elapsedFromServer(phaseStartedAt));
  const [running, setRunning] = useState(!!phaseStartedAt);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // When phase changes (server sends new phase), resync to server anchor
  useEffect(() => {
    const initial = elapsedFromServer(phaseStartedAt);
    setElapsed(initial);
    setRunning(!!phaseStartedAt);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, phaseStartedAt]);

  useEffect(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (running) {
      intervalRef.current = setInterval(() => {
        setElapsed((e) => e + 1);
      }, 1000);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [running]);

  const remaining = Math.max(0, timeLimitSeconds - elapsed);
  const pct = timeLimitSeconds > 0 ? Math.min((elapsed / timeLimitSeconds) * 100, 100) : 0;
  const overTime = elapsed >= timeLimitSeconds && timeLimitSeconds > 0;
  // Warning threshold: 80% elapsed
  const nearLimit = !overTime && pct >= 80;

  const speakerLabel = studentSpeaksNow
    ? `You (${studentSide === "pro" ? "Pro" : "Con"})`
    : `AI Opponent (${studentSide === "pro" ? "Con" : "Pro"})`;

  return (
    <div className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-30">
      <div className="px-4 py-3 flex items-center gap-4">
        {/* Phase label */}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              {phaseLabel}
            </span>
            <span
              className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                studentSpeaksNow
                  ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                  : "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
              }`}
            >
              {speakerLabel}
            </span>
            {nearLimit && (
              <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400">
                Time check
              </span>
            )}
            {overTime && (
              <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
                Over time
              </span>
            )}
          </div>
          {coachingHint && (
            <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{coachingHint}</p>
          )}
        </div>

        {/* Timer */}
        {timeLimitSeconds > 0 && (
          <div className="flex items-center gap-2 shrink-0">
            <div
              className={`tabular-nums text-lg font-mono font-semibold ${
                overTime ? "text-red-600" : nearLimit ? "text-amber-600" : ""
              }`}
              aria-live="off"
              aria-label={`${overTime ? "Overtime" : "Remaining"}: ${overTime ? formatSeconds(elapsed - timeLimitSeconds) : formatSeconds(remaining)}`}
            >
              {overTime
                ? `+${formatSeconds(elapsed - timeLimitSeconds)}`
                : formatSeconds(remaining)}
            </div>
            <button
              onClick={() => setRunning((r) => !r)}
              className="rounded-md border px-2 py-1 text-xs font-medium hover:bg-accent transition-colors"
              aria-label={running ? "Pause timer" : "Start timer"}
            >
              {running ? "Pause" : "Start"}
            </button>
            <button
              onClick={() => {
                const initial = elapsedFromServer(phaseStartedAt);
                setElapsed(initial);
                setRunning(!!phaseStartedAt);
              }}
              className="rounded-md border px-2 py-1 text-xs font-medium hover:bg-accent transition-colors"
              aria-label="Sync timer to server"
            >
              Sync
            </button>
          </div>
        )}
      </div>

      {/* Progress bar */}
      {timeLimitSeconds > 0 && (
        <div className="h-1 w-full bg-muted" role="progressbar" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100}>
          <div
            className={`h-full transition-all duration-1000 ${
              overTime ? "bg-red-500" : nearLimit ? "bg-amber-500" : "bg-primary"
            }`}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
    </div>
  );
}
