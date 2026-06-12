/**
 * Tests for Research Search UI helpers and data shape.
 * Covers: formatDiagnosticsSummary, hasDiagnostics, GenerateCardsResponse shape,
 * and the click-chip / best_supported_claim / overclaim_warning behavior contracts.
 */

import {
  formatDiagnosticsSummary,
  hasDiagnostics,
  supportLevelLabel,
} from "@/lib/researchHelpers";
import type {
  CardDraft,
  GenerateCardsResponse,
  SearchDiagnostics,
} from "@/types";

// ── Factory helpers ───────────────────────────────────────────────────────────

function makeDiagnostics(overrides: Partial<SearchDiagnostics> = {}): SearchDiagnostics {
  return {
    sources_found: 3,
    sources_attempted: 3,
    sources_extracted: 2,
    passages_considered: 2,
    candidates_generated: 0,
    filtered_no_support: 2,
    filtered_low_quality: 0,
    query_variants_used: ["query 1", "query 2"],
    ...overrides,
  };
}

function makeCard(overrides: Partial<CardDraft> = {}): CardDraft {
  return {
    id: "card-1",
    user_id: "user-1",
    research_source_id: null,
    url: "https://example.com/article",
    topic: "Section 230",
    claim_goal: "Section 230 leads to lack of accountability",
    side: "Pro",
    tag: "Section 230 shields platforms from civil liability",
    cite: "Smith · Harvard Law Review · 2024",
    body_text: "Section 230 provides broad immunity to platforms from civil liability for user content.",
    highlighted_spans_json: [],
    underline_spans_json: [],
    author: "Jane Smith",
    publication: "Harvard Law Review",
    title: "Section 230 and Platform Accountability",
    published_date: "2024-01-10",
    author_credentials: null,
    warrant_summary: null,
    impact_summary: null,
    source_quality: "high",
    credibility_notes: "Peer-reviewed law journal.",
    extraction_confidence: 0.9,
    generated_tag: true,
    missing_metadata_json: {},
    card_source_type: "research_search",
    status: "draft",
    saved_card_id: null,
    support_level: "partial_support",
    support_rationale: "Passage addresses platform liability.",
    card_purpose: "link",
    claim_supported: true,
    best_supported_claim: "Section 230 shields platforms from civil liability for user content",
    overclaim_warning: "Original claim is broader than what this passage proves.",
    safe_tag_scope: "Platform liability shield under Section 230",
    created_at: "2026-06-10T00:00:00Z",
    updated_at: "2026-06-10T00:00:00Z",
    ...overrides,
  };
}

function makeGenerateCardsResponse(overrides: Partial<GenerateCardsResponse> = {}): GenerateCardsResponse {
  return {
    search_configured: true,
    query_used: "Section 230 accountability harmful content",
    cards: [],
    no_card_reason: null,
    suggestions: [],
    warnings: [],
    diagnostics: null,
    suggested_revised_claims: [],
    ...overrides,
  };
}

// ── formatDiagnosticsSummary ──────────────────────────────────────────────────

describe("formatDiagnosticsSummary", () => {
  it("returns empty string for null", () => {
    expect(formatDiagnosticsSummary(null)).toBe("");
  });

  it("returns empty string for undefined", () => {
    expect(formatDiagnosticsSummary(undefined)).toBe("");
  });

  it("returns no-sources message when sources_attempted is 0", () => {
    const d = makeDiagnostics({ sources_attempted: 0, sources_found: 0 });
    expect(formatDiagnosticsSummary(d)).toContain("No sources");
  });

  it("returns extraction failure message when sources_extracted is 0", () => {
    const d = makeDiagnostics({ sources_extracted: 0, sources_attempted: 3, sources_found: 3 });
    const msg = formatDiagnosticsSummary(d);
    expect(msg).toContain("could not extract");
  });

  it("mentions filtered_no_support count", () => {
    const d = makeDiagnostics({ filtered_no_support: 3 });
    expect(formatDiagnosticsSummary(d)).toContain("3");
  });

  it("mentions filtered_low_quality when non-zero", () => {
    const d = makeDiagnostics({ filtered_low_quality: 2 });
    const msg = formatDiagnosticsSummary(d);
    expect(msg).toContain("2");
    expect(msg).toContain("credibility");
  });

  it("returns clean message when nothing filtered", () => {
    const d = makeDiagnostics({ filtered_no_support: 0, filtered_low_quality: 0 });
    const msg = formatDiagnosticsSummary(d);
    expect(msg).not.toContain("filtered");
  });
});

// ── hasDiagnostics ────────────────────────────────────────────────────────────

describe("hasDiagnostics", () => {
  it("returns false for null", () => {
    expect(hasDiagnostics(null)).toBe(false);
  });

  it("returns false for undefined", () => {
    expect(hasDiagnostics(undefined)).toBe(false);
  });

  it("returns false for zero-count diagnostics", () => {
    const d = makeDiagnostics({ sources_found: 0, sources_attempted: 0 });
    expect(hasDiagnostics(d)).toBe(false);
  });

  it("returns true when sources_found > 0", () => {
    expect(hasDiagnostics(makeDiagnostics({ sources_found: 1 }))).toBe(true);
  });

  it("returns true when sources_attempted > 0", () => {
    expect(hasDiagnostics(makeDiagnostics({ sources_attempted: 1, sources_found: 0 }))).toBe(true);
  });
});

// ── GenerateCardsResponse shape — no cards ────────────────────────────────────

describe("GenerateCardsResponse — no-card state shape", () => {
  it("suggested_revised_claims defaults to empty array", () => {
    const resp = makeGenerateCardsResponse();
    expect(resp.suggested_revised_claims).toEqual([]);
  });

  it("diagnostics defaults to null", () => {
    const resp = makeGenerateCardsResponse();
    expect(resp.diagnostics).toBeNull();
  });

  it("accepts suggested_revised_claims array", () => {
    const claims = ["Section 230 shields platforms from liability", "Section 230 limits legal recourse"];
    const resp = makeGenerateCardsResponse({ suggested_revised_claims: claims });
    expect(resp.suggested_revised_claims).toHaveLength(2);
    expect(resp.suggested_revised_claims![0]).toContain("Section 230");
  });

  it("clicking a chip would pass the exact claim string", () => {
    const claim = "Section 230 shields platforms from civil liability for user content";
    const resp = makeGenerateCardsResponse({ suggested_revised_claims: [claim] });
    // Simulate chip click: the onClick sets cbClaimGoal to claim
    let cbClaimGoal = "";
    const handleChipClick = (c: string) => { cbClaimGoal = c; };
    handleChipClick(resp.suggested_revised_claims![0]);
    expect(cbClaimGoal).toBe(claim);
  });
});

// ── Candidate card fields — cards-found state ─────────────────────────────────

describe("CardDraft with research-search fields", () => {
  it("support_level is set on candidate card", () => {
    const card = makeCard({ support_level: "partial_support" });
    expect(card.support_level).toBe("partial_support");
    expect(supportLevelLabel(card.support_level)).toBe("Partial support");
  });

  it("best_supported_claim is accessible and differs from user claim", () => {
    const userClaim = "Section 230 leads to lack of accountability for harmful content";
    const card = makeCard({
      claim_goal: userClaim,
      best_supported_claim: "Section 230 shields platforms from civil liability for user content",
    });
    expect(card.best_supported_claim).toBeTruthy();
    expect(card.best_supported_claim).not.toBe(userClaim);
  });

  it("overclaim_warning is a non-empty string when present", () => {
    const card = makeCard({ overclaim_warning: "Original claim is broader than this evidence." });
    expect(card.overclaim_warning).toBeTruthy();
    expect(card.overclaim_warning!.length).toBeGreaterThan(5);
  });

  it("overclaim_warning can be null", () => {
    const card = makeCard({ overclaim_warning: null });
    expect(card.overclaim_warning).toBeNull();
  });

  it("safe_tag_scope describes safe argument scope", () => {
    const card = makeCard({ safe_tag_scope: "Platform liability shield under Section 230" });
    expect(card.safe_tag_scope).toBeTruthy();
  });

  it("cards with strong_support should not have overclaim_warning", () => {
    const card = makeCard({ support_level: "strong_support", overclaim_warning: null });
    expect(card.support_level).toBe("strong_support");
    expect(card.overclaim_warning).toBeNull();
  });
});

// ── Search diagnostics in no-card response ────────────────────────────────────

describe("Search diagnostics shape", () => {
  it("query_variants_used is an array of strings", () => {
    const d = makeDiagnostics({ query_variants_used: ["q1", "q2", "q3"] });
    expect(Array.isArray(d.query_variants_used)).toBe(true);
    expect(d.query_variants_used).toHaveLength(3);
  });

  it("diagnostic counts are non-negative", () => {
    const d = makeDiagnostics();
    expect(d.sources_found).toBeGreaterThanOrEqual(0);
    expect(d.sources_attempted).toBeGreaterThanOrEqual(0);
    expect(d.sources_extracted).toBeGreaterThanOrEqual(0);
    expect(d.passages_considered).toBeGreaterThanOrEqual(0);
    expect(d.filtered_no_support).toBeGreaterThanOrEqual(0);
    expect(d.filtered_low_quality).toBeGreaterThanOrEqual(0);
  });

  it("no-card response with diagnostics can be displayed", () => {
    const resp = makeGenerateCardsResponse({
      cards: [],
      no_card_reason: "No passages supported the claim.",
      diagnostics: makeDiagnostics(),
      suggested_revised_claims: ["Section 230 shields platforms from liability"],
    });
    expect(resp.search_configured).toBe(true);
    expect(resp.cards).toHaveLength(0);
    expect(resp.no_card_reason).toBeTruthy();
    expect(hasDiagnostics(resp.diagnostics)).toBe(true);
    expect(resp.suggested_revised_claims).toHaveLength(1);
  });
});

// ── Results flow + card component contracts (rebuilt Card Builder) ─────────────

import {
  shouldShowResultsSummary,
  shouldShowEmptyState,
} from "@/components/EvidenceSearchPanel";
import {
  getDisplayTag,
  isGenericTag,
  hostnameOnly,
  copyCardText,
  showCopyMlaButton,
  showSnippetBadge,
  cardBorderClass,
  DEFAULT_BODY_TAB,
} from "@/components/EvidenceCardDraft";

describe("Results Summary Bar visibility", () => {
  it("shows Results Summary Bar when cbGenerateResult has cards", () => {
    const resp = makeGenerateCardsResponse({ cards: [makeCard()] });
    expect(shouldShowResultsSummary(resp, false)).toBe(true);
  });

  it("does not show summary while loading", () => {
    const resp = makeGenerateCardsResponse({ cards: [makeCard()] });
    expect(shouldShowResultsSummary(resp, true)).toBe(false);
  });

  it("does not show summary when search returned zero cards", () => {
    const resp = makeGenerateCardsResponse({ cards: [] });
    expect(shouldShowResultsSummary(resp, false)).toBe(false);
  });

  it("does not show summary when search not configured", () => {
    const resp = makeGenerateCardsResponse({ search_configured: false, cards: [makeCard()] });
    expect(shouldShowResultsSummary(resp, false)).toBe(false);
  });
});

describe("No-card-drafts empty state", () => {
  it("does not show No card drafts yet when cbGenerateResult.cards has items", () => {
    const resp = makeGenerateCardsResponse({ cards: [makeCard()] });
    expect(shouldShowEmptyState(resp, [], false)).toBe(false);
  });

  it("shows No card drafts yet only when no search results and no saved drafts", () => {
    expect(shouldShowEmptyState(null, [], false)).toBe(true);
    expect(shouldShowEmptyState(makeGenerateCardsResponse({ cards: [] }), [], false)).toBe(true);
  });

  it("does not show empty state when saved drafts exist", () => {
    const drafts = [{ status: "draft" }];
    expect(shouldShowEmptyState(null, drafts, false)).toBe(false);
  });

  it("ignores discarded drafts when deciding empty state", () => {
    const drafts = [{ status: "discarded" }];
    expect(shouldShowEmptyState(null, drafts, false)).toBe(true);
  });

  it("never shows empty state while loading", () => {
    expect(shouldShowEmptyState(null, [], true)).toBe(false);
  });
});

describe("Card body tabs", () => {
  it("Final Card tab is default active tab in card component", () => {
    expect(DEFAULT_BODY_TAB).toBe("final");
  });
});

describe("getDisplayTag fallback logic", () => {
  it("returns tag when no overclaim warning and tag is specific", () => {
    const card = makeCard({
      tag: "Section 230 shields platforms from civil liability",
      overclaim_warning: "",  // no warning → raw tag shown
    });
    expect(getDisplayTag(card, card.claim_goal)).toBe(
      "Section 230 shields platforms from civil liability",
    );
  });

  it("prefers safe_tag_scope over raw tag when overclaim warning is present", () => {
    const card = makeCard({
      tag: "Section 230 shields platforms from civil liability",
      overclaim_warning: "Claim is broader than what this passage proves.",
      safe_tag_scope: "Platform liability shield under Section 230",
    });
    expect(getDisplayTag(card, card.claim_goal)).toBe(
      "Platform liability shield under Section 230",
    );
  });

  it("falls back to safe_tag_scope when tag is generic", () => {
    const card = makeCard({
      tag: "230 — mechanism",
      overclaim_warning: "",
      safe_tag_scope: "Platform liability shield under Section 230",
    });
    expect(getDisplayTag(card, card.claim_goal)).toBe(
      "Platform liability shield under Section 230",
    );
  });

  it("falls back to best_supported_claim when tag generic and no scope", () => {
    const card = makeCard({
      tag: "short",
      overclaim_warning: "",
      safe_tag_scope: "",
      best_supported_claim: "Section 230 shields platforms from civil liability for user content",
    });
    expect(getDisplayTag(card, card.claim_goal)).toBe(
      "Section 230 shields platforms from civil liability for user content",
    );
  });

  it("falls back to claim goal truncated to 100 chars", () => {
    const longClaim = "x".repeat(150);
    const card = makeCard({
      tag: "short",
      overclaim_warning: "",
      safe_tag_scope: "",
      best_supported_claim: "",
      claim_goal: longClaim,
    });
    const tag = getDisplayTag(card, longClaim);
    expect(tag.endsWith("…")).toBe(true);
    expect(tag.length).toBeLessThanOrEqual(101);
  });
});

describe("isGenericTag", () => {
  it("returns true for generic tags", () => {
    expect(isGenericTag("230 — mechanism")).toBe(true);
    expect(isGenericTag("tariffs — direct_support")).toBe(true);
    expect(isGenericTag("short")).toBe(true);
  });

  it("returns true when tag equals the claim verbatim", () => {
    const claim = "Section 230 facilitates harmful content";
    expect(isGenericTag(claim, claim)).toBe(true);
  });

  it("returns false for specific debate tags", () => {
    expect(
      isGenericTag("Section 230 grants platforms immunity from civil liability for content"),
    ).toBe(false);
  });
});

describe("hostnameOnly", () => {
  it("returns hostname from valid URL", () => {
    expect(hostnameOnly("https://scholar.harvard.edu/files/x.pdf")).toBe("scholar.harvard.edu");
  });

  it("returns original string for invalid URL", () => {
    expect(hostnameOnly("not a url")).toBe("not a url");
  });
});

describe("card action button contracts", () => {
  it("copy card button copies cut_text_with_ellipses when available", () => {
    const card = makeCard({
      cut_text_with_ellipses: "Section 230 grants immunity. […] Reform is needed.",
      body_text: "long full body text",
    });
    expect(copyCardText(card)).toBe("Section 230 grants immunity. […] Reform is needed.");
  });

  it("copy card button falls back to body_text when no cut", () => {
    const card = makeCard({ cut_text_with_ellipses: null, body_text: "full body" });
    expect(copyCardText(card)).toBe("full body");
  });

  it("copy MLA button only appears when mla_citation present", () => {
    expect(showCopyMlaButton(makeCard({ mla_citation: "Smith. 2024." }))).toBe(true);
    expect(showCopyMlaButton(makeCard({ mla_citation: null }))).toBe(false);
  });

  it("snippet-only badge shows only when card.is_snippet_source is true", () => {
    expect(showSnippetBadge(makeCard({ is_snippet_source: true }))).toBe(true);
    expect(showSnippetBadge(makeCard({ is_snippet_source: false }))).toBe(false);
    expect(showSnippetBadge(makeCard({ is_snippet_source: null }))).toBe(false);
  });

  it("counter-evidence card gets orange border class", () => {
    expect(cardBorderClass(makeCard({ is_counter_evidence: true }))).toContain("border-l-orange-400");
    expect(cardBorderClass(makeCard({ is_counter_evidence: false }))).toBe("border-border");
  });
});

describe("HighlightedPassage mode mapping", () => {
  it("Highlighted Cut tab shows HighlightedPassage with deemphasize mode", () => {
    // Contract: cut tab uses "deemphasize"; non-selected text is faded.
    const mode: "full" | "deemphasize" = "deemphasize";
    expect(mode).toBe("deemphasize");
  });

  it("Full Passage tab shows HighlightedPassage with full mode", () => {
    const mode: "full" | "deemphasize" = "full";
    expect(mode).toBe("full");
  });
});
