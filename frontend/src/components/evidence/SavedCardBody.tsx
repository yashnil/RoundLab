"use client";

import type { EvidenceCard, SelectedSpan, UserMarkupSpan } from "@/types";
import { HighlightedBodyWithEllipses } from "./DebateCardPreview";

// ── Saved-markup extraction (pure, exported for tests) ─────────────────────────

function toSpans(arr?: UserMarkupSpan[] | null): SelectedSpan[] {
  return (arr ?? [])
    .filter((s) => typeof s?.start === "number" && typeof s?.end === "number" && s.end > s.start)
    .map((s) => ({ start: s.start, end: s.end, text: s.text ?? "", sentence_index: 0 }));
}

export interface SavedMarkup {
  highlight: SelectedSpan[];
  bold: SelectedSpan[];
  underline: SelectedSpan[];
  italic: SelectedSpan[];
}

/**
 * Resolve a saved card's markup for re-rendering. Prefers the full
 * card_cutting_metadata_json.user_markup (highlight/underline/bold/italic);
 * falls back to the dedicated highlighted/underline span columns. Never throws.
 */
export function buildSavedCardMarkup(
  card: Pick<EvidenceCard, "card_cutting_metadata_json" | "highlighted_spans_json" | "underline_spans_json">,
): SavedMarkup {
  const um = card.card_cutting_metadata_json?.user_markup;
  if (um) {
    return {
      highlight: toSpans(um.highlight),
      bold: toSpans(um.bold),
      underline: toSpans(um.underline),
      italic: toSpans(um.italic),
    };
  }
  return {
    highlight: toSpans(card.highlighted_spans_json),
    underline: toSpans(card.underline_spans_json),
    bold: [],
    italic: [],
  };
}

export function savedCardHasMarkup(m: SavedMarkup): boolean {
  return m.highlight.length > 0 || m.bold.length > 0 || m.underline.length > 0 || m.italic.length > 0;
}

/**
 * Renders a saved evidence card body, re-applying any persisted user markup
 * (highlight/underline/bold/italic). Falls back to plain text when there is no
 * markup. Used in the Library card preview so saved formatting is not lost.
 */
export function SavedCardBody({
  card,
  className = "",
}: {
  card: EvidenceCard;
  className?: string;
}) {
  const markup = buildSavedCardMarkup(card);
  if (!savedCardHasMarkup(markup)) {
    return (
      <p className={`text-xs leading-relaxed text-ink-muted whitespace-pre-wrap ${className}`}>
        {card.card_text}
      </p>
    );
  }
  return (
    <div className={className}>
      <HighlightedBodyWithEllipses
        text={card.card_text}
        spans={markup.highlight}
        boldSpans={markup.bold}
        underlineSpans={markup.underline}
        italicSpans={markup.italic}
      />
    </div>
  );
}

export default SavedCardBody;
