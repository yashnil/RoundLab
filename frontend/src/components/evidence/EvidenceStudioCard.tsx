"use client";

import { useState } from "react";
import { Save, Copy, Download, Quote, Trash2, ExternalLink, X, Check } from "lucide-react";
import type { CardDraft, EvidenceCutResult, SelectedSpan } from "@/types";
import { apiFetch } from "@/lib/api";

import { copyCardRich, downloadCardAsTxt, hostnameOnly } from "./HighlightedCardText";
import { DebateCardPreview } from "./DebateCardPreview";
import { CardAnalysis } from "./CardAnalysis";
import { DebatePrepPanel } from "./DebatePrepPanel";
import { computeSaveReadiness } from "./SaveReadinessGate";
import { CardMarkupToolbar, CardMarkupArea, useMarkupState, buildUserMarkupPayload, isUserSpan } from "./CardMarkupToolbar";

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

// ── CutStyleControls — two styles only (Medium / High) ───────────────────────

/** Map the backend cut_style onto the two user-facing styles. */
export function activeStyleFromCut(cutStyle?: string | null): "medium" | "high" {
  if (!cutStyle) return "medium";
  if (cutStyle === "aggressive_cut" || cutStyle === "high") return "high";
  return "medium";
}

function CutStyleControls({
  card,
  activeStyle,
  onStyleChange,
}: {
  card: CardDraft;
  activeStyle: "medium" | "high";
  onStyleChange: (style: "medium" | "high", result: EvidenceCutResult) => void;
}) {
  const [loading, setLoading] = useState<"medium" | "high" | null>(null);

  async function handleStyleChange(style: "medium" | "high") {
    if (style === activeStyle || loading) return;
    setLoading(style);
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
      onStyleChange(style, data.cut);
    } catch {
      // keep current cut on failure
    } finally {
      setLoading(null);
    }
  }

  const styles: { key: "medium" | "high"; label: string; hint: string }[] = [
    { key: "medium", label: "Medium", hint: "Keeps the warrant + key context" },
    { key: "high", label: "High", hint: "Hard cut to the core phrases" },
  ];

  return (
    <div className="flex items-center gap-2.5 flex-wrap">
      <span className="text-[10px] text-gray-400 uppercase tracking-wide font-medium">Cut</span>
      <div className="inline-flex items-center rounded-lg border border-gray-200 bg-white p-0.5">
        {styles.map(({ key, label, hint }) => (
          <button
            key={key}
            title={hint}
            disabled={!!loading}
            onClick={() => handleStyleChange(key)}
            className={`px-3 py-1 rounded-md text-[11px] font-medium transition-colors ${
              activeStyle === key
                ? "bg-gray-900 text-white"
                : "text-gray-500 hover:text-gray-800"
            }`}
          >
            {loading === key ? "…" : label}
          </button>
        ))}
      </div>
      <span className="text-[10px] text-gray-400">
        {styles.find((s) => s.key === activeStyle)?.hint}
      </span>
    </div>
  );
}

// ── Sticky action-bar pieces ─────────────────────────────────────────────────

function ReadinessPill({ readiness }: { readiness: "ready" | "review_needed" | "weak" }) {
  const cfg = {
    ready: { label: "Ready to save", dot: "bg-emerald-500", cls: "bg-emerald-50 border-emerald-200 text-emerald-700" },
    review_needed: { label: "Review needed", dot: "bg-amber-500", cls: "bg-amber-50 border-amber-200 text-amber-700" },
    weak: { label: "Verify source", dot: "bg-rose-500", cls: "bg-rose-50 border-rose-200 text-rose-700" },
  }[readiness];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium ${cfg.cls}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  );
}

function ActionIconButton({
  icon, label, onClick, href, disabled, tone = "default", active,
}: {
  icon: React.ReactNode;
  label: string;
  onClick?: () => void;
  href?: string;
  disabled?: boolean;
  tone?: "default" | "danger";
  active?: boolean;
}) {
  const toneCls = active
    ? "text-emerald-600 bg-emerald-50"
    : tone === "danger"
      ? "text-gray-400 hover:text-rose-600 hover:bg-rose-50"
      : "text-gray-500 hover:text-gray-900 hover:bg-gray-100";
  const cls = `inline-flex h-8 w-8 items-center justify-center rounded-lg transition-colors disabled:opacity-40 disabled:hover:bg-transparent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-300 ${toneCls}`;
  if (href) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" aria-label={label} title={label} className={cls}>
        {icon}
      </a>
    );
  }
  return (
    <button type="button" onClick={onClick} disabled={disabled} aria-label={label} title={label} className={cls}>
      {icon}
    </button>
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
  onClose,
}: {
  card: CardDraft;
  claimGoal?: string | null;
  onSave: (card: CardDraft) => void;
  onDiscard: (id: string) => void;
  forceExpanded?: boolean;
  /** If provided, clicking "Open Studio" calls this instead of inline-expanding. */
  onOpenStudio?: () => void;
  /** Modal close handler — surfaces a Close control in the sticky action bar. */
  onClose?: () => void;
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
  const initialCut = card.evidence_cut;
  const [activeStyle, setActiveStyle] = useState<"medium" | "high">(
    activeStyleFromCut(initialCut?.cut_style),
  );
  // The card body shown + the AI highlight subset for it. Both update in place
  // when the cut style changes — there is no second editor panel.
  const [cutBody, setCutBody] = useState<string>(
    initialCut?.cut_text_with_ellipses || card.cut_text_with_ellipses || card.body_text || "",
  );
  const [aiSpans, setAiSpans] = useState<SelectedSpan[]>(
    initialCut?.cut_body_spans ?? card.selected_spans ?? [],
  );
  const [aiBoldSpans, setAiBoldSpans] = useState<SelectedSpan[]>(
    initialCut?.cut_body_bold_spans ?? [],
  );
  const [cutWarnings, setCutWarnings] = useState<string[]>(initialCut?.cut_warnings ?? []);
  const [copyState, setCopyState] = useState<"idle" | "copied" | "error">("idle");
  const [mlaCopied, setMlaCopied] = useState(false);

  // ── Markup state (user-applied highlight/underline/bold/italic) ────────────
  const { markup, setMarkup } = useMarkupState(aiSpans);

  function resetMarkupToAI() {
    setMarkup({ highlightSpans: aiSpans, underlineSpans: [], boldSpans: [], italicSpans: [] });
  }

  // Cut-style change re-cuts the passage and swaps the body + highlights in place.
  function handleStyleChange(style: "medium" | "high", result: EvidenceCutResult) {
    setActiveStyle(style);
    const body = result.cut_text_with_ellipses || result.cut_text || card.body_text || "";
    setCutBody(body);
    const newAi =
      (result.cut_body_spans && result.cut_body_spans.length
        ? result.cut_body_spans
        : result.selected_spans) ?? [];
    setAiSpans(newAi);
    setAiBoldSpans(result.cut_body_bold_spans ?? []);
    setCutWarnings(result.cut_warnings ?? []);
    setMarkup({ highlightSpans: newAi, underlineSpans: [], boldSpans: [], italicSpans: [] });
  }

  const previewCutText = cutBody;
  // Card built with the live (possibly re-cut) body so copy/download/save match.
  const liveCard: CardDraft = { ...card, cut_text_with_ellipses: cutBody };

  async function handleCopy(): Promise<void> {
    // Rich HTML (highlighted evidence) + plain-text fallback. Highlights follow
    // the user's current markup when present, else the AI read-aloud subset.
    const highlightSpans =
      markup.highlightSpans.length > 0 ? markup.highlightSpans : aiSpans;
    await copyCardRich(liveCard, highlightSpans);
  }

  function handleDownload() {
    downloadCardAsTxt(liveCard);
  }

  // Highlights shown = user markup (seeded from the AI subset). Bold merges
  // AI bold + user bold; underline/italic are user-only.
  const cardBodySpans = markup.highlightSpans.length > 0 ? markup.highlightSpans : aiSpans;
  const cardBodyBoldSpans = [...aiBoldSpans, ...markup.boldSpans];
  const cardBodyUnderlineSpans = markup.underlineSpans;
  const cardBodyItalicSpans = markup.italicSpans ?? [];

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
            <div className="flex items-center gap-2">
              {/* Readiness dot + label */}
              <div className="flex items-center gap-1.5">
                <div className={`w-1.5 h-1.5 rounded-full ${readinessDot}`} />
                <span className="text-[10px] text-gray-500">{readinessLabel}</span>
              </div>
              {/* Discard — polished icon button (replaces the raw ✕) */}
              <button
                onClick={() => onDiscard(card.id)}
                aria-label="Discard card"
                title="Discard card"
                className="inline-flex h-6 w-6 items-center justify-center rounded-md text-gray-300 transition-colors hover:bg-rose-50 hover:text-rose-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-200"
              >
                <Trash2 size={13} />
              </button>
            </div>
            <div className="flex items-center gap-1.5">
              {/* Quick save */}
              {card.status === "draft" && !card.is_counter_evidence && readiness === "ready" && (
                <button
                  onClick={() => onSave(card)}
                  className="text-[11px] px-2.5 py-1.5 rounded-lg border border-emerald-300 text-emerald-700 hover:bg-emerald-50 transition-colors font-medium"
                >
                  Save
                </button>
              )}
              {/* Open Studio — always opens modal, never inline expands */}
              <button
                onClick={() => onOpenStudio?.()}
                disabled={!onOpenStudio}
                className="text-[11px] px-3 py-1.5 rounded-lg bg-gray-900 text-white hover:bg-gray-700 transition-colors font-medium disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400"
              >
                Open Studio
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ── Expanded studio — card surface (left) + organized rail (right) ───────────
  function handleSaveWithMarkup(c: CardDraft) {
    // Merge ALL user markup into the card before saving so every formatting
    // edit (highlight/underline/bold/italic) is persisted. Highlight + underline
    // mirror into their dedicated columns; bold + italic ride in user_markup_json.
    const userMarkup = buildUserMarkupPayload(markup);
    onSave({
      ...c,
      cut_text_with_ellipses: cutBody,
      user_markup_json: userMarkup,
      highlighted_spans_json: [
        ...(c.highlighted_spans_json ?? []),
        ...markup.highlightSpans.filter(isUserSpan).map((s) => ({
          start: s.start, end: s.end, type: "highlight" as const, reason: "user",
        })),
      ],
      underline_spans_json: [
        ...(c.underline_spans_json ?? []),
        ...markup.underlineSpans.filter(isUserSpan).map((s) => ({
          start: s.start, end: s.end, type: "underline" as const, reason: "user",
        })),
      ],
    });
  }

  const isDraft = card.status === "draft" && !card.is_counter_evidence;
  const canSave = isDraft && readiness !== "weak";

  async function doCopy() {
    try {
      await handleCopy();
      setCopyState("copied");
      setTimeout(() => setCopyState("idle"), 1600);
    } catch {
      setCopyState("error");
      setTimeout(() => setCopyState("idle"), 2000);
    }
  }

  function doCopyMla() {
    if (!card.mla_citation) return;
    navigator.clipboard?.writeText(card.mla_citation);
    setMlaCopied(true);
    setTimeout(() => setMlaCopied(false), 1600);
  }

  // ── One-column document editor with a sticky top action bar ────────────────
  return (
    <div className={`min-w-0 w-full bg-white ${forceExpanded ? "" : `rounded-xl border-2 ${cardBorderClass(card)} shadow-sm`}`}>
      {/* Sticky action bar — stays visible while the document scrolls */}
      <div className="sticky top-0 z-20 flex items-center justify-between gap-3 border-b border-gray-100 bg-white/95 px-4 sm:px-6 py-2.5 backdrop-blur">
        <div className="flex items-center gap-3 min-w-0">
          <ReadinessPill readiness={readiness} />
          <CutStyleControls card={card} activeStyle={activeStyle} onStyleChange={handleStyleChange} />
        </div>
        <div className="flex items-center gap-1.5">
          {isDraft && (
            <button
              type="button"
              onClick={() => handleSaveWithMarkup(card)}
              disabled={!canSave}
              title={canSave ? "Save to library" : "Verify the source before saving"}
              className="inline-flex items-center gap-1.5 rounded-lg bg-gray-900 px-3 py-1.5 text-[12px] font-semibold text-white transition-colors hover:bg-gray-700 disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400"
            >
              <Save size={13} /> Save
            </button>
          )}
          <ActionIconButton
            icon={copyState === "copied" ? <Check size={15} /> : <Copy size={15} />}
            label={copyState === "copied" ? "Copied!" : "Copy card"}
            onClick={doCopy}
            active={copyState === "copied"}
          />
          <ActionIconButton icon={<Download size={15} />} label="Download .txt" onClick={handleDownload} />
          {showCopyMlaButton(card) && (
            <ActionIconButton
              icon={mlaCopied ? <Check size={15} /> : <Quote size={15} />}
              label={mlaCopied ? "MLA copied!" : "Copy MLA citation"}
              onClick={doCopyMla}
              active={mlaCopied}
            />
          )}
          {card.url && (
            <ActionIconButton icon={<ExternalLink size={15} />} label="Open source" href={card.url} />
          )}
          <ActionIconButton icon={<Trash2 size={15} />} label="Discard card" onClick={() => onDiscard(card.id)} tone="danger" />
          {onClose && (
            <>
              <span className="mx-0.5 h-5 w-px bg-gray-200" />
              <ActionIconButton icon={<X size={16} />} label="Close" onClick={onClose} />
            </>
          )}
        </div>
      </div>

      {/* Single-column document: Tag → MLA → Card → Analysis → Debate Prep */}
      <div className="mx-auto flex max-w-3xl flex-col gap-5 px-4 sm:px-6 py-5 sm:py-6 min-w-0">

        {card.is_counter_evidence && (
          <div className="rounded-lg border border-orange-200 bg-orange-50 px-3 py-2">
            <p className="text-[11px] text-orange-700">
              ⚡ Counter-evidence — use as a pre-empt, not support.
            </p>
          </div>
        )}

        {/* The debate card — selection capture happens directly on it (in place) */}
        <CardMarkupArea bodyText={previewCutText} markup={markup} onMarkupChange={setMarkup}>
          <DebateCardPreview
            tag={displayTag}
            shortCite={card.short_cite}
            containerTitle={card.citation?.container_title || card.citation?.publication_name}
            author={card.author || card.citation?.author_display}
            year={card.citation?.year || card.published_date}
            bodyText={previewCutText}
            spans={cardBodySpans ?? undefined}
            boldSpans={cardBodyBoldSpans}
            underlineSpans={cardBodyUnderlineSpans}
            italicSpans={cardBodyItalicSpans}
            mlacitation={card.mla_citation}
            claimGoal={card.best_supported_claim || claimGoal}
            isTagNarrowed={isTagNarrowed}
            sourceDomain={card.source_domain || (card.url ? hostnameOnly(card.url) : null)}
            onCopyMla={card.mla_citation ? doCopyMla : undefined}
          />
        </CardMarkupArea>

        {/* Markup reset/clear controls */}
        <CardMarkupToolbar
          markup={markup}
          onMarkupChange={setMarkup}
          onReset={resetMarkupToAI}
          aiHighlightSpans={aiSpans}
        />

        {cutWarnings.length > 0 && (
          <p className="text-[10px] text-amber-600/90 leading-snug">{cutWarnings[0]}</p>
        )}

        {/* RoundLab analysis (warrant + impact) directly under the card */}
        <CardAnalysis intelligence={card.intelligence} />

        {/* Debate prep, full-width below the analysis (not cramped in a rail) */}
        <DebatePrepPanel intelligence={card.intelligence} className="rounded-xl border border-gray-200 bg-white p-4 sm:p-5" />
      </div>
    </div>
  );
}
