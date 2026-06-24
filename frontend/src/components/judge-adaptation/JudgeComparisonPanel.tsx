"use client";

import { JudgeComparisonResult, JudgeType, JUDGE_TYPE_LABELS } from "@/types/judgeAdaptation";

interface Props {
  result: JudgeComparisonResult | null;
  isLoading?: boolean;
}

export function JudgeComparisonPanel({ result, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="space-y-3 animate-pulse">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 rounded-lg bg-[var(--surface-2)]" />
        ))}
      </div>
    );
  }

  if (!result) {
    return (
      <div className="text-center py-8 text-[var(--ink-subtle)]">
        <p className="text-sm">Select two judge types to compare adaptations.</p>
      </div>
    );
  }

  const [typeA, typeB] = result.judge_types as [JudgeType, JudgeType];

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <span className="text-sm font-semibold text-[var(--ink-primary)]">
          {JUDGE_TYPE_LABELS[typeA]}
        </span>
        <span className="text-[var(--ink-subtle)] text-xs">vs</span>
        <span className="text-sm font-semibold text-[var(--ink-primary)]">
          {JUDGE_TYPE_LABELS[typeB]}
        </span>
      </div>

      {/* Constants */}
      {result.constants.length > 0 && (
        <div>
          <p className="text-[11px] font-medium text-[var(--ink-subtle)] uppercase tracking-wide mb-2">
            Always the same ({result.constants.length})
          </p>
          <ul className="space-y-1">
            {result.constants.map((c, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-[var(--ink-primary)]">
                <span className="text-emerald-500 shrink-0 mt-0.5">✓</span>
                {c}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Preference differences */}
      {result.differences.length > 0 && (
        <div>
          <p className="text-[11px] font-medium text-[var(--ink-subtle)] uppercase tracking-wide mb-2">
            Key Differences
          </p>
          <div className="space-y-2">
            {result.differences.map((d, i) => (
              <div
                key={i}
                className="rounded-md border border-[var(--surface-3)] bg-[var(--surface-2)] p-3"
              >
                <p className="text-[11px] font-semibold text-[var(--lavender-8)] uppercase tracking-wide mb-1">
                  {d.dimension}
                </p>
                <div className="grid grid-cols-2 gap-2 mb-1">
                  <p className="text-xs text-[var(--ink-primary)]">{d.judge_a_value}</p>
                  <p className="text-xs text-[var(--ink-primary)]">{d.judge_b_value}</p>
                </div>
                <p className="text-[11px] text-[var(--ink-subtle)]">{d.why_different}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Time allocation */}
      {result.time_allocation_differences.length > 0 && (
        <div>
          <p className="text-[11px] font-medium text-[var(--ink-subtle)] uppercase tracking-wide mb-2">
            Time Allocation
          </p>
          <div className="space-y-2">
            {result.time_allocation_differences.map((d, i) => (
              <div key={i} className="rounded-md border border-[var(--surface-3)] p-3">
                <div className="grid grid-cols-2 gap-2">
                  <p className="text-xs text-[var(--ink-primary)]">{d.judge_a_value}</p>
                  <p className="text-xs text-[var(--ink-primary)]">{d.judge_b_value}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Wording differences */}
      {result.wording_differences.length > 0 && (
        <div>
          <p className="text-[11px] font-medium text-[var(--ink-subtle)] uppercase tracking-wide mb-2">
            Wording Changes
          </p>
          <div className="space-y-2">
            {result.wording_differences.slice(0, 4).map((d, i) => (
              <div key={i} className="rounded-md border border-[var(--surface-3)] p-3">
                <p className="text-[11px] font-semibold text-[var(--ink-primary)] mb-1">
                  {d.dimension.replace(/_/g, " ")}
                </p>
                <div className="grid grid-cols-2 gap-2">
                  <p className="text-xs text-[var(--ink-subtle)]">{d.judge_a_value}</p>
                  <p className="text-xs text-[var(--ink-subtle)]">{d.judge_b_value}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
