import {
  buildSavedCardMarkup,
  savedCardHasMarkup,
} from "@/components/evidence/SavedCardBody";
import type { EvidenceCard } from "@/types";

function card(over: Partial<EvidenceCard> = {}): EvidenceCard {
  return {
    id: "c1",
    document_id: "d1",
    user_id: "u1",
    chunk_id: null,
    tag: "Tag",
    author: null,
    source: null,
    year: null,
    card_text: "Section 230 grants platforms broad immunity to host content.",
    claim_summary: null,
    attribution_complete: true,
    metadata_json: {},
    created_at: "2026-06-12",
    ...over,
  };
}

describe("buildSavedCardMarkup", () => {
  it("reads highlight from user_markup metadata", () => {
    const m = buildSavedCardMarkup(card({
      card_cutting_metadata_json: {
        user_markup: {
          highlight: [{ start: 0, end: 11, type: "highlight" }],
          underline: [], bold: [], italic: [],
        },
      },
    }));
    expect(m.highlight).toHaveLength(1);
    expect(m.highlight[0]).toMatchObject({ start: 0, end: 11 });
  });

  it("reads underline from user_markup", () => {
    const m = buildSavedCardMarkup(card({
      card_cutting_metadata_json: {
        user_markup: { highlight: [], underline: [{ start: 0, end: 7, type: "underline" }], bold: [], italic: [] },
      },
    }));
    expect(m.underline).toHaveLength(1);
  });

  it("reads bold from user_markup", () => {
    const m = buildSavedCardMarkup(card({
      card_cutting_metadata_json: {
        user_markup: { highlight: [], underline: [], bold: [{ start: 0, end: 7, type: "bold" }], italic: [] },
      },
    }));
    expect(m.bold).toHaveLength(1);
  });

  it("reads italic from user_markup", () => {
    const m = buildSavedCardMarkup(card({
      card_cutting_metadata_json: {
        user_markup: { highlight: [], underline: [], bold: [], italic: [{ start: 0, end: 7, type: "italic" }] },
      },
    }));
    expect(m.italic).toHaveLength(1);
  });

  it("falls back to dedicated highlighted/underline columns", () => {
    const m = buildSavedCardMarkup(card({
      highlighted_spans_json: [{ start: 0, end: 11, type: "highlight" }],
      underline_spans_json: [{ start: 12, end: 18, type: "underline" }],
    }));
    expect(m.highlight).toHaveLength(1);
    expect(m.underline).toHaveLength(1);
  });

  it("does not crash with no markup", () => {
    const m = buildSavedCardMarkup(card());
    expect(savedCardHasMarkup(m)).toBe(false);
    expect(m.highlight).toEqual([]);
  });

  it("drops invalid spans (end <= start)", () => {
    const m = buildSavedCardMarkup(card({
      card_cutting_metadata_json: {
        user_markup: { highlight: [{ start: 5, end: 5, type: "highlight" }], underline: [], bold: [], italic: [] },
      },
    }));
    expect(m.highlight).toEqual([]);
  });
});

describe("savedCardHasMarkup", () => {
  it("true when any markup present", () => {
    expect(savedCardHasMarkup({ highlight: [{ start: 0, end: 1, text: "", sentence_index: 0 }], bold: [], underline: [], italic: [] })).toBe(true);
  });
  it("false when empty", () => {
    expect(savedCardHasMarkup({ highlight: [], bold: [], underline: [], italic: [] })).toBe(false);
  });
});
