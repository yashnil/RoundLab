"use client";

import type { CardIntelligence } from "@/types";

/**
 * Dissio's own short analysis of a card, shown directly under the evidence:
 *   - Warrant: why this evidence logically supports the claim
 *   - Impact:  why it matters / how it helps win the round
 *
 * This is coaching, not evidence — it never replaces the source text.
 */
export function CardAnalysis({
  intelligence,
  className = "",
}: {
  intelligence?: CardIntelligence | null;
  className?: string;
}) {
  const warrant = intelligence?.warrant_analysis?.trim();
  const impact = intelligence?.impact_analysis?.trim();
  if (!warrant && !impact) return null;

  return (
    <div
      className={`rounded-xl border border-hairline bg-surface-2 px-4 py-3.5 flex flex-col gap-3 ${className}`}
    >
      <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-faint">
        Dissio analysis
      </p>
      {warrant && (
        <div className="flex gap-2.5">
          <span className="shrink-0 text-[10px] font-bold uppercase tracking-wide text-ok w-14 pt-0.5">
            Warrant
          </span>
          <p className="text-[12.5px] leading-relaxed text-ink-subtle">{warrant}</p>
        </div>
      )}
      {impact && (
        <div className="flex gap-2.5">
          <span className="shrink-0 text-[10px] font-bold uppercase tracking-wide text-danger w-14 pt-0.5">
            Impact
          </span>
          <p className="text-[12.5px] leading-relaxed text-ink-subtle">{impact}</p>
        </div>
      )}
    </div>
  );
}

export default CardAnalysis;
