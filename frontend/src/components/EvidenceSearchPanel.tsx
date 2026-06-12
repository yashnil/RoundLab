"use client";

import { useEffect, useState } from "react";
import type { CardDraft, GenerateCardsResponse } from "@/types";
import { evidenceRoleLabel } from "@/lib/researchHelpers";

// ── Multi-step loading indicator ──────────────────────────────────────────────

const LOADING_STEPS = [
  "Planning argument paths...",
  "Searching sources...",
  "Extracting passages...",
  "Cutting cards...",
  "Formatting citations...",
];

export function SearchLoadingSteps({ active }: { active: boolean }) {
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (!active) {
      setStep(0);
      return;
    }
    const id = setInterval(() => {
      setStep((s) => (s + 1) % LOADING_STEPS.length);
    }, 2000);
    return () => clearInterval(id);
  }, [active]);

  if (!active) return null;

  return (
    <div className="flex flex-col gap-3">
      <p className="text-[12px] font-mono text-ink-muted">
        [{step + 1}/{LOADING_STEPS.length}] {LOADING_STEPS[step]}
      </p>
      <div className="flex flex-col gap-3">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="h-[160px] w-full rounded-xl border border-border bg-surface-faint animate-pulse"
          />
        ))}
      </div>
    </div>
  );
}

// ── Page-level flow predicates (exported for testing) ────────────────────────

/** The Results Summary Bar (and card list) shows when search returned cards. */
export function shouldShowResultsSummary(
  result: Pick<GenerateCardsResponse, "search_configured" | "cards"> | null,
  loading: boolean,
): boolean {
  if (loading) return false;
  return !!(result && result.search_configured && result.cards.length > 0);
}

/**
 * "No card drafts yet" shows ONLY when there are no search results AND no
 * non-discarded saved drafts.
 */
export function shouldShowEmptyState(
  result: Pick<GenerateCardsResponse, "cards"> | null,
  drafts: { status: string }[],
  loading: boolean,
): boolean {
  if (loading) return false;
  const hasSearchCards = !!result && result.cards.length > 0;
  const hasSavedDrafts = drafts.filter((d) => d.status !== "discarded").length > 0;
  return !hasSearchCards && !hasSavedDrafts;
}

// ── Results summary bar ───────────────────────────────────────────────────────

const ROLE_SUMMARY_ORDER: { role: CardDraft["evidence_role"]; short: string }[] = [
  { role: "direct_support", short: "Direct" },
  { role: "mechanism_support", short: "Mechanism" },
  { role: "example_support", short: "Example" },
  { role: "impact_support", short: "Impact" },
  { role: "authority_support", short: "Authority" },
  { role: "definition_support", short: "Definition" },
  { role: "counter_evidence", short: "Counter" },
];

export function ResultsSummaryBar({
  result,
  claimGoal,
}: {
  result: GenerateCardsResponse;
  claimGoal: string;
}) {
  const cards = result.cards ?? [];
  const counts = new Map<string, number>();
  for (const c of cards) {
    const r = (c.evidence_role ?? "direct_support") as string;
    counts.set(r, (counts.get(r) ?? 0) + 1);
  }

  const roleParts = ROLE_SUMMARY_ORDER.filter(({ role }) => (counts.get(role as string) ?? 0) > 0).map(
    ({ role, short }) => `${short}: ${counts.get(role as string)}`,
  );

  const diag = result.diagnostics;
  const sourceLabel =
    diag?.providers_used && diag.providers_used.length > 0
      ? diag.providers_used
          .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
          .join(", ")
      : "Search";
  const rerankerRaw = diag?.reranker_used ?? "none";
  const rerankerLabel =
    rerankerRaw === "cohere" ? "Cohere" : rerankerRaw === "heuristic" ? "Heuristic" : "None";

  const normalizedDiffers =
    result.normalized_claim && result.normalized_claim !== claimGoal.trim();

  return (
    <div className="rounded-lg border border-border bg-surface-faint/40 px-3 py-2 flex flex-col gap-1">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-ink">
        <span className="font-semibold">
          {cards.length} card{cards.length === 1 ? "" : "s"} found
        </span>
        {roleParts.length > 0 && (
          <>
            <span className="text-ink-muted">·</span>
            <span className="text-ink-muted">{roleParts.join("  ")}</span>
          </>
        )}
        <span className="text-ink-muted">·</span>
        <span className="text-ink-muted">Source: {sourceLabel}</span>
        <span className="text-ink-muted">·</span>
        <span className="text-ink-muted">Reranker: {rerankerLabel}</span>
      </div>

      <details className="text-[10px] text-ink-muted">
        <summary className="cursor-pointer hover:text-ink">Details</summary>
        <div className="mt-1.5 flex flex-col gap-1 pl-1">
          {result.query_used && (
            <p>
              <span className="font-medium">Query:</span> {result.query_used}
            </p>
          )}
          {normalizedDiffers && (
            <p>
              <span className="font-medium">Normalized:</span> <em>{result.normalized_claim}</em>
            </p>
          )}
          {result.corrections_applied && result.corrections_applied.length > 0 && (
            <p>
              <span className="font-medium">Corrections:</span>{" "}
              {result.corrections_applied.join("; ")}
            </p>
          )}
          {result.warnings && result.warnings.length > 0 && (
            <ul className="list-disc list-inside text-amber-700">
              {result.warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          )}
          {diag && (
            <details className="mt-1">
              <summary className="cursor-pointer hover:text-ink">View diagnostics</summary>
              <pre className="mt-1 max-h-48 overflow-auto rounded bg-gray-50 border border-border/50 p-2 text-[9px] font-mono leading-relaxed text-ink-muted whitespace-pre-wrap break-all">
                {JSON.stringify(diag, null, 2)}
              </pre>
            </details>
          )}
        </div>
      </details>
    </div>
  );
}

// Re-export so callers can map labels if needed.
export { evidenceRoleLabel };
