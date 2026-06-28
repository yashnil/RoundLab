"use client";

/**
 * DissioJourneyRail — practice-loop position indicator.
 *
 * Record → Flow → Ballot → Drill → Improve
 *
 * Uses a CSS grid so nodes and labels are guaranteed to share the same
 * column width — no SVG-to-CSS coordinate mapping needed.
 * Progress line draws in once when the component enters the viewport.
 * Respects prefers-reduced-motion.
 */

import { useEffect, useRef, useState } from "react";

export type RailStepId = "record" | "flow" | "ballot" | "drill" | "improve";

const STEPS: Array<{ id: RailStepId; label: string }> = [
  { id: "record",  label: "Record"  },
  { id: "flow",    label: "Flow"    },
  { id: "ballot",  label: "Ballot"  },
  { id: "drill",   label: "Drill"   },
  { id: "improve", label: "Improve" },
];

// Each step column is 20% wide; node centers sit at 10%, 30%, 50%, 70%, 90%.
// The connector line spans from 10% to 90% = 80% of the container.
const LINE_LEFT_PCT  = 10; // %
const LINE_SPAN_PCT  = 80; // %
const NODE_PX        = 16; // node width / height in pixels

interface Props {
  /**
   * Index of the most recently completed step:
   * -1 = nothing started
   *  0 = recorded
   *  1 = flow / ballot done
   *  2 = drilled
   *  3 = re-recorded
   *  4 = full loop complete
   */
  activeIndex?: number;
  showLabels?: boolean;
  className?: string;
}

export default function DissioJourneyRail({
  activeIndex = -1,
  showLabels = true,
  className = "",
}: Props) {
  const ref    = useRef<HTMLDivElement>(null);
  const [drawn, setDrawn] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setDrawn(true);
      return;
    }

    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setDrawn(true); obs.disconnect(); } },
      { threshold: 0.4 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  const clampedIndex = Math.max(-1, Math.min(activeIndex, STEPS.length - 1));

  // Progress fraction: 0 when nothing done or only first node done,
  // rising linearly to 1 when all nodes done.
  const progressFrac = clampedIndex <= 0 ? 0 : clampedIndex / (STEPS.length - 1);

  return (
    <div ref={ref} className={`select-none ${className}`}>
      <div className="relative">
        {/* ── Connector lines ──────────────────────────────────────────── */}

        {/* Background hairline — from col-0 center (10%) to col-4 center (90%) */}
        <div
          className="pointer-events-none absolute h-px bg-[var(--theme-hairline-strong)]"
          style={{
            top:   NODE_PX / 2,
            left:  `${LINE_LEFT_PCT}%`,
            width: `${LINE_SPAN_PCT}%`,
          }}
        />

        {/* Lav progress fill */}
        {clampedIndex >= 0 && (
          <div
            className="pointer-events-none absolute bg-[oklch(0.510_0.156_278)]"
            style={{
              top:    NODE_PX / 2 - 0.75,
              left:   `${LINE_LEFT_PCT}%`,
              height: 1.5,
              width:  drawn ? `${progressFrac * LINE_SPAN_PCT}%` : "0%",
              transition: drawn
                ? "width 0.8s cubic-bezier(0.22, 1, 0.36, 1) 0.1s"
                : "none",
            }}
          />
        )}

        {/* ── Step columns ─────────────────────────────────────────────── */}
        <div className="grid grid-cols-5">
          {STEPS.map((step, i) => {
            const isDone   = i <= clampedIndex;
            const isActive = i === clampedIndex;
            const isNext   = i === clampedIndex + 1;

            return (
              <div key={step.id} className="flex flex-col items-center gap-1.5">
                {/* Node — centered in column, sits above the line */}
                <div
                  className="relative z-10 flex items-center justify-center"
                  style={{
                    width:           NODE_PX,
                    height:          NODE_PX,
                    borderRadius:    2,
                    backgroundColor: isDone ? "oklch(0.510 0.156 278)" : "var(--theme-canvas)",
                    border:          isDone ? "none" : `1.5px solid ${
                      isNext
                        ? "oklch(0.510 0.156 278 / 0.35)"
                        : "var(--theme-hairline-strong)"
                    }`,
                  }}
                >
                  {/* Active node: white square dot */}
                  {isActive && (
                    <div
                      style={{
                        width: 6, height: 6,
                        borderRadius: 1,
                        backgroundColor: "white",
                      }}
                    />
                  )}

                  {/* Done but not active: checkmark */}
                  {isDone && !isActive && (
                    <svg
                      viewBox="0 0 10 10"
                      fill="none"
                      aria-hidden
                      style={{ width: 10, height: 10 }}
                    >
                      <path
                        d="M2 5l2 2.5 4-4"
                        stroke="white"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  )}
                </div>

                {/* Label — directly below its node */}
                {showLabels && (
                  <span
                    className="text-center"
                    style={{
                      fontFamily:    "var(--font-jetbrains-mono)",
                      fontSize:      "0.5rem",
                      fontWeight:    600,
                      letterSpacing: "0.08em",
                      textTransform: "uppercase",
                      lineHeight:    1,
                      color:         isDone
                        ? "oklch(0.510 0.156 278)"
                        : "var(--theme-ink-faint)",
                    }}
                  >
                    {step.label}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
