"use client";

/**
 * DeliveryCoachPanel — speaking delivery analysis for a speech report.
 *
 * Sections:
 *   A. Score card: delivery score, pacing band, WPM, filler count, word count, duration
 *   B. Coach note: debate-specific interpretation of the top issue
 *   C. Diagnostics: clarity flags expanded with label + description
 *   D. Speaking timeline: approximate transcript chunks with filler/repetition markers
 *   E. Filler word breakdown: per-word counts
 *
 * Progressive disclosure: timeline and breakdowns are collapsed by default.
 * Uses existing design tokens only.
 */

import { useState } from "react";
import {
  ChevronDown, ChevronUp, Clock, MessageSquare,
  AlertTriangle, CheckCircle2, Mic, BarChart2,
} from "lucide-react";
import type { DeliveryMetrics } from "@/types";
import {
  getPacingBandDisplay,
  getFlagDisplay,
  deliveryScoreColor,
  formatWpm,
  formatFillerBreakdown,
  deriveDeliveryCoachNote,
  segmentFlagColor,
} from "@/lib/deliveryHelpers";

// ── Small helpers ──────────────────────────────────────────────────────────────

function StatPill({
  label,
  value,
  valueClass,
}: {
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <div className="flex flex-col items-center gap-0.5 rounded-xl border border-hairline bg-surface-2 px-3 py-2.5">
      <span className={`text-lg font-bold tabular-nums leading-none ${valueClass ?? "text-ink"}`}>
        {value}
      </span>
      <span className="text-[10px] text-ink-faint">{label}</span>
    </div>
  );
}

function Expandable({
  label,
  children,
  defaultOpen = false,
}: {
  label: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="flex flex-col gap-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 text-left text-xs font-medium text-ink-subtle hover:text-ink transition-colors py-1"
      >
        {open ? <ChevronUp size={11} className="text-ink-faint shrink-0" /> : <ChevronDown size={11} className="text-ink-faint shrink-0" />}
        {label}
      </button>
      {open && <div className="mt-1.5">{children}</div>}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

interface Props {
  metrics: DeliveryMetrics;
}

export default function DeliveryCoachPanel({ metrics }: Props) {
  const pacingDisplay = getPacingBandDisplay(metrics.pacing_band);
  const coachNote = deriveDeliveryCoachNote(metrics);
  const flags = metrics.clarity_flags_json ?? [];
  const fillerBreakdown = formatFillerBreakdown(metrics.filler_words_json);
  const repeatedPhrases = metrics.repeated_phrases_json ?? [];
  const timeline = metrics.timeline_json ?? [];
  const score = metrics.delivery_score;
  const scoreColor = deliveryScoreColor(score);
  const hasDuration = metrics.duration_seconds !== null && metrics.duration_seconds !== undefined;

  return (
    <div className="flex flex-col gap-4">

      {/* ── A. Score row ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
        <StatPill
          label="Delivery"
          value={score !== null && score !== undefined ? `${score}/100` : "—"}
          valueClass={scoreColor}
        />
        <StatPill
          label="Pacing"
          value={pacingDisplay.label}
          valueClass={pacingDisplay.colorClass}
        />
        <StatPill
          label="WPM"
          value={formatWpm(metrics.words_per_minute)}
          valueClass={hasDuration ? "text-ink" : "text-ink-faint"}
        />
        <StatPill
          label="Fillers"
          value={metrics.filler_word_count !== null && metrics.filler_word_count !== undefined
            ? String(metrics.filler_word_count) : "—"}
          valueClass={
            (metrics.filler_word_count ?? 0) > 10 ? "text-danger"
            : (metrics.filler_word_count ?? 0) > 5 ? "text-warn"
            : "text-ok"
          }
        />
        <StatPill
          label="Words"
          value={metrics.word_count !== null && metrics.word_count !== undefined
            ? String(metrics.word_count) : "—"}
        />
      </div>

      {/* ── B. Coach note ─────────────────────────────────────────────────── */}
      {coachNote && (
        <div className="flex items-start gap-2.5 rounded-lg border border-lav/20 bg-lav/5 px-4 py-3">
          <MessageSquare size={13} className="shrink-0 text-lav mt-0.5" />
          <p className="text-xs leading-relaxed text-ink">{coachNote}</p>
        </div>
      )}

      {/* ── C. Clarity diagnostics ────────────────────────────────────────── */}
      {flags.length > 0 ? (
        <div className="flex flex-col gap-2">
          <p className="section-stamp">Delivery issues</p>
          {flags.map((flag) => {
            const fd = getFlagDisplay(flag);
            const Icon = fd.severity === "danger" ? AlertTriangle : fd.severity === "warn" ? AlertTriangle : CheckCircle2;
            const color = fd.severity === "danger" ? "text-danger border-danger/20 bg-danger/5"
              : fd.severity === "warn" ? "text-warn border-warn/20 bg-warn/5"
              : "text-ink-subtle border-hairline bg-surface-2";
            return (
              <div key={flag} className={`flex items-start gap-2 rounded-lg border px-3 py-2.5 ${color}`}>
                <Icon size={12} className="shrink-0 mt-0.5" />
                <div className="flex flex-col gap-0.5">
                  <p className="text-xs font-semibold text-ink">{fd.label}</p>
                  {fd.description && (
                    <p className="text-[11px] text-ink-subtle leading-relaxed">{fd.description}</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : score !== null && score !== undefined && score >= 70 ? (
        <div className="flex items-center gap-2 rounded-lg border border-ok/20 bg-ok/5 px-3 py-2">
          <CheckCircle2 size={12} className="text-ok shrink-0" />
          <p className="text-xs text-ok">No significant delivery issues detected</p>
        </div>
      ) : null}

      {/* ── Filler word breakdown (collapsible) ───────────────────────────── */}
      {fillerBreakdown.length > 0 && (
        <Expandable label={`Filler word breakdown (${fillerBreakdown.length} types)`}>
          <div className="flex flex-wrap gap-2">
            {fillerBreakdown.map(({ word, count }) => (
              <div
                key={word}
                className="flex items-center gap-1.5 rounded-full border border-warn/20 bg-warn/5 px-2.5 py-1"
              >
                <span className="text-xs font-medium text-ink">"{word}"</span>
                <span className="text-[10px] font-semibold text-warn tabular-nums">{count}×</span>
              </div>
            ))}
          </div>
        </Expandable>
      )}

      {/* ── Repeated phrases (collapsible) ────────────────────────────────── */}
      {repeatedPhrases.length > 0 && (
        <Expandable label={`Repeated phrases (${repeatedPhrases.length} found)`}>
          <div className="flex flex-col gap-1.5">
            {repeatedPhrases.slice(0, 6).map(({ phrase, count }) => (
              <div
                key={phrase}
                className="flex items-center justify-between gap-2 rounded-lg border border-lav/15 bg-lav/5 px-3 py-1.5"
              >
                <span className="text-xs text-ink font-mono">"{phrase}"</span>
                <span className="text-[10px] text-lav font-semibold shrink-0">{count}× repeated</span>
              </div>
            ))}
          </div>
        </Expandable>
      )}

      {/* ── D. Speaking timeline ──────────────────────────────────────────── */}
      {timeline.length > 0 && (
        <Expandable label="Speaking timeline (approximate)">
          <div className="flex flex-col gap-1.5">
            <p className="text-[10px] text-ink-faint mb-1">
              Approximate timeline based on transcript position.
              {!hasDuration && " Add speech duration to see real timestamps."}
            </p>
            {timeline.map((seg) => {
              const borderColor = segmentFlagColor(seg.flags);
              const hasIssues = seg.flags.length > 0;
              return (
                <div
                  key={seg.segment_index}
                  className={`flex flex-col gap-1.5 rounded-lg border px-3 py-2.5 ${borderColor}`}
                >
                  {/* Segment header */}
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="flex h-4 w-4 items-center justify-center rounded-full bg-surface-3 text-[9px] font-bold text-ink-faint shrink-0">
                      {seg.segment_index + 1}
                    </span>
                    {hasDuration && seg.approx_start_seconds !== null && seg.approx_end_seconds !== null ? (
                      <span className="text-[10px] text-ink-faint font-mono">
                        {seg.approx_start_seconds.toFixed(0)}s – {seg.approx_end_seconds.toFixed(0)}s
                      </span>
                    ) : (
                      <span className="text-[10px] text-ink-faint">Part {seg.segment_index + 1}</span>
                    )}
                    <span className="text-[10px] text-ink-faint">{seg.word_count} words</span>
                    {seg.filler_count > 0 && (
                      <span className="rounded-full border border-warn/20 bg-warn/5 px-1.5 py-0.5 text-[9px] font-semibold text-warn">
                        {seg.filler_count} fillers
                      </span>
                    )}
                    {seg.repeated_phrase_hits > 0 && (
                      <span className="rounded-full border border-lav/20 bg-lav/5 px-1.5 py-0.5 text-[9px] font-semibold text-lav">
                        {seg.repeated_phrase_hits} repeats
                      </span>
                    )}
                  </div>
                  {/* Excerpt */}
                  <p className="text-[11px] text-ink-subtle leading-relaxed line-clamp-2">{seg.excerpt}</p>
                </div>
              );
            })}
          </div>
        </Expandable>
      )}

      {/* ── Pacing detail ─────────────────────────────────────────────────── */}
      <div className="rounded-lg border border-hairline bg-surface-2 px-3 py-2.5 flex flex-col gap-1.5">
        <div className="flex items-center gap-1.5">
          <BarChart2 size={11} className="text-ink-faint shrink-0" />
          <p className="text-[10px] font-medium uppercase tracking-wide text-ink-faint">Pacing reference</p>
        </div>
        <div className="flex flex-wrap gap-x-4 gap-y-0.5">
          <span className="text-[11px] text-ink-faint"><span className="font-semibold text-ok">110–180 WPM</span> — judge-friendly range</span>
          <span className="text-[11px] text-ink-faint"><span className="font-semibold text-warn">&lt;110</span> — too slow (lose attention)</span>
          <span className="text-[11px] text-ink-faint"><span className="font-semibold text-danger">&gt;180</span> — too fast (warrants blur)</span>
        </div>
        <p className="text-[11px] text-ink-faint mt-0.5">{pacingDisplay.hint}</p>
      </div>

    </div>
  );
}

// ── Empty state ────────────────────────────────────────────────────────────────

export function DeliveryCoachPanelEmpty({ reason }: { reason?: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-hairline bg-surface-2 px-4 py-3">
      <Mic size={13} className="shrink-0 text-ink-faint mt-0.5" />
      <div className="flex flex-col gap-0.5">
        <p className="text-xs font-medium text-ink-subtle">Delivery metrics not yet available</p>
        <p className="text-[11px] text-ink-faint">
          {reason ?? "Delivery analysis runs automatically after transcription. Re-analyze the speech if metrics are missing."}
        </p>
      </div>
    </div>
  );
}
