"use client";

/**
 * Barrel re-export for the Evidence Studio card (Part 7 split).
 *
 * EvidenceCardDraft was split into focused components under ./evidence/*.
 * This module preserves the original public API so existing imports keep
 * working unchanged.
 */

export { default } from "./evidence/EvidenceStudioCard";
export {
  isGenericTag,
  getDisplayTag,
  DEFAULT_BODY_TAB,
  copyCardText,
  showCopyMlaButton,
  showSnippetBadge,
  cardBorderClass,
  hostnameOnly,
} from "./evidence/EvidenceStudioCard";

export {
  buildCutTextFromSpans,
  exportCardText,
  HighlightedPassage,
  HighlightedCardText,
} from "./evidence/HighlightedCardText";

export {
  computeSaveReadiness,
  SaveReadinessGate,
  SaveReadinessChip,
} from "./evidence/SaveReadinessGate";
export type { SaveReadiness } from "./evidence/SaveReadinessGate";

export { DebateCardPreview } from "./evidence/DebateCardPreview";
export { CardMetadataRail } from "./evidence/CardMetadataRail";
export { CoachNotesPanel } from "./evidence/CoachNotesPanel";
export { SourceVerificationPanel } from "./evidence/SourceVerificationPanel";
export { EvidenceSlotBadge } from "./evidence/EvidenceSlotBadge";
