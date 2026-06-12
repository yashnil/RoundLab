"use client";

import { useEffect, useRef } from "react";
import type { CardDraft } from "@/types";
import EvidenceStudioCard from "./EvidenceStudioCard";

/**
 * Large, focused Evidence Studio modal overlay.
 * Takes up most of the viewport so the card editor feels like a real workspace.
 */
export function EvidenceStudioModal({
  card,
  claimGoal,
  onSave,
  onDiscard,
  onClose,
}: {
  card: CardDraft;
  claimGoal?: string | null;
  onSave: (card: CardDraft) => void;
  onDiscard: (id: string) => void;
  onClose: () => void;
}) {
  const modalRef = useRef<HTMLDivElement>(null);

  // Close on Escape
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  // Scroll lock
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = prev; };
  }, []);

  // Focus modal on open
  useEffect(() => {
    modalRef.current?.focus();
  }, []);

  function handleDiscard(id: string) {
    onDiscard(id);
    onClose();
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      aria-modal="true"
      role="dialog"
      aria-label="Evidence Studio"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal panel — large, focused editor */}
      <div
        ref={modalRef}
        tabIndex={-1}
        className="relative z-10 flex flex-col bg-white rounded-2xl shadow-2xl overflow-hidden focus:outline-none"
        style={{
          width: "min(1400px, 96vw)",
          height: "min(900px, 92vh)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Sticky header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100 bg-white/95 backdrop-blur-sm shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            {card.slot_label && (
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 font-medium shrink-0">
                {card.slot_label}
              </span>
            )}
            <span className="text-[13px] font-semibold text-gray-800 truncate max-w-[40vw]">
              {card.tag ? card.tag.slice(0, 80) : "Evidence card"}
            </span>
          </div>
          <button
            onClick={onClose}
            className="flex items-center justify-center w-8 h-8 rounded-full text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors shrink-0"
            aria-label="Close Evidence Studio"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z"/>
            </svg>
          </button>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto">
          <EvidenceStudioCard
            card={card}
            claimGoal={claimGoal}
            onSave={onSave}
            onDiscard={handleDiscard}
            forceExpanded
          />
        </div>
      </div>
    </div>
  );
}

export default EvidenceStudioModal;
