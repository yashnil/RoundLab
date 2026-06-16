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

      {/* Modal panel — one-column document editor. The sticky action bar +
          Close control live inside EvidenceStudioCard so they pin to the
          scroll container as the document scrolls. */}
      <div
        ref={modalRef}
        tabIndex={-1}
        className="relative z-10 flex flex-col bg-white rounded-2xl shadow-2xl overflow-hidden focus:outline-none"
        style={{
          width: "min(900px, 96vw)",
          height: "min(940px, 92vh)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex-1 overflow-y-auto overscroll-contain">
          <EvidenceStudioCard
            card={card}
            claimGoal={claimGoal}
            onSave={onSave}
            onDiscard={handleDiscard}
            onClose={onClose}
            forceExpanded
          />
        </div>
      </div>
    </div>
  );
}

export default EvidenceStudioModal;
