"use client";

import React, { useState } from "react";
import { SearchTraceResult } from "@/types";

// ── Icon helpers (inline SVG to avoid adding icon deps) ──────────────────────

function IconChevron({ open }: { open: boolean }) {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 14 14"
      fill="none"
      aria-hidden="true"
      style={{ transform: open ? "rotate(180deg)" : undefined, transition: "transform 150ms" }}
    >
      <path
        d="M3 5l4 4 4-4"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// ── Failure reason human labels ───────────────────────────────────────────────

const REASON_LABELS: Record<string, string> = {
  no_search_results: "No search results returned",
  provider_failure: "Search provider error",
  page_fetch_failed: "Pages could not be fetched",
  extraction_failed: "Text extraction failed",
  no_relevant_passages: "No relevant passages found",
  source_quality_too_low: "Sources below quality threshold",
  claim_not_supported: "Claim not supported by sources",
  citation_metadata_incomplete: "Citation metadata incomplete",
  card_validation_failed: "Evidence cut validation failed",
  credible_counterevidence_only: "Only counterevidence found",
  no_credible_support_found: "No credible support found",
};

const REASON_ICONS: Record<string, string> = {
  no_search_results: "🔍",
  provider_failure: "⚠️",
  page_fetch_failed: "📄",
  extraction_failed: "📄",
  no_relevant_passages: "🔎",
  source_quality_too_low: "📊",
  claim_not_supported: "❌",
  citation_metadata_incomplete: "📋",
  card_validation_failed: "✂️",
  credible_counterevidence_only: "↔️",
  no_credible_support_found: "🔎",
};

// ── Component ─────────────────────────────────────────────────────────────────

interface Props {
  trace: SearchTraceResult;
  noCardReason?: string | null;
}

export function SearchFailurePanel({ trace, noCardReason }: Props) {
  const [detailsOpen, setDetailsOpen] = useState(false);

  const reason = trace.failure_reason;
  const reasonLabel = reason ? REASON_LABELS[reason] ?? reason : "No cards produced";
  const reasonIcon = reason ? REASON_ICONS[reason] ?? "🔎" : "🔎";

  const displayDetail = trace.failure_detail || noCardReason || null;
  const recoveryActions = trace.recovery_actions ?? [];
  const attemptsSummary = trace.attempts_summary ?? [];

  const searchStage = trace.stages?.find((s) => s.stage === "search");
  const extractionStage = trace.stages?.find((s) => s.stage === "extraction");

  return (
    <div className="rounded-xl border border-border bg-surface-subtle p-4 space-y-3">
      {/* Header */}
      <div className="flex items-start gap-2">
        <span className="text-lg leading-none mt-0.5" aria-hidden="true">
          {reasonIcon}
        </span>
        <div>
          <p className="text-sm font-semibold text-fg-default">{reasonLabel}</p>
          {displayDetail && (
            <p className="text-xs text-fg-muted mt-0.5">{displayDetail}</p>
          )}
        </div>
      </div>

      {/* What was tried */}
      {attemptsSummary.length > 0 && (
        <div>
          <p className="text-xs font-medium text-fg-subtle uppercase tracking-wide mb-1">
            What was tried
          </p>
          <ul className="space-y-0.5">
            {attemptsSummary.map((step, i) => (
              <li key={i} className="text-xs text-fg-muted flex items-start gap-1.5">
                <span className="text-fg-subtle mt-0.5">–</span>
                <span>{step}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Recovery actions */}
      {recoveryActions.length > 0 && (
        <div>
          <p className="text-xs font-medium text-fg-subtle uppercase tracking-wide mb-1">
            Next steps
          </p>
          <ul className="space-y-1">
            {recoveryActions.map((action, i) => (
              <li
                key={i}
                className="text-xs text-fg-default flex items-start gap-1.5 bg-surface-default rounded-md px-2 py-1"
              >
                <span className="text-accent-default font-bold mt-0.5">→</span>
                <span>{action}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Developer details (collapsed by default) */}
      {(searchStage || extractionStage || trace.total_queries > 0) && (
        <div className="border-t border-border pt-2">
          <button
            type="button"
            onClick={() => setDetailsOpen((o) => !o)}
            className="flex items-center gap-1 text-xs text-fg-subtle hover:text-fg-muted transition-colors"
            aria-expanded={detailsOpen}
          >
            <IconChevron open={detailsOpen} />
            Developer details
          </button>

          {detailsOpen && (
            <div className="mt-2 space-y-2 text-xs text-fg-muted font-mono">
              {/* Queries + roles */}
              {searchStage && (
                <div>
                  <span className="text-fg-subtle">Queries run: </span>
                  {searchStage.queries_run.length}
                  {searchStage.roles_attempted.length > 0 && (
                    <span className="ml-2 text-fg-subtle">
                      Roles: {searchStage.roles_attempted.join(", ")}
                    </span>
                  )}
                </div>
              )}

              {/* URL counts */}
              {searchStage && (
                <div>
                  <span className="text-fg-subtle">URLs found: </span>
                  {searchStage.urls_found}
                  {searchStage.urls_deduplicated > 0 && (
                    <span className="ml-2 text-fg-subtle">
                      ({searchStage.urls_deduplicated} deduped)
                    </span>
                  )}
                </div>
              )}

              {/* Provider errors (already sanitized — no secrets) */}
              {searchStage && searchStage.provider_errors.length > 0 && (
                <div>
                  <span className="text-fg-subtle">Provider errors: </span>
                  {searchStage.provider_errors.slice(0, 2).join(" | ")}
                </div>
              )}

              {/* Extraction */}
              {extractionStage && (
                <div>
                  <span className="text-fg-subtle">Extracted: </span>
                  {extractionStage.extraction_successes} ok
                  {extractionStage.extraction_failures > 0 && (
                    <span className="ml-2 text-fg-subtle">
                      {extractionStage.extraction_failures} failed
                    </span>
                  )}
                  {extractionStage.passages_considered > 0 && (
                    <span className="ml-2">
                      <span className="text-fg-subtle">Passages: </span>
                      {extractionStage.passages_considered}
                      {extractionStage.passages_rejected_relevance > 0 && (
                        <span className="text-fg-subtle">
                          {" "}({extractionStage.passages_rejected_relevance} rejected)
                        </span>
                      )}
                    </span>
                  )}
                </div>
              )}

              {/* Escalation stopped early */}
              {trace.stopped_early && (
                <div className="text-fg-subtle">
                  Escalation stopped early (enough high-priority candidates found)
                </div>
              )}

              {/* Stage notes */}
              {searchStage?.notes && searchStage.notes.length > 0 && (
                <div className="text-fg-subtle">{searchStage.notes.join(" | ")}</div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
