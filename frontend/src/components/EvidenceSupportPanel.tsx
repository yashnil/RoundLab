"use client";

/**
 * EvidenceSupportPanel — displays per-argument evidence support check results.
 *
 * Phase 2: accepts pre-loaded saved checks (from GET /evidence-checks)
 * and fresh batch results (from POST /evidence-check run-all), in addition
 * to the original per-argument on-demand check flow.
 *
 * Prop hierarchy (highest priority wins):
 *   freshResults   — batch results from "Check all" button (has full card details)
 *   savedChecks    — persisted results reloaded from DB (support level + explanation only)
 *   (per-argument) — user clicks "Check evidence" on individual argument rows
 */

import { useState } from "react";
import {
  CheckCircle2, AlertCircle, HelpCircle, XCircle,
  ChevronDown, ChevronUp, BookOpen, Loader2, ExternalLink,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { apiFetch } from "@/lib/api";
import type {
  ArgumentItem, ClaimEvidenceCheck, EvidenceCard, EvidenceCheckResult,
  EvidenceSupportLevel,
} from "@/types";

// ── Support level display config ───────────────────────────────────────────────

const SUPPORT_CONFIG: Record<
  EvidenceSupportLevel,
  {
    label: string;
    icon: React.ReactNode;
    variant: "default" | "green" | "amber" | "red" | "indigo";
    shortCopy: string;
    longCopy: string;
  }
> = {
  supported: {
    label: "Supported",
    icon: <CheckCircle2 size={12} />,
    variant: "green",
    shortCopy: "This uploaded card supports the claim.",
    longCopy:
      "Your uploaded evidence directly establishes the claim and its warrant. " +
      "A flow judge would accept this card as supporting this argument.",
  },
  partially_supported: {
    label: "Partially Supported",
    icon: <AlertCircle size={12} />,
    variant: "amber",
    shortCopy: "This card supports the general idea, but not the exact claim or impact strength.",
    longCopy:
      "Your uploaded evidence is relevant to the topic but does not prove the " +
      "specific mechanism, magnitude, or impact you stated. Consider citing a " +
      "card that addresses the exact warrant you're running.",
  },
  unsupported: {
    label: "Not Supported",
    icon: <XCircle size={12} />,
    variant: "red",
    shortCopy: "The uploaded evidence does not support the claim as stated.",
    longCopy:
      "The card found in your library does not establish the specific claim you " +
      "made in your speech, or may even contradict it. Review whether you stated " +
      "the card accurately or if you need a different source.",
  },
  unverifiable: {
    label: "No Match Found",
    icon: <HelpCircle size={12} />,
    variant: "default",
    shortCopy: "No matching uploaded evidence was found.",
    longCopy:
      "No uploaded card matched the keywords in your claim. " +
      "Upload a case file that includes evidence for this argument, then re-run " +
      "the check to verify support.",
  },
};

// ── Unified display type ───────────────────────────────────────────────────────

type DisplayResult = {
  support_level: EvidenceSupportLevel;
  explanation: string;
  matched_card?: EvidenceCard | null;
  top_similarity?: number | null;
  retrieved_snippets?: Array<{chunk_id: string; snippet: string; similarity: number; heading: string | null;}> | null;
  support_rationale?: string | null;
  missing_link?: string | null;
  retrieval_mode?: string | null;
};

function fromSavedCheck(c: ClaimEvidenceCheck): DisplayResult {
  return {
    support_level: (c.support_level as EvidenceSupportLevel) ?? "unverifiable",
    explanation: c.explanation ?? "",
    matched_card: null,
    top_similarity: c.top_similarity,
    retrieved_snippets: c.retrieved_snippets_json ?? null,
    support_rationale: c.support_rationale,
    missing_link: c.missing_link,
    retrieval_mode: c.retrieval_mode,
  };
}

function fromFreshResult(r: EvidenceCheckResult): DisplayResult {
  return {
    support_level: r.support_level,
    explanation: r.explanation,
    matched_card: r.matched_card,
    top_similarity: r.top_similarity,
    retrieved_snippets: r.retrieved_snippets ?? null,
    support_rationale: r.support_rationale,
    missing_link: r.missing_link,
    retrieval_mode: r.retrieval_mode,
  };
}

function similarityLabel(sim: number): string {
  if (sim >= 0.70) return "Strong match";
  if (sim >= 0.45) return "Possible match";
  return "Weak match";
}

function similarityColor(sim: number): string {
  if (sim >= 0.70) return "text-ok";
  if (sim >= 0.45) return "text-warn";
  return "text-danger";
}

// ── Single argument row ────────────────────────────────────────────────────────

interface ArgumentCheckRowProps {
  arg: ArgumentItem;
  speechId: string;
  userId: string;
  preloaded?: DisplayResult;
}

function ArgumentCheckRow({
  arg, speechId, userId, preloaded,
}: ArgumentCheckRowProps) {
  const [result, setResult] = useState<DisplayResult | null>(preloaded ?? null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(!!preloaded);

  // Sync when parent passes new preloaded data (e.g. run-all result arrives)
  if (preloaded && !result) {
    setResult(preloaded);
    setOpen(true);
  }

  async function runCheck() {
    setLoading(true);
    setError("");
    try {
      const data = await apiFetch<EvidenceCheckResult>(
        `/speeches/${speechId}/evidence-check`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: userId,
            argument_label: arg.label,
            claim_text: arg.claim,
            evidence_text_from_speech: arg.evidence ?? undefined,
          }),
        },
      );
      setResult(fromFreshResult(data));
      setOpen(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Check failed.");
    } finally {
      setLoading(false);
    }
  }

  const cfg = result ? SUPPORT_CONFIG[result.support_level] : null;

  return (
    <div className="rounded-xl border border-hairline bg-surface p-4 flex flex-col gap-3">
      {/* Argument header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-col gap-0.5 min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-subtle truncate">
            {arg.label}
          </p>
          <p className="text-sm text-ink leading-snug">{arg.claim}</p>
          {arg.evidence && (
            <p className="text-xs text-ink-subtle mt-0.5 italic line-clamp-1">
              Cited: &ldquo;{arg.evidence}&rdquo;
            </p>
          )}
        </div>

        <div className="shrink-0 flex items-center gap-1">
          {result ? (
            <button
              className="flex items-center gap-1 text-xs text-ink-subtle hover:text-ink"
              onClick={() => setOpen((v) => !v)}
            >
              {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            </button>
          ) : (
            <Button
              size="sm"
              variant="secondary"
              className="h-7 text-xs"
              onClick={runCheck}
              disabled={loading}
            >
              {loading ? (
                <><Loader2 size={11} className="mr-1.5 animate-spin" />Checking…</>
              ) : "Check evidence"}
            </Button>
          )}
        </div>
      </div>

      {error && <p className="text-xs text-danger">{error}</p>}

      {/* Collapsed badge */}
      {result && cfg && !open && (
        <button className="flex items-center gap-1.5 self-start" onClick={() => setOpen(true)}>
          <Badge variant={cfg.variant} className="gap-1 text-xs">
            {cfg.icon} {cfg.label}
          </Badge>
          <span className="text-xs text-ink-muted">expand</span>
        </button>
      )}

      {/* Expanded result */}
      {result && cfg && open && (
        <div className="border-t border-hairline pt-3 flex flex-col gap-2.5">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant={cfg.variant} className="w-fit gap-1 text-xs">
              {cfg.icon} {cfg.label}
            </Badge>
            {result.top_similarity !== null && result.top_similarity !== undefined && (
              <span className={`text-[10px] font-medium ${similarityColor(result.top_similarity)}`}>
                {similarityLabel(result.top_similarity)} ({Math.round(result.top_similarity * 100)}%)
              </span>
            )}
          </div>

          <p className="text-xs text-ink-subtle leading-relaxed">{cfg.shortCopy}</p>

          {result.explanation && result.explanation !== cfg.shortCopy && (
            <div className="rounded-lg bg-surface-2 px-3 py-2 text-xs text-ink leading-relaxed">
              {result.explanation}
            </div>
          )}

          {/* Retrieved snippets from semantic search */}
          {result.retrieved_snippets && result.retrieved_snippets.length > 0 && (
            <details className="group rounded-lg border border-hairline bg-surface-2 text-xs">
              <summary className="flex cursor-pointer items-center justify-between px-3 py-2 list-none">
                <span className="font-medium text-ink-subtle">
                  {result.retrieved_snippets.length} retrieved evidence snippet{result.retrieved_snippets.length > 1 ? "s" : ""}
                </span>
                <ChevronDown
                  size={12}
                  className="text-ink-muted transition-transform group-open:rotate-180"
                />
              </summary>
              <div className="border-t border-hairline px-3 py-2 flex flex-col gap-2">
                {result.retrieved_snippets.slice(0, 3).map((s, i) => (
                  <div key={s.chunk_id} className="flex flex-col gap-0.5">
                    <div className="flex items-center gap-1.5">
                      <span className="text-[9px] font-semibold uppercase tracking-wide text-ink-faint">
                        Snippet {i + 1}
                      </span>
                      <span className={`text-[9px] font-medium ${similarityColor(s.similarity)}`}>
                        {similarityLabel(s.similarity)} ({Math.round(s.similarity * 100)}%)
                      </span>
                    </div>
                    {s.heading && (
                      <p className="text-[10px] font-medium text-ink-subtle">{s.heading}</p>
                    )}
                    <p className="text-ink leading-relaxed line-clamp-4">
                      {s.snippet.length > 220 ? s.snippet.slice(0, 220) + "…" : s.snippet}
                    </p>
                  </div>
                ))}
              </div>
            </details>
          )}

          {/* Keyword fallback notice */}
          {result.retrieval_mode === "keyword" && (
            <p className="text-[10px] text-ink-faint leading-relaxed">
              Semantic evidence search is not ready for this document yet. Results are based on keyword matching.{" "}
              <a href="/evidence" className="underline underline-offset-2">Re-embed in your library.</a>
            </p>
          )}

          {/* Missing link suggestion */}
          {result.missing_link && (
            <div className="rounded-lg border border-warn/20 bg-warn/5 px-3 py-2 text-xs text-ink leading-relaxed">
              <span className="font-medium text-warn">To fix: </span>
              {result.missing_link}
            </div>
          )}

          {result.matched_card && (
            <details className="group rounded-lg border border-hairline bg-surface-2 text-xs">
              <summary className="flex cursor-pointer items-center justify-between px-3 py-2 list-none">
                <span className="font-medium text-ink-subtle">
                  Matched card
                  {result.matched_card.author && ` — ${result.matched_card.author}`}
                  {result.matched_card.year && ` (${result.matched_card.year})`}
                </span>
                <ChevronDown
                  size={12}
                  className="text-ink-muted transition-transform group-open:rotate-180"
                />
              </summary>
              <div className="border-t border-hairline px-3 py-2 flex flex-col gap-1.5">
                <p className="text-ink leading-relaxed line-clamp-6">
                  {result.matched_card.card_text}
                </p>
                {result.matched_card.source && (
                  <p className="text-ink-subtle">Source: {result.matched_card.source}</p>
                )}
                {!result.matched_card.attribution_complete && (
                  <p className="text-amber-600 flex items-center gap-1">
                    <AlertCircle size={10} />
                    Attribution incomplete — verify author and date.
                  </p>
                )}
              </div>
            </details>
          )}

          {/* Disclaimer */}
          <p className="text-[10px] text-ink-faint leading-relaxed border-t border-hairline pt-2">
            RoundLab only checked your uploaded evidence library. Outside knowledge is never used.
          </p>

          {result.support_level === "unverifiable" && (
            <a
              href="/evidence"
              className="inline-flex items-center gap-1 self-start text-xs text-lav underline-offset-2 hover:underline"
            >
              <ExternalLink size={10} />
              Open Evidence Library
            </a>
          )}

          <button
            className="self-start text-xs text-ink-muted hover:text-ink underline-offset-2 hover:underline"
            onClick={runCheck}
            disabled={loading}
          >
            {loading ? "Checking…" : "Re-check"}
          </button>
        </div>
      )}
    </div>
  );
}

// ── Main panel ─────────────────────────────────────────────────────────────────

interface EvidenceSupportPanelProps {
  speechId: string;
  userId: string;
  arguments: ArgumentItem[];
  hasLibrary?: boolean;
  /** Pre-loaded persisted checks from GET /evidence-checks (Phase 2). */
  savedChecks?: ClaimEvidenceCheck[];
  /** Fresh batch results from a run-all POST sequence (Phase 2). */
  freshResults?: EvidenceCheckResult[];
}

export default function EvidenceSupportPanel({
  speechId,
  userId,
  arguments: args,
  hasLibrary = true,
  savedChecks = [],
  freshResults = [],
}: EvidenceSupportPanelProps) {
  if (!hasLibrary) {
    return (
      <div className="rounded-xl border border-dashed border-hairline p-6 text-center">
        <BookOpen size={20} className="mx-auto mb-2 text-ink-subtle" />
        <p className="text-sm font-medium text-ink">Upload a case file to verify evidence</p>
        <p className="mt-1 text-xs text-ink-subtle leading-relaxed">
          Go to your Evidence Library and upload a case file. RoundLab will check
          whether your speech claims are supported by your own uploaded evidence —
          not outside knowledge.
        </p>
        <a
          href="/evidence"
          className="mt-3 inline-flex items-center gap-1 text-xs text-lav underline-offset-2 hover:underline"
        >
          <ExternalLink size={10} />
          Open Evidence Library
        </a>
      </div>
    );
  }

  if (!args || args.length === 0) {
    return (
      <p className="text-sm text-ink-subtle">No arguments found in this speech.</p>
    );
  }

  // Build a lookup map: argument_label → DisplayResult
  // freshResults take priority over savedChecks
  const resultMap: Map<string, DisplayResult> = new Map();

  for (const check of savedChecks) {
    const key = check.argument_label ?? check.claim_text;
    if (key) resultMap.set(key, fromSavedCheck(check));
  }
  for (const r of freshResults) {
    const key = r.argument_label ?? r.claim_text;
    if (key) resultMap.set(key, fromFreshResult(r));
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-xs text-ink-subtle leading-relaxed">
        Results are based only on your uploaded evidence — RoundLab does not use outside knowledge.{" "}
        {savedChecks.length > 0 && freshResults.length === 0 && (
          <span className="text-ink-muted">Showing previously saved results. Click &ldquo;Re-check&rdquo; on any argument to update.</span>
        )}
      </p>
      {args.map((arg, i) => {
        const preloaded = resultMap.get(arg.label) ?? resultMap.get(arg.claim) ?? undefined;
        return (
          <ArgumentCheckRow
            key={arg.id ?? `arg-${i}`}
            arg={arg}
            speechId={speechId}
            userId={userId}
            preloaded={preloaded}
          />
        );
      })}
    </div>
  );
}
