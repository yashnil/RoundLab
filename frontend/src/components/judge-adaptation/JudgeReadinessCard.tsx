"use client";

import { JudgeReadinessDimensionScore, JudgeReadinessReport, JUDGE_TYPE_LABELS } from "@/types/judgeAdaptation";

interface Props {
  report: JudgeReadinessReport;
}

const DIM_LABELS: Record<string, string> = {
  clarity: "Clarity",
  organization: "Organization",
  extension_completeness: "Extensions",
  evidence_explanation: "Evidence Explanation",
  weighing_fit: "Weighing Fit",
  jargon_fit: "Jargon Fit",
  strategic_focus: "Strategic Focus",
  speech_stage_legality: "Speech Legality",
};

function DimBar({ dim }: { dim: JudgeReadinessDimensionScore }) {
  if (dim.score === null) {
    return (
      <div className="flex items-center gap-3">
        <span className="text-xs text-[var(--ink-subtle)] w-36 shrink-0">
          {DIM_LABELS[dim.dimension] || dim.dimension}
        </span>
        <span className="text-[11px] text-[var(--ink-subtle)] italic">No data</span>
      </div>
    );
  }

  const color =
    dim.score >= 80
      ? "bg-emerald-500"
      : dim.score >= 60
      ? "bg-yellow-400"
      : "bg-red-500";

  return (
    <div>
      <div className="flex items-center gap-3 mb-0.5">
        <span className="text-xs text-[var(--ink-primary)] w-36 shrink-0">
          {DIM_LABELS[dim.dimension] || dim.dimension}
        </span>
        <div className="flex-1 h-1.5 rounded-full bg-[var(--surface-3)] overflow-hidden">
          <div
            className={`h-full rounded-full ${color} transition-all duration-500`}
            style={{ width: `${dim.score}%` }}
          />
        </div>
        <span className="text-xs font-medium text-[var(--ink-primary)] w-8 text-right tabular-nums">
          {dim.score}
        </span>
      </div>
      {dim.contributing_risks.length > 0 && (
        <div className="ml-36 pl-3">
          {dim.contributing_risks.slice(0, 2).map((r, i) => (
            <p key={i} className="text-[10px] text-[var(--ink-subtle)] truncate">{r}</p>
          ))}
        </div>
      )}
    </div>
  );
}

export function JudgeReadinessCard({ report }: Props) {
  const dims = [
    report.clarity,
    report.organization,
    report.extension_completeness,
    report.evidence_explanation,
    report.weighing_fit,
    report.jargon_fit,
    report.strategic_focus,
    report.speech_stage_legality,
  ];

  const composite = report.composite_score;
  const compositeColor =
    composite === null
      ? "text-[var(--ink-subtle)]"
      : composite >= 80
      ? "text-emerald-600"
      : composite >= 60
      ? "text-yellow-600"
      : "text-red-600";

  return (
    <div className="rounded-lg border border-[var(--surface-3)] bg-[var(--surface-2)] p-4">
      <div className="flex items-start justify-between mb-4">
        <div>
          <p className="text-[11px] font-medium text-[var(--ink-subtle)] uppercase tracking-wide">
            Judge Readiness
          </p>
          <p className="text-sm font-semibold text-[var(--ink-primary)] mt-0.5">
            {JUDGE_TYPE_LABELS[report.judge_type]}
          </p>
          <p className="text-[11px] text-[var(--ink-subtle)] mt-0.5">
            Separate from evidence quality
          </p>
        </div>
        <div className="text-right">
          <p className={`text-2xl font-bold tabular-nums ${compositeColor}`}>
            {composite !== null ? composite : "—"}
          </p>
          <p className="text-[10px] text-[var(--ink-subtle)]">/ 100</p>
        </div>
      </div>

      <div className="space-y-2">
        {dims.map((d) => (
          <DimBar key={d.dimension} dim={d} />
        ))}
      </div>

      {report.risks.filter((r) => r.level === "critical").length > 0 && (
        <div className="mt-3 rounded-md bg-red-50 border border-red-200 px-3 py-2">
          <p className="text-xs font-semibold text-red-700">
            {report.risks.filter((r) => r.level === "critical").length} critical risk
            {report.risks.filter((r) => r.level === "critical").length !== 1 ? "s" : ""} detected
          </p>
        </div>
      )}
    </div>
  );
}
