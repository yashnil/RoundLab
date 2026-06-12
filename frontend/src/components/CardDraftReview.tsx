"use client";

/**
 * CardDraftReview — clean card row for URL/Paste drafts using the same EvidenceStudioModal.
 *
 * Replaces the old "debug dashboard" style with a clean horizontal card row
 * that opens the polished Evidence Studio modal on click.
 */

import { useState } from "react";
import type { CardDraft } from "@/types";
import { computeSaveReadiness } from "@/components/evidence/SaveReadinessGate";
import { EvidenceStudioModal } from "@/components/evidence/EvidenceStudioModal";

interface CardDraftReviewProps {
  draft: CardDraft;
  onSave: (draft: CardDraft, confirmed: boolean) => Promise<void>;
  onDiscard: (draftId: string) => Promise<void>;
  onPatch: (draftId: string, updates: Partial<CardDraft>) => Promise<void>;
  saving?: boolean;
  discarding?: boolean;
}

export default function CardDraftReview({
  draft,
  onSave,
  onDiscard,
  onPatch: _onPatch,
  saving = false,
  discarding = false,
}: CardDraftReviewProps) {
  const [studioOpen, setStudioOpen] = useState(false);
  const { level: readiness } = computeSaveReadiness(draft);

  const displayTag = draft.tag || "Untitled card";
  const citeDisplay = draft.cite || draft.short_cite || draft.author || "";
  const publication = draft.publication || draft.citation?.publication_name || "";
  const evidencePreview = (draft.cut_text_with_ellipses || draft.body_text || "")
    .replace(/\n+/g, " ").trim().slice(0, 130);

  const readinessDot =
    readiness === "ready" ? "bg-green-500" :
    readiness === "review_needed" ? "bg-amber-400" : "bg-red-400";
  const readinessLabel =
    readiness === "ready" ? "Ready" :
    readiness === "review_needed" ? "Review needed" : "Verify source";

  async function handleSave(card: CardDraft) {
    await onSave(card, true);
    setStudioOpen(false);
  }

  async function handleDiscard(id: string) {
    await onDiscard(id);
  }

  return (
    <>
      {/* Modal */}
      {studioOpen && (
        <EvidenceStudioModal
          card={draft}
          claimGoal={draft.claim_goal}
          onSave={(c) => { onSave(c, true); setStudioOpen(false); }}
          onDiscard={handleDiscard}
          onClose={() => setStudioOpen(false)}
        />
      )}

      {/* Clean horizontal card row — same style as EvidenceStudioCard collapsed */}
      <div className={`min-w-0 w-full rounded-xl border bg-white hover:shadow-sm transition-shadow ${
        discarding ? "opacity-50" : ""
      } border-gray-200`}>
        <div className="flex items-stretch gap-0">
          {/* Left: tag + cite + preview */}
          <div className="flex-1 min-w-0 px-4 py-3.5 flex flex-col gap-1">
            {/* Source URL as subtle label */}
            {draft.url && (
              <p className="text-[10px] text-gray-400 truncate">
                {draft.url.replace(/^https?:\/\/(www\.)?/, "").split("/")[0]}
              </p>
            )}
            {/* Tag */}
            <p
              className="text-[15px] font-semibold text-gray-900 leading-snug break-words"
              style={{ fontFamily: 'Arial, "Helvetica Neue", Helvetica, sans-serif' }}
            >
              {displayTag}
            </p>
            {/* Cite line */}
            {(citeDisplay || publication) && (
              <p className="text-[12px] text-gray-500 truncate"
                 style={{ fontFamily: 'Arial, "Helvetica Neue", Helvetica, sans-serif' }}>
                {citeDisplay}
                {publication && <span className="text-gray-400"> — {publication}</span>}
              </p>
            )}
            {/* Evidence preview */}
            {evidencePreview && (
              <p className="text-[12px] text-gray-400 leading-relaxed line-clamp-2 mt-0.5"
                 style={{ fontFamily: 'Arial, "Helvetica Neue", Helvetica, sans-serif' }}>
                {evidencePreview}{evidencePreview.length >= 130 ? "…" : ""}
              </p>
            )}
          </div>

          {/* Right: actions */}
          <div className="flex flex-col items-end justify-between px-3 py-3 gap-2 shrink-0 border-l border-gray-100">
            {/* Readiness */}
            <div className="flex items-center gap-1.5">
              <div className={`w-1.5 h-1.5 rounded-full ${readinessDot}`} />
              <span className="text-[10px] text-gray-500">{readinessLabel}</span>
            </div>
            {/* Open Studio */}
            <button
              onClick={() => setStudioOpen(true)}
              className="text-[11px] px-3 py-1.5 rounded-lg bg-gray-900 text-white hover:bg-gray-700 transition-colors font-medium"
            >
              Open Studio
            </button>
            {/* Quick save */}
            {readiness === "ready" && (
              <button
                onClick={() => handleSave(draft)}
                disabled={saving}
                className="text-[10px] px-2.5 py-1 rounded-lg border border-green-300 text-green-700 hover:bg-green-50 transition-colors disabled:opacity-50"
              >
                {saving ? "Saving…" : "Save"}
              </button>
            )}
            {/* Discard */}
            <button
              onClick={() => handleDiscard(draft.id)}
              disabled={discarding}
              aria-label="Discard draft"
              className="text-[10px] text-gray-300 hover:text-red-400 transition-colors p-0.5"
            >
              ✕
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
