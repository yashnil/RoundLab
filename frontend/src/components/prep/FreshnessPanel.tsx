"use client";

import type { EvidenceFreshnessAssessment, FreshnessState } from "@/types/prep";

const FRESHNESS_LABELS: Record<FreshnessState, string> = {
  current: "Current",
  aging: "Aging",
  stale: "Stale",
  superseded: "Superseded",
  older_but_still_relevant: "Older but relevant",
  freshness_unknown: "Unknown date",
  not_time_sensitive: "Non-temporal",
};

const FRESHNESS_COLORS: Record<FreshnessState, string> = {
  current: "bg-ok/10 text-ok border-ok/20",
  aging: "bg-amber-50 text-amber-700 border-amber-200",
  stale: "bg-danger/10 text-danger border-danger/20",
  superseded: "bg-danger/10 text-danger border-danger/20",
  older_but_still_relevant: "bg-sky-50 text-sky-700 border-sky-200",
  freshness_unknown: "bg-surface-muted text-ink-subtle border-border",
  not_time_sensitive: "bg-surface-muted text-ink-subtle border-border",
};

interface FreshnessPanelProps {
  assessments: EvidenceFreshnessAssessment[];
}

export function FreshnessPanel({ assessments }: FreshnessPanelProps) {
  if (assessments.length === 0) {
    return (
      <p className="py-8 text-center text-[12px] text-ink-subtle">
        No evidence cards assessed yet.
      </p>
    );
  }

  // Sort: stale first, then aging, then unknown, then rest
  const order: Record<FreshnessState, number> = {
    stale: 0,
    superseded: 1,
    aging: 2,
    freshness_unknown: 3,
    older_but_still_relevant: 4,
    current: 5,
    not_time_sensitive: 6,
  };
  const sorted = [...assessments].sort(
    (a, b) => (order[a.freshness_state] ?? 9) - (order[b.freshness_state] ?? 9)
  );

  const counts: Partial<Record<FreshnessState, number>> = {};
  for (const a of assessments) {
    counts[a.freshness_state] = (counts[a.freshness_state] ?? 0) + 1;
  }

  return (
    <div className="space-y-4">
      {/* Summary bar */}
      <div className="flex flex-wrap gap-2">
        {(Object.entries(counts) as [FreshnessState, number][]).map(([state, count]) => (
          <span
            key={state}
            className={`text-[10px] px-2 py-1 rounded-md border ${FRESHNESS_COLORS[state]}`}
          >
            {FRESHNESS_LABELS[state]}: {count}
          </span>
        ))}
      </div>

      {/* Card list */}
      <div className="space-y-2">
        {sorted
          .filter(
            (a) =>
              a.freshness_state !== "current" &&
              a.freshness_state !== "not_time_sensitive"
          )
          .map((a) => (
            <div
              key={a.card_id}
              className="rounded-xl border border-border px-4 py-3 space-y-1"
            >
              <div className="flex items-center gap-2">
                <span
                  className={`text-[10px] px-1.5 py-0.5 rounded border ${FRESHNESS_COLORS[a.freshness_state]}`}
                >
                  {FRESHNESS_LABELS[a.freshness_state]}
                </span>
                <p className="text-[12px] font-semibold text-ink truncate flex-1">
                  {a.card_tag || a.card_id}
                </p>
                {a.days_old !== undefined && a.days_old !== null && (
                  <span className="text-[10px] text-ink-faint shrink-0">
                    {Math.floor(a.days_old / 365) > 0
                      ? `${Math.floor(a.days_old / 365)}y`
                      : `${Math.floor(a.days_old / 30)}mo`}{" "}
                    old
                  </span>
                )}
              </div>
              <p className="text-[11px] text-ink-subtle leading-relaxed">
                {a.explanation}
              </p>
              <p className="text-[10px] text-ink-faint">
                Rule: {a.rule_applied} · Claim type: {a.claim_type}
              </p>
            </div>
          ))}
        {sorted.filter(
          (a) =>
            a.freshness_state !== "current" &&
            a.freshness_state !== "not_time_sensitive"
        ).length === 0 && (
          <p className="py-6 text-center text-[12px] text-ok">
            All assessed cards are current or non-temporal.
          </p>
        )}
      </div>
    </div>
  );
}
