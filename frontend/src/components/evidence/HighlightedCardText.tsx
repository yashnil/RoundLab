"use client";

import type { CardDraft, SelectedSpan } from "@/types";

// ── Pure text helpers (exported, used by barrel + tests) ─────────────────────

/** Return just the hostname for display; falls back to the raw string. */
export function hostnameOnly(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

/**
 * Rebuild cut_text_with_ellipses from a set of selected spans and the original passage.
 * Spans are sorted by position, non-adjacent spans get " […] " between them.
 * Returns empty string if spans is empty (caller should fall back to full passage).
 *
 * SAFETY: uses originalPassage.slice(span.start, span.end) — exact substrings only.
 * Evidence body text is never paraphrased or modified.
 */
export function buildCutTextFromSpans(
  originalPassage: string,
  spans: SelectedSpan[],
): string {
  if (!originalPassage || !spans || spans.length === 0) return "";

  const sorted = [...spans].sort((a, b) => a.start - b.start);
  const parts: string[] = [];

  for (let i = 0; i < sorted.length; i++) {
    const span = sorted[i];
    const text = originalPassage.slice(span.start, span.end);
    if (!text.trim()) continue;

    if (i > 0) {
      const prevEnd = sorted[i - 1].end;
      const gap = originalPassage.slice(prevEnd, span.start).trim();
      if (gap) {
        parts.push("[…]");
      }
    }
    parts.push(text);
  }

  return parts.join(" ");
}

/**
 * Build the plaintext export of a card (tag, cite row, evidence, optional slot
 * label + MLA). Slot label is included when present so exported drafts carry
 * their strategic context.
 */
export function exportCardText(
  card: Pick<
    CardDraft,
    | "tag"
    | "short_cite"
    | "citation"
    | "cut_text_with_ellipses"
    | "body_text"
    | "mla_citation"
    | "slot_label"
  >,
  spans?: SelectedSpan[] | null,
): string {
  const tag = card.tag || "Card";
  const cite = card.short_cite || "Unknown";
  const pub = card.citation?.container_title || card.citation?.publication_name || "";
  const citeRow = pub ? `${cite} — ${pub}` : cite;

  const bodyText =
    spans && spans.length > 0
      ? buildCutTextFromSpans(card.cut_text_with_ellipses ?? card.body_text ?? "", spans)
      : card.cut_text_with_ellipses || card.body_text || "";

  const parts: string[] = [];
  if (card.slot_label) parts.push(`[${card.slot_label}]`);
  parts.push(tag, citeRow, bodyText);
  if (card.mla_citation) {
    parts.push(`\nMLA:\n${card.mla_citation}`);
  }
  return parts.join("\n");
}

/**
 * Download a card as a plain-text .txt file. No backend required.
 * Uses the same exportCardText format.
 */
export function downloadCardAsTxt(
  card: Parameters<typeof exportCardText>[0],
  spans?: SelectedSpan[] | null,
): void {
  const text = exportCardText(card, spans);
  const slug = (card.short_cite || "card").replace(/[^a-z0-9]/gi, "_").toLowerCase().slice(0, 30);
  const filename = `roundlab_card_${slug}.txt`;
  const blob = new Blob([text], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ── HighlightedCardText (renders body with highlighted + bold spans) ──────────

function spanKey(s: SelectedSpan): string {
  return `${s.start}:${s.end}`;
}

export function HighlightedCardText({
  text,
  spans,
  boldSpans = [],
  mode = "full",
  editable = false,
  onRemoveSpan,
}: {
  text: string;
  spans: SelectedSpan[];
  boldSpans?: SelectedSpan[];
  mode?: "full" | "deemphasize";
  editable?: boolean;
  onRemoveSpan?: (index: number) => void;
}) {
  if (!text) return null;

  if (!spans || spans.length === 0) {
    return (
      <p className="text-[12px] leading-relaxed text-ink-dark whitespace-pre-wrap break-words px-2.5 py-2">
        {text}
      </p>
    );
  }

  const boldKeys = new Set(boldSpans.map(spanKey));

  const sorted = [...spans].sort((a, b) => a.start - b.start);
  const segments: {
    text: string;
    highlighted: boolean;
    bold?: boolean;
    spanIndex?: number;
  }[] = [];
  let cursor = 0;

  sorted.forEach((span, spanIndex) => {
    const s = Math.max(span.start, cursor);
    const e = Math.min(span.end, text.length);
    if (s > cursor) {
      segments.push({ text: text.slice(cursor, s), highlighted: false });
    }
    if (s < e) {
      segments.push({
        text: text.slice(s, e),
        highlighted: true,
        bold: boldKeys.has(spanKey(span)),
        spanIndex,
      });
    }
    cursor = Math.max(cursor, e);
  });
  if (cursor < text.length) {
    segments.push({ text: text.slice(cursor), highlighted: false });
  }

  // Map spanIndex → display number (1-based)
  const uniqueSpanIndices = [
    ...new Set(segments.filter((s) => s.highlighted).map((s) => s.spanIndex!)),
  ];
  const spanNumberMap = new Map(uniqueSpanIndices.map((idx, n) => [idx, n + 1]));

  return (
    <p className="text-[12px] leading-relaxed whitespace-pre-wrap break-words px-2.5 py-2">
      {segments.map((seg, i) =>
        seg.highlighted ? (
          <mark
            key={i}
            className={`rounded px-0.5 not-italic relative ${
              seg.bold
                ? "bg-amber-200 text-amber-950 font-semibold"
                : "bg-amber-100 text-amber-900"
            } ${editable ? "cursor-pointer hover:bg-amber-300" : ""}`}
          >
            {spanNumberMap.has(seg.spanIndex!) && (
              <sup className="text-[8px] font-bold text-amber-600 mr-0.5">
                {spanNumberMap.get(seg.spanIndex!)}
              </sup>
            )}
            {seg.text}
            {editable && onRemoveSpan && (
              <button
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onRemoveSpan(seg.spanIndex!);
                }}
                className="ml-0.5 text-[9px] text-red-500 hover:text-red-700 font-bold leading-none"
                title="Remove this span from cut"
              >
                ×
              </button>
            )}
          </mark>
        ) : (
          <span
            key={i}
            className={mode === "deemphasize" ? "text-ink-muted/20" : "text-ink-dark"}
          >
            {seg.text}
          </span>
        ),
      )}
    </p>
  );
}

/** Backward-compatible alias for the prior HighlightedPassage component. */
export function HighlightedPassage(props: {
  text: string;
  spans: SelectedSpan[];
  mode: "full" | "deemphasize";
  editable?: boolean;
  onRemoveSpan?: (index: number) => void;
}) {
  return <HighlightedCardText {...props} />;
}
