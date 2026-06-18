"use client";

import { type ReactNode } from "react";
import { TrendingUp, TrendingDown, Minus, ArrowRight, Target, ListChecks } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { SpeechComparisonResult } from "@/types";
import {
  deriveComparisonChanges, supportingScores, type ChangeTone,
} from "@/lib/comparisonModel";
import { cn } from "@/lib/utils";

interface ImprovementReceiptProps {
  comparison: SpeechComparisonResult;
  /** Action buttons (Retry drill / Re-record / Next / Return), rendered in the footer. */
  actions?: ReactNode;
}

const TONE_ICON: Record<ChangeTone, LucideIcon> = {
  improved: TrendingUp,
  declined: TrendingDown,
  steady: Minus,
  info: Minus,
};

const TONE_CLS: Record<ChangeTone, string> = {
  improved: "text-ok",
  declined: "text-danger",
  steady: "text-ink-subtle",
  info: "text-ink-subtle",
};

/**
 * Improvement receipt — leads with *what changed* (named dimensions), then what
 * still needs work and the recommended next step. Scores are demoted to a
 * supporting chip; improvement is never claimed from the overall score alone.
 * Reused by the re-record comparison and the drill result.
 */
export default function ImprovementReceipt({ comparison, actions }: ImprovementReceiptProps) {
  const changes = deriveComparisonChanges(comparison);
  const scores = supportingScores(comparison);
  const targetLabel = comparison.source_drill_skill
    ? comparison.source_drill_skill.replace(/_/g, " ")
    : null;

  return (
    <div className="rounded-2xl border border-hairline bg-surface-1 p-5">
      {/* Header */}
      <div className="mb-4 flex items-center gap-2.5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-lav/10">
          <ListChecks size={15} className="text-lav" aria-hidden />
        </div>
        <div className="min-w-0">
          <p className="text-eyebrow text-lav">Improvement receipt</p>
          <p className="flex items-center gap-1.5 text-sm font-semibold text-ink">
            What changed
            {targetLabel && (
              <span className="inline-flex items-center gap-1 rounded-full border border-lav/25 bg-lav/10 px-2 py-0.5 text-[10px] font-medium capitalize text-lav">
                <Target size={9} aria-hidden /> {targetLabel}
              </span>
            )}
          </p>
        </div>
      </div>

      {/* What changed — dimension-named, not score-first */}
      {changes.length > 0 ? (
        <ul className="flex flex-col divide-y divide-hairline rounded-lg border border-hairline">
          {changes.map((c) => {
            const Icon = TONE_ICON[c.tone];
            return (
              <li key={c.label} className="flex items-center justify-between gap-3 px-3 py-2.5">
                <span className="text-xs font-medium text-ink">{c.label}</span>
                <span className="flex items-center gap-1.5">
                  <span className="font-mono text-xs tabular-nums text-ink-subtle">{c.detail}</span>
                  <Icon size={13} className={cn("shrink-0", TONE_CLS[c.tone])} aria-hidden />
                </span>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="rounded-lg border border-hairline bg-surface-2/50 px-3 py-2.5 text-xs text-ink-subtle">
          No measurable change on the tracked dimensions yet — the coach note below explains why.
        </p>
      )}

      {/* Coach summary */}
      {comparison.summary && (
        <p className="mt-3 rounded-lg border border-hairline bg-surface-2/50 px-3 py-2.5 text-xs leading-relaxed text-ink">
          {comparison.summary}
        </p>
      )}

      {/* Still needs work */}
      {comparison.still_needs_work && (
        <div className="mt-3 flex flex-col gap-0.5">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-faint">Still needs work</p>
          <p className="text-xs text-ink-subtle">{comparison.still_needs_work}</p>
        </div>
      )}

      {/* Recommended next */}
      {comparison.next_action && (
        <div className="mt-3 flex items-start gap-1.5 border-t border-hairline pt-3">
          <ArrowRight size={12} className="mt-0.5 shrink-0 text-lav" aria-hidden />
          <div className="flex flex-col gap-0.5">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-faint">Recommended next</p>
            <p className="text-xs font-medium text-ink">{comparison.next_action}</p>
          </div>
        </div>
      )}

      {/* Supporting scores — demoted */}
      {scores.length > 0 && (
        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-hairline pt-3">
          <span className="text-[10px] uppercase tracking-wide text-ink-faint">Scores (supporting)</span>
          {scores.map((s) => (
            <span key={s.label} className="inline-flex items-center gap-1 rounded-full border border-hairline bg-surface-2 px-2 py-0.5 text-[11px] text-ink-subtle">
              {s.label}: <span className="font-mono tabular-nums text-ink">{s.before ?? "—"}→{s.after ?? "—"}</span>
              {s.delta !== null && (
                <span className={cn("font-semibold", s.delta > 0 ? "text-ok" : s.delta < 0 ? "text-danger" : "text-ink-subtle")}>
                  {s.delta > 0 ? "+" : ""}{s.delta}
                </span>
              )}
            </span>
          ))}
        </div>
      )}

      {actions && <div className="mt-4 flex flex-wrap gap-2 border-t border-hairline pt-4">{actions}</div>}
    </div>
  );
}
