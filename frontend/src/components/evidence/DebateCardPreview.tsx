"use client";

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

/** Does any span fully cover the half-open range [a, b)? */
function rangeCovered(arr: SelectedSpan[], a: number, b: number): boolean {
  return arr.some((s) => s.start <= a && s.end >= b);
}

export interface MarkupSegment {
  text: string;
  highlighted: boolean;
  bold: boolean;
  underlined: boolean;
  italic: boolean;
}

/**
 * Split `text` at every span boundary, then resolve which of
 * highlight/bold/underline/italic covers each segment. This boundary-splitting
 * approach is what lets the four styles render independently AND combine on the
 * same run of text (highlight+bold, bold+underline, all four, etc.). Exported
 * for unit testing.
 */
export function computeMarkupSegments(
  text: string,
  ranges: {
    highlight?: SelectedSpan[];
    bold?: SelectedSpan[];
    underline?: SelectedSpan[];
    italic?: SelectedSpan[];
  },
): MarkupSegment[] {
  const highlight = ranges.highlight ?? [];
  const bold = ranges.bold ?? [];
  const underline = ranges.underline ?? [];
  const italic = ranges.italic ?? [];

  const clamp = (n: number) => Math.max(0, Math.min(n, text.length));
  const points = new Set<number>([0, text.length]);
  for (const arr of [highlight, bold, underline, italic]) {
    for (const s of arr) {
      points.add(clamp(s.start));
      points.add(clamp(s.end));
    }
  }
  const bounds = [...points].sort((a, b) => a - b);

  const segments: MarkupSegment[] = [];
  for (let i = 0; i < bounds.length - 1; i++) {
    const a = bounds[i];
    const b = bounds[i + 1];
    if (b <= a) continue;
    const segText = text.slice(a, b);
    if (!segText) continue;
    segments.push({
      text: segText,
      highlighted: rangeCovered(highlight, a, b),
      bold: rangeCovered(bold, a, b),
      underlined: rangeCovered(underline, a, b),
      italic: rangeCovered(italic, a, b),
    });
  }
  return segments;
}

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
  const highlight = spans ?? [];
  const bold = boldSpans ?? [];
  const underline = underlineSpans ?? [];
  const italic = italicSpans ?? [];

  const hasAny =
    highlight.length > 0 || bold.length > 0 || underline.length > 0 || italic.length > 0;
  if (!hasAny) {
    return (
      <p className="text-[16px] leading-[1.75] text-gray-700 break-words whitespace-pre-wrap" style={CARD_BODY_STYLE}>
        <CardBodyWithEllipses text={text} />
      </p>
    );
  }

  // Boundary-split so the four styles render independently and combine.
  const segments = computeMarkupSegments(text, { highlight, bold, underline, italic });

  return (
    <p className="text-[16px] leading-[1.75] break-words whitespace-pre-wrap" style={CARD_BODY_STYLE}>
      {segments.map((seg, i) => {
        const fx = [
          seg.bold ? "font-bold" : "",
          seg.underlined ? "underline decoration-blue-500 decoration-2 underline-offset-2" : "",
          seg.italic ? "italic" : "",
        ]
          .filter(Boolean)
          .join(" ");
        const content = seg.text.includes("[…]")
          ? <CardBodyWithEllipses text={seg.text} />
          : seg.text;

        if (seg.highlighted) {
          // Read-aloud text — prominent regardless of de-emphasis mode.
          return (
            <mark key={i} className={`rounded-[3px] px-0.5 bg-amber-200 text-amber-950 text-[16px] ${fx}`}>
              {content}
            </mark>
          );
        }
        // Context — smaller/lighter when de-emphasizing, but bold/underline/italic
        // the user applied still show.
        const tone = deemphasizeUnmarked
          ? "text-gray-400 text-[12.5px]"
          : "text-gray-700 text-[16px]";
        return (
          <span key={i} className={`${tone} ${fx}`}>
            {content}
          </span>
        );
      })}
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
  author,
  year,
  bodyText,
  spans,
  boldSpans,
  underlineSpans,
  italicSpans,
  mlacitation,
  claimGoal,
  isTagNarrowed,
  sourceDomain,
  onCopyMla,
}: {
  tag: string;
  shortCite?: string | null;
  containerTitle?: string | null;
  author?: string | null;
  year?: string | null;
  bodyText: string;
  spans?: SelectedSpan[];
  boldSpans?: SelectedSpan[];
  underlineSpans?: SelectedSpan[];
  italicSpans?: SelectedSpan[];
  mlacitation?: string | null;
  claimGoal?: string | null;
  isTagNarrowed?: boolean;
  sourceDomain?: string | null;
  onCopyMla?: () => void;
}) {
  const hasHighlights = !!(spans && spans.length > 0);
  const hasMla = !!mlacitation?.trim();

  // Source line with graceful fallbacks: author → publication → "Unknown author";
  // year → "n.d."; publication → domain.
  const displayAuthor = (author || containerTitle || shortCite || "Unknown author").trim();
  const displayYear = (year && /\d{4}/.test(year) ? /(\d{4})/.exec(year)![1] : "n.d.");
  const displayPublication =
    (containerTitle && containerTitle !== author ? containerTitle : "") ||
    (sourceDomain || "");
  // Citation is "partial" when we lack a real author or year.
  const citationPartial = !author || !(year && /\d{4}/.test(year));

  return (
    <div
      className="bg-white rounded-2xl border border-gray-200/80 overflow-hidden"
      style={{ boxShadow: "0 1px 2px rgba(0,0,0,0.04), 0 10px 28px -14px rgba(0,0,0,0.14)" }}
    >
      {/* TAG — the biggest, clearest claim on the card */}
      <div className="px-6 sm:px-7 pt-6 pb-3">
        <p
          className="text-[28px] sm:text-[34px] font-bold leading-[1.12] text-gray-900 break-words"
          style={{ ...CARD_BODY_STYLE, letterSpacing: "-0.025em" }}
        >
          {tag}
        </p>
        {isTagNarrowed && (
          <p className="mt-1.5 text-[11px] text-amber-600 font-medium">Tag narrowed to match source.</p>
        )}
      </div>

      {/* SOURCE — author/org · year · publication, with graceful fallbacks */}
      <div className="px-6 sm:px-7">
        <div className="flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-[14px]" style={CARD_BODY_STYLE}>
          <span className="font-semibold text-gray-800">{displayAuthor}</span>
          <span className="font-semibold text-gray-800">· {displayYear}</span>
          {displayPublication && (
            <span className="text-gray-500">· {displayPublication}</span>
          )}
        </div>
      </div>

      {/* MLA — visible by default (not hidden behind an accordion) */}
      <div className="px-6 sm:px-7 mt-3">
        <div className="rounded-lg border border-gray-200/70 bg-gray-50/70 px-4 py-3">
          <div className="flex items-center justify-between mb-1">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">
              {citationPartial ? "Citation (partial)" : "MLA citation"}
            </p>
            {hasMla && onCopyMla && (
              <button
                onClick={onCopyMla}
                className="text-[10px] px-2 py-0.5 rounded-md border border-gray-200 text-gray-500 hover:bg-white transition-colors"
              >
                Copy MLA
              </button>
            )}
          </div>
          <p className="text-[13px] text-gray-700 leading-relaxed break-words" style={CARD_BODY_STYLE}>
            {mlacitation?.trim() || `${displayAuthor}. ${displayPublication || ""}${displayPublication ? ", " : ""}${displayYear}.`}
          </p>
        </div>
      </div>

      {/* Claim supported — secondary, demoted from the old tiny italic "Supports:" */}
      {claimGoal && (
        <div className="px-6 sm:px-7 mt-2.5">
          <p className="text-[11px] text-gray-500" style={CARD_BODY_STYLE}>
            <span className="font-semibold uppercase tracking-wide text-[9px] text-gray-400">Claim supported</span>
            {"  "}{claimGoal}
          </p>
        </div>
      )}

      {/* Divider */}
      <div className="mx-6 sm:mx-7 my-4 border-t border-gray-100" />

      {/* CARD BODY — entire card, one clean debate-styled display (no toggles) */}
      <div className="px-6 sm:px-7 pb-6">
        {hasHighlights ? (
          <HighlightedBodyWithEllipses
            text={bodyText}
            spans={spans!}
            boldSpans={boldSpans}
            underlineSpans={underlineSpans}
            italicSpans={italicSpans}
            deemphasizeUnmarked
          />
        ) : (
          <p className="text-[16px] text-gray-700 leading-[1.75] break-words whitespace-pre-wrap" style={CARD_BODY_STYLE}>
            <CardBodyWithEllipses text={bodyText} />
          </p>
        )}
      </div>
    </div>
  );
}

export default DebateCardPreview;
