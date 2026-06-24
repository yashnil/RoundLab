"use client";

import React, { useState } from "react";
import type {
  EvidenceVerificationResult,
  SupportDimensionResult,
  SupportVerdict,
} from "@/types";

// ── Verdict display helpers ───────────────────────────────────────────────────

const VERDICT_LABELS: Record<SupportVerdict, string> = {
  supported: "Claim Supported",
  partially_supported: "Partially Supported",
  unsupported: "Not Supported",
  contradicted: "Contradicts Claim",
  insufficient_context: "Insufficient Context",
  verification_unavailable: "Not Verified",
};

const VERDICT_COLORS: Record<SupportVerdict, string> = {
  supported: "text-emerald-700 bg-emerald-50 border-emerald-200",
  partially_supported: "text-amber-700 bg-amber-50 border-amber-200",
  unsupported: "text-red-700 bg-red-50 border-red-200",
  contradicted: "text-red-800 bg-red-100 border-red-300",
  insufficient_context: "text-zinc-600 bg-zinc-50 border-zinc-200",
  verification_unavailable: "text-zinc-400 bg-zinc-50 border-zinc-100",
};

const VERDICT_DOT: Record<SupportVerdict, string> = {
  supported: "bg-emerald-500",
  partially_supported: "bg-amber-400",
  unsupported: "bg-red-500",
  contradicted: "bg-red-700",
  insufficient_context: "bg-zinc-400",
  verification_unavailable: "bg-zinc-300",
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: "text-red-700 bg-red-50",
  major: "text-amber-700 bg-amber-50",
  minor: "text-zinc-500 bg-zinc-50",
  none: "text-emerald-700 bg-emerald-50",
};

const DIM_LABELS: Record<string, string> = {
  core_claim: "Core Claim",
  causal_strength: "Causal Strength",
  certainty: "Certainty Level",
  magnitude: "Magnitude / Numbers",
  timeframe: "Timeframe",
  population_scope: "Population Scope",
  geographic_scope: "Geographic Scope",
  policy_or_intervention_match: "Policy Match",
  source_attribution: "Source Attribution",
  caveat_completeness: "Caveat Completeness",
};

const CONTEXT_LIMIT_LABELS: Record<string, string> = {
  abstract_only:
    "Abstract only — full methods and limitations not available.",
  snippet_only: "Short snippet — source conclusion cannot be fully verified.",
  metadata_only: "No body text available.",
  partial_extraction: "Partial extraction — some sections may be missing.",
};

// ── Sub-components ────────────────────────────────────────────────────────────

function VerdictBadge({ verdict }: { verdict: SupportVerdict }) {
  const colorClass = VERDICT_COLORS[verdict] ?? VERDICT_COLORS.verification_unavailable;
  const dot = VERDICT_DOT[verdict] ?? VERDICT_DOT.verification_unavailable;
  const label = VERDICT_LABELS[verdict] ?? verdict;
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium ${colorClass}`}
      aria-label={`Support verdict: ${label}`}
    >
      <span className={`w-2 h-2 rounded-full flex-shrink-0 ${dot}`} aria-hidden />
      {label}
    </span>
  );
}

function DimensionRow({ dim }: { dim: SupportDimensionResult }) {
  const [open, setOpen] = useState(false);
  const labelCls = SEVERITY_COLORS[dim.severity] ?? SEVERITY_COLORS.none;
  const dimLabel = DIM_LABELS[dim.dimension] ?? dim.dimension;
  const isIssue = dim.severity !== "none" && dim.verdict !== "not_applicable";

  if (!isIssue) return null;

  return (
    <div className="border-b border-zinc-100 last:border-0">
      <button
        className="w-full flex items-center justify-between gap-2 px-3 py-2 text-left hover:bg-zinc-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--ring)]"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="flex items-center gap-2 text-xs text-zinc-700">
          <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium uppercase tracking-wide ${labelCls}`}>
            {dim.severity}
          </span>
          {dimLabel}
        </span>
        <svg
          className={`w-4 h-4 text-zinc-400 flex-shrink-0 transition-transform ${open ? "rotate-180" : ""}`}
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden
        >
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {open && (
        <div className="px-3 pb-3 space-y-2">
          <p className="text-xs text-zinc-600 leading-relaxed">{dim.explanation}</p>
          {dim.suggested_correction && (
            <p className="text-xs text-zinc-500 italic">
              <span className="font-medium not-italic text-zinc-600">Suggestion: </span>
              {dim.suggested_correction}
            </p>
          )}
          {dim.spans && dim.spans.length > 0 && (
            <div className="mt-1 space-y-1">
              {dim.spans.slice(0, 2).map((span, i) => (
                <blockquote
                  key={i}
                  className={`text-[11px] px-2 py-1 rounded border-l-2 ${
                    span.span_type === "conflicting"
                      ? "border-red-400 bg-red-50 text-red-700"
                      : "border-emerald-400 bg-emerald-50 text-emerald-700"
                  }`}
                >
                  &ldquo;{span.text}&rdquo;
                </blockquote>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface EvidenceSupportPanelProps {
  verification: EvidenceVerificationResult;
  onApplySaferTag?: (tag: string) => void;
  defaultOpen?: boolean;
}

export function EvidenceSupportPanel({
  verification,
  onApplySaferTag,
  defaultOpen = false,
}: EvidenceSupportPanelProps) {
  const [open, setOpen] = useState(defaultOpen);

  const verdict = verification.overall_verdict as SupportVerdict;
  const isClean =
    verdict === "supported" || verdict === "verification_unavailable";

  const hasIssues = verification.dimensions.some(
    (d) => d.severity !== "none" && d.verdict !== "not_applicable"
  );

  const contextLimitLabel =
    CONTEXT_LIMIT_LABELS[verification.source_text_type] ??
    verification.context_limitation ??
    "";

  if (verdict === "verification_unavailable" && !verification.context_limitation) {
    return null;
  }

  return (
    <section
      className="rounded-lg border border-zinc-200 bg-white text-xs overflow-hidden"
      aria-label="Claim support verification"
    >
      {/* Header row ─────────────────────────────────────────────────────── */}
      <button
        className="w-full flex items-center justify-between gap-2 px-3 py-2.5 hover:bg-zinc-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--ring)]"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <div className="flex items-center gap-2">
          <VerdictBadge verdict={verdict} />
          {contextLimitLabel && !open && (
            <span className="text-[10px] text-zinc-400 truncate max-w-[180px]">
              {contextLimitLabel}
            </span>
          )}
        </div>
        {!isClean && (
          <svg
            className={`w-4 h-4 text-zinc-400 flex-shrink-0 transition-transform ${open ? "rotate-180" : ""}`}
            viewBox="0 0 20 20"
            fill="currentColor"
            aria-hidden
          >
            <path
              fillRule="evenodd"
              d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
              clipRule="evenodd"
            />
          </svg>
        )}
      </button>

      {/* Expanded detail ─────────────────────────────────────────────────── */}
      {open && (
        <div className="border-t border-zinc-100">
          {/* Context limitation note */}
          {contextLimitLabel && (
            <div className="px-3 py-2 bg-zinc-50 border-b border-zinc-100">
              <p className="text-[11px] text-zinc-500">{contextLimitLabel}</p>
            </div>
          )}

          {/* Primary mismatch summary */}
          {verification.deterministic_mismatches.length > 0 && (
            <div className="px-3 py-2 border-b border-zinc-100">
              <p className="text-[11px] font-medium text-zinc-600 mb-1">
                Issues found:
              </p>
              <ul className="space-y-0.5">
                {verification.deterministic_mismatches.slice(0, 3).map((m, i) => (
                  <li key={i} className="text-[11px] text-zinc-500 flex items-start gap-1">
                    <span className="text-amber-500 flex-shrink-0 mt-0.5">•</span>
                    {m}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Safer tag suggestion */}
          {verification.safer_tag_generated && verification.safer_tag && (
            <div className="px-3 py-2 bg-amber-50 border-b border-amber-100">
              <p className="text-[11px] text-amber-700 mb-1.5">
                <span className="font-medium">Suggested narrower tag</span>
                {" — "}review before applying:
              </p>
              <p className="text-[11px] font-medium text-amber-800 italic">
                &ldquo;{verification.safer_tag}&rdquo;
              </p>
              {onApplySaferTag && (
                <button
                  className="mt-1.5 text-[10px] px-2 py-0.5 rounded border border-amber-300 text-amber-700 hover:bg-amber-100 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400"
                  onClick={() => onApplySaferTag(verification.safer_tag!)}
                >
                  Apply safer tag
                </button>
              )}
            </div>
          )}

          {/* Dimension-level results */}
          {hasIssues && (
            <div>
              <p className="px-3 pt-2 pb-1 text-[10px] font-medium uppercase tracking-wide text-zinc-400">
                Dimension breakdown
              </p>
              {verification.dimensions.map((dim, i) => (
                <DimensionRow key={`${dim.dimension}-${i}`} dim={dim} />
              ))}
            </div>
          )}

          {/* Clean card note */}
          {isClean && !contextLimitLabel && (
            <div className="px-3 py-2 text-[11px] text-zinc-500">
              Evidence body aligns with the claim on all checked dimensions.
            </div>
          )}
        </div>
      )}
    </section>
  );
}

export default EvidenceSupportPanel;
