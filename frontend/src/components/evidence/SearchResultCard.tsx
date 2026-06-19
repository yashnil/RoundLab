"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import type { SearchResultItem } from "@/types";

export function SearchResultCard({ item }: { item: SearchResultItem }) {
  const [open, setOpen] = useState(false);
  const topCard = item.cards[0];
  const displayTitle = (topCard?.tag && !topCard.tag.match(/^CARD\s+\d+$/i))
    ? topCard.tag
    : item.chunk.heading ?? null;

  const sim = item.similarity;
  const simLabel = sim !== null && sim !== undefined
    ? (sim >= 0.70 ? "Strong match" : sim >= 0.45 ? "Possible match" : "Weak match")
    : null;
  const simColor = sim !== null && sim !== undefined
    ? (sim >= 0.70 ? "text-ok" : sim >= 0.45 ? "text-warn" : "text-danger")
    : "";

  return (
    <div className="case-file-card p-3 text-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          {/* Source document + similarity */}
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-[10px] font-medium uppercase tracking-wide text-ink-muted truncate">
              {item.document_filename}
            </p>
            {simLabel && (
              <span className={`text-[10px] font-semibold ${simColor}`}>
                {simLabel} ({Math.round((sim ?? 0) * 100)}%)
              </span>
            )}
          </div>
          {/* Card tag or chunk heading */}
          {displayTitle && (
            <p className="text-xs font-semibold text-ink mt-0.5 leading-snug">{displayTitle}</p>
          )}
          {/* Attribution metadata from matched card */}
          {topCard && (
            <div className="flex flex-wrap gap-1 mt-0.5">
              {topCard.author && <span className="text-xs text-ink-subtle">{topCard.author}</span>}
              {topCard.source && <span className="text-xs text-ink-subtle">· {topCard.source}</span>}
              {topCard.year && <span className="text-xs text-ink-subtle">· {topCard.year}</span>}
            </div>
          )}
        </div>
        <button onClick={() => setOpen((v) => !v)} className="shrink-0 text-ink-muted hover:text-ink mt-0.5">
          {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </button>
      </div>
      {/* Text excerpt */}
      <p className={`mt-2 text-xs leading-relaxed text-ink-muted ${open ? "whitespace-pre-wrap" : "line-clamp-4"}`}>
        {topCard?.card_text ?? item.chunk.chunk_text}
      </p>
      {/* Claim summary when collapsed */}
      {!open && topCard?.claim_summary && (
        <p className="mt-1.5 text-xs text-ink-subtle italic line-clamp-1">
          Supports: {topCard.claim_summary}
        </p>
      )}
    </div>
  );
}
