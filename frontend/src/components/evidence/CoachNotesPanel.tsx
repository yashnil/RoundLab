"use client";

import { useState } from "react";
import type { CardIntelligence } from "@/types";

const bestUseColors: Record<string, string> = {
  contention: "bg-blue-50 border-blue-200 text-blue-700",
  rebuttal: "bg-purple-50 border-purple-200 text-purple-700",
  weighing: "bg-green-50 border-green-200 text-green-700",
  definition: "bg-slate-50 border-slate-200 text-slate-700",
  frontline: "bg-orange-50 border-orange-200 text-orange-700",
  crossfire: "bg-amber-50 border-amber-200 text-amber-700",
  impact: "bg-red-50 border-red-200 text-red-700",
  default: "bg-surface-faint border-border text-ink-muted",
};

export function CoachNotesPanel({
  intelligence,
  slotLabel,
  slotTargetClaim,
}: {
  intelligence?: CardIntelligence | null;
  slotLabel?: string | null;
  slotTargetClaim?: string | null;
}) {
  const [expanded, setExpanded] = useState(false);
  if (!intelligence || !intelligence.why_this_card) return null;

  const colorClass = bestUseColors[intelligence.best_use] ?? bestUseColors.default;

  return (
    <div className="border border-border/40 rounded-lg overflow-hidden">
      {/* Always-visible top: why + best use */}
      <div className="px-3 py-2.5 flex flex-col gap-1.5">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[10px] font-semibold text-ink uppercase tracking-wide">
            Coach
          </span>
          <span className={`text-[9px] px-2 py-0.5 rounded border font-medium ${colorClass}`}>
            {intelligence.best_use}
          </span>
          {slotLabel && (
            <span className="text-[9px] px-1.5 py-0.5 rounded border border-border text-ink-muted">
              {slotLabel}
            </span>
          )}
        </div>
        <p className="text-[11px] text-ink leading-relaxed">{intelligence.why_this_card}</p>

        {/* This proves — always shown if present */}
        {intelligence.supports_claim_because.length > 0 && (
          <div className="flex flex-col gap-0.5">
            {intelligence.supports_claim_because.slice(0, 2).map((r, i) => (
              <div key={i} className="flex items-start gap-1">
                <span className="text-green-600 text-[9px] mt-0.5 shrink-0">✓</span>
                <span className="text-[10px] text-ink leading-snug">{r}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Expandable section */}
      {(intelligence.debate_use_notes.length > 0 ||
        intelligence.limitations.length > 0 ||
        intelligence.opponent_response ||
        intelligence.crossfire_question) && (
        <>
          <button
            onClick={() => setExpanded((v) => !v)}
            className="w-full flex items-center justify-between px-3 py-1.5 text-[10px] text-ink-muted bg-surface-faint/40 hover:bg-surface-faint/60 border-t border-border/30 transition-colors"
          >
            <span>{expanded ? "Show less" : "Pair with / Limitations / Crossfire"}</span>
            <span>{expanded ? "▲" : "▼"}</span>
          </button>
          {expanded && (
            <div className="px-3 pb-3 flex flex-col gap-2.5 border-t border-border/20">
              {slotTargetClaim && (
                <p className="text-[10px] text-ink-muted italic pt-2">
                  Slot goal: {slotTargetClaim}
                </p>
              )}
              {intelligence.debate_use_notes.length > 0 && (
                <div>
                  <p className="text-[9px] font-semibold text-blue-700 uppercase tracking-wide mb-1 mt-2">
                    Pair with
                  </p>
                  <ul className="text-[10px] text-ink-muted list-none space-y-0.5">
                    {intelligence.debate_use_notes.map((n, i) => (
                      <li key={i} className="flex items-start gap-1">
                        <span className="text-blue-500 mt-0.5">→</span>
                        <span>{n}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {intelligence.limitations.length > 0 && (
                <div>
                  <p className="text-[9px] font-semibold text-amber-700 uppercase tracking-wide mb-1">
                    Does not prove
                  </p>
                  <ul className="text-[10px] text-amber-800 list-none space-y-0.5">
                    {intelligence.limitations.map((l, i) => (
                      <li key={i} className="flex items-start gap-1">
                        <span className="text-amber-600 mt-0.5">⚠</span>
                        <span>{l}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {intelligence.opponent_response && (
                <div>
                  <p className="text-[9px] font-semibold text-rose-700 uppercase tracking-wide mb-1">
                    Opponent response
                  </p>
                  <p className="text-[10px] text-rose-800 leading-relaxed">
                    {intelligence.opponent_response}
                  </p>
                </div>
              )}
              {intelligence.crossfire_question && (
                <div>
                  <p className="text-[9px] font-semibold text-indigo-700 uppercase tracking-wide mb-1">
                    Crossfire question
                  </p>
                  <p className="text-[10px] text-indigo-800 leading-relaxed">
                    {intelligence.crossfire_question}
                  </p>
                </div>
              )}
              {intelligence.suggested_block_label && (
                <p className="text-[9px] font-mono text-ink-muted border-t border-border/40 pt-1.5">
                  Block label:{" "}
                  <span className="text-ink font-medium">{intelligence.suggested_block_label}</span>
                </p>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default CoachNotesPanel;
