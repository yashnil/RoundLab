"use client";

/**
 * SourceProvenancePanel — collapsible source detail disclosure.
 *
 * Shows concise provenance: source type, full-text vs abstract-only,
 * page number (PDF), section heading, retrieval date, and extraction
 * warnings when relevant.
 *
 * Developer details (parser, offsets, content hash) are hidden inside
 * a nested "Technical details" toggle — never shown in primary card UI.
 */

import React, { useState } from "react";

// ── Props ─────────────────────────────────────────────────────────────────────

export interface CardProvenance {
  source_text_type?: string;   // "full_text" | "abstract_only" | "partial_extraction" | …
  document_type?: string;      // "html" | "pdf" | "docx" | "text"
  page_number?: number | null; // PDF only (1-based)
  section_heading?: string;
  retrieval_timestamp?: string;
  extraction_method?: string;
  extraction_warnings?: string[];
  content_hash?: string;
  start_char?: number;
  end_char?: number;
}

interface SourceProvenancePanelProps {
  provenance: CardProvenance;
  showDeveloperDetails?: boolean;
  className?: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function sourceTypeLabel(type: string | undefined): {
  label: string;
  color: string;
} {
  switch (type) {
    case "full_text":
      return { label: "Full text", color: "text-green-700 bg-green-50" };
    case "abstract_only":
      return { label: "Abstract only", color: "text-amber-700 bg-amber-50" };
    case "partial_extraction":
      return { label: "Partial extraction", color: "text-amber-700 bg-amber-50" };
    case "snippet_only":
      return { label: "Snippet", color: "text-orange-700 bg-orange-50" };
    case "metadata_only":
      return { label: "Metadata only", color: "text-red-700 bg-red-50" };
    default:
      return { label: "Unknown", color: "text-gray-600 bg-gray-100" };
  }
}

function docTypeLabel(type: string | undefined): string {
  switch (type) {
    case "pdf":  return "PDF";
    case "docx": return "Word document";
    case "html": return "Web page";
    case "text": return "Plain text";
    default:     return "";
  }
}

function formatTimestamp(ts: string | undefined): string {
  if (!ts) return "";
  try {
    return new Date(ts).toLocaleDateString("en-US", {
      year: "numeric", month: "short", day: "numeric",
    });
  } catch {
    return ts.slice(0, 10);
  }
}

// ── Component ─────────────────────────────────────────────────────────────────

export function SourceProvenancePanel({
  provenance,
  showDeveloperDetails = false,
  className = "",
}: SourceProvenancePanelProps) {
  const [open, setOpen] = useState(false);
  const [devOpen, setDevOpen] = useState(false);

  const { label: stLabel, color: stColor } = sourceTypeLabel(provenance.source_text_type);
  const docLabel = docTypeLabel(provenance.document_type);
  const dateLabel = formatTimestamp(provenance.retrieval_timestamp);

  const hasWarnings =
    provenance.extraction_warnings && provenance.extraction_warnings.length > 0;

  const hasMeaningfulInfo =
    provenance.source_text_type ||
    provenance.page_number ||
    provenance.section_heading ||
    provenance.retrieval_timestamp ||
    hasWarnings;

  if (!hasMeaningfulInfo) return null;

  return (
    <div className={`text-xs ${className}`}>
      {/* Toggle trigger */}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-[11px] text-[var(--color-ink-subtle)] hover:text-[var(--color-ink-base)] transition-colors"
        aria-expanded={open}
        aria-controls="source-provenance-body"
      >
        <svg
          className={`w-3 h-3 transition-transform ${open ? "rotate-90" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        <span>Source details</span>
      </button>

      {/* Body */}
      {open && (
        <div
          id="source-provenance-body"
          className="mt-2 space-y-1.5 pl-4 border-l border-[var(--color-border-subtle)]"
        >
          {/* Source-text type badge */}
          {provenance.source_text_type && (
            <div className="flex items-center gap-1.5">
              <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${stColor}`}>
                {stLabel}
              </span>
              {docLabel && (
                <span className="text-[var(--color-ink-subtle)]">· {docLabel}</span>
              )}
            </div>
          )}

          {/* Page number (PDF) */}
          {provenance.page_number != null && (
            <p className="text-[var(--color-ink-subtle)]">
              Page {provenance.page_number}
            </p>
          )}

          {/* Section heading */}
          {provenance.section_heading && (
            <p className="text-[var(--color-ink-subtle)] italic truncate max-w-[260px]" title={provenance.section_heading}>
              Section: {provenance.section_heading}
            </p>
          )}

          {/* Retrieval date */}
          {dateLabel && (
            <p className="text-[var(--color-ink-subtle)]">
              Retrieved {dateLabel}
            </p>
          )}

          {/* Extraction warnings */}
          {hasWarnings && (
            <div className="space-y-0.5">
              {(provenance.extraction_warnings ?? []).map((w, i) => (
                <p key={i} className="text-amber-700">⚠ {w}</p>
              ))}
            </div>
          )}

          {/* Developer details (collapsed by default, shown only when flag set) */}
          {showDeveloperDetails && (
            <div className="mt-1">
              <button
                type="button"
                onClick={() => setDevOpen((o) => !o)}
                className="text-[10px] text-[var(--color-ink-subtle)] underline underline-offset-2"
                aria-expanded={devOpen}
              >
                {devOpen ? "Hide" : "Show"} technical details
              </button>
              {devOpen && (
                <dl className="mt-1 space-y-0.5 font-mono text-[10px] text-[var(--color-ink-subtle)]">
                  {provenance.extraction_method && (
                    <div><dt className="inline">Parser:</dt>{" "}<dd className="inline">{provenance.extraction_method}</dd></div>
                  )}
                  {provenance.start_char != null && provenance.end_char != null && (
                    <div><dt className="inline">Offsets:</dt>{" "}<dd className="inline">{provenance.start_char}–{provenance.end_char}</dd></div>
                  )}
                  {provenance.content_hash && (
                    <div className="truncate max-w-[260px]">
                      <dt className="inline">Hash:</dt>{" "}
                      <dd className="inline" title={provenance.content_hash}>{provenance.content_hash.slice(0, 16)}…</dd>
                    </div>
                  )}
                </dl>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
