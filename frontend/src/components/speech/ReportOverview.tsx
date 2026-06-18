"use client";

import { Stethoscope, TrendingUp, AlertTriangle, ArrowRight, Info } from "lucide-react";
import type { FeedbackReport, Speech } from "@/types";
import { deriveOverview } from "@/lib/reportModel";

interface ReportOverviewProps {
  feedback: FeedbackReport;
  speech: Speech | null;
  judgeLabel?: string;
  /** Anchors for the recommended action. */
  drillsHref?: string;
}

/**
 * Executive coaching diagnosis — leads with the assessment and the single most
 * important fix, not the score. The overall score appears only as a small
 * supporting chip.
 */
export default function ReportOverview({ feedback, speech, judgeLabel, drillsHref = "#drills" }: ReportOverviewProps) {
  const o = deriveOverview(feedback, speech);

  return (
    <section id="overview" className="flex flex-col gap-4 scroll-mt-20" aria-label="Overview">
      {/* Diagnosis */}
      <div className="rounded-xl border border-hairline bg-surface-2/50 p-4">
        <div className="mb-2 flex items-center justify-between gap-2">
          <span className="flex items-center gap-1.5 text-eyebrow text-lav">
            <Stethoscope size={13} aria-hidden /> Coach diagnosis
          </span>
          <div className="flex items-center gap-2">
            {judgeLabel && (
              <span className="rounded-full border border-hairline bg-surface-1 px-2 py-0.5 text-[10px] text-ink-subtle">
                {judgeLabel} lens
              </span>
            )}
            {o.overallScore != null && (
              <span className="rounded-full border border-hairline bg-surface-1 px-2 py-0.5 text-[10px] tabular-nums text-ink-subtle">
                {o.overallScore}/100
              </span>
            )}
          </div>
        </div>
        <p className="text-sm leading-relaxed text-ink">{o.diagnosis}</p>
        {o.reason && <p className="mt-1.5 text-xs text-ink-subtle">Most of all: {o.reason}</p>}
      </div>

      {/* Strength + priority weakness */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5 rounded-xl border border-ok/20 bg-ok/5 p-4">
          <span className="flex items-center gap-1.5 text-xs font-semibold text-ok">
            <TrendingUp size={13} aria-hidden /> Main strength
          </span>
          <p className="text-sm leading-relaxed text-ink">{o.strength ?? "No standout strength flagged yet."}</p>
        </div>
        <div className="flex flex-col gap-1.5 rounded-xl border border-warn/25 bg-warn/5 p-4">
          <span className="flex items-center gap-1.5 text-xs font-semibold text-warn">
            <AlertTriangle size={13} aria-hidden /> Priority weakness
          </span>
          <p className="text-sm leading-relaxed text-ink">{o.weakness ?? "No single weakness dominated."}</p>
        </div>
      </div>

      {/* Recommended next step */}
      {o.recommendedAction && (
        <a
          href={drillsHref}
          className="group flex items-center gap-3 rounded-xl border border-lav/30 bg-lav/[0.06] p-4 transition-colors hover:border-lav/50"
        >
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-lav/15">
            <ArrowRight size={15} className="text-lav" aria-hidden />
          </span>
          <span className="flex min-w-0 flex-col">
            <span className="text-eyebrow text-lav">Recommended next step</span>
            <span className="text-sm font-medium text-ink">{o.recommendedAction}</span>
          </span>
        </a>
      )}

      {/* Limitations */}
      {o.limitations.length > 0 && (
        <div className="flex items-start gap-2 rounded-lg border border-hairline bg-surface-2/40 px-3 py-2.5">
          <Info size={12} className="mt-0.5 shrink-0 text-ink-faint" aria-hidden />
          <ul className="flex flex-col gap-0.5">
            {o.limitations.map((l) => (
              <li key={l} className="text-xs leading-relaxed text-ink-subtle">{l}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
