"use client";

/**
 * PilotChecklist — 6-step practice loop checklist.
 *
 * Each item shows:
 *   - completed: check icon + strikethrough
 *   - current (first incomplete): highlighted, "why this matters", CTA link
 *   - locked (subsequent): muted, no CTA
 *
 * derivePilotChecklist() is exported for testing and reuse.
 */

import Link from "next/link";
import { ArrowRight, CheckCircle2, Circle, Lock } from "lucide-react";
import type { PilotSummary, ProgressSummary } from "@/types";

export interface ChecklistItem {
  label: string;
  description: string;
  why: string;
  done: boolean;
  href?: string;
  ctaLabel?: string;
}

interface Props {
  progress: ProgressSummary;
  pilot?: PilotSummary | null;
}

export function derivePilotChecklist(
  progress: ProgressSummary,
  pilot?: PilotSummary | null,
): ChecklistItem[] {
  return [
    {
      label: "Record your first speech",
      description: "Record or upload a PF speech to get started.",
      why: "The flow is built from your speech — it's the foundation for everything else.",
      done: progress.speech_count > 0,
      href: "/session",
      ctaLabel: "Start session",
    },
    {
      label: "Open your flow report",
      description: "Get judge-style feedback on your speech.",
      why: "The ballot shows exactly how a judge scores clash, weighing, and drops — not just 'good job'.",
      done: progress.feedback_ready_count > 0,
      href: "/dashboard",
      ctaLabel: "View latest report",
    },
    {
      label: "Complete one recommended drill",
      description: "Practice the drill targeting your weakest skill.",
      why: "This turns feedback into a skill rep instead of just a comment.",
      done: progress.drill_attempts_count > 0,
      href: "/dashboard",
      ctaLabel: "Open drill queue",
    },
    {
      label: "Re-record the speech",
      description: "Record the speech again to track improvement.",
      why: "Re-recording after a drill is how you prove the feedback was actionable.",
      done: pilot ? pilot.rerecord_count > 0 : progress.speech_count >= 2,
      href: "/session",
      ctaLabel: "Start re-record",
    },
    {
      label: "View improvement report",
      description: "Compare your new score to the original.",
      why: "The delta score shows whether your drills moved the needle on a real judge's criteria.",
      done: pilot ? pilot.comparison_count > 0 : false,
      href: "/dashboard",
      ctaLabel: "View comparison",
    },
    {
      label: "Rate the feedback",
      description: "Tell us if the feedback was useful.",
      why: "Your rating shapes how future reports are calibrated.",
      done: pilot ? pilot.feedback_rating_count > 0 : false,
    },
  ];
}

export default function PilotChecklist({ progress, pilot }: Props) {
  const items = derivePilotChecklist(progress, pilot);
  const completed = items.filter((i) => i.done).length;
  const currentIndex = items.findIndex((i) => !i.done);

  return (
    <div className="flex flex-col gap-3">
      {/* Header with progress */}
      <div className="flex items-center justify-between gap-2">
        <span className="section-stamp">Practice loop progress</span>
        <span
          className="text-[10px] font-medium text-ink-faint tabular-nums"
          style={{ fontFamily: "var(--font-jetbrains-mono)" }}
        >
          {completed}/{items.length}
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-0.5 overflow-hidden rounded-none bg-hairline">
        <div
          className="h-full bg-lav transition-all duration-700"
          style={{ width: `${(completed / items.length) * 100}%` }}
        />
      </div>

      {/* Steps */}
      <ol className="flex flex-col gap-2">
        {items.map((item, i) => {
          const isCurrent = i === currentIndex;
          const isLocked = !item.done && i > currentIndex;

          return (
            <li
              key={i}
              className={[
                "flex flex-col gap-1.5 rounded-lg px-3 py-2.5 transition-colors",
                isCurrent
                  ? "border border-lav/20 bg-lav/5"
                  : item.done
                  ? ""
                  : "opacity-60",
              ].join(" ")}
            >
              {/* Row: icon + label */}
              <div className="flex items-start gap-2.5">
                <span className="mt-0.5 shrink-0">
                  {item.done ? (
                    <CheckCircle2 size={14} className="text-ok" />
                  ) : isLocked ? (
                    <Lock size={12} className="text-ink-faint mt-0.5" />
                  ) : (
                    <Circle size={14} className="text-lav/70" />
                  )}
                </span>
                <div className="flex flex-col gap-0.5 flex-1">
                  <span
                    className={`text-xs font-medium leading-snug ${
                      item.done
                        ? "text-ink-subtle line-through"
                        : isCurrent
                        ? "text-ink"
                        : "text-ink-subtle"
                    }`}
                  >
                    {item.label}
                  </span>

                  {/* "Why this matters" — show for current step only */}
                  {isCurrent && (
                    <p className="text-[11px] text-ink-faint leading-relaxed mt-0.5">
                      <span className="font-medium text-lav/80">Why: </span>
                      {item.why}
                    </p>
                  )}
                </div>
              </div>

              {/* CTA for current step */}
              {isCurrent && item.href && item.ctaLabel && (
                <div className="pl-[26px]">
                  <Link
                    href={item.href}
                    className="inline-flex items-center gap-1 rounded-md bg-lav px-2.5 py-1 text-[11px] font-semibold text-white hover:opacity-90 transition-opacity"
                  >
                    {item.ctaLabel}
                    <ArrowRight size={9} />
                  </Link>
                </div>
              )}
            </li>
          );
        })}
      </ol>

      {/* Completion state */}
      {completed === items.length && (
        <div className="rounded-lg border border-ok/20 bg-ok/5 px-3 py-2">
          <p className="text-xs font-medium text-ok">
            Loop complete — you&apos;ve run the full Dissio practice cycle.
          </p>
        </div>
      )}
    </div>
  );
}
