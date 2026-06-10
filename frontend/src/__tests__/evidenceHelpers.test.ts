import {
  getSimilarityLabel,
  getSimilarityPct,
  getSearchModeDisplay,
  getSearchModeHelperText,
  getRetrievalModeLabel,
  isSemanticRetrievalAvailable,
  getSupportLevelDisplay,
  truncateSnippet,
  anySemanticResults,
} from "@/lib/evidenceHelpers";

// ── getSimilarityLabel ─────────────────────────────────────────────────────────

describe("getSimilarityLabel", () => {
  it("returns Strong match for similarity >= 0.70", () => {
    expect(getSimilarityLabel(0.70).label).toBe("Strong match");
    expect(getSimilarityLabel(0.85).label).toBe("Strong match");
    expect(getSimilarityLabel(1.00).label).toBe("Strong match");
  });

  it("marks strong matches as isStrong", () => {
    expect(getSimilarityLabel(0.80).isStrong).toBe(true);
    expect(getSimilarityLabel(0.50).isStrong).toBe(false);
  });

  it("returns Possible match for 0.45 to 0.69", () => {
    expect(getSimilarityLabel(0.50).label).toBe("Possible match");
    expect(getSimilarityLabel(0.45).label).toBe("Possible match");
    expect(getSimilarityLabel(0.69).label).toBe("Possible match");
  });

  it("returns Weak match for similarity below 0.45", () => {
    expect(getSimilarityLabel(0.30).label).toBe("Weak match");
    expect(getSimilarityLabel(0.00).label).toBe("Weak match");
  });

  it("returns No match for null", () => {
    expect(getSimilarityLabel(null).label).toBe("No match");
  });

  it("returns No match for undefined", () => {
    expect(getSimilarityLabel(undefined).label).toBe("No match");
  });

  it("strong match uses ok color class", () => {
    expect(getSimilarityLabel(0.80).colorClass).toContain("ok");
  });

  it("possible match uses warn color class", () => {
    expect(getSimilarityLabel(0.55).colorClass).toContain("warn");
  });

  it("weak match uses danger color class", () => {
    expect(getSimilarityLabel(0.20).colorClass).toContain("danger");
  });
});

// ── getSimilarityPct ───────────────────────────────────────────────────────────

describe("getSimilarityPct", () => {
  it("converts 0.75 to 75%", () => {
    expect(getSimilarityPct(0.75)).toBe("75%");
  });

  it("rounds 0.846 to 85%", () => {
    expect(getSimilarityPct(0.846)).toBe("85%");
  });

  it("returns dash for null", () => {
    expect(getSimilarityPct(null)).toBe("—");
  });

  it("returns dash for undefined", () => {
    expect(getSimilarityPct(undefined)).toBe("—");
  });
});

// ── getSearchModeDisplay ───────────────────────────────────────────────────────

describe("getSearchModeDisplay", () => {
  it("returns label for keyword mode", () => {
    const d = getSearchModeDisplay("keyword");
    expect(d.label).toBe("Keyword");
  });

  it("returns label for semantic mode", () => {
    const d = getSearchModeDisplay("semantic");
    expect(d.label).toBe("Semantic");
  });

  it("returns label for hybrid mode", () => {
    const d = getSearchModeDisplay("hybrid");
    expect(d.label).toBe("Hybrid");
  });

  it("each mode has a non-empty description", () => {
    for (const mode of ["keyword", "semantic", "hybrid"] as const) {
      expect(getSearchModeDisplay(mode).description.length).toBeGreaterThan(0);
    }
  });
});

// ── getSearchModeHelperText ────────────────────────────────────────────────────

describe("getSearchModeHelperText", () => {
  it("semantic mode mentions AI or embeddings", () => {
    const text = getSearchModeHelperText("semantic").toLowerCase();
    expect(text.includes("embedding") || text.includes("ai")).toBe(true);
  });

  it("hybrid mode mentions semantic", () => {
    const text = getSearchModeHelperText("hybrid").toLowerCase();
    expect(text).toContain("semantic");
  });

  it("keyword mode does not mention embeddings", () => {
    const text = getSearchModeHelperText("keyword").toLowerCase();
    expect(text).not.toContain("embedding");
  });
});

// ── getRetrievalModeLabel ──────────────────────────────────────────────────────

describe("getRetrievalModeLabel", () => {
  it("returns Semantic retrieval for semantic mode", () => {
    expect(getRetrievalModeLabel("semantic")).toBe("Semantic retrieval");
  });

  it("returns keyword label for keyword mode", () => {
    const label = getRetrievalModeLabel("keyword");
    expect(label.toLowerCase()).toContain("keyword");
  });

  it("returns empty string for null", () => {
    expect(getRetrievalModeLabel(null)).toBe("");
  });

  it("returns empty string for undefined", () => {
    expect(getRetrievalModeLabel(undefined)).toBe("");
  });
});

// ── isSemanticRetrievalAvailable ───────────────────────────────────────────────

describe("isSemanticRetrievalAvailable", () => {
  it("returns true for semantic mode", () => {
    expect(isSemanticRetrievalAvailable("semantic")).toBe(true);
  });

  it("returns false for keyword mode", () => {
    expect(isSemanticRetrievalAvailable("keyword")).toBe(false);
  });

  it("returns false for none mode", () => {
    expect(isSemanticRetrievalAvailable("none")).toBe(false);
  });

  it("returns false for null", () => {
    expect(isSemanticRetrievalAvailable(null)).toBe(false);
  });
});

// ── getSupportLevelDisplay ─────────────────────────────────────────────────────

describe("getSupportLevelDisplay", () => {
  it("returns correct label for supported", () => {
    expect(getSupportLevelDisplay("supported").label).toBe("Supported");
  });

  it("returns correct label for partially_supported", () => {
    expect(getSupportLevelDisplay("partially_supported").label).toBe("Partially Supported");
  });

  it("returns correct label for unsupported", () => {
    expect(getSupportLevelDisplay("unsupported").label).toBe("Not Supported");
  });

  it("returns correct label for unverifiable", () => {
    expect(getSupportLevelDisplay("unverifiable").label).toBe("No Match Found");
  });

  it("returns unverifiable for null", () => {
    expect(getSupportLevelDisplay(null).label).toBe("No Match Found");
  });

  it("all non-supported levels have a suggested fix", () => {
    for (const level of ["partially_supported", "unsupported", "unverifiable"] as const) {
      expect(getSupportLevelDisplay(level).suggestedFix.length).toBeGreaterThan(0);
    }
  });

  it("supported level has empty suggested fix", () => {
    expect(getSupportLevelDisplay("supported").suggestedFix).toBe("");
  });
});

// ── truncateSnippet ────────────────────────────────────────────────────────────

describe("truncateSnippet", () => {
  it("returns short text unchanged", () => {
    const text = "short text";
    expect(truncateSnippet(text)).toBe(text);
  });

  it("appends ellipsis for long text", () => {
    const long = "word ".repeat(60);
    const result = truncateSnippet(long, 50);
    expect(result.endsWith("…")).toBe(true);
  });

  it("truncates at a word boundary", () => {
    const text = "the quick brown fox jumps over the lazy dog and more text continues here beyond limit";
    const result = truncateSnippet(text, 30);
    expect(result.endsWith("…")).toBe(true);
    // The character in the original string right after the truncated portion should be a space
    const truncated = result.slice(0, -1);
    const nextChar = text.charAt(truncated.length);
    expect(nextChar === " " || truncated.length >= text.length).toBe(true);
  });

  it("respects custom maxChars", () => {
    const text = "a".repeat(100);
    const result = truncateSnippet(text, 50);
    expect(result.length).toBeLessThanOrEqual(53); // 50 chars + "…"
  });
});

// ── anySemanticResults ─────────────────────────────────────────────────────────

describe("anySemanticResults", () => {
  it("returns true when any result has a similarity score", () => {
    const results = [
      { similarity: null },
      { similarity: 0.75 },
    ];
    expect(anySemanticResults(results)).toBe(true);
  });

  it("returns false when all results have null similarity", () => {
    const results = [{ similarity: null }, { similarity: null }];
    expect(anySemanticResults(results)).toBe(false);
  });

  it("returns false for empty array", () => {
    expect(anySemanticResults([])).toBe(false);
  });

  it("returns false for null input", () => {
    expect(anySemanticResults(null)).toBe(false);
  });

  it("returns false for undefined input", () => {
    expect(anySemanticResults(undefined)).toBe(false);
  });
});
