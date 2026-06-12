"use client";

import { useState } from "react";
import type { CardDraft, EvidenceCutResult, SelectedSpan } from "@/types";
import { apiFetch } from "@/lib/api";
import {
  evidenceRoleBadgeStyle,
  evidenceRoleLabel,
  sourceQualityBadgeStyle,
  sourceQualityLabel,
} from "@/lib/researchHelpers";

import { buildCutTextFromSpans, exportCardText, downloadCardAsTxt, hostnameOnly } from "./HighlightedCardText";
import { DebateCardPreview } from "./DebateCardPreview";
import { CardMetadataRail } from "./CardMetadataRail";
import { CoachNotesPanel } from "./CoachNotesPanel";
import { SaveReadinessGate, computeSaveReadiness } from "./SaveReadinessGate";
import { SourceVerificationPanel } from "./SourceVerificationPanel";
import { EvidenceSlotBadge } from "./EvidenceSlotBadge";
import { CardMarkupToolbar, CardMarkupArea, useMarkupState } from "./CardMarkupToolbar";

export { hostnameOnly };

// ── Tag display helpers (exported for tests + barrel) ────────────────────────

/**
 * A tag is "generic" (low-value, machine-ish) if it:
 *  - matches the `<concept> — <role>` template, or
 *  - is too short (< 15 chars), or
 *  - is just the claim verbatim.
 */
export function isGenericTag(tag: string, claim?: string | null): boolean {
  const t = (tag ?? "").trim();
  if (!t) return true;
  if (t.length < 15) return true;
  if (claim && t.toLowerCase() === claim.trim().toLowerCase()) return true;
  if (
    /^[a-z\s230]+ — (direct|mechanism|example|impact|definition|authority|counter)(_support)?$/i.test(
      t,
    )
  ) {
    return true;
  }
  return false;
}

/**
 * Pick the most useful tag to show as the card hero line, with fallbacks:
 *  1. card.tag (if specific)
 *  2. card.safe_tag_scope
 *  3. card.best_supported_claim
 *  4. card.claim_goal / claimGoal (truncated to 100 chars)
 */
export function getDisplayTag(card: CardDraft, claimGoal?: string | null): string {
  // When overclaim warning is present, skip the raw tag and prefer the safe scope.
  const hasOverclaim = !!card.overclaim_warning?.trim();
  if (card.tag && !hasOverclaim && !isGenericTag(card.tag, card.claim_goal ?? claimGoal)) {
    return card.tag;
  }
  if (card.safe_tag_scope && card.safe_tag_scope.trim()) {
    return card.safe_tag_scope.trim();
  }
  if (card.tag && !isGenericTag(card.tag, card.claim_goal ?? claimGoal)) {
    return card.tag;
  }
  if (card.best_supported_claim && card.best_supported_claim.trim()) {
    return card.best_supported_claim.trim();
  }
  const fallback = (card.claim_goal || claimGoal || "Untitled card").trim();
  return fallback.length > 100 ? fallback.slice(0, 100) + "…" : fallback;
}

// ── Card behavior helpers (exported for tests + barrel) ──────────────────────

/** The body tab shown by default when a card first renders. */
export const DEFAULT_BODY_TAB: "final" | "cut" | "passage" = "final";

/** Text copied by the "Copy card" button: cut text preferred, body fallback. */
export function copyCardText(
  card: Pick<CardDraft, "cut_text_with_ellipses" | "body_text">,
): string {
  return card.cut_text_with_ellipses || card.body_text;
}

/** Whether the "Copy MLA" button is shown. */
export function showCopyMlaButton(card: Pick<CardDraft, "mla_citation">): boolean {
  return !!card.mla_citation;
}

/** Whether the ⚠ Snippet badge is shown. */
export function showSnippetBadge(card: Pick<CardDraft, "is_snippet_source">): boolean {
  return card.is_snippet_source === true;
}

/** Left-accent border class applied to counter-evidence cards. */
export function cardBorderClass(card: Pick<CardDraft, "is_counter_evidence">): string {
  return card.is_counter_evidence
    ? "border-orange-300 border-l-4 border-l-orange-400"
    : "border-border";
}

// ── CutStyleControls ──────────────────────────────────────────────────────────

function CutStyleControls({
  card,
  onCutChanged,
}: {
  card: CardDraft;
  onCutChanged: (result: EvidenceCutResult) => void;
}) {
  const [activeCutStyle, setActiveCutStyle] = useState<string>(
    card.evidence_cut?.cut_style ?? "medium_cut",
  );
  const [loading, setLoading] = useState(false);

  const styles = [
    { key: "full", label: "Full" },
    { key: "light", label: "Light" },
    { key: "medium", label: "Medium" },
    { key: "aggressive", label: "Aggressive" },
  ];

  async function handleStyleChange(style: string) {
    if (style === "full" && card.body_text) {
      setActiveCutStyle("full");
      onCutChanged({
        original_passage: card.body_text,
        selected_spans: [],
        cut_text: card.body_text,
        cut_text_with_ellipses: card.body_text,
        compression_ratio: 1.0,
        confidence: 1.0,
        cut_style: "full",
        validation_passed: true,
      });
      return;
    }

    setLoading(true);
    try {
      const data = await apiFetch<{ cut: EvidenceCutResult; cut_style_applied: string }>(
        "/research/regenerate-cut",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            original_passage: card.body_text,
            claim: card.claim_goal || "",
            evidence_role: card.evidence_role || "direct_support",
            tag: card.tag || "",
            cut_style: style,
            use_llm: false,
          }),
        },
      );
      setActiveCutStyle(style);
      onCutChanged(data.cut);
    } catch {
      // silently fail, keep current cut
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <span className="text-[9px] text-ink-muted uppercase tracking-wide">Cut style:</span>
      <div className="flex gap-1">
        {styles.map(({ key, label }) => (
          <button
            key={key}
            disabled={loading}
            onClick={() => handleStyleChange(key)}
            className={`text-[9px] px-2 py-0.5 rounded border transition-colors ${
              activeCutStyle.startsWith(key) ||
              (key === "medium" && activeCutStyle === "medium_cut")
                ? "bg-blue-100 border-blue-300 text-blue-700 font-medium"
                : "border-border text-ink-muted hover:bg-surface-faint"
            }`}
          >
            {label}
          </button>
        ))}
        {loading && <span className="text-[9px] text-ink-muted">…</span>}
      </div>
    </div>
  );
}

function RoleQualityBadges({ card }: { card: CardDraft }) {
  return (
    <>
      <span
        className={`text-[10px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full ${evidenceRoleBadgeStyle(
          card.evidence_role,
        )}`}
      >
        {evidenceRoleLabel(card.evidence_role)}
      </span>
      <span
        className={`text-[10px] px-2 py-0.5 rounded-full border ${sourceQualityBadgeStyle(
          card.source_quality,
        )}`}
      >
        {sourceQualityLabel(card.source_quality)}
      </span>
    </>
  );
}

// ── EvidenceStudioCard (card-first layout) ───────────────────────────────────

export default function EvidenceStudioCard({
  card,
  claimGoal,
  onSave,
  onDiscard,
  forceExpanded = false,
  onOpenStudio,
}: {
  card: CardDraft;
  claimGoal?: string | null;
  onSave: (card: CardDraft) => void;
  onDiscard: (id: string) => void;
  forceExpanded?: boolean;
  /** If provided, clicking "Open Studio" calls this instead of inline-expanding. */
  onOpenStudio?: () => void;
}) {
  const displayTag = getDisplayTag(card, claimGoal);
  // isTagNarrowed: true when an overclaim was detected and the displayed tag
  // differs from the raw card.tag (meaning it was replaced with a safer version).
  const isTagNarrowed =
    !!card.overclaim_warning?.trim() &&
    displayTag !== card.tag;
  const { level: readiness } = computeSaveReadiness(card);

  // Non-modal path always shows collapsed view; expanded view only via forceExpanded (modal).
  const expanded = forceExpanded;
  const [isEditingCut, setIsEditingCut] = useState(false);
  const [isSourceOpen, setIsSourceOpen] = useState(false);
  const [editingSpans, setEditingSpans] = useState<SelectedSpan[] | null>(null);
  const [verified, setVerified] = useState(false);

  // ── Markup state (user-applied highlights + underlines) ────────────────────
  const aiHighlightSpans: SelectedSpan[] = card.evidence_cut?.cut_body_spans ?? card.selected_spans ?? [];
  const { markup, setMarkup, resetToAI: resetMarkupToAI } = useMarkupState(aiHighlightSpans);

  const activeSpans = editingSpans ?? card.selected_spans ?? [];

  function handleRemoveSpan(sortedIndex: number) {
    const base = editingSpans ?? card.selected_spans ?? [];
    const sorted = [...base].sort((a, b) => a.start - b.start);
    const updated = sorted.filter((_, i) => i !== sortedIndex);
    setEditingSpans(updated);
  }

  function handleResetCut() {
    setEditingSpans(null);
    setIsEditingCut(false);
  }

  function handleCutChanged(result: EvidenceCutResult) {
    setEditingSpans(result.selected_spans ?? []);
  }

  async function handleCopy(): Promise<void> {
    const text = exportCardText(card, editingSpans);
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(text);
    } else {
      // Fallback: create a temporary textarea and execCommand
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      const success = document.execCommand("copy");
      document.body.removeChild(ta);
      if (!success) throw new Error("execCommand copy failed");
    }
  }

  function handleDownload() {
    downloadCardAsTxt(card, editingSpans);
  }

  const previewCutText =
    buildCutTextFromSpans(card.body_text, activeSpans) ||
    card.cut_text_with_ellipses ||
    card.body_text;

  // In edit mode: remap current editing spans to cut-body offsets so card
  // preview keeps highlights visible. Falls back to cut_body_spans from backend.
  const remappedEditingSpans: SelectedSpan[] | null = (() => {
    if (!editingSpans || !previewCutText) return null;
    const remapped: SelectedSpan[] = [];
    for (const span of editingSpans) {
      const pos = previewCutText.indexOf(span.text);
      if (pos !== -1) {
        remapped.push({ ...span, start: pos, end: pos + span.text.length });
      }
    }
    return remapped.length > 0 ? remapped : null;
  })();
  // Use user markup when present, else fall back to AI spans
  const cardBodySpans =
    markup.highlightSpans.length > 0
      ? markup.highlightSpans
      : (remappedEditingSpans ?? (card.evidence_cut?.cut_body_spans ?? null));
  // Merge user bold with AI bold
  const cardBodyBoldSpans = [
    ...(card.evidence_cut?.cut_body_bold_spans ?? []),
    ...markup.boldSpans,
  ];
  const cardBodyUnderlineSpans = markup.underlineSpans;
  const cardBodyItalicSpans = markup.italicSpans ?? [];
  const boldSpans = card.evidence_cut?.bold_spans ?? [];

  // ── Collapsed card — clean horizontal evidence card row ─────────────────────
  if (!expanded) {
    // Readiness dot
    const readinessDot =
      readiness === "ready" ? "bg-green-500" :
      readiness === "review_needed" ? "bg-amber-400" : "bg-red-400";
    const readinessLabel =
      readiness === "ready" ? "Ready" :
      readiness === "review_needed" ? "Review needed" : "Verify source";

    // Short evidence preview (first ~120 chars of cut text)
    const evidencePreview = (card.cut_text_with_ellipses || card.body_text || "")
      .replace(/\n+/g, " ").trim().slice(0, 130);

    return (
      <div
        className={`min-w-0 w-full rounded-xl border bg-white hover:shadow-sm transition-shadow ${
          card.is_counter_evidence ? "border-l-4 border-l-orange-400 border-orange-200" : "border-gray-200"
        }`}
      >
        <div className="flex items-stretch gap-0">
          {/* Left column: slot + tag + cite */}
          <div className="flex-1 min-w-0 px-4 py-3.5 flex flex-col gap-1">
            {/* Slot label as subtle text */}
            <div className="flex items-center gap-2">
              {card.slot_label && (
                <span className="text-[10px] text-gray-400 font-medium uppercase tracking-wide">
                  {card.slot_label}
                </span>
              )}
              {card.is_counter_evidence && (
                <span className="text-[10px] text-orange-600 font-medium">⚡ Counter</span>
              )}
              {card.is_snippet_source && (
                <span className="text-[10px] text-amber-600">⚠ Snippet</span>
              )}
            </div>
            {/* Tag — clear and large */}
            <p
              className="text-[15px] font-semibold text-gray-900 leading-snug break-words"
              style={{ fontFamily: 'Arial, "Helvetica Neue", Helvetica, sans-serif' }}
            >
              {displayTag}
            </p>
            {/* Cite line */}
            <p className="text-[12px] text-gray-500 truncate"
               style={{ fontFamily: 'Arial, "Helvetica Neue", Helvetica, sans-serif' }}>
              {card.short_cite || card.citation?.short_cite || "No citation"}
              {(card.citation?.container_title || card.citation?.publication_name) && (
                <span className="text-gray-400">
                  {" — "}{card.citation?.container_title || card.citation?.publication_name}
                </span>
              )}
            </p>
            {/* Evidence preview */}
            {evidencePreview && (
              <p className="text-[12px] text-gray-400 leading-relaxed line-clamp-2 mt-0.5"
                 style={{ fontFamily: 'Arial, "Helvetica Neue", Helvetica, sans-serif' }}>
                {evidencePreview}{evidencePreview.length >= 130 ? "…" : ""}
              </p>
            )}
          </div>

          {/* Right column: actions */}
          <div className="flex flex-col items-end justify-between px-3 py-3 gap-2 shrink-0 border-l border-gray-100">
            {/* Readiness dot + label */}
            <div className="flex items-center gap-1.5">
              <div className={`w-1.5 h-1.5 rounded-full ${readinessDot}`} />
              <span className="text-[10px] text-gray-500">{readinessLabel}</span>
            </div>
            {/* Open Studio — always opens modal, never inline expands */}
            <button
              onClick={() => onOpenStudio?.()}
              disabled={!onOpenStudio}
              className="text-[11px] px-3 py-1.5 rounded-lg bg-gray-900 text-white hover:bg-gray-700 transition-colors font-medium disabled:opacity-40"
            >
              Open Studio
            </button>
            {/* Quick save */}
            {card.status === "draft" && !card.is_counter_evidence && readiness === "ready" && (
              <button
                onClick={() => onSave(card)}
                className="text-[10px] px-2.5 py-1 rounded-lg border border-green-300 text-green-700 hover:bg-green-50 transition-colors"
              >
                Save
              </button>
            )}
            {/* Discard */}
            <button
              onClick={() => onDiscard(card.id)}
              aria-label="Discard card"
              className="text-[10px] text-gray-300 hover:text-red-400 transition-colors p-0.5"
            >
              ✕
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Expanded studio — single-scroll focused editor layout ────────────────────
  return (
    <div className={`min-w-0 w-full bg-white ${forceExpanded ? "" : `rounded-xl border-2 ${cardBorderClass(card)} shadow-sm`}`}>
      {/* Inline header (only shown outside modal — forceExpanded=false is now dead code) */}
      {!forceExpanded && null}

      {/* Main editor scroll area */}
      <div className={`flex flex-col ${forceExpanded ? "lg:flex-row" : ""} gap-0`}>

        {/* ── Left: card editor (main focus) ──────────────────────────── */}
        <div className={`flex flex-col gap-5 p-5 ${forceExpanded ? "lg:flex-1 lg:border-r lg:border-gray-100" : "w-full"} min-w-0`}>

          {/* Overclaim warning */}
          {card.overclaim_warning && (
            <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
              <span className="text-amber-500 text-sm shrink-0">⚠</span>
              <p className="text-[11px] text-amber-800 leading-snug">{card.overclaim_warning}</p>
            </div>
          )}

          {/* Counter evidence notice */}
          {card.is_counter_evidence && (
            <div className="rounded-lg border border-orange-200 bg-orange-50 px-3 py-2">
              <p className="text-[11px] text-orange-700">
                ⚡ Counter-evidence — use as a pre-empt, not support.
              </p>
            </div>
          )}

          {/* The debate card — wrapped in CardMarkupArea for selection capture */}
          <CardMarkupArea bodyText={previewCutText} markup={markup} onMarkupChange={setMarkup}>
            <DebateCardPreview
              tag={displayTag}
              shortCite={card.short_cite}
              containerTitle={card.citation?.container_title || card.citation?.publication_name}
              bodyText={previewCutText}
              spans={cardBodySpans ?? undefined}
              boldSpans={cardBodyBoldSpans}
              underlineSpans={cardBodyUnderlineSpans}
              italicSpans={cardBodyItalicSpans}
              mlacitation={card.mla_citation}
              claimGoal={card.best_supported_claim || claimGoal}
              isTagNarrowed={isTagNarrowed}
            />
          </CardMarkupArea>

          {/* Markup controls bar — reset/clear all */}
          <CardMarkupToolbar
            markup={markup}
            onMarkupChange={setMarkup}
            onReset={resetMarkupToAI}
            aiHighlightSpans={aiHighlightSpans}
          />
          <p className="text-[10px] text-gray-400">
            Select text in the card above, then click Highlight, Underline, or Bold in the popup.
          </p>

          {/* Edit cut controls — only in edit mode */}
          {!isEditingCut && (
            <button
              onClick={() => { setIsEditingCut(true); setIsSourceOpen(true); }}
              className="self-start text-[11px] px-3 py-1.5 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 hover:text-gray-700 transition-colors"
            >
              ✂ Edit cut
            </button>
          )}
          {isEditingCut && (
            <div className="flex flex-col gap-2 p-3 rounded-lg border border-gray-100 bg-gray-50">
              <CutStyleControls card={card} onCutChanged={handleCutChanged} />
              {card.evidence_cut?.cut_warnings && card.evidence_cut.cut_warnings.length > 0 && (
                <ul className="text-[9px] text-amber-700 space-y-0.5">
                  {card.evidence_cut.cut_warnings.map((w, i) => (
                    <li key={i}>⚠ {w}</li>
                  ))}
                </ul>
              )}
              <button
                onClick={handleResetCut}
                className="self-start text-[10px] px-2 py-0.5 rounded border border-amber-200 text-amber-600 hover:bg-amber-50"
              >
                Reset cut
              </button>
            </div>
          )}

          {/* Source verification — collapsed by default */}
          <div className="flex flex-col gap-1.5">
            <button
              onClick={() => setIsSourceOpen((v) => !v)}
              className="flex items-center gap-1.5 text-[11px] text-gray-400 hover:text-gray-600 w-fit transition-colors py-1"
            >
              <span
                className="text-[10px] transition-transform duration-150 inline-block"
                style={{ transform: isSourceOpen ? "rotate(90deg)" : "none" }}
              >
                ▸
              </span>
              <span className="font-medium">Verify source</span>
              {card.url && (
                <span className="text-blue-400 truncate max-w-[160px] text-[10px]">
                  {card.url.replace(/^https?:\/\/(www\.)?/, "").split("/")[0]}
                </span>
              )}
            </button>
            {isSourceOpen && (
              <div className="rounded-lg border border-gray-100 overflow-hidden">
                <SourceVerificationPanel
                  card={card}
                  editingSpans={activeSpans}
                  boldSpans={boldSpans}
                  onRemoveSpan={handleRemoveSpan}
                  isEditing={isEditingCut}
                  onEditStart={() => { setIsEditingCut(true); }}
                  onEditReset={handleResetCut}
                />
              </div>
            )}
          </div>

          {/* Action bar — bottom of editor column */}
          <div className="flex flex-wrap gap-2 pt-2 border-t border-gray-100">
            <SaveReadinessGate
              card={card}
              onSave={(c) => {
                // Merge user markup into card before saving so spans are persisted
                const cardWithMarkup: typeof c = {
                  ...c,
                  highlighted_spans_json: [
                    ...(c.highlighted_spans_json ?? []),
                    ...markup.highlightSpans.filter((s) => s.rationale?.startsWith("user")).map((s) => ({
                      start: s.start, end: s.end, type: "highlight" as const, reason: "user",
                    })),
                  ],
                  underline_spans_json: [
                    ...(c.underline_spans_json ?? []),
                    ...markup.underlineSpans.filter((s) => s.rationale?.startsWith("user")).map((s) => ({
                      start: s.start, end: s.end, type: "underline" as const, reason: "user",
                    })),
                  ],
                };
                onSave(cardWithMarkup);
              }}
              onDiscard={onDiscard}
              onCopy={handleCopy}
              verified={verified}
              onVerifiedChange={setVerified}
            />
            {showCopyMlaButton(card) && (
              <button
                onClick={() => navigator.clipboard?.writeText(card.mla_citation!)}
                className="text-[11px] px-2.5 py-1.5 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50"
              >
                Copy MLA
              </button>
            )}
            <button
              onClick={handleDownload}
              className="text-[11px] px-2.5 py-1.5 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50"
              title="Download card as .txt"
            >
              ↓ Download
            </button>
          </div>
        </div>

        {/* ── Right rail: metadata + coach notes ───────────────────────── */}
        {forceExpanded && (
          <div className="lg:w-80 xl:w-96 flex flex-col gap-4 p-5 bg-gray-50/50 shrink-0">
            <CardMetadataRail card={card} />
            <CoachNotesPanel
              intelligence={card.intelligence}
              slotLabel={card.slot_label}
            />
          </div>
        )}
      </div>
    </div>
  );
}
