"use client";

import type { PrepReadinessReport, DimensionScore } from "@/types/prep";
import { AlertTriangle, CheckCircle, Clock, TrendingUp } from "lucide-react";

const DIMENSION_LABELS: Record<string, string> = {
  argument_coverage: "Argument Coverage",
  evidence_quality: "Evidence Quality",
  evidence_freshness: "Evidence Freshness",
  frontline_readiness: "Frontline Readiness",
  source_diversity: "Source Diversity",
  speech_stage_readiness: "Speech Stage",
  weighing_preparation: "Weighing Prep",
};

function ScoreBar({ score }: { score?: number }) {
  if (score === undefined || score === null) {
    return (
      <div className="flex items-center gap-2">
        <div className="flex-1 h-1.5 rounded-full bg-surface-muted" />
        <span className="text-[10px] text-ink-faint w-8 text-right">—</span>
      </div>
    );
  }
  const color =
    score >= 80 ? "bg-ok" : score >= 60 ? "bg-amber-500" : "bg-danger";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-surface-muted">
        <div
          className={`h-full rounded-full ${color} transition-all`}
          style={{ width: `${score}%` }}
        />
      </div>
      <span className="text-[10px] text-ink-subtle w-8 text-right tabular-nums">
        {score}
      </span>
    </div>
  );
}

function DimensionRow({ dim }: { dim: DimensionScore }) {
  return (
    <div className="space-y-0.5">
      <div className="flex items-center justify-between">
        <span className="text-[12px] text-ink">
          {DIMENSION_LABELS[dim.dimension] || dim.dimension}
        </span>
        {dim.score === undefined || dim.score === null ? (
          <span className="text-[10px] text-ink-faint">no data</span>
        ) : null}
      </div>
      <ScoreBar score={dim.score ?? undefined} />
      {dim.explanation && (
        <p className="text-[10px] text-ink-subtle leading-relaxed">{dim.explanation}</p>
      )}
    </div>
  );
}

interface ReadinessOverviewProps {
  report: PrepReadinessReport;
}

export function ReadinessOverview({ report }: ReadinessOverviewProps) {
  const dims = report.dimensions;
  const dimList = [
    dims.argument_coverage,
    dims.evidence_quality,
    dims.evidence_freshness,
    dims.frontline_readiness,
    dims.source_diversity,
    dims.speech_stage_readiness,
    dims.weighing_preparation,
  ];

  const composite = report.composite_score;
  const compositeColor =
    composite !== undefined && composite !== null
      ? composite >= 80
        ? "text-ok"
        : composite >= 60
          ? "text-amber-500"
          : "text-danger"
      : "text-ink-subtle";

  return (
    <div className="space-y-5">
      {/* Composite score */}
      <div className="rounded-xl border border-border bg-surface-muted px-4 py-3 flex items-center gap-4">
        <div className="text-center">
          <p className={`text-[32px] font-bold tabular-nums ${compositeColor}`}>
            {composite !== undefined && composite !== null ? composite : "—"}
          </p>
          <p className="text-[10px] text-ink-subtle">Readiness Score</p>
        </div>
        <div className="flex-1 space-y-1">
          <p className="text-[13px] font-semibold text-ink">
            {report.resolution_title || "Tournament Prep Overview"}
          </p>
          <p className="text-[11px] text-ink-subtle capitalize">
            {report.side === "both" ? "Pro + Con" : report.side} ·{" "}
            {report.total_arguments} argument{report.total_arguments !== 1 ? "s" : ""} ·{" "}
            {report.total_cards} card{report.total_cards !== 1 ? "s" : ""} ·{" "}
            {report.total_frontlines} frontline{report.total_frontlines !== 1 ? "s" : ""}
          </p>
          {report.tournament_date && (
            <p className="text-[10px] text-lav flex items-center gap-1">
              <Clock size={11} />
              Tournament: {report.tournament_date}
            </p>
          )}
        </div>
      </div>

      {/* Dimension scores */}
      <div className="space-y-3">
        <p className="text-[11px] font-semibold text-ink-subtle uppercase tracking-wide">
          Readiness Dimensions
        </p>
        <div className="space-y-3">
          {dimList.map((d) => (
            <DimensionRow key={d.dimension} dim={d} />
          ))}
        </div>
      </div>

      {/* Next actions */}
      {report.next_recommended_actions.length > 0 && (
        <div className="space-y-2">
          <p className="text-[11px] font-semibold text-ink-subtle uppercase tracking-wide">
            Recommended Next Steps
          </p>
          {report.next_recommended_actions.map((action, i) => (
            <div
              key={i}
              className="flex items-start gap-2 text-[12px] text-ink rounded-lg border border-border px-3 py-2"
            >
              <TrendingUp size={13} className="text-lav mt-0.5 shrink-0" />
              <span>{action}</span>
            </div>
          ))}
        </div>
      )}

      {/* Strengths and weaknesses */}
      {(report.strongest_arguments.length > 0 || report.weakest_frontlines.length > 0) && (
        <div className="grid grid-cols-2 gap-3">
          {report.strongest_arguments.length > 0 && (
            <div className="rounded-xl border border-ok/20 bg-ok/5 px-3 py-2 space-y-1.5">
              <p className="text-[10px] font-semibold text-ok uppercase tracking-wide flex items-center gap-1">
                <CheckCircle size={11} />
                Strongest
              </p>
              {report.strongest_arguments.map((a, i) => (
                <p key={i} className="text-[11px] text-ink truncate">{a}</p>
              ))}
            </div>
          )}
          {report.weakest_frontlines.length > 0 && (
            <div className="rounded-xl border border-amber-300/40 bg-amber-50/50 px-3 py-2 space-y-1.5">
              <p className="text-[10px] font-semibold text-amber-700 uppercase tracking-wide flex items-center gap-1">
                <AlertTriangle size={11} />
                Needs Work
              </p>
              {report.weakest_frontlines.map((f, i) => (
                <p key={i} className="text-[11px] text-ink truncate">{f}</p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
