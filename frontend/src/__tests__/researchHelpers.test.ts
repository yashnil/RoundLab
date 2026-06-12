/**
 * Tests for researchHelpers.ts pure functions.
 * No DOM, no API calls — fully deterministic.
 */

import {
  sourceQualityLabel,
  sourceQualityColor,
  sourceQualityBadgeStyle,
  cardSourceTypeLabel,
  formatCardCite,
  hasMissingMetadata,
  canSaveCard,
  renderHighlightedBody,
  supportLevelLabel,
  supportLevelBadgeStyle,
  cardPurposeLabel,
} from "@/lib/researchHelpers";
import type { CardDraft, HighlightSpan } from "@/types";

// ── Factory ───────────────────────────────────────────────────────────────────

function makeDraft(overrides: Partial<CardDraft> = {}): CardDraft {
  return {
    id: "draft-1",
    user_id: "user-1",
    research_source_id: null,
    url: "https://example.com/article",
    topic: "US-China trade",
    claim_goal: "tariffs hurt growth",
    side: "Pro",
    tag: "IMF finds tariffs reduce economic growth by 3%",
    cite: "IMF · 2024",
    body_text: "The IMF finds that tariffs reduce economic growth significantly.",
    highlighted_spans_json: [],
    underline_spans_json: [],
    author: "Jane Smith",
    publication: "IMF",
    title: "Trade Report 2024",
    published_date: "2024-03-01",
    author_credentials: null,
    warrant_summary: "Proves economic harm",
    impact_summary: "GDP loss",
    source_quality: "high",
    credibility_notes: "Recognized high-credibility domain.",
    extraction_confidence: 0.85,
    generated_tag: true,
    missing_metadata_json: {},
    card_source_type: "url",
    status: "draft",
    saved_card_id: null,
    created_at: "2026-06-09T00:00:00Z",
    updated_at: "2026-06-09T00:00:00Z",
    ...overrides,
  };
}

// ── sourceQualityLabel ────────────────────────────────────────────────────────

describe("sourceQualityLabel", () => {
  it("returns label for high", () => {
    expect(sourceQualityLabel("high")).toBe("High credibility");
  });

  it("returns label for medium", () => {
    expect(sourceQualityLabel("medium")).toBe("Medium credibility");
  });

  it("returns label for low", () => {
    expect(sourceQualityLabel("low")).toBe("Low credibility");
  });

  it("returns label for unknown", () => {
    expect(sourceQualityLabel("unknown")).toBe("Unknown credibility");
  });

  it("returns unknown label for null", () => {
    expect(sourceQualityLabel(null)).toBe("Unknown credibility");
  });

  it("returns unknown label for undefined", () => {
    expect(sourceQualityLabel(undefined)).toBe("Unknown credibility");
  });
});

// ── sourceQualityColor ────────────────────────────────────────────────────────

describe("sourceQualityColor", () => {
  it("returns green for high", () => {
    expect(sourceQualityColor("high")).toContain("green");
  });

  it("returns amber for medium", () => {
    expect(sourceQualityColor("medium")).toContain("amber");
  });

  it("returns red for low", () => {
    expect(sourceQualityColor("low")).toContain("red");
  });

  it("returns muted for unknown", () => {
    expect(sourceQualityColor("unknown")).toContain("muted");
  });
});

// ── sourceQualityBadgeStyle ───────────────────────────────────────────────────

describe("sourceQualityBadgeStyle", () => {
  it("high badge has green colors", () => {
    const style = sourceQualityBadgeStyle("high");
    expect(style).toContain("green");
  });

  it("medium badge has amber colors", () => {
    const style = sourceQualityBadgeStyle("medium");
    expect(style).toContain("amber");
  });

  it("low badge has red colors", () => {
    const style = sourceQualityBadgeStyle("low");
    expect(style).toContain("red");
  });

  it("unknown badge uses surface colors", () => {
    const style = sourceQualityBadgeStyle("unknown");
    expect(style).toContain("surface");
  });
});

// ── cardSourceTypeLabel ───────────────────────────────────────────────────────

describe("cardSourceTypeLabel", () => {
  it("url returns correct label", () => {
    expect(cardSourceTypeLabel("url")).toBe("From URL");
  });

  it("manual_paste returns correct label", () => {
    expect(cardSourceTypeLabel("manual_paste")).toBe("Manually pasted");
  });

  it("research_search returns correct label", () => {
    expect(cardSourceTypeLabel("research_search")).toBe("Found via search");
  });

  it("null returns unknown label", () => {
    expect(cardSourceTypeLabel(null)).toBe("Unknown source");
  });
});

// ── formatCardCite ────────────────────────────────────────────────────────────

describe("formatCardCite", () => {
  it("formats full metadata", () => {
    const cite = formatCardCite({
      author: "Jane Smith",
      publication: "Nature",
      published_date: "2024-03-15",
      title: "Climate Effects",
      url: "https://nature.com/article",
    });
    expect(cite).toContain("Jane Smith");
    expect(cite).toContain("Nature");
    expect(cite).toContain("2024");
  });

  it("extracts year from full datetime", () => {
    const cite = formatCardCite({
      author: "Bob",
      publication: null,
      published_date: "2023-08-22T14:30:00Z",
      title: null,
      url: "https://example.com",
    });
    expect(cite).toContain("2023");
  });

  it("falls back to URL when no metadata", () => {
    const cite = formatCardCite({
      author: null,
      publication: null,
      published_date: null,
      title: null,
      url: "https://example.com/article",
    });
    expect(cite).toBe("https://example.com/article");
  });

  it("excludes title longer than 80 chars", () => {
    const longTitle = "A".repeat(81);
    const cite = formatCardCite({
      author: "Author",
      publication: "Journal",
      published_date: "2024",
      title: longTitle,
      url: "https://example.com",
    });
    expect(cite).not.toContain(longTitle);
  });

  it("uses · as separator", () => {
    const cite = formatCardCite({
      author: "Smith",
      publication: "Journal",
      published_date: "2024-01",
      title: null,
      url: "https://example.com",
    });
    expect(cite).toContain("·");
  });
});

// ── hasMissingMetadata ────────────────────────────────────────────────────────

describe("hasMissingMetadata", () => {
  it("returns empty array when nothing missing", () => {
    const result = hasMissingMetadata({ missing_metadata_json: {} });
    expect(result).toHaveLength(0);
  });

  it("returns messages for missing fields", () => {
    const result = hasMissingMetadata({
      missing_metadata_json: {
        author: "Author not found",
        date: "Publication date not found",
      },
    });
    expect(result).toHaveLength(2);
    expect(result).toContain("Author not found");
  });

  it("handles null missing_metadata_json", () => {
    const result = hasMissingMetadata({ missing_metadata_json: null as any });
    expect(result).toHaveLength(0);
  });
});

// ── canSaveCard ───────────────────────────────────────────────────────────────

describe("canSaveCard", () => {
  it("returns true for valid draft", () => {
    expect(canSaveCard(makeDraft())).toBe(true);
  });

  it("returns false for empty body_text", () => {
    expect(canSaveCard(makeDraft({ body_text: "" }))).toBe(false);
  });

  it("returns false for whitespace-only body", () => {
    expect(canSaveCard(makeDraft({ body_text: "   " }))).toBe(false);
  });

  it("returns false for empty tag", () => {
    expect(canSaveCard(makeDraft({ tag: "" }))).toBe(false);
  });

  it("returns false for saved status", () => {
    expect(canSaveCard(makeDraft({ status: "saved" }))).toBe(false);
  });

  it("returns false for discarded status", () => {
    expect(canSaveCard(makeDraft({ status: "discarded" }))).toBe(false);
  });

  it("returns false for very short body", () => {
    expect(canSaveCard(makeDraft({ body_text: "Short" }))).toBe(false);
  });
});

// ── renderHighlightedBody ─────────────────────────────────────────────────────

describe("renderHighlightedBody", () => {
  const body = "The IMF finds tariffs reduce economic growth significantly.";

  it("returns single plain segment with no spans", () => {
    const segs = renderHighlightedBody(body, []);
    expect(segs).toHaveLength(1);
    expect(segs[0].type).toBe("plain");
    expect(segs[0].text).toBe(body);
  });

  it("returns empty array for empty body", () => {
    expect(renderHighlightedBody("", [])).toHaveLength(0);
  });

  it("produces highlight segment for valid span", () => {
    const spans: HighlightSpan[] = [{ start: 4, end: 7, type: "highlight" }];
    const segs = renderHighlightedBody(body, spans);
    const highlighted = segs.find((s) => s.type === "highlight");
    expect(highlighted).toBeDefined();
    expect(highlighted!.text).toBe(body.slice(4, 7));
  });

  it("produces underline segment for underline type", () => {
    const spans: HighlightSpan[] = [{ start: 0, end: 7, type: "underline" }];
    const segs = renderHighlightedBody(body, spans);
    const underlined = segs.find((s) => s.type === "underline");
    expect(underlined).toBeDefined();
  });

  it("drops out-of-range spans silently", () => {
    const spans: HighlightSpan[] = [{ start: 999, end: 1100, type: "highlight" }];
    const segs = renderHighlightedBody(body, spans);
    expect(segs.every((s) => s.type === "plain")).toBe(true);
    expect(segs[0].text).toBe(body);
  });

  it("drops negative-start spans", () => {
    const spans: HighlightSpan[] = [{ start: -1, end: 5, type: "highlight" }];
    const segs = renderHighlightedBody(body, spans);
    expect(segs.every((s) => s.type === "plain")).toBe(true);
  });

  it("reconstructs text in order", () => {
    const spans: HighlightSpan[] = [{ start: 4, end: 7 }];
    const segs = renderHighlightedBody(body, spans);
    const reconstructed = segs.map((s) => s.text).join("");
    expect(reconstructed).toBe(body);
  });

  it("handles multiple non-overlapping spans", () => {
    const spans: HighlightSpan[] = [
      { start: 0, end: 3, type: "highlight" },
      { start: 10, end: 16, type: "underline" },
    ];
    const segs = renderHighlightedBody(body, spans);
    const reconstructed = segs.map((s) => s.text).join("");
    expect(reconstructed).toBe(body);
    expect(segs.some((s) => s.type === "highlight")).toBe(true);
    expect(segs.some((s) => s.type === "underline")).toBe(true);
  });

  it("drops overlapping span and keeps the first", () => {
    const spans: HighlightSpan[] = [
      { start: 0, end: 10, type: "highlight" },
      { start: 5, end: 15, type: "highlight" }, // overlaps
    ];
    const segs = renderHighlightedBody(body, spans);
    const highlighted = segs.filter((s) => s.type === "highlight");
    // Only one highlight should exist (overlapping span dropped)
    expect(highlighted).toHaveLength(1);
    expect(highlighted[0].text).toBe(body.slice(0, 10));
  });
});

// ── supportLevelLabel ─────────────────────────────────────────────────────────

describe("supportLevelLabel", () => {
  it("returns label for strong_support", () => {
    expect(supportLevelLabel("strong_support")).toBe("Strong support");
  });
  it("returns label for partial_support", () => {
    expect(supportLevelLabel("partial_support")).toBe("Partial support");
  });
  it("returns label for weak_support", () => {
    expect(supportLevelLabel("weak_support")).toBe("Weak support");
  });
  it("returns label for no_support", () => {
    expect(supportLevelLabel("no_support")).toBe("No support");
  });
  it("returns fallback for null", () => {
    expect(supportLevelLabel(null)).toBe("Support unknown");
  });
  it("returns fallback for undefined", () => {
    expect(supportLevelLabel(undefined)).toBe("Support unknown");
  });
});

// ── supportLevelBadgeStyle ────────────────────────────────────────────────────

describe("supportLevelBadgeStyle", () => {
  it("returns green for strong_support", () => {
    expect(supportLevelBadgeStyle("strong_support")).toContain("green");
  });
  it("returns amber for partial_support", () => {
    expect(supportLevelBadgeStyle("partial_support")).toContain("amber");
  });
  it("returns orange for weak_support", () => {
    expect(supportLevelBadgeStyle("weak_support")).toContain("orange");
  });
  it("returns red for no_support", () => {
    expect(supportLevelBadgeStyle("no_support")).toContain("red");
  });
  it("returns muted fallback for null", () => {
    const style = supportLevelBadgeStyle(null);
    expect(style).toBeTruthy();
    expect(style).not.toContain("green");
    expect(style).not.toContain("red");
  });
  it("returns different styles for strong vs weak", () => {
    expect(supportLevelBadgeStyle("strong_support")).not.toBe(supportLevelBadgeStyle("weak_support"));
  });
});

// ── cardPurposeLabel ──────────────────────────────────────────────────────────

describe("cardPurposeLabel", () => {
  const cases: Array<[string, string]> = [
    ["uniqueness", "Uniqueness"],
    ["link", "Link"],
    ["internal_link", "Internal link"],
    ["impact", "Impact"],
    ["answer", "Answer"],
    ["frontline", "Frontline"],
    ["weighing", "Weighing"],
    ["background", "Background"],
    ["solvency", "Solvency"],
    ["harm", "Harm"],
    ["unknown", "Evidence"],
  ];

  it.each(cases)("purpose %s → %s", (purpose, expected) => {
    expect(cardPurposeLabel(purpose as Parameters<typeof cardPurposeLabel>[0])).toBe(expected);
  });

  it("returns fallback for null", () => {
    expect(cardPurposeLabel(null)).toBe("Evidence");
  });

  it("returns fallback for undefined", () => {
    expect(cardPurposeLabel(undefined)).toBe("Evidence");
  });
});
