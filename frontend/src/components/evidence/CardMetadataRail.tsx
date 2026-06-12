"use client";

import { useState } from "react";
import type { CardDraft } from "@/types";
import { sourceQualityBadgeStyle, sourceQualityLabel } from "@/lib/researchHelpers";
import { EvidenceSlotBadge } from "./EvidenceSlotBadge";

const PROVENANCE_ICON: Record<string, string> = {
  meta_tags: "🏷",
  schema_org: "🧩",
  search_provider: "🔎",
  organization_heuristic: "🏛",
  grobid: "📄",
  zotero: "📚",
  crossref: "🔗",
  missing: "∅",
};

function CitationQualityRow({ card }: { card: CardDraft }) {
  const [open, setOpen] = useState(false);
  const c = card.citation;

  const fields = [
    { label: "Author", value: c?.author_display || card.author, prov: c?.author_source },
    { label: "Year", value: c?.year, prov: c?.date_source },
    { label: "Title", value: c?.title, prov: c?.title_source },
    { label: "Publication", value: c?.publication_name || c?.container_title || card.publication, prov: c?.publication_source },
    { label: "URL", value: card.url ? "✓" : null },
  ];
  const filled = fields.filter((f) => f.value).length;
  const total = fields.length;
  const pct = Math.round((filled / total) * 100);

  const qualityColor =
    card.citation_quality === "complete"
      ? "text-green-600"
      : card.citation_quality === "partial"
        ? "text-amber-600"
        : "text-red-500";

  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-[10px] hover:underline"
      >
        <span className={`font-semibold ${qualityColor}`}>
          Citation {card.citation_quality ?? "unknown"}
        </span>
        <div className="w-14 h-1 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${
              pct >= 80 ? "bg-green-500" : pct >= 50 ? "bg-amber-500" : "bg-red-400"
            }`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="text-ink-muted">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="mt-1.5 grid grid-cols-1 gap-y-1 text-[10px]">
          {fields.map((f) => (
            <div key={f.label} className="flex items-center gap-1.5">
              <span className={f.value ? "text-green-600" : "text-red-400"}>
                {f.value ? "✓" : "✗"}
              </span>
              <span className="text-ink-muted">{f.label}:</span>
              <span className={f.value ? "text-ink truncate max-w-[120px]" : "text-red-500"}>
                {f.value ? String(f.value).slice(0, 30) : "missing"}
              </span>
              {f.prov && f.prov !== "missing" && (
                <span className="text-[8px] text-ink-muted/60" title={`Source: ${f.prov}`}>
                  {PROVENANCE_ICON[f.prov] ?? "•"}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/** Right-side rail: citation panel + MLA. */
export function CardMetadataRail({ card }: { card: CardDraft }) {
  const [mlaCopied, setMlaCopied] = useState(false);
  const publication =
    card.citation?.publication_name ||
    card.citation?.container_title ||
    card.publication ||
    null;

  const mla = card.mla_citation || card.citation?.mla_citation || "";
  const hasMla = !!mla.trim();

  function handleCopyMla() {
    navigator.clipboard?.writeText(mla);
    setMlaCopied(true);
    setTimeout(() => setMlaCopied(false), 1500);
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Slot + quality badges */}
      <div className="flex flex-wrap items-center gap-1.5">
        <EvidenceSlotBadge slotLabel={card.slot_label} />
        <span
          className={`text-[10px] px-2 py-0.5 rounded-full border ${sourceQualityBadgeStyle(card.source_quality)}`}
        >
          {sourceQualityLabel(card.source_quality)}
        </span>
      </div>

      {/* Cite line */}
      <div className="flex flex-col gap-0.5">
        <p className="text-[13px] font-semibold text-ink leading-tight">
          {card.short_cite || card.citation?.short_cite || "Unknown"}
        </p>
        {publication && (
          <p className="text-[11px] text-ink-muted leading-tight">{publication}</p>
        )}
        {card.citation?.year && (
          <p className="text-[11px] text-ink-muted">{card.citation.year}</p>
        )}
      </div>

      {/* Citation quality meter */}
      <CitationQualityRow card={card} />

      {/* MLA citation */}
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-muted">
            MLA Citation
          </span>
          {hasMla && (
            <button
              onClick={handleCopyMla}
              className="text-[9px] px-2 py-0.5 rounded border border-border text-ink-muted hover:bg-surface-1 transition-colors"
            >
              {mlaCopied ? "Copied!" : "Copy"}
            </button>
          )}
        </div>
        {hasMla ? (
          <p className="text-[10px] text-ink leading-relaxed break-words bg-surface-faint rounded-lg border border-border/40 px-2.5 py-2">
            {mla}
          </p>
        ) : (
          <p className="text-[10px] text-ink-muted italic">
            {card.url ? "Citation incomplete — open source to verify" : "No source URL"}
          </p>
        )}
        {card.url && (
          <a
            href={card.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[10px] text-blue-600 hover:underline truncate"
          >
            Open source ↗
          </a>
        )}
      </div>
    </div>
  );
}

export default CardMetadataRail;
