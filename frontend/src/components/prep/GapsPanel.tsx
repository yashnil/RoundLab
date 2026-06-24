"use client";

import type { PrepGap, GapSeverity } from "@/types/prep";
import { AlertTriangle, Info, AlertCircle } from "lucide-react";

const SEVERITY_LABELS: Record<GapSeverity, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
  info: "Info",
};

const SEVERITY_COLORS: Record<GapSeverity, string> = {
  critical: "bg-danger/10 text-danger border-danger/20",
  high: "bg-rose-50 text-rose-700 border-rose-200",
  medium: "bg-amber-50 text-amber-700 border-amber-200",
  low: "bg-surface-muted text-ink-subtle border-border",
  info: "bg-surface-muted text-ink-subtle border-border",
};

const SEVERITY_ICON: Record<GapSeverity, React.ReactNode> = {
  critical: <AlertCircle size={12} />,
  high: <AlertTriangle size={12} />,
  medium: <AlertTriangle size={12} />,
  low: <Info size={12} />,
  info: <Info size={12} />,
};

interface GapsPanelProps {
  gaps: PrepGap[];
}

export function GapsPanel({ gaps }: GapsPanelProps) {
  if (gaps.length === 0) {
    return (
      <p className="py-8 text-center text-[12px] text-ok">
        No gaps detected. Your preparation looks strong.
      </p>
    );
  }

  const grouped: Record<GapSeverity, PrepGap[]> = {
    critical: [],
    high: [],
    medium: [],
    low: [],
    info: [],
  };
  for (const g of gaps) {
    grouped[g.severity].push(g);
  }

  const severityOrder: GapSeverity[] = ["critical", "high", "medium", "low", "info"];

  return (
    <div className="space-y-4">
      <p className="text-[12px] text-ink-subtle">
        {gaps.length} gap{gaps.length !== 1 ? "s" : ""} detected
      </p>
      {severityOrder.map((sev) => {
        const sevGaps = grouped[sev];
        if (sevGaps.length === 0) return null;
        return (
          <div key={sev} className="space-y-2">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-subtle">
              {SEVERITY_LABELS[sev]} ({sevGaps.length})
            </p>
            {sevGaps.map((gap, i) => (
              <div
                key={gap.id || i}
                className={`rounded-xl border px-4 py-3 space-y-1.5 ${SEVERITY_COLORS[gap.severity]}`}
              >
                <div className="flex items-start gap-2">
                  <span className="mt-0.5 shrink-0">{SEVERITY_ICON[gap.severity]}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-[12px] font-semibold leading-snug">{gap.title}</p>
                    <p className="text-[11px] opacity-80 leading-relaxed">{gap.reason}</p>
                  </div>
                </div>
                {gap.recommended_action && (
                  <p className="text-[11px] opacity-70 pl-5">
                    <span className="font-medium">Action:</span> {gap.recommended_action}
                    {gap.estimated_minutes ? ` (~${gap.estimated_minutes}m)` : ""}
                  </p>
                )}
                <div className="flex items-center gap-2 pl-5 flex-wrap">
                  <span className="text-[9px] opacity-60 uppercase tracking-wide">
                    {gap.gap_category.replace(/_/g, " ")}
                  </span>
                  {gap.is_deterministic && (
                    <span className="text-[9px] opacity-60">deterministic</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}
