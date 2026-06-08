"use client";

import { TrendingUp, TrendingDown, Minus, ArrowRight } from "lucide-react";
import type { SpeechComparisonResult } from "@/types";

interface Props {
  comparison: SpeechComparisonResult;
}

function DeltaChip({ delta }: { delta: number | null }) {
  if (delta === null) return null;
  const Icon = delta > 0 ? TrendingUp : delta === 0 ? Minus : TrendingDown;
  const cls =
    delta > 0
      ? "text-ok bg-ok/10 border-ok/20"
      : delta === 0
      ? "text-ink-subtle bg-surface-2 border-hairline"
      : "text-danger bg-danger/10 border-danger/20";
  return (
    <span className={`inline-flex items-center gap-0.5 rounded-full border px-2 py-0.5 text-[11px] font-semibold ${cls}`}>
      <Icon size={9} />
      {delta > 0 ? "+" : ""}{delta}
    </span>
  );
}

function ScoreRow({
  label,
  before,
  after,
  delta,
  suffix = "",
}: {
  label: string;
  before: number | null;
  after: number | null;
  delta: number | null;
  suffix?: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <p className="text-[10px] font-medium uppercase tracking-wide text-ink-faint">{label}</p>
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold text-ink-subtle">
          {before !== null ? `${before}${suffix}` : "—"}
        </span>
        <ArrowRight size={12} className="text-ink-faint" />
        <span className="text-sm font-bold text-ink">
          {after !== null ? `${after}${suffix}` : "—"}
        </span>
        <DeltaChip delta={delta} />
      </div>
    </div>
  );
}

export default function ImprovementComparisonCard({ comparison }: Props) {
  if (!comparison.has_parent) return null;

  const hasAnyScore =
    comparison.original_overall_score !== null || comparison.new_overall_score !== null;

  return (
    <div
      className="rounded-2xl border border-ok/20 bg-ok/5 p-5"
      style={{ boxShadow: "0 0 32px -12px oklch(0.620 0.170 145 / 0.12)" }}
    >
      {/* Header */}
      <div className="mb-4 flex items-center gap-2.5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-ok/15">
          <TrendingUp size={15} className="text-ok" />
        </div>
        <div>
          <p className="text-eyebrow text-ok">Drill improvement</p>
          <p className="text-sm font-semibold text-ink">Re-record comparison</p>
        </div>
      </div>

      {!hasAnyScore ? (
        <p className="text-xs text-ink-faint">
          Comparison will appear once both reports are fully analyzed.
        </p>
      ) : (
        <div className="flex flex-col gap-4">
          {/* Score rows */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <ScoreRow
              label="Overall score"
              before={comparison.original_overall_score}
              after={comparison.new_overall_score}
              delta={comparison.overall_delta}
              suffix="/100"
            />
            {comparison.source_drill_skill && (
              <ScoreRow
                label={`Targeted: ${comparison.source_drill_skill.replace(/_/g, " ")}`}
                before={comparison.original_skill_score}
                after={comparison.new_skill_score}
                delta={comparison.skill_delta}
                suffix="/20"
              />
            )}
          </div>

          {/* Coach summary */}
          <div className="rounded-lg border border-ok/15 bg-ok/8 px-3 py-2.5">
            <p className="text-xs leading-relaxed text-ink">{comparison.summary}</p>
          </div>

          {/* Still working on */}
          {comparison.still_needs_work && (
            <div className="flex flex-col gap-0.5">
              <p className="text-[10px] font-medium uppercase tracking-wide text-ink-faint">
                Still working on
              </p>
              <p className="text-xs text-ink-subtle">{comparison.still_needs_work}</p>
            </div>
          )}

          {/* Coach next action */}
          <div className="flex flex-col gap-0.5 border-t border-ok/10 pt-3">
            <p className="text-[10px] font-medium uppercase tracking-wide text-ink-faint">
              Coach note
            </p>
            <p className="text-xs font-medium text-ink-subtle">{comparison.next_action}</p>
          </div>
        </div>
      )}
    </div>
  );
}
