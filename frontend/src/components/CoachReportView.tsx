"use client";

/**
 * CoachReportView — clean, print-friendly coach report.
 * Used by the public shared report page and the authenticated print view.
 * Renders only sections present in the payload (controlled by include_flags).
 */

import {
  CheckCircle2, AlertCircle, XCircle, HelpCircle,
  TrendingUp, TrendingDown, Minus,
} from "lucide-react";
import type {
  SharedReportPayload,
  SharedReportArgument,
  SharedReportDrill,
  ArgumentType,
} from "@/types";
import {
  speechTypeLabel,
  judgeTypeLabel,
  scoreColor,
  formatDelta,
  deltaBadgeClass,
} from "@/lib/reportHelpers";

// ── Tiny primitives ────────────────────────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-3 print:break-inside-avoid-page">
      <h2 className="border-b border-hairline pb-1.5 text-sm font-semibold uppercase tracking-widest text-ink-subtle print:border-gray-300 print:text-gray-500">
        {title}
      </h2>
      {children}
    </section>
  );
}

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-full border border-hairline bg-surface-2 px-2.5 py-0.5 text-xs font-medium text-ink-subtle print:border-gray-200 print:bg-white print:text-gray-600">
      {children}
    </span>
  );
}

function ScoreRingSimple({ score }: { score: number }) {
  const color = score >= 80 ? "text-ok" : score >= 60 ? "text-warn" : "text-danger";
  return (
    <div className={`flex flex-col items-center ${color}`}>
      <span className="text-3xl font-bold tabular-nums">{score}</span>
      <span className="text-[10px] uppercase tracking-wide text-ink-faint">/100</span>
    </div>
  );
}

const ARG_TYPE_COLORS: Record<ArgumentType, string> = {
  offense: "border-l-ok",
  defense: "border-l-lav",
  weighing: "border-l-warn",
  response: "border-l-cyan",
  unclear: "border-l-hairline",
};

function ArgumentRow({ arg }: { arg: SharedReportArgument }) {
  return (
    <div className={`border-l-2 pl-3 ${ARG_TYPE_COLORS[arg.argument_type] ?? "border-l-hairline"} flex flex-col gap-0.5 print:break-inside-avoid`}>
      <p className="text-xs font-semibold uppercase tracking-wide text-ink-subtle">{arg.label}</p>
      <p className="text-sm text-ink">{arg.claim}</p>
      {arg.warrant && <p className="text-xs text-ink-muted">{arg.warrant}</p>}
      {arg.evidence && (
        <p className="text-[11px] italic text-ink-faint">Evidence: {arg.evidence}</p>
      )}
    </div>
  );
}

function DrillRow({ drill, index }: { drill: SharedReportDrill; index: number }) {
  return (
    <div className="rounded-lg border border-hairline bg-surface p-3 flex flex-col gap-1.5 print:border-gray-200 print:break-inside-avoid">
      <div className="flex items-center gap-2">
        <span className="text-xs font-semibold text-lav">{index + 1}.</span>
        <p className="text-sm font-medium text-ink">{drill.title}</p>
        <span className="ml-auto text-[10px] uppercase tracking-wide text-ink-faint">{drill.skill_target}</span>
      </div>
      {drill.description && <p className="text-xs text-ink-subtle">{drill.description}</p>}
      <p className="text-xs text-ink-muted leading-relaxed">{drill.prompt}</p>
      {drill.success_criteria.length > 0 && (
        <ul className="mt-0.5 flex flex-col gap-0.5 pl-3">
          {drill.success_criteria.slice(0, 3).map((c, i) => (
            <li key={i} className="text-[11px] text-ink-faint list-disc">{c}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

const SUPPORT_ICON: Record<string, React.ReactNode> = {
  supported: <CheckCircle2 size={12} className="text-ok" />,
  partially_supported: <AlertCircle size={12} className="text-warn" />,
  unsupported: <XCircle size={12} className="text-danger" />,
  unverifiable: <HelpCircle size={12} className="text-ink-faint" />,
};

function DeltaRow({
  label,
  delta,
  unit = "",
}: {
  label: string;
  delta: number | null | undefined;
  unit?: string;
}) {
  const Icon =
    delta === null || delta === undefined ? Minus :
    delta > 0 ? TrendingUp :
    delta < 0 ? TrendingDown : Minus;
  return (
    <div className="flex items-center justify-between gap-2 text-sm">
      <span className="text-ink-subtle">{label}</span>
      <span className={`flex items-center gap-1 font-semibold tabular-nums ${deltaBadgeClass(delta)}`}>
        <Icon size={13} />
        {formatDelta(delta, unit)}
      </span>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

interface CoachReportViewProps {
  data: SharedReportPayload;
}

export default function CoachReportView({ data }: CoachReportViewProps) {
  const date = new Date(data.created_at).toLocaleDateString(undefined, {
    month: "long", day: "numeric", year: "numeric",
  });

  return (
    <article className="mx-auto flex max-w-3xl flex-col gap-8 px-4 py-8 sm:px-6 print:max-w-none print:px-0 print:py-4 print:gap-6">

      {/* ── Report Header ──────────────────────────────────────────────────── */}
      <header className="flex flex-col gap-3">
        <div className="flex items-start justify-between gap-4">
          <div className="flex flex-col gap-1">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-ink-faint print:text-gray-400">
              Dissio Coach Report
            </p>
            <h1 className="text-2xl font-bold text-ink print:text-3xl print:text-black">
              {speechTypeLabel(data.speech_type)}
            </h1>
            <div className="flex flex-wrap gap-1.5 mt-0.5">
              {data.side && <Chip>{data.side === "pro" ? "Pro" : "Con"}</Chip>}
              {data.judge_type && <Chip>{judgeTypeLabel(data.judge_type)}</Chip>}
              <Chip>{date}</Chip>
            </div>
          </div>
          {data.feedback?.overall_score !== null && data.feedback?.overall_score !== undefined && (
            <div className="shrink-0">
              <ScoreRingSimple score={data.feedback.overall_score} />
            </div>
          )}
        </div>
        {data.topic && (
          <p className="text-xs leading-relaxed text-ink-faint border-l-2 border-hairline pl-2 print:border-gray-300 print:text-gray-400">
            {data.topic}
          </p>
        )}
      </header>

      {/* ── Feedback ───────────────────────────────────────────────────────── */}
      {data.feedback && (
        <Section title="Judge Feedback">
          {data.feedback.summary && (
            <div className="rounded-lg border border-hairline bg-surface px-4 py-3 text-sm text-ink leading-relaxed print:border-gray-200 print:bg-white print:text-black">
              {data.feedback.summary}
            </div>
          )}

          {data.feedback.top_3_priorities && data.feedback.top_3_priorities.length > 0 && (
            <div className="flex flex-col gap-1.5">
              <p className="text-xs font-semibold uppercase tracking-wide text-ink-subtle">Top priorities</p>
              {data.feedback.top_3_priorities.map((p, i) => (
                <div key={i} className="flex gap-2 text-sm text-ink">
                  <span className="shrink-0 font-bold text-lav">{i + 1}.</span>
                  <span>{p}</span>
                </div>
              ))}
            </div>
          )}

          <div className="grid gap-3 sm:grid-cols-2">
            {data.feedback.strengths.length > 0 && (
              <div className="flex flex-col gap-1.5">
                <p className="text-xs font-semibold uppercase tracking-wide text-ok">Strengths</p>
                {data.feedback.strengths.map((s, i) => (
                  <p key={i} className="flex gap-1.5 text-xs text-ink">
                    <CheckCircle2 size={12} className="mt-0.5 shrink-0 text-ok" />
                    {s}
                  </p>
                ))}
              </div>
            )}
            {data.feedback.weaknesses.length > 0 && (
              <div className="flex flex-col gap-1.5">
                <p className="text-xs font-semibold uppercase tracking-wide text-danger">Areas to improve</p>
                {data.feedback.weaknesses.map((w, i) => (
                  <p key={i} className="flex gap-1.5 text-xs text-ink">
                    <AlertCircle size={12} className="mt-0.5 shrink-0 text-warn" />
                    {w}
                  </p>
                ))}
              </div>
            )}
          </div>

          {data.feedback.scores && (
            <div className="grid grid-cols-5 gap-2">
              {Object.entries(data.feedback.scores).map(([dim, score]) => (
                <div key={dim} className="flex flex-col items-center gap-0.5 rounded border border-hairline bg-surface-2 py-2 print:border-gray-200">
                  <span className={`text-lg font-bold tabular-nums ${scoreColor(score)}`}>{score}</span>
                  <span className="text-center text-[9px] uppercase tracking-wide text-ink-faint leading-tight print:text-gray-400">
                    {dim.replace("_", " ")}
                  </span>
                </div>
              ))}
            </div>
          )}
        </Section>
      )}

      {/* ── Flow ───────────────────────────────────────────────────────────── */}
      {data.arguments && data.arguments.length > 0 && (
        <Section title="Argument Flow">
          <div className="flex flex-col gap-3">
            {data.arguments.map((arg, i) => (
              <ArgumentRow key={i} arg={arg} />
            ))}
          </div>
        </Section>
      )}

      {/* ── Delivery ───────────────────────────────────────────────────────── */}
      {data.delivery && (
        <Section title="Delivery Coach">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {[
              {
                label: "Score",
                value: data.delivery.delivery_score !== null ? `${data.delivery.delivery_score}/100` : "—",
                color: scoreColor(data.delivery.delivery_score),
              },
              {
                label: "WPM",
                value: data.delivery.words_per_minute !== null ? `${Math.round(data.delivery.words_per_minute ?? 0)}` : "—",
                color: "text-ink",
              },
              {
                label: "Filler words",
                value: data.delivery.filler_word_count !== null ? String(data.delivery.filler_word_count) : "—",
                color: (data.delivery.filler_word_count ?? 0) > 5 ? "text-warn" : "text-ok",
              },
              {
                label: "Pacing",
                value: data.delivery.pacing_band?.replace("_", " ") ?? "—",
                color:
                  data.delivery.pacing_band === "steady" ? "text-ok" :
                  data.delivery.pacing_band === "unknown" ? "text-ink-faint" :
                  "text-warn",
              },
            ].map(({ label, value, color }) => (
              <div key={label} className="flex flex-col items-center rounded border border-hairline bg-surface-2 py-3 print:border-gray-200">
                <span className={`text-xl font-bold ${color}`}>{value}</span>
                <span className="text-[10px] uppercase tracking-wide text-ink-faint">{label}</span>
              </div>
            ))}
          </div>
          {data.delivery.repeated_phrases_json && data.delivery.repeated_phrases_json.length > 0 && (
            <div className="flex flex-col gap-1">
              <p className="text-xs font-medium text-ink-subtle">Repeated phrases</p>
              <div className="flex flex-wrap gap-1.5">
                {data.delivery.repeated_phrases_json.slice(0, 5).map(({ phrase, count }) => (
                  <span key={phrase} className="rounded-full border border-hairline bg-surface-2 px-2 py-0.5 text-xs text-ink-subtle print:border-gray-200">
                    &ldquo;{phrase}&rdquo; &times;{count}
                  </span>
                ))}
              </div>
            </div>
          )}
        </Section>
      )}

      {/* ── Evidence Summary ───────────────────────────────────────────────── */}
      {data.evidence_summary && (
        <Section title="Evidence Risk Summary">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {([
              { label: "Supported", count: data.evidence_summary.supported_count, color: "text-ok" },
              { label: "Partial", count: data.evidence_summary.partially_supported_count, color: "text-warn" },
              { label: "Unsupported", count: data.evidence_summary.unsupported_count, color: "text-danger" },
              { label: "No match", count: data.evidence_summary.unverifiable_count, color: "text-ink-faint" },
            ] as const).map(({ label, count, color }) => (
              <div key={label} className="flex flex-col items-center rounded border border-hairline bg-surface-2 py-2 print:border-gray-200">
                <span className={`text-2xl font-bold ${color}`}>{count}</span>
                <span className="text-[10px] uppercase tracking-wide text-ink-faint">{label}</span>
              </div>
            ))}
          </div>
          {data.evidence_summary.top_issues.length > 0 && (
            <div className="flex flex-col gap-1.5">
              <p className="text-xs font-medium text-ink-subtle">Claims needing attention</p>
              {data.evidence_summary.top_issues.map((issue, i) => (
                <div key={i} className="flex gap-2 items-start text-xs print:break-inside-avoid">
                  {SUPPORT_ICON[issue.support_level] ?? <HelpCircle size={12} />}
                  <span className="text-ink">{issue.claim_text}</span>
                </div>
              ))}
            </div>
          )}
          <p className="text-[10px] text-ink-faint">
            Only uploaded evidence was checked. Outside knowledge was never used.
          </p>
        </Section>
      )}

      {/* ── Practice Plan ──────────────────────────────────────────────────── */}
      {data.drills && data.drills.length > 0 && (
        <Section title="Practice Plan">
          <div className="flex flex-col gap-2">
            {data.drills.map((drill, i) => (
              <DrillRow key={i} drill={drill} index={i} />
            ))}
          </div>
        </Section>
      )}

      {/* ── Improvement ────────────────────────────────────────────────────── */}
      {data.comparison && (
        <Section title="Improvement vs. Previous Speech">
          <div className="rounded-lg border border-hairline bg-surface p-4 flex flex-col gap-2 print:border-gray-200">
            <p className="text-sm text-ink leading-relaxed">{data.comparison.summary}</p>
            <div className="mt-1 flex flex-col gap-1.5 border-t border-hairline pt-3 print:border-gray-200">
              <DeltaRow label="Overall score" delta={data.comparison.overall_delta} unit=" pts" />
              {data.comparison.delivery_score_delta !== null && (
                <DeltaRow label="Delivery score" delta={data.comparison.delivery_score_delta} unit=" pts" />
              )}
              {data.comparison.filler_delta !== null && (
                <DeltaRow label="Filler words" delta={data.comparison.filler_delta !== null ? -data.comparison.filler_delta : null} unit=" fewer" />
              )}
              {data.comparison.wpm_delta !== null && (
                <DeltaRow label="WPM change" delta={data.comparison.wpm_delta} unit=" wpm" />
              )}
            </div>
          </div>
        </Section>
      )}

      {/* ── Transcript ─────────────────────────────────────────────────────── */}
      {data.transcript_text && (
        <Section title="Transcript">
          <div className="rounded-lg border border-hairline bg-surface-2 px-4 py-3 print:border-gray-200">
            <p className="whitespace-pre-wrap text-xs text-ink leading-relaxed print:text-sm print:text-black">
              {data.transcript_text}
            </p>
          </div>
        </Section>
      )}

      {/* ── Footer ─────────────────────────────────────────────────────────── */}
      <footer className="border-t border-hairline pt-4 text-[10px] text-ink-faint print:border-gray-200 print:text-gray-400">
        Generated by Dissio — AI flow coach for Public Forum debaters.
        Shared reports are read-only. Audio and full evidence documents are never shared.
      </footer>
    </article>
  );
}
