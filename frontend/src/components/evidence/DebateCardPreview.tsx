"use client";

import { useState } from "react";
import type { SelectedSpan } from "@/types";

// ── Card body font stack ──────────────────────────────────────────────────────
export const CARD_BODY_STYLE: React.CSSProperties = {
  fontFamily: 'Arial, "Helvetica Neue", Helvetica, sans-serif',
};

// ── Ellipsis rendering ────────────────────────────────────────────────────────

export function CardBodyWithEllipses({ text }: { text: string }) {
  const parts = text.split(/(\[…\])/);
  return (
    <>
      {parts.map((part, i) =>
        part === "[…]" ? (
          <span
            key={i}
            className="inline-block mx-1 px-1 py-px rounded text-[10px] bg-gray-100 text-gray-400 select-none align-middle"
            aria-label="omitted text"
          >
            …
          </span>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </>
  );
}

// ── Highlighted + underlined body ─────────────────────────────────────────────

export function HighlightedBodyWithEllipses({
  text,
  spans,
  boldSpans = [],
  underlineSpans = [],
  italicSpans = [],
  deemphasizeUnmarked = false,
}: {
  text: string;
  spans: SelectedSpan[];
  boldSpans?: SelectedSpan[];
  underlineSpans?: SelectedSpan[];
  italicSpans?: SelectedSpan[];
  deemphasizeUnmarked?: boolean;
}) {
  if (!spans || spans.length === 0) {
    return (
      <p className="text-[16px] leading-[1.75] text-gray-700 break-words whitespace-pre-wrap" style={CARD_BODY_STYLE}>
        <CardBodyWithEllipses text={text} />
      </p>
    );
  }

  // Build per-span lookup sets using "start:end" keys
  const boldSet = new Set(boldSpans.map((s) => `${s.start}:${s.end}`));
  const underSet = new Set(underlineSpans.map((s) => `${s.start}:${s.end}`));
  const italicSet = new Set(italicSpans.map((s) => `${s.start}:${s.end}`));

  // Also check if any non-highlight italic spans exist (user may have applied italic
  // to unhighlighted text — we render those as plain italic spans in the non-highlighted path)
  const allItalicRanges = italicSpans.map((s) => ({ start: s.start, end: s.end }));

  const sorted = [...spans].sort((a, b) => a.start - b.start);
  const segments: {
    text: string;
    highlighted: boolean;
    bold: boolean;
    underlined: boolean;
    italic: boolean;
  }[] = [];
  let cursor = 0;

  for (const span of sorted) {
    const s = Math.max(span.start, cursor);
    const e = Math.min(span.end, text.length);
    if (s > cursor) {
      // Non-highlighted segment — check if any italic span covers it
      const segText = text.slice(cursor, s);
      const midPos = cursor + Math.floor(segText.length / 2);
      const isItalic = allItalicRanges.some((r) => r.start <= cursor && r.end >= s);
      segments.push({ text: segText, highlighted: false, bold: false, underlined: false, italic: isItalic });
    }
    if (s < e) {
      const key = `${span.start}:${span.end}`;
      segments.push({
        text: text.slice(s, e),
        highlighted: true,
        bold: boldSet.has(key),
        underlined: underSet.has(key),
        italic: italicSet.has(key),
      });
    }
    cursor = Math.max(cursor, e);
  }
  if (cursor < text.length) {
    const segText = text.slice(cursor);
    const isItalic = allItalicRanges.some((r) => r.start <= cursor && r.end >= text.length);
    segments.push({ text: segText, highlighted: false, bold: false, underlined: false, italic: isItalic });
  }

  return (
    <p className="text-[16px] leading-[1.75] break-words whitespace-pre-wrap" style={CARD_BODY_STYLE}>
      {segments.map((seg, i) =>
        seg.highlighted ? (
          <mark
            key={i}
            className={`rounded-[3px] px-0.5 text-[16px] ${
              seg.bold ? "bg-amber-200 text-amber-950 font-semibold" : "bg-amber-100 text-amber-900"
            } ${seg.underlined ? "underline decoration-blue-600 decoration-[1.5px]" : ""} ${seg.italic ? "italic" : ""}`}
          >
            {seg.text.includes("[…]") ? <CardBodyWithEllipses text={seg.text} /> : seg.text}
          </mark>
        ) : (
          <span
            key={i}
            className={`${
              deemphasizeUnmarked ? "text-gray-400 text-[13px]" : "text-gray-700 text-[16px]"
            } ${seg.italic ? "italic" : ""}`}
          >
            {seg.text.includes("[…]") ? <CardBodyWithEllipses text={seg.text} /> : seg.text}
          </span>
        ),
      )}
    </p>
  );
}

// ── DebateCardPreview ─────────────────────────────────────────────────────────

/**
 * Final debate card view — large, Arial typography, card-first.
 * Supports "debate" mode (de-emphasize non-highlighted) and "full" mode.
 */
export function DebateCardPreview({
  tag,
  shortCite,
  containerTitle,
  bodyText,
  spans,
  boldSpans,
  underlineSpans,
  italicSpans,
  mlacitation,
  claimGoal,
  isTagNarrowed,
}: {
  tag: string;
  shortCite?: string | null;
  containerTitle?: string | null;
  bodyText: string;
  spans?: SelectedSpan[];
  boldSpans?: SelectedSpan[];
  underlineSpans?: SelectedSpan[];
  italicSpans?: SelectedSpan[];
  mlacitation?: string | null;
  claimGoal?: string | null;
  isTagNarrowed?: boolean;
}) {
  const [showMore, setShowMore] = useState(false);
  const [mlaOpen, setMlaOpen] = useState(false);
  const [emphasisMode, setEmphasisMode] = useState<"debate" | "full">("debate");

  // Truncate at sentence boundary
  const PREVIEW_CHARS = 800;
  const needsTruncate = bodyText.length > PREVIEW_CHARS && !showMore;
  let visibleText = bodyText;
  if (needsTruncate) {
    const slice = bodyText.slice(0, PREVIEW_CHARS);
    const lastPeriod = Math.max(slice.lastIndexOf(". "), slice.lastIndexOf(".\n"));
    const lastSpace = slice.lastIndexOf(" ");
    const cutAt = lastPeriod > PREVIEW_CHARS - 120 ? lastPeriod + 1 : lastSpace;
    visibleText = (cutAt > 0 ? slice.slice(0, cutAt) : slice) + " …";
  }

  const visibleSpans = !spans
    ? undefined
    : needsTruncate
      ? spans.filter((s) => s.start < visibleText.length - 2)
      : spans;

  const hasHighlights = !!(visibleSpans && visibleSpans.length > 0);
  const hasMla = !!mlacitation?.trim();

  return (
    <div
      className="bg-white rounded-xl border border-gray-200 overflow-hidden"
      style={{ boxShadow: "0 2px 16px rgba(0,0,0,0.07), 0 1px 3px rgba(0,0,0,0.04)" }}
    >
      {/* Tag */}
      <div className="px-6 pt-6 pb-2">
        <p
          className="text-[22px] sm:text-[26px] font-bold leading-snug text-gray-900 break-words"
          style={{ ...CARD_BODY_STYLE, letterSpacing: "-0.02em" }}
        >
          {tag}
        </p>
        {isTagNarrowed && (
          <p className="mt-1 text-[11px] text-amber-600 font-medium">Tag narrowed to match source.</p>
        )}
      </div>

      {/* Cite line */}
      <div className="px-6 pb-3">
        <p className="text-[13px] text-gray-500 font-medium leading-snug" style={CARD_BODY_STYLE}>
          {shortCite || "Unknown"}
          {containerTitle && <span className="text-gray-400"> — {containerTitle}</span>}
        </p>
        {claimGoal && (
          <p className="text-[11px] text-gray-400 italic mt-1" style={CARD_BODY_STYLE}>
            Supports: {claimGoal}
          </p>
        )}
      </div>

      {/* Divider */}
      <div className="mx-6 border-t border-gray-100" />

      {/* Mode toggle + body */}
      <div className="px-6 py-4">
        {hasHighlights && (
          <div className="flex items-center gap-1 mb-3">
            {(["debate", "full"] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setEmphasisMode(mode)}
                className={`text-[10px] px-2 py-0.5 rounded border transition-colors ${
                  emphasisMode === mode
                    ? "bg-gray-800 text-white border-gray-800"
                    : "border-gray-200 text-gray-400 hover:border-gray-300"
                }`}
              >
                {mode === "debate" ? "Card view" : "Full quote"}
              </button>
            ))}
            <span className="text-[9px] text-gray-400 ml-1">
              {emphasisMode === "debate" ? "Highlights prominent" : "Full text equally sized"}
            </span>
          </div>
        )}

        {hasHighlights ? (
          <HighlightedBodyWithEllipses
            text={visibleText}
            spans={visibleSpans!}
            boldSpans={boldSpans}
            underlineSpans={underlineSpans}
            italicSpans={italicSpans}
            deemphasizeUnmarked={emphasisMode === "debate"}
          />
        ) : (
          <p className="text-[16px] text-gray-700 leading-[1.75] break-words whitespace-pre-wrap" style={CARD_BODY_STYLE}>
            <CardBodyWithEllipses text={visibleText} />
          </p>
        )}

        {bodyText.length > PREVIEW_CHARS && (
          <button
            onClick={() => setShowMore(!showMore)}
            className="mt-2 text-[11px] text-blue-600 hover:text-blue-700 hover:underline"
          >
            {showMore ? "Show less ↑" : "Show more ↓"}
          </button>
        )}
      </div>

      {/* MLA (compact collapsible) */}
      {hasMla && (
        <div className="border-t border-gray-100 bg-gray-50/50">
          <button
            onClick={() => setMlaOpen((v) => !v)}
            className="w-full flex items-center justify-between px-6 py-2 text-[10px] text-gray-400 hover:bg-gray-50 hover:text-gray-600 transition-colors"
          >
            <span className="font-semibold uppercase tracking-wide">MLA</span>
            <span>{mlaOpen ? "▲" : "▼"}</span>
          </button>
          {mlaOpen && (
            <p className="px-6 pb-3 text-[10px] text-gray-500 leading-relaxed break-words" style={CARD_BODY_STYLE}>
              {mlacitation}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default DebateCardPreview;
