"use client";

import { useState } from "react";
import { Check, ChevronDown, Copy } from "lucide-react";
import { cn } from "@/lib/utils";
import type { CardIntelligence } from "@/types";

// ── Speech-use labels ──────────────────────────────────────────────────────────

const SPEECH_USE_LABEL: Record<string, string> = {
  contention: "Constructive",
  rebuttal: "Rebuttal",
  summary: "Summary",
  final_focus: "Final Focus",
  frontline: "Frontline",
  weighing: "Weighing",
  impact: "Impact / Weighing",
  definition: "Framework",
  crossfire: "Crossfire",
};

// ── Clipboard copy hook ────────────────────────────────────────────────────────

function useCopy(resetMs = 1800): [string | null, (text: string, key: string) => void] {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  function copy(text: string, key: string) {
    navigator.clipboard.writeText(text).catch(() => {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    });
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), resetMs);
  }

  return [copiedKey, copy];
}

// ── Primitive components ──────────────────────────────────────────────────────

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[9.5px] font-semibold uppercase tracking-[0.07em] text-ink-faint mb-1.5">
      {children}
    </p>
  );
}

function FieldRow({
  label,
  value,
  labelClass = "text-ink-faint",
  copyKey,
  copiedKey,
  onCopy,
}: {
  label: string;
  value?: string | null;
  labelClass?: string;
  copyKey?: string;
  copiedKey?: string | null;
  onCopy?: (text: string, key: string) => void;
}) {
  if (!value?.trim()) return null;
  const isCopied = copyKey !== undefined && copiedKey === copyKey;
  return (
    <div className="group flex gap-2">
      <div className="flex-1 min-w-0">
        <span className={cn("text-[9.5px] font-semibold uppercase tracking-[0.06em]", labelClass)}>
          {label}
        </span>
        <p className="mt-0.5 text-[12.5px] leading-relaxed text-ink-subtle">{value}</p>
      </div>
      {copyKey && onCopy && (
        <button
          type="button"
          aria-label={`Copy ${label}`}
          onClick={() => onCopy(value, copyKey)}
          className={cn(
            "mt-0.5 self-start shrink-0 rounded p-0.5",
            "opacity-0 group-hover:opacity-100 focus-visible:opacity-100",
            "text-ink-faint hover:text-ink",
            "transition-opacity focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-lav/40",
          )}
        >
          {isCopied ? <Check size={11} className="text-ok" /> : <Copy size={11} />}
        </button>
      )}
    </div>
  );
}

/**
 * Debate-prep coaching panel with four sections:
 *  1. Lead — what this card proves + best-use badge
 *  2. Strategic use — warrant, impact, weighing (copyable)
 *  3. Answer opposition — weakness → pushback → answer (sequential, numbered)
 *  4. Crossfire — Q + A (copyable)
 *  5. Best pairing — footer
 */
export function DebatePrepPanel({
  intelligence,
  className = "",
}: {
  intelligence?: CardIntelligence | null;
  className?: string;
}) {
  const [copiedKey, onCopy] = useCopy();

  if (!intelligence) return null;

  const speechUse = SPEECH_USE_LABEL[intelligence.best_use] ?? "Constructive";

  const hasStrategic =
    intelligence.warrant_analysis ||
    intelligence.impact_analysis ||
    intelligence.weighing_angle;

  const hasOpposition =
    intelligence.potential_weakness ||
    intelligence.opponent_response ||
    intelligence.how_to_answer_weakness;

  const hasCrossfire =
    intelligence.crossfire_question || intelligence.crossfire_answer;

  const hasContent =
    intelligence.why_this_card || hasStrategic || hasOpposition || hasCrossfire || intelligence.best_pairing;

  if (!hasContent) return null;

  return (
    <div className={cn("flex flex-col divide-y divide-hairline rounded-xl border border-hairline overflow-hidden", className)}>

      {/* ── 1. Lead: what this proves ───────────────────────────────────────── */}
      {intelligence.why_this_card?.trim() && (
        <div className="px-3.5 py-3 bg-surface-1">
          <div className="flex items-start justify-between gap-2 mb-1.5">
            <p className="text-[9.5px] font-semibold uppercase tracking-[0.07em] text-ink-faint">
              What this card proves
            </p>
            <span className="shrink-0 text-[10px] font-medium text-ink-subtle border border-hairline rounded-full px-2 py-0.5 whitespace-nowrap">
              Best in {speechUse}
            </span>
          </div>
          <p className="text-[13px] font-medium leading-snug text-ink">
            {intelligence.why_this_card}
          </p>
        </div>
      )}

      {/* ── 2. Strategic use ────────────────────────────────────────────────── */}
      {hasStrategic && (
        <div className="px-3.5 py-3 bg-surface-1 flex flex-col gap-2.5">
          <SectionLabel>Strategic use</SectionLabel>
          <FieldRow
            label="Warrant / link"
            value={intelligence.warrant_analysis}
            labelClass="text-lav"
          />
          <FieldRow
            label="Impact significance"
            value={intelligence.impact_analysis}
            labelClass="text-ink-faint"
          />
          <FieldRow
            label="Weighing angle"
            value={intelligence.weighing_angle}
            labelClass="text-lav"
            copyKey="weighing"
            copiedKey={copiedKey}
            onCopy={onCopy}
          />
        </div>
      )}

      {/* ── 3. Answer opposition ────────────────────────────────────────────── */}
      {hasOpposition && (
        <div className="px-3.5 py-3 bg-surface-1">
          <SectionLabel>Answer opposition</SectionLabel>
          <ol className="flex flex-col gap-0" role="list">
            {intelligence.potential_weakness?.trim() && (
              <li className="flex flex-col gap-0">
                <div className="flex gap-2 items-start">
                  <span className="mt-0.5 shrink-0 text-[9px] font-bold text-warn/70 w-3.5 text-right">1</span>
                  <div className="flex-1 min-w-0">
                    <span className="text-[9.5px] font-semibold uppercase tracking-[0.06em] text-warn">
                      Potential weakness
                    </span>
                    <p className="mt-0.5 text-[12.5px] leading-relaxed text-ink-subtle">
                      {intelligence.potential_weakness}
                    </p>
                  </div>
                </div>
                {(intelligence.opponent_response || intelligence.how_to_answer_weakness) && (
                  <div className="ml-3.5 mt-1 flex items-center gap-1.5">
                    <ChevronDown size={11} className="text-ink-faint shrink-0" aria-hidden />
                  </div>
                )}
              </li>
            )}

            {intelligence.opponent_response?.trim() && (
              <li className="flex flex-col gap-0">
                <div className="flex gap-2 items-start">
                  <span className="mt-0.5 shrink-0 text-[9px] font-bold text-danger/60 w-3.5 text-right">2</span>
                  <div className="flex-1 min-w-0">
                    <span className="text-[9.5px] font-semibold uppercase tracking-[0.06em] text-danger">
                      Likely pushback
                    </span>
                    <p className="mt-0.5 text-[12.5px] leading-relaxed text-ink-subtle">
                      {intelligence.opponent_response}
                    </p>
                  </div>
                </div>
                {intelligence.how_to_answer_weakness && (
                  <div className="ml-3.5 mt-1 flex items-center gap-1.5">
                    <ChevronDown size={11} className="text-ink-faint shrink-0" aria-hidden />
                  </div>
                )}
              </li>
            )}

            {intelligence.how_to_answer_weakness?.trim() && (
              <li>
                <div className="flex gap-2 items-start">
                  <span className="mt-0.5 shrink-0 text-[9px] font-bold text-ok/70 w-3.5 text-right">3</span>
                  <div className="flex-1 min-w-0">
                    <span className="text-[9.5px] font-semibold uppercase tracking-[0.06em] text-ok">
                      How to answer
                    </span>
                    <p className="mt-0.5 text-[12.5px] leading-relaxed text-ink-subtle">
                      {intelligence.how_to_answer_weakness}
                    </p>
                  </div>
                </div>
              </li>
            )}
          </ol>
        </div>
      )}

      {/* ── 4. Crossfire ────────────────────────────────────────────────────── */}
      {hasCrossfire && (
        <div className="px-3.5 py-3 bg-surface-1 flex flex-col gap-2.5">
          <SectionLabel>Crossfire</SectionLabel>
          <FieldRow
            label="Question to ask"
            value={intelligence.crossfire_question}
            labelClass="text-ink-faint"
            copyKey="cf_q"
            copiedKey={copiedKey}
            onCopy={onCopy}
          />
          <FieldRow
            label="Answer to give"
            value={intelligence.crossfire_answer}
            labelClass="text-ink-faint"
            copyKey="cf_a"
            copiedKey={copiedKey}
            onCopy={onCopy}
          />
        </div>
      )}

      {/* ── 5. Best pairing footer ──────────────────────────────────────────── */}
      {intelligence.best_pairing?.trim() && (
        <div className="px-3.5 py-2.5 bg-surface-1">
          <p className="text-[9.5px] font-semibold uppercase tracking-[0.07em] text-ink-faint mb-0.5">
            Best pairing
          </p>
          <p className="text-[12px] leading-relaxed text-ink-subtle">
            {intelligence.best_pairing}
          </p>
        </div>
      )}

    </div>
  );
}

export default DebatePrepPanel;
