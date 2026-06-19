import type { EvidenceRetrievalMode, EvidenceSupportLevel, SearchMode } from "@/types";

// ── Document upload constraints + formatting ─────────────────────────────────────

export const ALLOWED_EVIDENCE_EXTS = ["pdf", "docx", "txt", "md"];
export const MAX_EVIDENCE_MB = 20;

export function fileSizeLabel(bytes: number | null): string {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function extFromFilename(name: string): string {
  return name.split(".").pop()?.toLowerCase() ?? "";
}

// ── Similarity label ───────────────────────────────────────────────────────────

export interface SimilarityDisplay {
  label: string;
  colorClass: string;
  /** True when similarity meets the "strong" threshold */
  isStrong: boolean;
}

export function getSimilarityLabel(similarity: number | null | undefined): SimilarityDisplay {
  if (similarity === null || similarity === undefined) {
    return { label: "No match", colorClass: "text-ink-faint", isStrong: false };
  }
  if (similarity >= 0.70) {
    return { label: "Strong match", colorClass: "text-ok", isStrong: true };
  }
  if (similarity >= 0.45) {
    return { label: "Possible match", colorClass: "text-warn", isStrong: false };
  }
  return { label: "Weak match", colorClass: "text-danger", isStrong: false };
}

export function getSimilarityPct(similarity: number | null | undefined): string {
  if (similarity === null || similarity === undefined) return "—";
  return `${Math.round(similarity * 100)}%`;
}

// ── Search mode helpers ────────────────────────────────────────────────────────

export interface SearchModeDisplay {
  label: string;
  description: string;
}

const SEARCH_MODE_DISPLAY: Record<SearchMode, SearchModeDisplay> = {
  keyword: {
    label: "Keyword",
    description: "Matches exact words. Fast and deterministic.",
  },
  semantic: {
    label: "Semantic",
    description:
      "Finds conceptually related cards even when the wording differs. Uses AI embeddings.",
  },
  hybrid: {
    label: "Hybrid",
    description:
      "Semantic results first, then keyword results to fill any gaps. Recommended.",
  },
};

export function getSearchModeDisplay(mode: SearchMode): SearchModeDisplay {
  return SEARCH_MODE_DISPLAY[mode] ?? SEARCH_MODE_DISPLAY.keyword;
}

export function getSearchModeHelperText(mode: SearchMode): string {
  return SEARCH_MODE_DISPLAY[mode]?.description ?? "";
}

// ── Retrieval mode display ─────────────────────────────────────────────────────

export function getRetrievalModeLabel(mode: EvidenceRetrievalMode | null | undefined): string {
  switch (mode) {
    case "semantic":
      return "Semantic retrieval";
    case "keyword":
      return "Keyword retrieval (embeddings not yet ready)";
    case "none":
      return "No retrieval — library empty";
    default:
      return "";
  }
}

export function isSemanticRetrievalAvailable(mode: EvidenceRetrievalMode | null | undefined): boolean {
  return mode === "semantic";
}

// ── Support level helpers ──────────────────────────────────────────────────────

export interface SupportLevelDisplay {
  label: string;
  shortCopy: string;
  suggestedFix: string;
}

const SUPPORT_LEVEL_DISPLAY: Record<EvidenceSupportLevel, SupportLevelDisplay> = {
  supported: {
    label: "Supported",
    shortCopy: "An uploaded card directly supports this claim.",
    suggestedFix: "",
  },
  partially_supported: {
    label: "Partially Supported",
    shortCopy:
      "The closest card is relevant but does not prove the exact claim, magnitude, or impact.",
    suggestedFix:
      "Narrow your claim to match the card, or add a warrant bridging the gap.",
  },
  unsupported: {
    label: "Not Supported",
    shortCopy: "No uploaded card supports the claim as stated.",
    suggestedFix:
      "Restate the claim using language from the card, or upload the card you used in the speech.",
  },
  unverifiable: {
    label: "No Match Found",
    shortCopy: "No uploaded card matched this claim.",
    suggestedFix:
      "Upload a case file containing evidence for this argument, then re-run the check.",
  },
};

export function getSupportLevelDisplay(
  level: EvidenceSupportLevel | null | undefined
): SupportLevelDisplay {
  if (!level) return SUPPORT_LEVEL_DISPLAY.unverifiable;
  return SUPPORT_LEVEL_DISPLAY[level] ?? SUPPORT_LEVEL_DISPLAY.unverifiable;
}

// ── Snippet truncation ─────────────────────────────────────────────────────────

export function truncateSnippet(text: string, maxChars: number = 220): string {
  if (text.length <= maxChars) return text;
  const truncated = text.slice(0, maxChars);
  const lastSpace = truncated.lastIndexOf(" ");
  return (lastSpace > maxChars * 0.7 ? truncated.slice(0, lastSpace) : truncated) + "…";
}

// ── Document embedding status ──────────────────────────────────────────────────

/** Returns true when any chunk in the result set has a similarity score (semantic was used). */
export function anySemanticResults(
  results: Array<{ similarity: number | null }> | null | undefined
): boolean {
  return (results ?? []).some((r) => r.similarity !== null && r.similarity !== undefined);
}
