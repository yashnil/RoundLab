"""Tests for search trace models and failure-reason determination.

Covers:
- Provider failure is distinguished from genuinely no search results.
- Extraction failure is distinguished from no search results.
- Trace data contains no API keys, headers, or credentials.
- Each failure reason maps to the correct scenario.
- Recovery actions are non-empty for every failure reason.
- build_search_trace produces sanitized, well-formed output.
"""

import pytest
from app.services.search_trace import (
    determine_failure_reason,
    build_search_trace,
    sanitize_error,
    sanitize_errors,
    SearchTraceResult,
    SearchStageTrace,
    FAILURE_REASONS,
)


# ── Failure reason determination ──────────────────────────────────────────────

class TestDetermineFailureReason:
    """Each scenario maps to a specific failure_reason code."""

    def _call(self, **overrides):
        defaults = dict(
            sources_found=0,
            sources_attempted=0,
            sources_extracted=0,
            passages_considered=0,
            filtered_no_support=0,
            filtered_low_quality=0,
            rejected_by_source_quality=0,
            rejected_by_missing_best_claim=0,
            counter_evidence_count=0,
            candidates_generated=0,
            tavily_errors=[],
            card_validation_failures=0,
        )
        defaults.update(overrides)
        return determine_failure_reason(**defaults)

    def test_provider_failure_when_no_results_and_error(self):
        reason, detail, attempts, recovery = self._call(
            sources_found=0, tavily_errors=["timeout"]
        )
        assert reason == "provider_failure"
        assert len(recovery) > 0

    def test_no_search_results_when_no_results_no_error(self):
        reason, detail, attempts, recovery = self._call(sources_found=0)
        assert reason == "no_search_results"
        assert len(recovery) > 0

    def test_extraction_failed_when_sources_found_but_none_extracted(self):
        reason, detail, attempts, recovery = self._call(
            sources_found=5,
            sources_attempted=5,
            sources_extracted=0,
        )
        assert reason == "extraction_failed"
        assert "5" in detail

    def test_source_quality_too_low_when_quality_filter_rejects_all(self):
        reason, detail, attempts, recovery = self._call(
            sources_found=5,
            sources_attempted=5,
            sources_extracted=0,
            filtered_low_quality=5,
        )
        assert reason == "source_quality_too_low"

    def test_page_fetch_failed_partial_extraction(self):
        reason, detail, attempts, recovery = self._call(
            sources_found=5,
            sources_attempted=5,
            sources_extracted=2,
            passages_considered=0,
        )
        assert reason == "page_fetch_failed"

    def test_counter_evidence_only(self):
        reason, detail, attempts, recovery = self._call(
            sources_found=3,
            sources_attempted=3,
            sources_extracted=3,
            passages_considered=5,
            counter_evidence_count=5,
            filtered_no_support=0,
            candidates_generated=0,
        )
        assert reason == "credible_counterevidence_only"

    def test_no_relevant_passages(self):
        reason, detail, attempts, recovery = self._call(
            sources_found=5,
            sources_attempted=5,
            sources_extracted=5,
            passages_considered=10,
            filtered_no_support=10,
            candidates_generated=0,
        )
        assert reason == "no_relevant_passages"

    def test_claim_not_supported_fallback(self):
        reason, detail, attempts, recovery = self._call(
            sources_found=5,
            sources_attempted=5,
            sources_extracted=5,
            passages_considered=3,
            candidates_generated=0,
        )
        assert reason == "claim_not_supported"

    def test_all_failure_reasons_are_in_known_set(self):
        scenarios = [
            dict(sources_found=0, tavily_errors=["err"]),
            dict(sources_found=0),
            dict(sources_found=5, sources_attempted=5, sources_extracted=0),
            dict(sources_found=5, sources_attempted=5, sources_extracted=0, filtered_low_quality=5),
            dict(sources_found=5, sources_attempted=5, sources_extracted=2, passages_considered=0),
            dict(sources_found=3, sources_attempted=3, sources_extracted=3, passages_considered=5, counter_evidence_count=5, candidates_generated=0),
            dict(sources_found=5, sources_attempted=5, sources_extracted=5, passages_considered=10, filtered_no_support=10, candidates_generated=0),
            dict(sources_found=5, sources_attempted=5, sources_extracted=5, passages_considered=3, candidates_generated=0),
        ]
        for s in scenarios:
            r, _, _, _ = self._call(**s)
            assert r in FAILURE_REASONS, f"Unknown reason: {r!r} for scenario {s}"

    def test_each_reason_has_recovery_actions(self):
        """Every failure scenario must provide non-empty recovery actions."""
        scenarios = [
            dict(sources_found=0, tavily_errors=["err"]),
            dict(sources_found=0),
            dict(sources_found=5, sources_attempted=5, sources_extracted=0),
            dict(sources_found=5, sources_attempted=5, sources_extracted=0, filtered_low_quality=5),
            dict(sources_found=3, sources_attempted=3, sources_extracted=3, passages_considered=5, counter_evidence_count=5, candidates_generated=0),
            dict(sources_found=5, sources_attempted=5, sources_extracted=5, passages_considered=10, filtered_no_support=10, candidates_generated=0),
        ]
        for s in scenarios:
            _, _, _, recovery = self._call(**s)
            assert len(recovery) > 0, f"No recovery actions for scenario {s}"

    def test_detail_includes_counts(self):
        reason, detail, _, _ = self._call(
            sources_found=7, sources_attempted=7, sources_extracted=0
        )
        assert "7" in detail


# ── Credential sanitization ───────────────────────────────────────────────────

class TestSanitization:
    """Trace data must never contain API keys, bearer tokens, or auth headers."""

    def test_strips_tavily_key_pattern(self):
        err = "Request failed with Tvly-ABCDEFGHIJKLMNOPQRSTUVWXYZ1234"
        result = sanitize_error(err)
        assert "Tvly-" not in result
        assert "[REDACTED]" in result

    def test_strips_openai_key_pattern(self):
        err = "OpenAI error: sk-abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"
        result = sanitize_error(err)
        assert "sk-" not in result or "[REDACTED]" in result

    def test_strips_bearer_token(self):
        err = "HTTP 401: Authorization required. Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        result = sanitize_error(err)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result

    def test_strips_authorization_header(self):
        err = "Request headers: Authorization: Bearer secret-token-value-123456789012"
        result = sanitize_error(err)
        assert "secret-token-value" not in result

    def test_strips_api_key_param(self):
        err = "URL contained: api_key=MYSECRETAPIKEY12345678"
        result = sanitize_error(err)
        assert "MYSECRETAPIKEY" not in result

    def test_safe_message_unchanged(self):
        err = "Connection timed out after 10 seconds"
        result = sanitize_error(err)
        assert result == err

    def test_sanitize_list(self):
        errors = [
            "timeout error",
            "Tvly-ABCDEFGHIJKLMNOPQRSTUVWXYZ1234 is invalid",
        ]
        results = sanitize_errors(errors)
        assert results[0] == "timeout error"
        assert "Tvly-" not in results[1]

    def test_build_search_trace_sanitizes_errors(self):
        trace = build_search_trace(
            queries_run=["test query"],
            roles_attempted=["direct_outcome"],
            sources_found=0,
            sources_attempted=0,
            sources_extracted=0,
            passages_considered=0,
            filtered_no_support=0,
            filtered_low_quality=0,
            rejected_by_source_quality=0,
            rejected_by_missing_best_claim=0,
            counter_evidence_count=0,
            candidates_generated=0,
            tavily_errors=["Tvly-SECRETKEYABCDEF12345 failed"],
            possible_lead_urls=[],
        )
        search_stage = trace.stages[0]
        for err in search_stage.provider_errors:
            assert "Tvly-" not in err
            assert "[REDACTED]" in err or "Tvly-" not in err

    def test_trace_contains_no_raw_secrets(self):
        trace = build_search_trace(
            queries_run=["section 230 accountability"],
            roles_attempted=["direct_outcome"],
            sources_found=3,
            sources_attempted=3,
            sources_extracted=0,
            passages_considered=0,
            filtered_no_support=0,
            filtered_low_quality=3,
            rejected_by_source_quality=0,
            rejected_by_missing_best_claim=0,
            counter_evidence_count=0,
            candidates_generated=0,
            tavily_errors=["api_key=SECRETKEY123456789 rejected"],
            possible_lead_urls=[],
        )
        trace_str = trace.model_dump_json()
        assert "SECRETKEY123456789" not in trace_str


# ── build_search_trace: correctness ──────────────────────────────────────────

class TestBuildSearchTrace:
    def test_success_path_no_failure_reason(self):
        trace = build_search_trace(
            queries_run=["q1", "q2"],
            roles_attempted=["direct_outcome"],
            sources_found=5,
            sources_attempted=5,
            sources_extracted=3,
            passages_considered=10,
            filtered_no_support=7,
            filtered_low_quality=0,
            rejected_by_source_quality=0,
            rejected_by_missing_best_claim=0,
            counter_evidence_count=0,
            candidates_generated=3,
            tavily_errors=[],
            possible_lead_urls=[],
            cards_produced=3,
        )
        assert trace.failure_reason is None
        assert trace.total_cards == 3

    def test_failure_path_has_reason(self):
        trace = build_search_trace(
            queries_run=["q1"],
            roles_attempted=["direct_outcome"],
            sources_found=0,
            sources_attempted=0,
            sources_extracted=0,
            passages_considered=0,
            filtered_no_support=0,
            filtered_low_quality=0,
            rejected_by_source_quality=0,
            rejected_by_missing_best_claim=0,
            counter_evidence_count=0,
            candidates_generated=0,
            tavily_errors=[],
            possible_lead_urls=[],
            cards_produced=0,
        )
        assert trace.failure_reason == "no_search_results"
        assert len(trace.recovery_actions) > 0

    def test_trace_has_two_stages(self):
        trace = build_search_trace(
            queries_run=["q1"],
            roles_attempted=["direct_outcome"],
            sources_found=5,
            sources_attempted=5,
            sources_extracted=5,
            passages_considered=10,
            filtered_no_support=10,
            filtered_low_quality=0,
            rejected_by_source_quality=0,
            rejected_by_missing_best_claim=0,
            counter_evidence_count=0,
            candidates_generated=0,
            tavily_errors=[],
            possible_lead_urls=[],
        )
        assert len(trace.stages) == 2
        assert trace.stages[0].stage == "search"
        assert trace.stages[1].stage == "extraction"

    def test_stopped_early_propagated(self):
        trace = build_search_trace(
            queries_run=["q1", "q2"],
            roles_attempted=["direct_outcome"],
            sources_found=10,
            sources_attempted=5,
            sources_extracted=5,
            passages_considered=8,
            filtered_no_support=0,
            filtered_low_quality=0,
            rejected_by_source_quality=0,
            rejected_by_missing_best_claim=0,
            counter_evidence_count=0,
            candidates_generated=3,
            tavily_errors=[],
            possible_lead_urls=[],
            cards_produced=3,
            stopped_early=True,
        )
        assert trace.stopped_early is True

    def test_total_queries_count(self):
        trace = build_search_trace(
            queries_run=["q1", "q2", "q3"],
            roles_attempted=["direct_outcome", "causal_mechanism"],
            sources_found=0,
            sources_attempted=0,
            sources_extracted=0,
            passages_considered=0,
            filtered_no_support=0,
            filtered_low_quality=0,
            rejected_by_source_quality=0,
            rejected_by_missing_best_claim=0,
            counter_evidence_count=0,
            candidates_generated=0,
            tavily_errors=[],
            possible_lead_urls=[],
        )
        assert trace.total_queries == 3

    def test_possible_leads_note_in_trace(self):
        trace = build_search_trace(
            queries_run=["q1"],
            roles_attempted=["direct_outcome"],
            sources_found=3,
            sources_attempted=3,
            sources_extracted=0,
            passages_considered=0,
            filtered_no_support=0,
            filtered_low_quality=0,
            rejected_by_source_quality=0,
            rejected_by_missing_best_claim=0,
            counter_evidence_count=0,
            candidates_generated=0,
            tavily_errors=[],
            possible_lead_urls=["https://example.com/a", "https://example.com/b"],
        )
        search_stage = trace.stages[0]
        assert len(search_stage.notes) > 0

    def test_serializable_to_dict(self):
        trace = build_search_trace(
            queries_run=["q1"],
            roles_attempted=["direct_outcome"],
            sources_found=0,
            sources_attempted=0,
            sources_extracted=0,
            passages_considered=0,
            filtered_no_support=0,
            filtered_low_quality=0,
            rejected_by_source_quality=0,
            rejected_by_missing_best_claim=0,
            counter_evidence_count=0,
            candidates_generated=0,
            tavily_errors=[],
            possible_lead_urls=[],
        )
        d = trace.model_dump()
        assert isinstance(d, dict)
        assert "failure_reason" in d
        assert "stages" in d


# ── Provider vs extraction failure distinction ────────────────────────────────

class TestProviderVsExtractionDistinction:
    """Provider failure (Tavily error) must be distinguished from
    extraction failure (page could not be scraped)."""

    def test_provider_failure_when_tavily_errored(self):
        reason, _, _, _ = determine_failure_reason(
            sources_found=0, sources_attempted=0, sources_extracted=0,
            passages_considered=0, filtered_no_support=0, filtered_low_quality=0,
            rejected_by_source_quality=0, rejected_by_missing_best_claim=0,
            counter_evidence_count=0, candidates_generated=0,
            tavily_errors=["Connection refused"],
        )
        assert reason == "provider_failure"

    def test_extraction_failure_when_search_succeeded_but_pages_failed(self):
        reason, _, _, _ = determine_failure_reason(
            sources_found=5, sources_attempted=5, sources_extracted=0,
            passages_considered=0, filtered_no_support=0, filtered_low_quality=0,
            rejected_by_source_quality=0, rejected_by_missing_best_claim=0,
            counter_evidence_count=0, candidates_generated=0,
            tavily_errors=[],  # no provider error — search worked
        )
        assert reason == "extraction_failed"

    def test_no_search_results_when_search_returned_nothing(self):
        reason, _, _, _ = determine_failure_reason(
            sources_found=0, sources_attempted=0, sources_extracted=0,
            passages_considered=0, filtered_no_support=0, filtered_low_quality=0,
            rejected_by_source_quality=0, rejected_by_missing_best_claim=0,
            counter_evidence_count=0, candidates_generated=0,
            tavily_errors=[],  # search ran fine, just no results
        )
        assert reason == "no_search_results"


# ── SearchTraceResult model structure ────────────────────────────────────────

class TestSearchTraceResultModel:
    def test_default_construction(self):
        trace = SearchTraceResult()
        assert trace.failure_reason is None
        assert trace.stages == []
        assert trace.attempts_summary == []
        assert trace.recovery_actions == []

    def test_stage_construction(self):
        stage = SearchStageTrace(stage="search", urls_found=5)
        assert stage.urls_found == 5
        assert stage.provider_errors == []

    def test_failure_reason_none_on_success(self):
        trace = SearchTraceResult(total_cards=3)
        assert trace.failure_reason is None

    def test_all_failure_reasons_valid(self):
        """All documented failure reasons are valid strings."""
        for r in FAILURE_REASONS:
            assert isinstance(r, str)
            assert len(r) > 0
