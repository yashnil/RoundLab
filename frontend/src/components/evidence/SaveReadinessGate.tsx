"use client";

import { useState } from "react";
import type { CardDraft } from "@/types";

// ── Save readiness computation (exported for tests + barrel) ─────────────────

export interface SaveReadiness {
  level: "ready" | "review_needed" | "weak";
  reasons: string[];
}

export function computeSaveReadiness(card: CardDraft): SaveReadiness {
  const hasGoodCitation =
    card.citation_quality === "complete" || card.citation_quality === "partial";
  const hasFullSource = !card.is_snippet_source;
  const noOverclaim = !card.overclaim_warning;
  const hasGoodQuality = ["high", "peer_reviewed", "medium"].includes(
    card.source_quality ?? "",
  );

  const reasons: string[] = [];
  if (!hasGoodCitation) reasons.push("Incomplete citation");
  if (!hasFullSource) reasons.push("Snippet-only source");
  if (!noOverclaim) reasons.push("Overclaim warning");
  if (!hasGoodQuality) reasons.push("Low source quality");

  const level: "ready" | "review_needed" | "weak" =
    card.is_snippet_source && !hasGoodCitation
      ? "weak"
      : reasons.length === 0
        ? "ready"
        : "review_needed";

  return { level, reasons };
}

const chipConfig = {
  ready: { label: "Ready to save", cls: "bg-green-50 border-green-300 text-green-700" },
  review_needed: {
    label: "Review needed",
    cls: "bg-amber-50 border-amber-300 text-amber-700",
  },
  weak: { label: "Verify source", cls: "bg-red-50 border-red-300 text-red-700" },
} as const;

export function SaveReadinessChip({ card }: { card: CardDraft }) {
  const { level, reasons } = computeSaveReadiness(card);
  const { label, cls } = chipConfig[level];
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className={`text-[9px] px-2 py-0.5 rounded-full border font-medium ${cls}`}>
        {label}
      </span>
      {reasons.map((r) => (
        <span
          key={r}
          className="text-[9px] px-1.5 py-0.5 rounded border border-border text-ink-muted"
        >
          {r}
        </span>
      ))}
    </div>
  );
}

/**
 * Handles all save / verify / copy gating for a card draft (Part 8).
 *   weak          → no save; "Verify source" + open-source link; copy is "unverified"
 *   review_needed → save disabled until verified checkbox; then "Save verified draft"
 *   ready         → enabled "Save to library"
 */
export function SaveReadinessGate({
  card,
  onSave,
  onDiscard,
  onCopy,
  verified,
  onVerifiedChange,
}: {
  card: CardDraft;
  onSave: (card: CardDraft) => void;
  onDiscard: (id: string) => void;
  onCopy: () => Promise<void> | void;
  verified: boolean;
  onVerifiedChange: (v: boolean) => void;
}) {
  const { level } = computeSaveReadiness(card);
  const isDraft = card.status === "draft" && !card.is_counter_evidence;
  const canSave = isDraft && (level === "ready" || (level === "review_needed" && verified));
  const [copyState, setCopyState] = useState<"idle" | "copied" | "error">("idle");

  const saveLabel =
    level === "ready"
      ? "Save to library"
      : level === "review_needed"
        ? "Save verified draft"
        : "Save";

  return (
    <div className="flex flex-col gap-2">
      <SaveReadinessChip card={card} />

      {/* review_needed verify checkbox */}
      {isDraft && level === "review_needed" && (
        <label className="flex items-center gap-2 text-[10px] text-ink-muted cursor-pointer">
          <input
            type="checkbox"
            checked={verified}
            onChange={(e) => onVerifiedChange(e.target.checked)}
            className="rounded"
          />
          I verified this card against the original source
        </label>
      )}

      {/* weak source warning + open-source action */}
      {isDraft && level === "weak" && (
        <div className="text-[10px] text-red-700 bg-red-50 border border-red-200 rounded px-2 py-1.5">
          ⚠ Snippet-only or weak citation — open the source and verify before saving.
          {card.url && (
            <a
              href={card.url}
              target="_blank"
              rel="noopener noreferrer"
              className="ml-1 text-blue-600 hover:underline"
            >
              Open source ↗
            </a>
          )}
        </div>
      )}

      <div className="flex flex-wrap gap-1.5">
        {isDraft && level !== "weak" && (
          <button
            onClick={() => onSave(card)}
            disabled={!canSave}
            className={`text-[11px] px-3 py-1 rounded-md ${
              canSave
                ? "bg-blue-600 text-white hover:bg-blue-700"
                : "bg-gray-100 text-gray-400 cursor-not-allowed border border-gray-200"
            }`}
          >
            {saveLabel}
          </button>
        )}
        {isDraft && level === "weak" && card.url && (
          <a
            href={card.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[11px] px-3 py-1 rounded-md bg-blue-600 text-white hover:bg-blue-700"
          >
            Open source ↗
          </a>
        )}
        <button
          onClick={async () => {
            try {
              await onCopy();
              setCopyState("copied");
              setTimeout(() => setCopyState("idle"), 1800);
            } catch {
              setCopyState("error");
              setTimeout(() => setCopyState("idle"), 2000);
            }
          }}
          className={`text-[11px] px-2 py-1 rounded-md border transition-colors ${
            copyState === "copied"
              ? "border-green-300 bg-green-50 text-green-700"
              : copyState === "error"
                ? "border-red-300 bg-red-50 text-red-600"
                : "border-border text-ink-muted hover:bg-surface-1"
          }`}
        >
          {copyState === "copied"
            ? "Copied! ✓"
            : copyState === "error"
              ? "Copy failed"
              : level === "weak"
                ? "Copy lead"
                : level === "review_needed" && !verified
                  ? "Copy draft"
                  : "Copy card"}
        </button>
        <button
          onClick={() => onDiscard(card.id)}
          className="text-[11px] px-2 py-1 rounded-md border border-red-200 text-red-600 hover:bg-red-50"
        >
          Discard
        </button>
      </div>
    </div>
  );
}

export default SaveReadinessGate;
