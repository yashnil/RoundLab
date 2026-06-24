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
import { CitationDetailsPanel } from "./CitationDetailsPanel";

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
    ? "border-warn/40 border-l-4 border-l-warn/60"
    : "border-hairline";
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
      <span className="text-[10px] text-ink-faint uppercase tracking-wide font-medium">Cut</span>
      <div
        className="inline-flex items-center rounded-lg border border-hairline bg-surface-2 p-0.5"
        role="radiogroup"
        aria-label="Cut density"
      >
        {styles.map(({ key, label, hint }) => (
          <button
            key={key}
            role="radio"
            aria-checked={activeStyle === key}
            title={hint}
            disabled={!!loading}
            onClick={() => handleStyleChange(key)}
            className={`px-3 py-1 rounded-md text-[11px] font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50 ${
              activeStyle === key
                ? "bg-ink text-canvas"
                : "text-ink-subtle hover:text-ink"
            }`}
          >
            {loading === key ? "…" : label}
          </button>
        ))}
      </div>
      <span className="text-[10px] text-ink-faint">
        {styles.find((s) => s.key === activeStyle)?.hint}
      </span>
    </div>
  );
}

// ── Sticky action-bar pieces ─────────────────────────────────────────────────

function ReadinessPill({ readiness }: { readiness: "ready" | "review_needed" | "weak" }) {
  const cfg = {
    ready: { label: "Ready to save", dot: "bg-ok", cls: "bg-ok/10 border-ok/30 text-ok" },
    review_needed: { label: "Review needed", dot: "bg-warn", cls: "bg-warn/10 border-warn/30 text-warn" },
    weak: { label: "Verify source", dot: "bg-danger", cls: "bg-danger/10 border-danger/30 text-danger" },
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
    ? "text-ok bg-ok/10"
    : tone === "danger"
      ? "text-ink-faint hover:text-danger hover:bg-danger/10"
      : "text-ink-subtle hover:text-ink hover:bg-surface-2";
  const cls = `inline-flex h-8 w-8 items-center justify-center rounded-lg transition-colors disabled:opacity-40 disabled:hover:bg-transparent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50 ${toneCls}`;
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
      readiness === "ready" ? "bg-ok" :
      readiness === "review_needed" ? "bg-warn" : "bg-danger";
    const readinessLabel =
      readiness === "ready" ? "Ready" :
      readiness === "review_needed" ? "Review needed" : "Verify source";

    // Short evidence preview (first ~120 chars of cut text)
    const evidencePreview = (card.cut_text_with_ellipses || card.body_text || "")
      .replace(/\n+/g, " ").trim().slice(0, 130);

    return (
      <div
        className={`min-w-0 w-full rounded-xl border bg-surface-1 hover:shadow-sm transition-shadow ${
          card.is_counter_evidence ? "border-l-4 border-l-warn/60 border-warn/30" : "border-hairline"
        }`}
      >
        <div className="flex items-stretch gap-0">
          {/* Left column: slot + tag + cite */}
          <div className="flex-1 min-w-0 px-4 py-3.5 flex flex-col gap-1">
            {/* Slot label as subtle text */}
            <div className="flex items-center gap-2">
              {card.slot_label && (
                <span className="text-[10px] text-ink-faint font-medium uppercase tracking-wide">
                  {card.slot_label}
                </span>
              )}
              {card.is_counter_evidence && (
                <span className="text-[10px] text-warn font-medium">⚡ Counter</span>
              )}
              {card.is_snippet_source && (
                <span className="text-[10px] text-warn">⚠ Snippet</span>
              )}
            </div>
            {/* Tag — clear and large */}
            <p
              className="text-[15px] font-semibold text-ink leading-snug break-words"
              style={{ fontFamily: 'Arial, "Helvetica Neue", Helvetica, sans-serif' }}
            >
              {displayTag}
            </p>
            {/* Cite line */}
            <p className="text-[12px] text-ink-subtle truncate"
               style={{ fontFamily: 'Arial, "Helvetica Neue", Helvetica, sans-serif' }}>
              {card.short_cite || card.citation?.short_cite || "No citation"}
              {(card.citation?.container_title || card.citation?.publication_name) && (
                <span className="text-ink-faint">
                  {" — "}{card.citation?.container_title || card.citation?.publication_name}
                </span>
              )}
            </p>
            {/* Evidence preview */}
            {evidencePreview && (
              <p className="text-[12px] text-ink-faint leading-relaxed line-clamp-2 mt-0.5"
                 style={{ fontFamily: 'Arial, "Helvetica Neue", Helvetica, sans-serif' }}>
                {evidencePreview}{evidencePreview.length >= 130 ? "…" : ""}
              </p>
            )}
          </div>

          {/* Right column: actions — stopPropagation prevents selection when clicking these */}
          <div className="flex flex-col items-end justify-between px-3 py-3 gap-2 shrink-0 border-l border-hairline">
            <div className="flex items-center gap-2">
              {/* Readiness dot + label */}
              <div className="flex items-center gap-1.5">
                <div className={`w-1.5 h-1.5 rounded-full ${readinessDot}`} aria-hidden="true" />
                <span className="text-[10px] text-ink-subtle">{readinessLabel}</span>
              </div>
              {/* Discard */}
              <button
                onClick={(e) => { e.stopPropagation(); onDiscard(card.id); }}
                aria-label="Discard card"
                title="Discard card"
                className="inline-flex h-6 w-6 items-center justify-center rounded-md text-ink-faint transition-colors hover:bg-danger/10 hover:text-danger focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-danger/30"
              >
                <Trash2 size={13} />
              </button>
            </div>
            <div className="flex items-center gap-1.5">
              {/* Quick save */}
              {card.status === "draft" && !card.is_counter_evidence && readiness === "ready" && (
                <button
                  onClick={(e) => { e.stopPropagation(); onSave(card); }}
                  className="text-[11px] px-2.5 py-1.5 rounded-lg border border-ok/40 text-ok hover:bg-ok/10 transition-colors font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ok/40"
                >
                  Save
                </button>
              )}
              {/* Open Studio — always opens modal, never inline expands */}
              <button
                onClick={(e) => { e.stopPropagation(); onOpenStudio?.(); }}
                disabled={!onOpenStudio}
                className="text-[11px] px-3 py-1.5 rounded-lg bg-ink text-canvas hover:bg-ink/80 transition-colors font-medium disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50"
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
    <div className={`min-w-0 w-full bg-surface-1 ${forceExpanded ? "" : `rounded-xl border-2 ${cardBorderClass(card)} shadow-sm`}`}>
      {/* Sticky action bar — stays visible while the document scrolls */}
      <div className="sticky top-0 z-20 flex items-center justify-between gap-3 border-b border-hairline bg-surface-1/95 px-4 sm:px-6 py-2.5 backdrop-blur">
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
              className="inline-flex items-center gap-1.5 rounded-lg bg-ink px-3 py-1.5 text-[12px] font-semibold text-canvas transition-colors hover:bg-ink/80 disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50"
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
              <span className="mx-0.5 h-5 w-px bg-hairline" aria-hidden="true" />
              <ActionIconButton icon={<X size={16} />} label="Close" onClick={onClose} />
            </>
          )}
        </div>
      </div>

      {/* Single-column document: Tag → MLA → Card → Analysis → Debate Prep */}
      <div className="mx-auto flex max-w-3xl flex-col gap-5 px-4 sm:px-6 py-5 sm:py-6 min-w-0">

        {card.is_counter_evidence && (
          <div className="rounded-lg border border-warn/30 bg-warn/10 px-3 py-2">
            <p className="text-[11px] text-warn">
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
          <p className="text-[10px] text-warn leading-snug" role="alert">{cutWarnings[0]}</p>
        )}

        {/* RoundLab analysis (warrant + impact) directly under the card */}
        <CardAnalysis intelligence={card.intelligence} />

        {/* Debate prep, full-width below the analysis (not cramped in a rail) */}
        <DebatePrepPanel intelligence={card.intelligence} className="rounded-xl border border-hairline bg-surface-1 p-4 sm:p-5" />

        {/* Structured citation details — collapsed by default; edits are citation-only */}
        {card.citation?.citation_record && (
          <CitationDetailsPanel
            record={card.citation.citation_record}
            legacyMla={card.mla_citation || card.citation?.mla_citation || undefined}
            defaultOpen={false}
            onFieldEdit={async (field, value) => {
              try {
                await apiFetch(`/research/card-drafts/${card.id}/citation-field`, {
                  method: "PATCH",
                  body: JSON.stringify({ user_id: card.user_id, field, value }),
                });
              } catch {
                /* non-fatal: citation edit will not surface outside the panel */
              }
            }}
          />
        )}
      </div>
    </div>
  );
}
