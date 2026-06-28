"use client";

import Link from "next/link";
import { Target, ArrowRight } from "lucide-react";
import { deriveCoachingFocus } from "@/lib/coachingFocus";
import type { SkillAverages } from "@/types";

interface CoachingFocusCardProps {
  skillAverages: SkillAverages | null;
  feedbackReadyCount: number;
}

/**
 * The student's current coaching focus — the lowest skill from real reports,
 * why it matters, and a concrete next practice. Shows an honest
 * data-insufficient state instead of a fabricated focus.
 */
export default function CoachingFocusCard({
  skillAverages,
  feedbackReadyCount,
}: CoachingFocusCardProps) {
  const focus = deriveCoachingFocus(skillAverages, feedbackReadyCount);

  return (
    <section
      aria-label="Current coaching focus"
      className="surface-flow flex flex-col gap-3 rounded-xl p-5"
    >
      <div className="flex items-center gap-2">
        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-skill-down/10 text-skill-down">
          <Target size={15} aria-hidden="true" />
        </span>
        <h2 className="text-heading text-ink">Current coaching focus</h2>
      </div>

      {focus ? (
        <>
          <div>
            <p className="text-eyebrow text-ink-subtle">
              Priority skill
            </p>
            <p className="mt-0.5 text-title font-semibold text-ink">{focus.label}</p>
          </div>
          <p className="text-sm leading-relaxed text-ink-subtle">{focus.why}</p>
          <div className="rounded-lg border border-hairline bg-surface-2/60 px-3.5 py-2.5">
            <p className="text-xs leading-relaxed text-ink-muted">
              <span className="font-medium text-ink">Try this:</span> {focus.suggestion}
            </p>
          </div>
          <Link
            href="/session"
            className="inline-flex w-fit items-center gap-1.5 text-sm font-medium text-lav-hi transition-colors hover:text-lav focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50"
          >
            Practice this now
            <ArrowRight size={14} aria-hidden="true" />
          </Link>
        </>
      ) : (
        <p className="text-sm leading-relaxed text-ink-subtle">
          Dissio will identify your top skill to work on after your first speech is
          analyzed. Record a constructive to get your first coaching focus.
        </p>
      )}
    </section>
  );
}
