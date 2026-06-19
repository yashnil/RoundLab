"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, AlertCircle, CheckCircle2 } from "lucide-react";
import { SavedCardBody } from "@/components/evidence/SavedCardBody";
import type { EvidenceCard } from "@/types";

function AttributionRow({ card }: { card: EvidenceCard }) {
  const parts: string[] = [];
  if (card.author) parts.push(card.author);
  if (card.source) parts.push(card.source);
  if (card.year) parts.push(String(card.year));

  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      {parts.length > 0 ? (
        <span className="text-xs text-ink-subtle">{parts.join(" · ")}</span>
      ) : null}
      {card.attribution_complete ? (
        <span className="inline-flex items-center gap-0.5 rounded-full bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-medium text-emerald-600">
          <CheckCircle2 size={9} /> Attribution complete
        </span>
      ) : (
        <span className="inline-flex items-center gap-0.5 rounded-full bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-medium text-amber-600">
          <AlertCircle size={9} />
          {!card.author && !card.year ? "Missing author & date" :
           !card.author ? "Missing author" :
           !card.year ? "Missing date" : "Incomplete"}
        </span>
      )}
    </div>
  );
}

export function CardItem({ card }: { card: EvidenceCard }) {
  const [open, setOpen] = useState(false);

  // Use tag as title; fall back to claim_summary truncated, then generic label
  const title = card.tag && !card.tag.match(/^CARD\s+\d+$/i)
    ? card.tag
    : card.claim_summary
      ? card.claim_summary.slice(0, 80) + (card.claim_summary.length > 80 ? "…" : "")
      : "Evidence card";

  return (
    <div className="case-file-card text-sm">
      {/* Compact header — always visible */}
      <div className="flex items-start justify-between gap-3 px-3 py-2.5">
        <div className="flex flex-col gap-1 min-w-0 flex-1">
          <p className="text-xs font-semibold text-ink leading-snug">{title}</p>
          <AttributionRow card={card} />
          {card.claim_summary && (
            <p className="text-xs text-ink-subtle leading-relaxed line-clamp-2">
              {card.claim_summary}
            </p>
          )}
          {/* Card body excerpt — re-renders saved user markup when expanded */}
          {card.card_text && (
            open ? (
              <div className="mt-1">
                <SavedCardBody card={card} />
              </div>
            ) : (
              <p className="mt-1 text-xs leading-relaxed text-ink-muted line-clamp-4">
                {card.card_text}
              </p>
            )
          )}
        </div>
        <button
          onClick={() => setOpen((v) => !v)}
          className="shrink-0 mt-0.5 text-ink-muted hover:text-ink"
          aria-label={open ? "Collapse" : "Expand"}
        >
          {open
            ? <ChevronUp size={13} />
            : <ChevronDown size={13} />}
        </button>
      </div>

      {/* Expanded: source note */}
      {open && card.source && (
        <div className="border-t border-hairline px-3 py-1.5">
          <p className="text-xs text-ink-subtle">Source: {card.source}</p>
        </div>
      )}
    </div>
  );
}
