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
const BEST_USE_LABEL: Record<string, string> = {
  contention: "Contention",
  rebuttal: "Rebuttal",
  summary: "Summary",
  final_focus: "Final Focus",
  frontline: "Frontline",
  weighing: "Weighing",
  impact: "Impact / Weighing",
  definition: "Framework",
  crossfire: "Crossfire",
};

/**
 * Build the full plain-text export of a card:
 *
 *   TAG: …
 *   SOURCE: Author Year — Publication / Title
 *   EVIDENCE: …
 *   MLA: …
 *   ROUNDLAB ANALYSIS: Warrant / Impact
 *   DEBATE PREP: proves / weakness / answer / counter / crossfire Q&A / use
 *
 * Sections with no data are omitted. Used by both Copy Card and Download.
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
    | "author"
    | "publication"
    | "title"
    | "published_date"
    | "intelligence"
  >,
  spans?: SelectedSpan[] | null,
): string {
  const tag = card.tag || "Card";
  const author = card.author || card.citation?.author_display || "";
  const yearRaw = card.citation?.year || card.published_date || "";
  const year = /(\d{4})/.exec(yearRaw)?.[1] || "";
  const pub =
    card.citation?.container_title ||
    card.citation?.publication_name ||
    card.publication ||
    "";
  const title = card.title || card.citation?.title || "";

  const sourceMain = [author, year].filter(Boolean).join(" ");
  const sourceLine =
    (sourceMain || card.short_cite || "Unknown source") + (pub ? ` — ${pub}` : "");

  const bodyText =
    spans && spans.length > 0
      ? buildCutTextFromSpans(card.cut_text_with_ellipses ?? card.body_text ?? "", spans)
      : card.cut_text_with_ellipses || card.body_text || "";

  const lines: string[] = [];
  if (card.slot_label) lines.push(`[${card.slot_label}]`);

  lines.push("TAG:", tag, "");
  lines.push("SOURCE:", sourceLine);
  if (title) lines.push(title);
  lines.push("", "EVIDENCE:", bodyText);

  if (card.mla_citation) {
    lines.push("", "MLA:", card.mla_citation);
  }

  const intel = card.intelligence;
  const warrant = intel?.warrant_analysis?.trim();
  const impact = intel?.impact_analysis?.trim();
  if (warrant || impact) {
    lines.push("", "ROUNDLAB ANALYSIS:");
    if (warrant) lines.push(`Warrant: ${warrant}`);
    if (impact) lines.push(`Impact: ${impact}`);
  }

  if (intel) {
    const prep: string[] = [];
    if (intel.why_this_card?.trim()) prep.push(`Proves: ${intel.why_this_card.trim()}`);
    if (intel.potential_weakness?.trim()) prep.push(`Weakness: ${intel.potential_weakness.trim()}`);
    if (intel.how_to_answer_weakness?.trim()) prep.push(`Response: ${intel.how_to_answer_weakness.trim()}`);
    if (intel.opponent_response?.trim()) prep.push(`Likely counter: ${intel.opponent_response.trim()}`);
    if (intel.crossfire_question?.trim()) prep.push(`Crossfire Q: ${intel.crossfire_question.trim()}`);
    if (intel.crossfire_answer?.trim()) prep.push(`Crossfire A: ${intel.crossfire_answer.trim()}`);
    if (intel.best_pairing?.trim()) prep.push(intel.best_pairing.trim());
    if (intel.weighing_angle?.trim()) prep.push(`Weighing angle: ${intel.weighing_angle.trim()}`);
    if (intel.best_use) prep.push(`Best use: ${BEST_USE_LABEL[intel.best_use] ?? intel.best_use}`);
    if (prep.length) {
      lines.push("", "DEBATE PREP:", ...prep);
    }
  }

  return lines.join("\n");
}

// ── Rich HTML clipboard ────────────────────────────────────────────────────────

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

/**
 * Build a formatted HTML representation of the card — bold tag, source line,
 * MLA, highlighted evidence (background color), and Analysis / Debate Prep
 * headings. Used for rich-clipboard copy where the browser supports text/html.
 */
export function exportCardHtml(
  card: Parameters<typeof exportCardText>[0] & { body_text?: string | null; cut_text_with_ellipses?: string | null },
  highlightSpans?: SelectedSpan[] | null,
): string {
  const tag = escapeHtml(card.tag || "Card");
  const author = card.author || card.citation?.author_display || "";
  const year = /(\d{4})/.exec(card.citation?.year || card.published_date || "")?.[1] || "";
  const pub = card.citation?.container_title || card.citation?.publication_name || card.publication || "";
  const sourceLine = escapeHtml(([author, year].filter(Boolean).join(" ") || card.short_cite || "Unknown source") + (pub ? ` — ${pub}` : ""));
  const body = card.cut_text_with_ellipses || card.body_text || "";

  // Highlighted evidence: wrap covered ranges in <mark>.
  let evidenceHtml: string;
  const spans = (highlightSpans ?? []).filter((s) => s.end > s.start).sort((a, b) => a.start - b.start);
  if (spans.length) {
    const parts: string[] = [];
    let cursor = 0;
    for (const s of spans) {
      const a = Math.max(cursor, s.start);
      const b = Math.min(body.length, s.end);
      if (a > cursor) parts.push(escapeHtml(body.slice(cursor, a)));
      if (b > a) parts.push(`<mark style="background:#fde68a;color:#1f2937">${escapeHtml(body.slice(a, b))}</mark>`);
      cursor = Math.max(cursor, b);
    }
    if (cursor < body.length) parts.push(escapeHtml(body.slice(cursor)));
    evidenceHtml = parts.join("");
  } else {
    evidenceHtml = escapeHtml(body);
  }

  const intel = card.intelligence;
  const blocks: string[] = [
    `<p style="font-size:18px;font-weight:bold;margin:0 0 4px">${tag}</p>`,
    `<p style="color:#444;margin:0 0 6px">${sourceLine}</p>`,
  ];
  if (card.mla_citation) {
    blocks.push(`<p style="font-size:11px;color:#666;margin:0 0 8px"><b>MLA:</b> ${escapeHtml(card.mla_citation)}</p>`);
  }
  blocks.push(`<p style="line-height:1.6;margin:0 0 8px">${evidenceHtml}</p>`);
  const warrant = intel?.warrant_analysis?.trim();
  const impact = intel?.impact_analysis?.trim();
  if (warrant || impact) {
    blocks.push(`<p style="margin:8px 0 2px"><b>RoundLab Analysis</b></p>`);
    if (warrant) blocks.push(`<p style="margin:0 0 2px"><b>Warrant:</b> ${escapeHtml(warrant)}</p>`);
    if (impact) blocks.push(`<p style="margin:0 0 6px"><b>Impact:</b> ${escapeHtml(impact)}</p>`);
  }
  if (intel) {
    const prep: [string, string | undefined][] = [
      ["Weakness", intel.potential_weakness],
      ["Response", intel.how_to_answer_weakness],
      ["Likely counter", intel.opponent_response],
      ["Crossfire Q", intel.crossfire_question],
      ["Crossfire A", intel.crossfire_answer],
      ["Weighing angle", intel.weighing_angle],
    ];
    const rows = prep.filter(([, v]) => v?.trim()).map(([k, v]) => `<p style="margin:0 0 2px"><b>${k}:</b> ${escapeHtml(v!.trim())}</p>`);
    if (rows.length) {
      blocks.push(`<p style="margin:8px 0 2px"><b>Debate Prep</b></p>`, ...rows);
    }
  }
  return `<div style="font-family:Arial,Helvetica,sans-serif;color:#1f2937">${blocks.join("")}</div>`;
}

/**
 * Copy a card to the clipboard. Writes rich text/html + text/plain when the
 * browser supports ClipboardItem, falling back to writeText, then execCommand.
 * Always copies the full plain-text card so copy never silently fails.
 */
export async function copyCardRich(
  card: Parameters<typeof exportCardText>[0] & { body_text?: string | null; cut_text_with_ellipses?: string | null },
  highlightSpans?: SelectedSpan[] | null,
): Promise<void> {
  const plain = exportCardText(card);
  // Rich path: text/html + text/plain via ClipboardItem.
  try {
    if (
      typeof navigator !== "undefined" &&
      navigator.clipboard &&
      typeof navigator.clipboard.write === "function" &&
      typeof ClipboardItem !== "undefined"
    ) {
      const html = exportCardHtml(card, highlightSpans);
      const item = new ClipboardItem({
        "text/html": new Blob([html], { type: "text/html" }),
        "text/plain": new Blob([plain], { type: "text/plain" }),
      });
      await navigator.clipboard.write([item]);
      return;
    }
  } catch {
    // fall through to plain text
  }
  if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(plain);
    return;
  }
  // Last resort: execCommand.
  const ta = document.createElement("textarea");
  ta.value = plain;
  ta.style.position = "fixed";
  ta.style.opacity = "0";
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  const ok = document.execCommand("copy");
  document.body.removeChild(ta);
  if (!ok) throw new Error("copy failed");
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
