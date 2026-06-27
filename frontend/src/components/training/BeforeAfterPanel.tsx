"use client";
import { ArrowRight, CheckCircle, AlertCircle } from "lucide-react";

interface Criterion {
  name: string;
  improved: boolean;
  description: string;
}

interface Props {
  beforeExcerpt: string;
  afterExcerpt: string;
  originalScore: number;
  revisedScore: number;
  criteriaChanged: Criterion[];
  remainingIssues: string[];
  skillName: string;
}

export function BeforeAfterPanel({
  beforeExcerpt,
  afterExcerpt,
  originalScore,
  revisedScore,
  criteriaChanged,
  remainingIssues,
  skillName,
}: Props) {
  const delta = revisedScore - originalScore;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <p className="text-[13px] font-bold text-ink">{skillName} — Improvement</p>
        <span
          className={`text-[12px] font-semibold px-2 py-0.5 rounded-full ${
            delta > 0
              ? "bg-ok/10 text-ok"
              : delta < 0
              ? "bg-danger/10 text-danger"
              : "bg-surface-2 text-ink-subtle"
          }`}
        >
          {delta > 0 ? "+" : ""}
          {delta.toFixed(0)} pts
        </span>
      </div>

      {/* Side by side */}
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-xl border border-danger/20 bg-danger/5 p-3">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-danger mb-2">Before</p>
          <p className="text-[12px] text-ink-subtle italic leading-relaxed">&ldquo;{beforeExcerpt}&rdquo;</p>
          <p className="mt-2 text-[11px] text-ink-faint">Score: {originalScore.toFixed(0)}</p>
        </div>
        <div className="rounded-xl border border-ok/20 bg-ok/5 p-3">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-ok mb-2">After</p>
          <p className="text-[12px] text-ink italic leading-relaxed">&ldquo;{afterExcerpt}&rdquo;</p>
          <p className="mt-2 text-[11px] text-ink-faint">Score: {revisedScore.toFixed(0)}</p>
        </div>
      </div>

      {/* What changed */}
      {criteriaChanged.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-subtle">What changed</p>
          {criteriaChanged.map((c, i) => (
            <div key={i} className="flex items-start gap-2">
              {c.improved ? (
                <CheckCircle size={13} className="shrink-0 mt-0.5 text-ok" aria-hidden />
              ) : (
                <AlertCircle size={13} className="shrink-0 mt-0.5 text-warn" aria-hidden />
              )}
              <div>
                <span className="text-[12px] font-medium text-ink">{c.name}</span>
                <p className="text-[11px] text-ink-subtle">{c.description}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Still missing */}
      {remainingIssues.length > 0 && (
        <div className="rounded-xl border border-warn/20 bg-warn/5 px-3 py-2.5 space-y-1">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-warn">Still missing</p>
          {remainingIssues.map((issue, i) => (
            <p key={i} className="text-[12px] text-ink-subtle flex items-center gap-1.5">
              <ArrowRight size={11} className="shrink-0 text-warn" aria-hidden />
              {issue}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
