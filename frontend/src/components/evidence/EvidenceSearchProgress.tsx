"use client";

import { useEffect, useRef, useState } from "react";
import type { LucideIcon } from "lucide-react";
import { Search, Globe, FileText, Scissors, Sparkles, CheckCircle2 } from "lucide-react";

// ── Phases shown as the bar fills ──────────────────────────────────────────────

interface Phase {
  at: number; // progress % at which this phase begins
  label: string;
  Icon: LucideIcon;
}

const PHASES: Phase[] = [
  { at: 0, label: "Searching credible sources", Icon: Search },
  { at: 18, label: "Opening source pages", Icon: Globe },
  { at: 38, label: "Extracting passages", Icon: FileText },
  { at: 58, label: "Cutting evidence", Icon: Scissors },
  { at: 78, label: "Building debate prep", Icon: Sparkles },
  { at: 100, label: "Finalizing cards", Icon: CheckCircle2 },
];

/** The phase whose threshold is the highest one <= progress. Exported for tests. */
export function phaseForProgress(progress: number): Phase {
  let current = PHASES[0];
  for (const p of PHASES) {
    if (progress >= p.at) current = p;
  }
  return current;
}

// The bar holds here until results actually arrive (never a fake 100).
const PROGRESS_CEILING = 98;

/**
 * Baseline progress for a given elapsed time. Monotonic ease-out toward the
 * ceiling over ~`durationMs` (default 70s) — fast at first, slowing near the
 * top so it never visually "sticks". Pure + exported for unit testing; the
 * component layers small random pulses on top for an organic feel.
 */
export function computeProgress(elapsedMs: number, durationMs = 70_000): number {
  const t = Math.max(0, Math.min(elapsedMs / durationMs, 1));
  // Steeper early curve → fast start, gentle finish (reads as "loading").
  const eased = 1 - Math.pow(1 - t, 2.6);
  return Math.min(PROGRESS_CEILING, Math.round(eased * PROGRESS_CEILING));
}

/**
 * Premium animated progress card for long evidence operations. Climbs 0→98 over
 * ~70s with small organic pulses; when `done` flips true it finishes quickly to
 * 100. If 70s elapses without completing, it holds near 98 and shows
 * "Finalizing cards…". No debug text, no dots.
 */
export function EvidenceSearchProgress({
  active,
  done = false,
  durationMs = 70_000,
  label,
}: {
  active: boolean;
  /** Set true when results have arrived — the bar finishes to 100. */
  done?: boolean;
  durationMs?: number;
  /**
   * Fixed status label. When provided (URL/Paste single-phase ops) it replaces
   * the rotating multi-phase label. Research Search omits it for phase rotation.
   */
  label?: string;
}) {
  const [progress, setProgress] = useState(0);
  const startRef = useRef<number | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Organic climb runs only while active and not done. setState happens inside
  // the timer callback (not synchronously in the effect body), and the "done"
  // finish is derived below — so the bar never mutates state during render.
  useEffect(() => {
    if (!active || done) {
      startRef.current = null;
      return;
    }
    startRef.current = Date.now();
    intervalRef.current = setInterval(() => {
      if (startRef.current == null) return;
      const elapsed = Date.now() - startRef.current;
      const target = computeProgress(elapsed, durationMs);
      setProgress((prev) => {
        const next = Math.max(prev, target);
        // Occasional small forward pulse so it feels organic, never decreasing,
        // never past the ceiling until results arrive.
        if (next < PROGRESS_CEILING - 1 && Math.random() < 0.3) {
          return Math.min(PROGRESS_CEILING, next + Math.round(Math.random() * 1.4));
        }
        return next;
      });
    }, Math.random() * 140 + 180); // slightly irregular cadence
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      intervalRef.current = null;
    };
  }, [active, done, durationMs]);

  if (!active) return null;

  // Derive the displayed value: finish to 100 the moment results arrive.
  const displayProgress = done ? 100 : progress;
  const phase = phaseForProgress(displayProgress);
  const holding = displayProgress >= PROGRESS_CEILING && !done;
  const PhaseIcon = phase.Icon;

  return (
    <div className="rounded-2xl border border-gray-200/80 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gray-900 text-white">
            <PhaseIcon size={15} />
          </span>
          <p className="text-[14px] font-semibold text-gray-900 truncate">
            {holding ? "Finalizing cards…" : (label ?? phase.label)}
          </p>
        </div>
        <span className="text-[13px] font-semibold tabular-nums text-gray-500" aria-live="polite">
          {displayProgress}%
        </span>
      </div>

      {/* Bar */}
      <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-gray-100">
        <div
          className="relative h-full rounded-full bg-gradient-to-r from-gray-600 via-gray-800 to-gray-900 transition-[width] duration-500 ease-out"
          style={{ width: `${displayProgress}%` }}
          role="progressbar"
          aria-valuenow={displayProgress}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          {/* Subtle moving shimmer */}
          <span className="absolute inset-0 animate-pulse bg-white/20" />
        </div>
      </div>
    </div>
  );
}

export default EvidenceSearchProgress;
