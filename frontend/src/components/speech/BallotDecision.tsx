"use client";

import { Gavel, Check, AlertCircle, Scale, GraduationCap, ArrowRight, ArrowDown } from "lucide-react";
import type { FeedbackReport } from "@/types";
import { deriveBallot } from "@/lib/reportModel";

interface BallotDecisionProps {
  feedback: FeedbackReport;
  judgeLabel?: string;
  drillsHref?: string;
  transcriptHref?: string;
}

/**
 * The ballot, split into two visually distinct layers: the judge's decision
 * (what happened on the flow) and the coach's translation (why, and what to fix).
 * Uses authorship tokens so judge reasoning reads differently from coaching.
 */
export default function BallotDecision({ feedback, judgeLabel, drillsHref = "#drills", transcriptHref = "#transcript" }: BallotDecisionProps) {
  const b = deriveBallot(feedback);

  return (
    <section id="ballot" className="flex flex-col gap-4 scroll-mt-20" aria-label="Ballot">
      <div className="flex items-center gap-2">
        <span className="flex h-6 w-6 items-center justify-center rounded-md bg-surface-2 text-ink-subtle">
          <Gavel size={13} aria-hidden />
        </span>
        <h3 className="text-heading text-ink">Ballot</h3>
        {judgeLabel && <span className="rounded-full border border-hairline bg-surface-1 px-2 py-0.5 text-[10px] text-ink-subtle">{judgeLabel} lens</span>}
      </div>

      {/* ── Judge decision ─────────────────────────────────────────────── */}
      <div className="rounded-xl border border-authored-ai/30 bg-authored-ai/[0.05] p-4">
        <p className="mb-3 flex items-center gap-1.5 text-eyebrow text-authored-ai">
          <Gavel size={12} aria-hidden /> Judge decision
        </p>

        {b.votingIssue && (
          <div className="mb-3">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-faint">Voting issue</p>
            <p className="text-sm font-medium text-ink">{b.votingIssue}</p>
          </div>
        )}

        {/* Decision path */}
        {b.decisionPath.length > 0 && (
          <ol className="mb-3 flex flex-col gap-1.5 sm:flex-row sm:flex-wrap sm:items-center">
            {b.decisionPath.map((step, i) => (
              <li key={step} className="flex items-center gap-1.5">
                <span className="rounded-md border border-hairline bg-surface-1 px-2 py-1 text-xs text-ink">{step}</span>
                {i < b.decisionPath.length - 1 && (
                  <>
                    <ArrowRight size={12} className="hidden text-ink-faint sm:inline" aria-hidden />
                    <ArrowDown size={12} className="text-ink-faint sm:hidden" aria-hidden />
                  </>
                )}
              </li>
            ))}
          </ol>
        )}

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {b.accepted.length > 0 && (
            <div className="flex flex-col gap-1">
              <p className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-ok"><Check size={10} aria-hidden /> Accepted</p>
              <ul className="flex flex-col gap-1">
                {b.accepted.map((a) => <li key={a} className="text-xs leading-relaxed text-ink-subtle">{a}</li>)}
              </ul>
            </div>
          )}
          {b.unresolved.length > 0 && (
            <div className="flex flex-col gap-1">
              <p className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-danger"><AlertCircle size={10} aria-hidden /> Unresolved / dropped</p>
              <ul className="flex flex-col gap-1">
                {b.unresolved.map((u) => <li key={u} className="text-xs leading-relaxed text-ink-subtle">{u}</li>)}
              </ul>
            </div>
          )}
        </div>

        {b.weighing.length > 0 && (
          <div className="mt-3 flex flex-col gap-1 border-t border-authored-ai/15 pt-3">
            <p className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-ink-faint"><Scale size={10} aria-hidden /> Weighing</p>
            <ul className="flex flex-col gap-1">
              {b.weighing.map((w) => <li key={w} className="text-xs leading-relaxed text-ink-subtle">{w}</li>)}
            </ul>
          </div>
        )}

        {b.rfd && <p className="mt-3 border-t border-authored-ai/15 pt-3 text-xs leading-relaxed text-ink-subtle"><span className="font-semibold text-ink">RFD:</span> {b.rfd}</p>}
      </div>

      {/* ── Coach translation ──────────────────────────────────────────── */}
      <div className="rounded-xl border border-authored-coach/30 bg-authored-coach/[0.05] p-4">
        <p className="mb-3 flex items-center gap-1.5 text-eyebrow text-authored-coach">
          <GraduationCap size={12} aria-hidden /> Coach translation
        </p>
        {b.coachFix && (
          <div className="mb-2">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-faint">The one fix that flips this</p>
            <p className="text-sm font-medium text-ink">{b.coachFix}</p>
          </div>
        )}
        {b.coachWhy && <p className="text-xs leading-relaxed text-ink-subtle">{b.coachWhy}</p>}
        {b.judgeAdaptation && (
          <p className="mt-2 text-xs leading-relaxed text-ink-subtle"><span className="font-semibold text-ink">Judge adaptation:</span> {b.judgeAdaptation}</p>
        )}
        {b.recommendations.length > 0 && (
          <ul className="mt-3 flex flex-col gap-1.5 border-t border-authored-coach/15 pt-3">
            {b.recommendations.map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-xs leading-relaxed text-ink">
                <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border border-authored-coach/30 text-[8px] font-bold text-authored-coach">{i + 1}</span>
                {r}
              </li>
            ))}
          </ul>
        )}
        <div className="mt-3 flex flex-wrap gap-3 border-t border-authored-coach/15 pt-3 text-[11px] font-medium">
          <a href={transcriptHref} className="text-lav hover:underline">Jump to transcript →</a>
          <a href={drillsHref} className="text-lav hover:underline">Practice this →</a>
        </div>
      </div>
    </section>
  );
}
