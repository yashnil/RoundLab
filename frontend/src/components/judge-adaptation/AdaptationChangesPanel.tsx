"use client";

import { AdaptationChange, AdaptationRisk, RISK_LEVEL_COLORS } from "@/types/judgeAdaptation";

interface Props {
  changes: AdaptationChange[];
  risks: AdaptationRisk[];
}

const RISK_LEVEL_LABELS = {
  critical: "CRITICAL",
  high: "HIGH",
  medium: "MED",
  low: "LOW",
};

export function AdaptationChangesPanel({ changes, risks }: Props) {
  const criticalRisks = risks.filter((r) => r.level === "critical");

  return (
    <div className="space-y-4">
      {criticalRisks.length > 0 && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3">
          <p className="text-xs font-semibold text-red-700 mb-2">
            {criticalRisks.length} Critical Risk{criticalRisks.length !== 1 ? "s" : ""}
          </p>
          {criticalRisks.map((r, i) => (
            <div key={i} className="mb-2 last:mb-0">
              <p className="text-xs text-red-700 font-medium">{r.description}</p>
              <p className="text-[11px] text-red-600 mt-0.5">{r.how_to_mitigate}</p>
            </div>
          ))}
        </div>
      )}

      {changes.length > 0 && (
        <div>
          <p className="text-xs font-medium text-[var(--ink-subtle)] uppercase tracking-wide mb-2">
            Recommended Adaptations
          </p>
          <div className="space-y-2">
            {changes.map((c, i) => (
              <div
                key={i}
                className="rounded-md border border-[var(--surface-3)] bg-[var(--surface-2)] p-3"
              >
                <div className="flex items-start justify-between gap-2 mb-1">
                  <span className="text-[11px] font-semibold text-[var(--lavender-8)] uppercase tracking-wide">
                    {c.dimension.replace(/_/g, " ")}
                  </span>
                  {c.may_be_omitted && (
                    <span className="text-[10px] text-[var(--ink-subtle)] border border-[var(--surface-3)] rounded px-1">
                      Optional
                    </span>
                  )}
                </div>
                <p className="text-xs text-[var(--ink-primary)] mb-1">{c.adapted}</p>
                <p className="text-[11px] text-[var(--ink-subtle)]">{c.reason}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {risks.filter((r) => r.level !== "critical").length > 0 && (
        <div>
          <p className="text-xs font-medium text-[var(--ink-subtle)] uppercase tracking-wide mb-2">
            Other Risks
          </p>
          <div className="space-y-2">
            {risks
              .filter((r) => r.level !== "critical")
              .map((r, i) => (
                <div
                  key={i}
                  className={`rounded-md border px-3 py-2 ${RISK_LEVEL_COLORS[r.level]}`}
                >
                  <div className="flex items-start gap-2">
                    <span className="text-[10px] font-bold shrink-0 mt-0.5">
                      {RISK_LEVEL_LABELS[r.level]}
                    </span>
                    <div>
                      <p className="text-xs font-medium">{r.description}</p>
                      <p className="text-[11px] mt-0.5 opacity-80">{r.how_to_mitigate}</p>
                    </div>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {changes.length === 0 && risks.length === 0 && (
        <div className="text-center py-6 text-[var(--ink-subtle)]">
          <p className="text-sm">Select a source and judge type to see adaptation guidance.</p>
        </div>
      )}
    </div>
  );
}
