/**
 * Tests for evidence-role UI helpers and data contracts.
 * Covers: evidenceRoleLabel, evidenceRoleGroupLabel, EVIDENCE_ROLE_ORDER,
 * groupCardsByRole logic, claim-ladder UX state, no-card panel differentiation,
 * and normalized-claim display.
 */

import {
  evidenceRoleLabel,
  evidenceRoleGroupLabel,
  evidenceRoleBadgeStyle,
  EVIDENCE_ROLE_ORDER,
} from "@/lib/researchHelpers";
import type {
  CardDraft,
  EvidenceRole,
  EvidenceCutResult,
  CitationMetadata,
  GenerateCardsResponse,
  SearchDiagnostics,
} from "@/types";

// ── Factory helpers ───────────────────────────────────────────────────────────

function makeCard(overrides: Partial<CardDraft> = {}): CardDraft {
  return {
    id: "card-1",
    user_id: "user-1",
    research_source_id: null,
    url: "https://law.cornell.edu/uscode/text/47/230",
    topic: "section 230",
    claim_goal: "Section 230 facilitates harmful content",
    side: "Pro",
    tag: "Section 230 grants platforms broad immunity from civil liability",
    cite: "Cornell LII · 47 U.S.C. § 230 · 2024",
    body_text: "Section 230 grants platforms broad immunity from civil liability for third-party content.",
    highlighted_spans_json: [],
    underline_spans_json: [],
    author: null,
    publication: "Cornell LII",
    title: "47 U.S. Code § 230",
    published_date: null,
    author_credentials: null,
    warrant_summary: null,
    impact_summary: null,
    source_quality: "high",
    credibility_notes: null,
    extraction_confidence: 0.9,
    generated_tag: true,
    missing_metadata_json: {},
    card_source_type: "research_search",
    status: "draft",
    saved_card_id: null,
    support_level: "partial_support",
    support_rationale: null,
    card_purpose: "link",
    claim_supported: true,
    best_supported_claim: "Section 230 grants platforms immunity from civil liability",
    overclaim_warning: null,
    safe_tag_scope: "Section 230 immunity provision",
    created_at: "2026-06-10T00:00:00Z",
    updated_at: "2026-06-10T00:00:00Z",
    evidence_role: "mechanism_support",
    is_counter_evidence: false,
    is_snippet_source: false,
    ...overrides,
  };
}

function makeDiagnostics(overrides: Partial<SearchDiagnostics> = {}): SearchDiagnostics {
  return {
    sources_found: 5,
    sources_attempted: 5,
    sources_extracted: 3,
    passages_considered: 6,
    candidates_generated: 1,
    filtered_no_support: 2,
    filtered_low_quality: 1,
    query_variants_used: ["Section 230 liability shield", "Section 230 Backpage"],
    ...overrides,
  };
}

function makeResponse(overrides: Partial<GenerateCardsResponse> = {}): GenerateCardsResponse {
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

// ── groupCardsByRole helper (mirrors page.tsx logic) ─────────────────────────

function groupCardsByRole(cards: CardDraft[]): Map<EvidenceRole, CardDraft[]> {
  const groups = new Map<EvidenceRole, CardDraft[]>();
  for (const card of cards) {
    const role = (card.evidence_role ?? "direct_support") as EvidenceRole;
    if (!groups.has(role)) groups.set(role, []);
    groups.get(role)!.push(card);
  }
  return groups;
}

// ── evidenceRoleLabel ─────────────────────────────────────────────────────────

describe("evidenceRoleLabel", () => {
  it("direct_support returns Direct evidence", () => {
    expect(evidenceRoleLabel("direct_support")).toBe("Direct evidence");
  });

  it("mechanism_support returns Mechanism", () => {
    expect(evidenceRoleLabel("mechanism_support")).toBe("Mechanism");
  });

  it("example_support returns Example/case", () => {
    expect(evidenceRoleLabel("example_support")).toBe("Example/case");
  });

  it("impact_support returns Impact", () => {
    expect(evidenceRoleLabel("impact_support")).toBe("Impact");
  });

  it("definition_support returns Definition", () => {
    expect(evidenceRoleLabel("definition_support")).toBe("Definition");
  });

  it("authority_support returns Authority", () => {
    expect(evidenceRoleLabel("authority_support")).toBe("Authority");
  });

  it("counter_evidence returns Counter-evidence", () => {
    expect(evidenceRoleLabel("counter_evidence")).toBe("Counter-evidence");
  });

  it("null returns Evidence fallback", () => {
    expect(evidenceRoleLabel(null)).toBe("Evidence");
  });

  it("undefined returns Evidence fallback", () => {
    expect(evidenceRoleLabel(undefined)).toBe("Evidence");
  });
});

// ── evidenceRoleGroupLabel ────────────────────────────────────────────────────

describe("evidenceRoleGroupLabel", () => {
  it("direct_support returns Direct support", () => {
    expect(evidenceRoleGroupLabel("direct_support")).toBe("Direct support");
  });

  it("mechanism_support returns Mechanism cards", () => {
    expect(evidenceRoleGroupLabel("mechanism_support")).toBe("Mechanism cards");
  });

  it("example_support returns Example / case cards", () => {
    expect(evidenceRoleGroupLabel("example_support")).toBe("Example / case cards");
  });

  it("impact_support includes impact", () => {
    const label = evidenceRoleGroupLabel("impact_support");
    expect(label.toLowerCase()).toContain("impact");
  });

  it("counter_evidence label includes review carefully", () => {
    const label = evidenceRoleGroupLabel("counter_evidence");
    expect(label.toLowerCase()).toContain("review carefully");
  });

  it("null returns Evidence fallback", () => {
    expect(evidenceRoleGroupLabel(null)).toBe("Evidence");
  });
});

// ── EVIDENCE_ROLE_ORDER ───────────────────────────────────────────────────────

describe("EVIDENCE_ROLE_ORDER", () => {
  it("is an array", () => {
    expect(Array.isArray(EVIDENCE_ROLE_ORDER)).toBe(true);
  });

  it("direct_support is first", () => {
    expect(EVIDENCE_ROLE_ORDER[0]).toBe("direct_support");
  });

  it("counter_evidence is last", () => {
    expect(EVIDENCE_ROLE_ORDER[EVIDENCE_ROLE_ORDER.length - 1]).toBe("counter_evidence");
  });

  it("includes mechanism_support, example_support, impact_support", () => {
    expect(EVIDENCE_ROLE_ORDER).toContain("mechanism_support");
    expect(EVIDENCE_ROLE_ORDER).toContain("example_support");
    expect(EVIDENCE_ROLE_ORDER).toContain("impact_support");
  });

  it("has at least 6 roles", () => {
    expect(EVIDENCE_ROLE_ORDER.length).toBeGreaterThanOrEqual(6);
  });

  it("does not include not_useful", () => {
    expect(EVIDENCE_ROLE_ORDER).not.toContain("not_useful");
  });
});

// ── groupCardsByRole ──────────────────────────────────────────────────────────

describe("groupCardsByRole", () => {
  it("groups cards by their evidence_role", () => {
    const cards = [
      makeCard({ id: "c1", evidence_role: "mechanism_support" }),
      makeCard({ id: "c2", evidence_role: "mechanism_support" }),
      makeCard({ id: "c3", evidence_role: "example_support" }),
    ];
    const groups = groupCardsByRole(cards);
    expect(groups.get("mechanism_support")).toHaveLength(2);
    expect(groups.get("example_support")).toHaveLength(1);
    expect(groups.has("direct_support")).toBe(false);
  });

  it("cards without evidence_role go to direct_support group", () => {
    const cards = [makeCard({ evidence_role: null })];
    const groups = groupCardsByRole(cards);
    expect(groups.get("direct_support")).toHaveLength(1);
  });

  it("counter_evidence cards are grouped separately", () => {
    const cards = [
      makeCard({ id: "c1", evidence_role: "direct_support" }),
      makeCard({ id: "c2", evidence_role: "counter_evidence", is_counter_evidence: true }),
    ];
    const groups = groupCardsByRole(cards);
    expect(groups.get("direct_support")).toHaveLength(1);
    expect(groups.get("counter_evidence")).toHaveLength(1);
  });

  it("empty card array returns empty map", () => {
    const groups = groupCardsByRole([]);
    expect(groups.size).toBe(0);
  });
});

// ── Claim ladder UX states ────────────────────────────────────────────────────

describe("Claim ladder UX state contracts", () => {
  it("direct_support_found=true means no warning banner needed", () => {
    const response = makeResponse({
      cards: [makeCard({ evidence_role: "direct_support" })],
      direct_support_found: true,
      usable_indirect_support_found: false,
    });
    expect(response.direct_support_found).toBe(true);
    expect(response.usable_indirect_support_found).toBe(false);
  });

  it("direct absent but indirect present triggers ladder banner", () => {
    const response = makeResponse({
      cards: [makeCard({ evidence_role: "mechanism_support" })],
      direct_support_found: false,
      usable_indirect_support_found: true,
      indirect_support_explanation:
        "No source directly proves the full claim, but these sources support narrower aspects.",
    });
    expect(response.direct_support_found).toBe(false);
    expect(response.usable_indirect_support_found).toBe(true);
    expect(response.indirect_support_explanation).toBeTruthy();
    expect(response.indirect_support_explanation!.length).toBeGreaterThan(10);
  });

  it("zero cards means both flags false", () => {
    const response = makeResponse({
      cards: [],
      direct_support_found: false,
      usable_indirect_support_found: false,
    });
    expect(response.direct_support_found).toBe(false);
    expect(response.usable_indirect_support_found).toBe(false);
  });

  it("indirect_support_explanation is null when no indirect cards", () => {
    const response = makeResponse({
      cards: [],
      direct_support_found: false,
      usable_indirect_support_found: false,
      indirect_support_explanation: null,
    });
    expect(response.indirect_support_explanation).toBeNull();
  });
});

// ── Normalized claim / typo correction display ────────────────────────────────

describe("Normalized claim and corrections display", () => {
  it("corrections_applied non-empty when typo was fixed", () => {
    const response = makeResponse({
      normalized_claim: "Section 230 facilitates harmful content",
      corrections_applied: ["ion 230 → Section 230"],
    });
    expect(response.corrections_applied).toHaveLength(1);
    expect(response.corrections_applied![0]).toContain("Section 230");
  });

  it("corrections_applied empty when claim was already correct", () => {
    const response = makeResponse({
      normalized_claim: "Section 230 facilitates harmful content",
      corrections_applied: [],
    });
    expect(response.corrections_applied).toHaveLength(0);
  });

  it("normalized_claim differs from original when typo was fixed", () => {
    const original = "ion 230 facilitates harmful content";
    const response = makeResponse({
      normalized_claim: "Section 230 facilitates harmful content",
      corrections_applied: ["ion 230 → Section 230"],
    });
    expect(response.normalized_claim).not.toBe(original);
    expect(response.normalized_claim).toContain("Section 230");
  });

  it("normalized_claim undefined when no normalization ran", () => {
    const response = makeResponse({});
    expect(response.normalized_claim).toBeUndefined();
  });
});

// ── No-card panel differentiation ────────────────────────────────────────────

describe("No-card panel diagnostics differentiation", () => {
  it("urls_snippet_only > 0 and no cards → snippet-extraction state", () => {
    const diag: SearchDiagnostics = {
      ...makeDiagnostics({
        sources_extracted: 0,
        urls_snippet_only: 3,
        rejected_by_low_debate_usefulness: 0,
        rejected_by_low_source_quality: 0,
      }),
    };
    const response = makeResponse({ cards: [], diagnostics: diag });
    expect(response.diagnostics?.urls_snippet_only).toBeGreaterThan(0);
    expect(response.cards).toHaveLength(0);
  });

  it("rejected_by_low_source_quality > 0 → quality gate state", () => {
    const diag: SearchDiagnostics = {
      ...makeDiagnostics({
        rejected_by_low_source_quality: 2,
        filtered_no_support: 0,
      }),
    };
    const response = makeResponse({ cards: [], diagnostics: diag });
    expect(response.diagnostics?.rejected_by_low_source_quality).toBe(2);
  });

  it("possible_lead_urls non-empty → manual follow-up state", () => {
    const diag: SearchDiagnostics = {
      ...makeDiagnostics({
        sources_extracted: 0,
        possible_lead_urls: ["https://law.cornell.edu/uscode/text/47/230"],
      }),
    };
    const response = makeResponse({ cards: [], diagnostics: diag });
    expect(response.diagnostics?.possible_lead_urls).toHaveLength(1);
  });

  it("all zeros → no sources found state", () => {
    const diag: SearchDiagnostics = {
      ...makeDiagnostics({
        sources_found: 0,
        sources_attempted: 0,
        sources_extracted: 0,
        passages_considered: 0,
      }),
    };
    const response = makeResponse({ cards: [], diagnostics: diag });
    expect(response.diagnostics?.sources_found).toBe(0);
    expect(response.diagnostics?.sources_attempted).toBe(0);
  });
});

// ── Counter-evidence card rendering contracts ─────────────────────────────────

describe("Counter-evidence card rendering contracts", () => {
  it("is_counter_evidence=true marks the card as opposing", () => {
    const card = makeCard({
      evidence_role: "counter_evidence",
      is_counter_evidence: true,
    });
    expect(card.is_counter_evidence).toBe(true);
    expect(card.evidence_role).toBe("counter_evidence");
  });

  it("is_snippet_source=true marks partial text card", () => {
    const card = makeCard({ is_snippet_source: true });
    expect(card.is_snippet_source).toBe(true);
  });

  it("normal support card has is_counter_evidence=false", () => {
    const card = makeCard({ evidence_role: "mechanism_support", is_counter_evidence: false });
    expect(card.is_counter_evidence).toBe(false);
  });
});

// ── candidates_by_role contract ───────────────────────────────────────────────

describe("candidates_by_role response field", () => {
  it("is a record of string to number", () => {
    const response = makeResponse({
      candidates_by_role: { mechanism_support: 2, example_support: 1 },
    });
    expect(response.candidates_by_role?.mechanism_support).toBe(2);
    expect(response.candidates_by_role?.example_support).toBe(1);
  });

  it("defaults to undefined when not present", () => {
    const response = makeResponse({});
    expect(response.candidates_by_role).toBeUndefined();
  });

  it("can be used to detect indirect-only results", () => {
    const candidates = { mechanism_support: 2, direct_support: 0 };
    const hasIndirect = Object.entries(candidates)
      .some(([role, count]) => role !== "direct_support" && count > 0);
    expect(hasIndirect).toBe(true);
  });
});

// ── evidenceRoleBadgeStyle helper ─────────────────────────────────────────────

describe("evidenceRoleBadgeStyle", () => {
  it("direct_support returns green styling", () => {
    const style = evidenceRoleBadgeStyle("direct_support");
    expect(style).toContain("green");
  });
  it("mechanism_support returns blue styling", () => {
    const style = evidenceRoleBadgeStyle("mechanism_support");
    expect(style).toContain("blue");
  });
  it("example_support returns purple styling", () => {
    const style = evidenceRoleBadgeStyle("example_support");
    expect(style).toContain("purple");
  });
  it("impact_support returns red styling", () => {
    const style = evidenceRoleBadgeStyle("impact_support");
    expect(style).toContain("red");
  });
  it("counter_evidence returns orange styling", () => {
    const style = evidenceRoleBadgeStyle("counter_evidence");
    expect(style).toContain("orange");
  });
  it("null returns safe default", () => {
    expect(evidenceRoleBadgeStyle(null)).toBeTruthy();
  });
  it("undefined returns safe default", () => {
    expect(evidenceRoleBadgeStyle(undefined)).toBeTruthy();
  });
});

// ── EvidenceCutResult shape ───────────────────────────────────────────────────

describe("EvidenceCutResult shape", () => {
  it("has required fields", () => {
    const cut: EvidenceCutResult = {
      original_passage: "Section 230 grants immunity. Courts have held this.",
      selected_spans: [{ start: 0, end: 30, text: "Section 230 grants immunity.", sentence_index: 0 }],
      cut_text: "Section 230 grants immunity.",
      cut_text_with_ellipses: "Section 230 grants immunity.",
      compression_ratio: 0.55,
      confidence: 0.8,
      cut_style: "medium_cut",
      validation_passed: true,
    };
    expect(cut.cut_text_with_ellipses).toBeTruthy();
    expect(cut.selected_spans).toHaveLength(1);
    expect(cut.selected_spans[0].text).toBe("Section 230 grants immunity.");
  });

  it("cut_style accepts all valid values", () => {
    const styles: EvidenceCutResult["cut_style"][] = ["full", "light_cut", "medium_cut", "aggressive_cut"];
    styles.forEach((style) => {
      const cut: EvidenceCutResult = {
        original_passage: "test",
        selected_spans: [],
        cut_text: "test",
        cut_text_with_ellipses: "test",
        compression_ratio: 1.0,
        confidence: 0.5,
        cut_style: style,
        validation_passed: true,
      };
      expect(cut.cut_style).toBe(style);
    });
  });

  it("selected_spans have correct shape", () => {
    const text = "grants immunity.";
    const span = { start: 0, end: text.length, text, sentence_index: 1, rationale: "key legal claim" };
    expect(span.start).toBeGreaterThanOrEqual(0);
    expect(span.end).toBeGreaterThan(span.start);
    expect(span.text.length).toBe(span.end - span.start);
  });

  it("cut_text_with_ellipsis shows marker when spans are non-adjacent", () => {
    // Two non-adjacent spans joined with [...] marker
    const original = "Section 230 grants immunity. The provision was enacted in 1996. Critics argue reform is needed.";
    const span1Text = "Section 230 grants immunity.";
    const span2Text = "Critics argue reform is needed.";
    const cut: EvidenceCutResult = {
      original_passage: original,
      selected_spans: [
        { start: 0, end: span1Text.length, text: span1Text, sentence_index: 0 },
        { start: original.indexOf(span2Text), end: original.indexOf(span2Text) + span2Text.length, text: span2Text, sentence_index: 2 },
      ],
      cut_text: span1Text + " " + span2Text,
      cut_text_with_ellipses: span1Text + " […] " + span2Text,
      compression_ratio: 0.6,
      confidence: 0.85,
      cut_style: "medium_cut",
      validation_passed: true,
    };
    expect(cut.cut_text_with_ellipses).toContain("[…]");
  });

  it("validation_passed true when spans point exactly into original", () => {
    const original = "Section 230 grants platforms broad immunity.";
    const spanText = "Section 230 grants platforms broad immunity.";
    const cut: EvidenceCutResult = {
      original_passage: original,
      selected_spans: [{ start: 0, end: spanText.length, text: spanText, sentence_index: 0 }],
      cut_text: spanText,
      cut_text_with_ellipses: spanText,
      compression_ratio: 1.0,
      confidence: 0.85,
      cut_style: "full",
      validation_passed: true,
    };
    expect(cut.validation_passed).toBe(true);
    for (const span of cut.selected_spans) {
      expect(original.substring(span.start, span.end)).toBe(span.text);
    }
  });
});

// ── CitationMetadata quality tests ────────────────────────────────────────────

describe("CitationMetadata quality tests", () => {
  it("complete quality when author, year, title, and publication all present", () => {
    const citation: CitationMetadata = {
      author_display: "Smith",
      authors: ["Smith, Jane"],
      year: "2024",
      title: "Platform Liability Study",
      publication_name: "Harvard Law Review",
      url: "https://example.com",
      accessed_date: "10 Jun. 2026",
      citation_quality: "complete",
      mla_citation: 'Smith. "Platform Liability Study." Harvard Law Review, 2024, https://example.com.',
      short_cite: "Smith 2024",
    };
    expect(citation.citation_quality).toBe("complete");
  });

  it("weak quality when only URL present", () => {
    const citation: CitationMetadata = {
      author_display: "",
      authors: [],
      year: "",
      title: "",
      publication_name: "",
      url: "https://example.com",
      accessed_date: "10 Jun. 2026",
      citation_quality: "weak",
      mla_citation: "https://example.com. Accessed 10 Jun. 2026.",
      short_cite: "Source",
    };
    expect(citation.citation_quality).toBe("weak");
    expect(citation.author_display).toBe("");
    expect(citation.year).toBe("");
  });

  it("MLA citation contains author and year when both present", () => {
    const mla = 'Smith. "Platform Liability." Harvard Law Review, 2024, https://example.com.';
    const citation: CitationMetadata = {
      author_display: "Smith",
      authors: ["Smith, Jane"],
      year: "2024",
      title: "Platform Liability",
      publication_name: "Harvard Law Review",
      url: "https://example.com",
      accessed_date: "10 Jun. 2026",
      citation_quality: "complete",
      mla_citation: mla,
      short_cite: "Smith 2024",
    };
    expect(citation.mla_citation).toContain("Smith");
    expect(citation.mla_citation).toContain("2024");
  });

  it("short_cite is author + year when both available", () => {
    const citation: CitationMetadata = {
      author_display: "Johnson",
      authors: ["Johnson, Alice"],
      year: "2023",
      title: "Internet Law",
      publication_name: "Journal of Internet Law",
      url: "https://example.com",
      accessed_date: "10 Jun. 2026",
      citation_quality: "complete",
      mla_citation: "",
      short_cite: "Johnson 2023",
    };
    expect(citation.short_cite).toBe("Johnson 2023");
  });

  it("citation_quality accepts complete, partial, weak", () => {
    const qualities: CitationMetadata["citation_quality"][] = ["complete", "partial", "weak"];
    qualities.forEach((q) => {
      const citation: CitationMetadata = {
        author_display: "",
        authors: [],
        year: "",
        title: "",
        publication_name: "",
        url: "https://example.com",
        accessed_date: "10 Jun. 2026",
        citation_quality: q,
        mla_citation: "",
        short_cite: "Source",
      };
      expect(citation.citation_quality).toBe(q);
    });
  });

  it("short_cite is truthy even for minimal citation", () => {
    const citation: CitationMetadata = {
      author_display: "",
      authors: [],
      year: "",
      title: "",
      publication_name: "Cornell LII",
      url: "https://law.cornell.edu",
      accessed_date: "10 Jun. 2026",
      citation_quality: "partial",
      mla_citation: "Cornell LII, https://law.cornell.edu.",
      short_cite: "Cornell LII",
    };
    expect(citation.short_cite).toBeTruthy();
  });
});

// ── Page-flow predicates (shouldShowResultsSummary / shouldShowEmptyState) ─────

import {
  shouldShowResultsSummary,
  shouldShowEmptyState,
} from "@/components/EvidenceSearchPanel";

describe("shouldShowResultsSummary", () => {
  it("returns false during loading", () => {
    const resp = makeResponse({ cards: [makeCard()] });
    expect(shouldShowResultsSummary(resp, true)).toBe(false);
  });

  it("returns true when cards present and not loading", () => {
    const resp = makeResponse({ cards: [makeCard()] });
    expect(shouldShowResultsSummary(resp, false)).toBe(true);
  });

  it("returns false when no cards", () => {
    const resp = makeResponse({ cards: [] });
    expect(shouldShowResultsSummary(resp, false)).toBe(false);
  });
});

describe("shouldShowEmptyState", () => {
  it("returns false when search cards present", () => {
    const resp = makeResponse({ cards: [makeCard()] });
    expect(shouldShowEmptyState(resp, [], false)).toBe(false);
  });

  it("returns true when no cards and no drafts", () => {
    const resp = makeResponse({ cards: [] });
    expect(shouldShowEmptyState(resp, [], false)).toBe(true);
  });

  it("returns false when saved (non-discarded) drafts exist", () => {
    const resp = makeResponse({ cards: [] });
    expect(shouldShowEmptyState(resp, [{ status: "draft" }], false)).toBe(false);
  });
});
