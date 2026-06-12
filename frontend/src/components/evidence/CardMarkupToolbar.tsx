"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import type { SelectedSpan } from "@/types";

export interface MarkupState {
  highlightSpans: SelectedSpan[];
  underlineSpans: SelectedSpan[];
  boldSpans: SelectedSpan[];
  italicSpans: SelectedSpan[];
}

interface CapturedSelection {
  start: number;
  end: number;
  text: string;
  // Position for floating toolbar (viewport coordinates)
  top: number;
  left: number;
}

// ── DOM helpers ───────────────────────────────────────────────────────────────

/**
 * Walk the text nodes inside `container` and compute the character offset
 * of `(targetNode, offsetInNode)` relative to the container's total text.
 */
function getCharOffset(container: Node, targetNode: Node, offsetInNode: number): number {
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  let chars = 0;
  while (walker.nextNode()) {
    const tn = walker.currentNode as Text;
    if (tn === targetNode) {
      return chars + offsetInNode;
    }
    chars += tn.length;
  }
  return chars + offsetInNode; // fallback
}

function captureSelection(container: HTMLElement, bodyText: string): CapturedSelection | null {
  const sel = window.getSelection();
  if (!sel || sel.isCollapsed || !sel.toString().trim()) return null;

  const selText = sel.toString();
  if (sel.rangeCount === 0) return null;
  const range = sel.getRangeAt(0);

  // Verify selection is inside our container
  if (!container.contains(range.commonAncestorContainer)) return null;

  // Compute character offsets from the text content of the container
  const start = getCharOffset(container, range.startContainer, range.startOffset);
  const end = getCharOffset(container, range.endContainer, range.endOffset);

  // Verify against bodyText (fallback: indexOf)
  const safeStart = Math.max(0, Math.min(start, bodyText.length));
  const safeEnd = Math.max(safeStart, Math.min(end, bodyText.length));

  // If the computed slice doesn't match, try indexOf as fallback
  let finalStart = safeStart;
  let finalEnd = safeEnd;
  if (bodyText.slice(safeStart, safeEnd).replace(/\s+/g, " ").trim() !== selText.replace(/\s+/g, " ").trim()) {
    const idx = bodyText.indexOf(selText);
    if (idx !== -1) {
      finalStart = idx;
      finalEnd = idx + selText.length;
    }
  }

  if (finalStart >= finalEnd) return null;

  // Get toolbar position from range bounding rect
  const rect = range.getBoundingClientRect();
  return {
    start: finalStart,
    end: finalEnd,
    text: selText,
    top: rect.top + window.scrollY,
    left: rect.left + window.scrollX + rect.width / 2,
  };
}

// ── Span helpers ──────────────────────────────────────────────────────────────

function addSpan(spans: SelectedSpan[], span: SelectedSpan): SelectedSpan[] {
  const key = `${span.start}:${span.end}`;
  if (spans.some((s) => `${s.start}:${s.end}` === key)) return spans;
  return [...spans, span].sort((a, b) => a.start - b.start);
}

function removeSpansOverlapping(spans: SelectedSpan[], start: number, end: number): SelectedSpan[] {
  return spans.filter((s) => s.end <= start || s.start >= end);
}

// ── FloatingToolbar ───────────────────────────────────────────────────────────

function FloatingToolbar({
  selection,
  onHighlight,
  onUnderline,
  onBold,
  onItalic,
  onClear,
  onDismiss,
}: {
  selection: CapturedSelection;
  onHighlight: () => void;
  onUnderline: () => void;
  onBold: () => void;
  onItalic: () => void;
  onClear: () => void;
  onDismiss: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);

  // Dismiss when clicking outside
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onDismiss();
      }
    }
    document.addEventListener("mousedown", handler, true);
    return () => document.removeEventListener("mousedown", handler, true);
  }, [onDismiss]);

  // Clamp to viewport
  const style: React.CSSProperties = {
    position: "fixed",
    top: Math.max(8, selection.top - 48),
    left: Math.max(8, Math.min(selection.left - 100, window.innerWidth - 216)),
    zIndex: 9999,
  };

  return (
    <div
      ref={ref}
      style={style}
      className="flex items-center gap-0.5 bg-gray-900 text-white rounded-xl shadow-2xl px-1.5 py-1.5 text-[12px] select-none border border-gray-700"
      onMouseDown={(e) => e.preventDefault()}
    >
      <ToolBtn onClick={onHighlight} title="Highlight" cls="hover:bg-amber-500 hover:text-gray-900">
        <span style={{ backgroundColor: "#fbbf24", borderRadius: 2, padding: "0 2px" }}>H</span>
      </ToolBtn>
      <ToolBtn onClick={onBold} title="Bold" cls="hover:bg-gray-200 hover:text-gray-900">
        <strong>B</strong>
      </ToolBtn>
      <ToolBtn onClick={onUnderline} title="Underline" cls="hover:bg-blue-400 hover:text-gray-900">
        <span style={{ textDecoration: "underline" }}>U</span>
      </ToolBtn>
      <ToolBtn onClick={onItalic} title="Italic" cls="hover:bg-purple-400 hover:text-gray-900">
        <em>I</em>
      </ToolBtn>
      <div className="w-px h-4 bg-gray-600 mx-0.5" />
      <ToolBtn onClick={onClear} title="Clear formatting" cls="hover:bg-red-400 hover:text-white text-gray-400">
        ✕
      </ToolBtn>
    </div>
  );
}

function ToolBtn({ onClick, title, cls, children }: {
  onClick: () => void;
  title: string;
  cls: string;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      className={`px-2 py-1 rounded-lg transition-colors font-medium min-w-[28px] text-center ${cls}`}
    >
      {children}
    </button>
  );
}

// ── CardMarkupArea ────────────────────────────────────────────────────────────

/**
 * Wraps a card body element and captures text selections.
 * Shows a floating toolbar on selection for highlight/underline/bold/clear.
 *
 * CRITICAL: Uses onMouseDown with preventDefault on toolbar to preserve the
 * DOM selection range, so toolbar button clicks see the full selection state.
 */
export function CardMarkupArea({
  bodyText,
  markup,
  onMarkupChange,
  children,
}: {
  bodyText: string;
  markup: MarkupState;
  onMarkupChange: (m: MarkupState) => void;
  children: React.ReactNode;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [floatingSelection, setFloatingSelection] = useState<CapturedSelection | null>(null);

  const handleMouseUp = useCallback(() => {
    if (!containerRef.current) return;
    // Small delay so DOM selection is finalized
    requestAnimationFrame(() => {
      const captured = captureSelection(containerRef.current!, bodyText);
      setFloatingSelection(captured);
    });
  }, [bodyText]);

  function makeSpan(sel: CapturedSelection, rationale: string): SelectedSpan {
    return {
      start: sel.start,
      end: sel.end,
      text: bodyText.slice(sel.start, sel.end),
      sentence_index: 0,
      rationale,
    };
  }

  function applyHighlight() {
    if (!floatingSelection) return;
    const span = makeSpan(floatingSelection, "user_highlight");
    onMarkupChange({ ...markup, highlightSpans: addSpan(markup.highlightSpans, span) });
    setFloatingSelection(null);
    window.getSelection()?.removeAllRanges();
  }

  function applyUnderline() {
    if (!floatingSelection) return;
    const span = makeSpan(floatingSelection, "user_underline");
    onMarkupChange({ ...markup, underlineSpans: addSpan(markup.underlineSpans, span) });
    setFloatingSelection(null);
    window.getSelection()?.removeAllRanges();
  }

  function applyBold() {
    if (!floatingSelection) return;
    const span = makeSpan(floatingSelection, "user_bold");
    onMarkupChange({ ...markup, boldSpans: addSpan(markup.boldSpans, span) });
    setFloatingSelection(null);
    window.getSelection()?.removeAllRanges();
  }

  function applyItalic() {
    if (!floatingSelection) return;
    const span = makeSpan(floatingSelection, "user_italic");
    onMarkupChange({ ...markup, italicSpans: addSpan(markup.italicSpans ?? [], span) });
    setFloatingSelection(null);
    window.getSelection()?.removeAllRanges();
  }

  function clearFormatting() {
    if (!floatingSelection) return;
    const { start, end } = floatingSelection;
    onMarkupChange({
      highlightSpans: removeSpansOverlapping(markup.highlightSpans, start, end),
      underlineSpans: removeSpansOverlapping(markup.underlineSpans, start, end),
      boldSpans: removeSpansOverlapping(markup.boldSpans, start, end),
      italicSpans: removeSpansOverlapping(markup.italicSpans ?? [], start, end),
    });
    setFloatingSelection(null);
    window.getSelection()?.removeAllRanges();
  }

  return (
    <>
      <div
        ref={containerRef}
        onMouseUp={handleMouseUp}
        onKeyUp={handleMouseUp}
        className="cursor-text"
      >
        {children}
      </div>
      {floatingSelection && (
        <FloatingToolbar
          selection={floatingSelection}
          onHighlight={applyHighlight}
          onUnderline={applyUnderline}
          onBold={applyBold}
          onItalic={applyItalic}
          onClear={clearFormatting}
          onDismiss={() => setFloatingSelection(null)}
        />
      )}
    </>
  );
}

// ── Static markup controls bar ────────────────────────────────────────────────

/**
 * Static toolbar (not floating) for reset/clear-all actions.
 * The floating toolbar handles per-selection actions.
 */
export function CardMarkupToolbar({
  markup,
  onMarkupChange,
  onReset,
  aiHighlightSpans = [],
}: {
  markup: MarkupState;
  onMarkupChange: (m: MarkupState) => void;
  onReset: () => void;
  aiHighlightSpans?: SelectedSpan[];
}) {
  const [feedback, setFeedback] = useState("");

  function flash(msg: string) {
    setFeedback(msg);
    setTimeout(() => setFeedback(""), 1500);
  }

  const hasUserMarkup =
    markup.highlightSpans.some((s) => s.rationale?.startsWith("user")) ||
    markup.underlineSpans.some((s) => s.rationale?.startsWith("user")) ||
    markup.boldSpans.some((s) => s.rationale?.startsWith("user"));

  return (
    <div className="flex items-center gap-2 flex-wrap text-[10px] text-gray-400">
      <span className="font-medium text-gray-400 uppercase tracking-wide text-[9px]">
        Select text in the card to mark it ↑
      </span>
      {hasUserMarkup && (
        <button
          onClick={() => {
            onMarkupChange({ highlightSpans: [], underlineSpans: [], boldSpans: [], italicSpans: [] });
            flash("Cleared");
          }}
          className="px-2 py-0.5 rounded border border-gray-200 text-gray-400 hover:text-gray-600 hover:bg-gray-50"
        >
          Clear all
        </button>
      )}
      <button
        onClick={() => {
          onReset();
          flash("Reset to AI");
        }}
        className="px-2 py-0.5 rounded border border-gray-200 text-gray-400 hover:text-gray-600 hover:bg-gray-50"
      >
        Reset to AI highlights
      </button>
      {feedback && <span className="text-green-500">{feedback}</span>}
    </div>
  );
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useMarkupState(aiHighlightSpans: SelectedSpan[]): {
  markup: MarkupState;
  setMarkup: (m: MarkupState) => void;
  resetToAI: () => void;
} {
  const [markup, setMarkup] = useState<MarkupState>({
    highlightSpans: aiHighlightSpans,
    underlineSpans: [],
    boldSpans: [],
    italicSpans: [],
  });

  const resetToAI = useCallback(() => {
    setMarkup({ highlightSpans: aiHighlightSpans, underlineSpans: [], boldSpans: [], italicSpans: [] });
  }, [aiHighlightSpans]);

  return { markup, setMarkup, resetToAI };
}
