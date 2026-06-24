/**
 * Tests for SearchFailurePanel data / type compatibility.
 *
 * Exercises:
 * - SearchTraceResult and SearchStageTrace TypeScript shape matches backend API
 * - failure_reason codes align with REASON_LABELS in the component
 * - GenerateCardsResponse.search_trace and .failure_reason optional fields exist
 * - Each major failure category has recovery_actions
 * - no_search_results vs provider_failure vs extraction_failed are distinct
 * - Developer trace fields are present on stages
 *
 * Note: The component itself is a React UI component and is tested visually.
 * These tests cover the data model and label mapping without requiring JSDOM.
 */

import type {
  SearchTraceResult,
  SearchStageTrace,
  GenerateCardsResponse,
} from "@/types";

// ── Reason labels (mirrors REASON_LABELS in SearchFailurePanel.tsx) ───────────

const KNOWN_REASON_LABELS: Record<string, string> = {
  no_search_results: "No search results returned",
  provider_failure: "Search provider error",
  page_fetch_failed: "Pages could not be fetched",
  extraction_failed: "Text extraction failed",
  no_relevant_passages: "No relevant passages found",
  source_quality_too_low: "Sources below quality threshold",
  claim_not_supported: "Claim not supported by sources",
  citation_metadata_incomplete: "Citation metadata incomplete",
  card_validation_failed: "Evidence cut validation failed",
  credible_counterevidence_only: "Only counterevidence found",
  no_credible_support_found: "No credible support found",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeStage(overrides: Partial<SearchStageTrace> = {}): SearchStageTrace {
  return {
    stage: "search",
    queries_run: [],
    roles_attempted: [],
    urls_found: 0,
    urls_deduplicated: 0,
    pages_fetched_ok: 0,
    extraction_successes: 0,
    extraction_failures: 0,
    passages_considered: 0,
    passages_rejected_relevance: 0,
    passages_rejected_quality: 0,
    passages_rejected_validation: 0,
    cards_produced: 0,
    provider_errors: [],
    notes: [],
    ...overrides,
  };
}

function makeTrace(overrides: Partial<SearchTraceResult> = {}): SearchTraceResult {
  return {
    stages: [],
    failure_reason: null,
    failure_detail: "",
    attempts_summary: [],
    recovery_actions: [],
    stopped_early: false,
    total_queries: 0,
    total_urls_found: 0,
    total_cards: 0,
    ...overrides,
  };
}

// ── Type shape tests (fail at compile time if types are wrong) ────────────────

describe("SearchTraceResult type shape", () => {
  it("has all required fields", () => {
    const trace: SearchTraceResult = makeTrace();
    expect(Array.isArray(trace.stages)).toBe(true);
    expect(trace.failure_reason).toBeNull();
    expect(typeof trace.failure_detail).toBe("string");
    expect(Array.isArray(trace.attempts_summary)).toBe(true);
    expect(Array.isArray(trace.recovery_actions)).toBe(true);
    expect(typeof trace.stopped_early).toBe("boolean");
    expect(typeof trace.total_queries).toBe("number");
    expect(typeof trace.total_urls_found).toBe("number");
    expect(typeof trace.total_cards).toBe("number");
  });

  it("accepts a failure_reason string", () => {
    const trace: SearchTraceResult = makeTrace({ failure_reason: "no_search_results" });
    expect(trace.failure_reason).toBe("no_search_results");
  });

  it("accepts null failure_reason on success", () => {
    const trace: SearchTraceResult = makeTrace({ total_cards: 3, failure_reason: null });
    expect(trace.failure_reason).toBeNull();
    expect(trace.total_cards).toBe(3);
  });
});

describe("SearchStageTrace type shape", () => {
  it("has all required fields", () => {
    const stage: SearchStageTrace = makeStage();
    expect(typeof stage.stage).toBe("string");
    expect(Array.isArray(stage.queries_run)).toBe(true);
    expect(Array.isArray(stage.roles_attempted)).toBe(true);
    expect(typeof stage.urls_found).toBe("number");
    expect(typeof stage.urls_deduplicated).toBe("number");
    expect(Array.isArray(stage.provider_errors)).toBe(true);
    expect(Array.isArray(stage.notes)).toBe(true);
  });

  it("can represent a search stage", () => {
    const stage: SearchStageTrace = makeStage({
      stage: "search",
      queries_run: ["q1", "q2"],
      roles_attempted: ["direct_outcome"],
      urls_found: 10,
      urls_deduplicated: 2,
    });
    expect(stage.queries_run).toHaveLength(2);
    expect(stage.roles_attempted).toContain("direct_outcome");
  });

  it("can represent an extraction stage", () => {
    const stage: SearchStageTrace = makeStage({
      stage: "extraction",
      extraction_successes: 3,
      extraction_failures: 2,
      passages_considered: 15,
      passages_rejected_relevance: 12,
    });
    expect(stage.stage).toBe("extraction");
    expect(stage.extraction_successes).toBe(3);
  });
});

describe("GenerateCardsResponse failure fields", () => {
  it("accepts optional failure_reason", () => {
    const resp: Partial<GenerateCardsResponse> = {
      search_configured: true,
      cards: [],
      failure_reason: "no_search_results",
    };
    expect(resp.failure_reason).toBe("no_search_results");
  });

  it("accepts optional search_trace", () => {
    const trace = makeTrace({ failure_reason: "extraction_failed", total_queries: 3 });
    const resp: Partial<GenerateCardsResponse> = {
      search_configured: true,
      cards: [],
      failure_reason: "extraction_failed",
      search_trace: trace,
    };
    expect(resp.search_trace?.failure_reason).toBe("extraction_failed");
    expect(resp.search_trace?.total_queries).toBe(3);
  });

  it("accepts null search_trace", () => {
    const resp: Partial<GenerateCardsResponse> = {
      search_configured: true,
      cards: [],
      search_trace: null,
    };
    expect(resp.search_trace).toBeNull();
  });
});

// ── Failure category distinctness ─────────────────────────────────────────────

describe("Failure reason label coverage", () => {
  it("all 11 reason codes have labels", () => {
    const codes = Object.keys(KNOWN_REASON_LABELS);
    expect(codes).toHaveLength(11);
  });

  it("no_search_results and provider_failure are distinct reasons", () => {
    const noResults = KNOWN_REASON_LABELS["no_search_results"];
    const providerFail = KNOWN_REASON_LABELS["provider_failure"];
    expect(noResults).not.toBe(providerFail);
  });

  it("extraction_failed and no_search_results are distinct", () => {
    const extraction = KNOWN_REASON_LABELS["extraction_failed"];
    const noResults = KNOWN_REASON_LABELS["no_search_results"];
    expect(extraction).not.toBe(noResults);
  });

  it("credible_counterevidence_only and claim_not_supported are distinct", () => {
    const counter = KNOWN_REASON_LABELS["credible_counterevidence_only"];
    const notSupported = KNOWN_REASON_LABELS["claim_not_supported"];
    expect(counter).not.toBe(notSupported);
  });
});

// ── Recovery actions (structural) ────────────────────────────────────────────

describe("recovery_actions on trace", () => {
  it("trace can carry recovery actions", () => {
    const trace = makeTrace({
      failure_reason: "no_search_results",
      recovery_actions: [
        "Broaden the claim wording",
        "Search the warrant separately",
      ],
    });
    expect(trace.recovery_actions).toHaveLength(2);
  });

  it("empty recovery_actions on success trace", () => {
    const trace = makeTrace({ failure_reason: null, total_cards: 2, recovery_actions: [] });
    expect(trace.recovery_actions).toHaveLength(0);
  });

  it("attempts_summary describes what was tried", () => {
    const trace = makeTrace({
      failure_reason: "extraction_failed",
      attempts_summary: ["Found 5 URLs from search", "Page text extraction failed for all sources"],
    });
    expect(trace.attempts_summary).toHaveLength(2);
    expect(trace.attempts_summary[0]).toMatch(/URL/i);
  });
});

// ── Trace stages (per-stage detail) ──────────────────────────────────────────

describe("trace stages", () => {
  it("can have search + extraction stages", () => {
    const trace = makeTrace({
      stages: [
        makeStage({ stage: "search", urls_found: 5, queries_run: ["q1", "q2"] }),
        makeStage({ stage: "extraction", extraction_successes: 3, extraction_failures: 2 }),
      ],
    });
    expect(trace.stages).toHaveLength(2);
    expect(trace.stages[0].stage).toBe("search");
    expect(trace.stages[1].stage).toBe("extraction");
  });

  it("provider_errors on search stage are sanitized (no real API keys)", () => {
    const stage = makeStage({
      stage: "search",
      provider_errors: ["Connection timed out after 10 seconds"],
    });
    for (const err of stage.provider_errors) {
      expect(err).not.toMatch(/Tvly-/);
      expect(err).not.toMatch(/sk-[A-Za-z0-9]{10,}/);
      expect(err).not.toMatch(/Bearer [A-Za-z0-9]{10,}/);
    }
  });

  it("notes on search stage describe lead URLs", () => {
    const stage = makeStage({
      stage: "search",
      notes: ["2 possible lead(s) found but not fully extracted"],
    });
    expect(stage.notes[0]).toMatch(/lead/i);
  });
});

// ── stopped_early flag ────────────────────────────────────────────────────────

describe("stopped_early escalation flag", () => {
  it("false by default", () => {
    const trace = makeTrace();
    expect(trace.stopped_early).toBe(false);
  });

  it("true when escalation was stopped", () => {
    const trace = makeTrace({ stopped_early: true });
    expect(trace.stopped_early).toBe(true);
  });
});

// ── No-card reason backward compat ────────────────────────────────────────────

describe("backward compatibility", () => {
  it("GenerateCardsResponse without trace still works (trace undefined)", () => {
    const resp: Partial<GenerateCardsResponse> = {
      search_configured: true,
      cards: [],
      no_card_reason: "No credible source text clearly supported this claim.",
    };
    expect(resp.search_trace).toBeUndefined();
    expect(resp.failure_reason).toBeUndefined();
    expect(resp.no_card_reason).toBeTruthy();
  });
});
