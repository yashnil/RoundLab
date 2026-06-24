"""Search trace models and failure-reason determination.

Provides typed trace models that record what happened at each pipeline stage,
a deterministic failure-reason selector based on actual counter data, and
sanitization helpers that strip secrets before data reaches the frontend.

SAFETY INVARIANTS
- sanitize_error() and sanitize_errors() strip API keys, bearer tokens,
  auth headers, and any string that looks like a credential.
- determine_failure_reason() never calls an LLM; it works from counters only.
- SearchTraceResult / SearchStageTrace contain no raw URLs, domain names,
  or query text beyond what the generate-cards endpoint already exposes.
- Reason codes are a closed Literal type so the frontend can switch on them.
"""

from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel

# ── Failure reason codes ──────────────────────────────────────────────────────

FAILURE_REASONS = (
    "no_search_results",
    "provider_failure",
    "page_fetch_failed",
    "extraction_failed",
    "no_relevant_passages",
    "source_quality_too_low",
    "claim_not_supported",
    "citation_metadata_incomplete",
    "card_validation_failed",
    "credible_counterevidence_only",
    "no_credible_support_found",
)

# ── Recovery-action map ───────────────────────────────────────────────────────

_RECOVERY: dict[str, list[str]] = {
    "no_search_results": [
        "Broaden the claim wording — try fewer or simpler terms",
        "Search the warrant separately: how does the mechanism work?",
        "Use URL mode with a specific source you already know",
    ],
    "provider_failure": [
        "The search provider timed out — try again in a moment",
        "Switch to URL mode or Paste Text mode",
    ],
    "page_fetch_failed": [
        "Paste the article text directly using Paste Text mode",
        "Provide the source URL directly in URL mode",
        "Retry — some pages are temporarily inaccessible",
    ],
    "extraction_failed": [
        "Paste the article text using Paste Text mode",
        "Try a different search wording to surface different sources",
        "Provide the article URL directly in URL mode",
    ],
    "no_relevant_passages": [
        "Search the mechanism separately (e.g. 'how [X] grants immunity')",
        "Search the impact separately (e.g. 'harm from [X] study')",
        "Reword the claim to match how sources actually discuss this topic",
    ],
    "source_quality_too_low": [
        "Add 'site:edu' or 'site:gov' to limit results to credible domains",
        "Use URL mode with a .gov, .edu, or law journal source",
        "Include 'study', 'report', or 'law review' in the claim to surface better sources",
    ],
    "claim_not_supported": [
        "Search warrant and impact separately using simpler phrasing",
        "Remove any unsupported magnitude ('always', 'completely', 'all')",
        "Credible counterevidence may exist — check if the claim is disputed",
    ],
    "citation_metadata_incomplete": [
        "Use URL mode to provide the source directly with full metadata",
        "Paste Text mode lets you enter author and date manually",
    ],
    "card_validation_failed": [
        "The evidence cut may be too fragmented — use URL mode for full extraction",
        "Paste Text mode gives you full control over the card body",
    ],
    "credible_counterevidence_only": [
        "The sources found argue the opposing side — consider cutting them as pre-empts",
        "Search specifically for the mechanism: 'how [X] works study'",
        "Search the impact independently: '[harm type] evidence research'",
    ],
    "no_credible_support_found": [
        "Try a narrower claim focused on mechanism ('how X shields from liability')",
        "Search warrant and impact independently with simpler phrasing",
        "Use URL mode with a law review, think tank, or government source",
        "Reconsider whether this specific claim has strong research support",
    ],
}


# ── Secret-stripping patterns ─────────────────────────────────────────────────

_SECRET_PATTERNS = [
    re.compile(r"\b[Tt]vly-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\b[Ee]xa-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"sk-[A-Za-z0-9]{32,}"),
    re.compile(r"Bearer [A-Za-z0-9._-]{20,}"),
    re.compile(r"Authorization:[^\n]{0,200}", re.IGNORECASE),
    re.compile(r"api[_-]?key[=:][^\s,\"']{8,}", re.IGNORECASE),
    re.compile(r"key=[A-Za-z0-9_-]{16,}"),
    re.compile(r"token=[A-Za-z0-9_-]{16,}", re.IGNORECASE),
]


def sanitize_error(error: str) -> str:
    """Strip credential-like patterns from an error string."""
    for pattern in _SECRET_PATTERNS:
        error = pattern.sub("[REDACTED]", error)
    return error[:300]


def sanitize_errors(errors: list[str]) -> list[str]:
    return [sanitize_error(e) for e in errors]


# ── Trace models ──────────────────────────────────────────────────────────────

class SearchStageTrace(BaseModel):
    """One pipeline stage's contribution to the search result."""
    stage: str  # "search" | "extraction" | "ranking" | "card_cutting"
    queries_run: list[str] = []
    roles_attempted: list[str] = []
    urls_found: int = 0
    urls_deduplicated: int = 0
    pages_fetched_ok: int = 0
    extraction_successes: int = 0
    extraction_failures: int = 0
    passages_considered: int = 0
    passages_rejected_relevance: int = 0
    passages_rejected_quality: int = 0
    passages_rejected_validation: int = 0
    passages_deduplicated: int = 0         # removed by dedup before ranking (Pass 8)
    cards_produced: int = 0
    provider_errors: list[str] = []
    notes: list[str] = []
    # Pass 8 retrieval metadata (optional, defaults preserve backward compat)
    reranker_applied: bool = False
    reranker_backend: str = ""             # "bm25" | "bm25+semantic" | "cohere" | "heuristic"
    # Pass 9 academic routing metadata (all optional)
    source_lanes_selected: list[str] = []
    specialized_providers_attempted: int = 0
    specialized_results_found: int = 0
    doi_matches: int = 0
    crossref_enrichments: int = 0
    trusted_domain_searches: int = 0
    metadata_only_excluded: int = 0
    primary_source_candidates: int = 0
    # Pass 10 extraction provenance metadata (all optional)
    document_types_encountered: list[str] = []   # ["html", "pdf", …]
    parsers_attempted: list[str] = []
    parser_selected: str = ""
    parser_failures: int = 0
    fallback_count: int = 0
    extraction_quality_warnings: list[str] = []
    full_text_count: int = 0
    abstract_only_count: int = 0
    snippet_only_count: int = 0
    partial_extraction_count: int = 0
    metadata_only_count: int = 0
    snapshot_success_count: int = 0
    snapshot_failure_count: int = 0
    page_aware_candidates: int = 0
    offset_validation_failures: int = 0
    # Pass 11: card support verification
    cards_verified: int = 0
    cards_supported: int = 0
    cards_partially_supported: int = 0
    cards_unsupported: int = 0
    cards_contradicted: int = 0
    cards_insufficient_context: int = 0
    deterministic_mismatches_found: int = 0
    semantic_verifier_attempted: int = 0
    semantic_verifier_backend: str = ""
    semantic_verifier_failures: int = 0
    invalid_verifier_spans: int = 0
    abstract_context_warnings: int = 0
    safer_tags_generated: int = 0
    # Pass 12: citation records
    citation_records_created: int = 0
    crossref_verified_records: int = 0
    citation_fields_enriched: int = 0
    citation_conflicts_found: int = 0
    citation_records_complete: int = 0
    citation_records_with_warnings: int = 0
    citation_records_incomplete: int = 0
    legacy_citations_migrated: int = 0
    citation_renderer_backend: str = "deterministic"
    citation_renderer_failures: int = 0


class SearchTraceResult(BaseModel):
    """Aggregated, sanitized trace for one generate-cards call."""
    stages: list[SearchStageTrace] = []
    failure_reason: Optional[str] = None   # one of FAILURE_REASONS or None (success)
    failure_detail: str = ""               # concise human-readable explanation
    attempts_summary: list[str] = []       # what was tried (user-facing)
    recovery_actions: list[str] = []       # concrete next steps
    stopped_early: bool = False            # True if escalation stopped before all queries
    total_queries: int = 0
    total_urls_found: int = 0
    total_cards: int = 0
    # Pass 8 aggregated retrieval info
    dedup_removed: int = 0                 # total passages removed by deduplication
    retrieval_backend: str = ""            # backend used for ranking ("bm25", "bm25+semantic", etc.)
    # Pass 9 aggregated source info
    source_type_distribution: dict[str, int] = {}
    specialized_summary: str = ""
    # Pass 10 extraction summary
    extraction_summary: str = ""           # user-facing plain-language summary
    # Pass 11 verification summary
    verification_summary: str = ""         # user-facing plain-language summary
    # Pass 12 citation summary
    citation_summary: str = ""             # user-facing plain-language summary


# ── Failure-reason determination ──────────────────────────────────────────────

def determine_failure_reason(
    sources_found: int,
    sources_attempted: int,
    sources_extracted: int,
    passages_considered: int,
    filtered_no_support: int,
    filtered_low_quality: int,
    rejected_by_source_quality: int,
    rejected_by_missing_best_claim: int,
    counter_evidence_count: int,
    candidates_generated: int,
    tavily_errors: list[str],
    card_validation_failures: int = 0,
) -> tuple[str, str, list[str], list[str]]:
    """Return (failure_reason, detail, attempts_summary, recovery_actions).

    Selects the most specific applicable reason from actual pipeline counters.
    Never calls an LLM. Priority matches the order in which stages can fail.
    """
    safe_errors = sanitize_errors(tavily_errors)

    # Stage 1 — provider error with no results at all
    if sources_found == 0 and safe_errors:
        return (
            "provider_failure",
            f"Search provider error: {safe_errors[0]}",
            ["Attempted claim-based queries — search provider failed"],
            _RECOVERY["provider_failure"],
        )

    # Stage 2 — search ran but returned nothing
    if sources_found == 0:
        return (
            "no_search_results",
            "No search results were returned for any query variant",
            ["Ran multiple query variants — all returned empty results"],
            _RECOVERY["no_search_results"],
        )

    # Stage 3 — URLs found but quality gate rejected everything before extraction
    if sources_attempted > 0 and sources_extracted == 0 and filtered_low_quality > 0:
        return (
            "source_quality_too_low",
            (
                f"{filtered_low_quality} source(s) were below the credibility threshold "
                "(blog, wiki, or forum)"
            ),
            [f"Found {sources_found} URLs", "Quality filter rejected all sources"],
            _RECOVERY["source_quality_too_low"],
        )

    # Stage 4 — URLs found but extraction failed for all
    if sources_attempted > 0 and sources_extracted == 0:
        return (
            "extraction_failed",
            f"Found {sources_attempted} source(s) but text extraction failed for all",
            [
                f"Found {sources_found} URLs from search",
                "Page text extraction failed for all sources",
            ],
            _RECOVERY["extraction_failed"],
        )

    # Stage 5 — partial extraction failure with no passages to work with
    if sources_attempted > 0 and sources_extracted < sources_attempted and passages_considered == 0:
        failed_count = sources_attempted - sources_extracted
        return (
            "page_fetch_failed",
            f"{failed_count} of {sources_attempted} pages could not be fetched",
            [
                f"Found {sources_found} URLs",
                f"Extracted {sources_extracted} of {sources_attempted} pages",
            ],
            _RECOVERY["page_fetch_failed"],
        )

    # Stage 6 — quality gate rejected after extraction
    if rejected_by_source_quality > 0 and candidates_generated == 0 and passages_considered == 0:
        return (
            "source_quality_too_low",
            f"{rejected_by_source_quality} source(s) rejected as below minimum credibility",
            [
                f"Extracted {sources_extracted} sources",
                f"Quality gate rejected {rejected_by_source_quality}",
            ],
            _RECOVERY["source_quality_too_low"],
        )

    # Stage 7 — counter-evidence dominated; nothing supports the claim
    if counter_evidence_count > 0 and filtered_no_support == 0 and candidates_generated == 0:
        return (
            "credible_counterevidence_only",
            f"The {counter_evidence_count} relevant passage(s) found argue against this claim",
            [
                f"Extracted {sources_extracted} sources",
                f"Found {passages_considered} passages — all oppose the claim",
            ],
            _RECOVERY["credible_counterevidence_only"],
        )

    # Stage 8 — passages considered but none relevant
    if passages_considered > 0 and filtered_no_support > 0 and candidates_generated == 0:
        return (
            "no_relevant_passages",
            f"Examined {passages_considered} passage(s) — none supported this claim",
            [
                f"Extracted {sources_extracted} sources",
                f"Scored {passages_considered} passages",
                f"{filtered_no_support} rejected as not relevant to the claim",
            ],
            _RECOVERY["no_relevant_passages"],
        )

    # Stage 9 — card-cutting validation failed
    if card_validation_failures > 0 and candidates_generated == 0:
        return (
            "card_validation_failed",
            f"Evidence cut validation failed for {card_validation_failures} candidate(s)",
            [
                f"Extracted {sources_extracted} sources",
                "Card-cutting validation rejected all candidates",
            ],
            _RECOVERY["card_validation_failed"],
        )

    # Stage 10 — sources extracted, claim simply not supported
    if sources_extracted > 0 and candidates_generated == 0:
        return (
            "claim_not_supported",
            f"Searched {sources_extracted} source(s) — none clearly supported this claim",
            [
                f"Found {sources_found} URLs",
                f"Extracted {sources_extracted} sources",
                f"Scored {passages_considered} passages",
                "No passage met the usefulness and quality threshold",
            ],
            _RECOVERY["claim_not_supported"],
        )

    # Fallback
    return (
        "no_credible_support_found",
        "No credible source text clearly supported this claim",
        [f"Attempted {sources_found} source(s)" if sources_found else "No sources found"],
        _RECOVERY["no_credible_support_found"],
    )


# ── Trace builder ─────────────────────────────────────────────────────────────

def build_search_trace(
    *,
    queries_run: list[str],
    roles_attempted: list[str],
    sources_found: int,
    sources_attempted: int,
    sources_extracted: int,
    passages_considered: int,
    filtered_no_support: int,
    filtered_low_quality: int,
    rejected_by_source_quality: int,
    rejected_by_missing_best_claim: int,
    counter_evidence_count: int,
    candidates_generated: int,
    tavily_errors: list[str],
    possible_lead_urls: list[str],
    cards_produced: int = 0,
    stopped_early: bool = False,
    # Pass 8 retrieval metadata (all optional for backward compat)
    passages_deduplicated: int = 0,
    retrieval_backend: str = "",
    # Pass 9 academic routing metadata (all optional)
    p9_lanes: list[str] | None = None,
    p9_providers_attempted: int = 0,
    p9_results_found: int = 0,
    p9_doi_matches: int = 0,
    p9_crossref_enrichments: int = 0,
    p9_trusted_domain_searches: int = 0,
    p9_metadata_only_excluded: int = 0,
    p9_primary_candidates: int = 0,
    p9_source_distribution: dict[str, int] | None = None,
    p9_specialized_summary: str = "",
    # Pass 10 extraction provenance metadata (all optional)
    p10_document_types: list[str] | None = None,
    p10_parsers_attempted: list[str] | None = None,
    p10_parser_selected: str = "",
    p10_parser_failures: int = 0,
    p10_fallback_count: int = 0,
    p10_quality_warnings: list[str] | None = None,
    p10_full_text_count: int = 0,
    p10_abstract_only_count: int = 0,
    p10_snippet_only_count: int = 0,
    p10_partial_extraction_count: int = 0,
    p10_metadata_only_count: int = 0,
    p10_snapshot_success: int = 0,
    p10_snapshot_failure: int = 0,
    p10_page_aware_candidates: int = 0,
    p10_offset_validation_failures: int = 0,
    p10_extraction_summary: str = "",
    # Pass 11: card support verification
    p11_cards_verified: int = 0,
    p11_cards_supported: int = 0,
    p11_cards_partially_supported: int = 0,
    p11_cards_unsupported: int = 0,
    p11_cards_contradicted: int = 0,
    p11_cards_insufficient_context: int = 0,
    p11_deterministic_mismatches: int = 0,
    p11_semantic_attempted: int = 0,
    p11_semantic_backend: str = "",
    p11_semantic_failures: int = 0,
    p11_abstract_context_warnings: int = 0,
    p11_safer_tags_generated: int = 0,
    p11_verification_summary: str = "",
    # Pass 12: citation records
    p12_records_created: int = 0,
    p12_crossref_verified: int = 0,
    p12_fields_enriched: int = 0,
    p12_conflicts_found: int = 0,
    p12_records_complete: int = 0,
    p12_records_with_warnings: int = 0,
    p12_records_incomplete: int = 0,
    p12_legacy_migrated: int = 0,
    p12_renderer_failures: int = 0,
    p12_citation_summary: str = "",
) -> SearchTraceResult:
    """Build a sanitized SearchTraceResult from pipeline counters.

    When cards_produced > 0, failure_reason is None (success path).
    All error strings are passed through sanitize_errors().
    """
    failure_reason: Optional[str]
    failure_detail: str
    attempts_summary: list[str]
    recovery_actions: list[str]

    if cards_produced > 0:
        failure_reason = None
        failure_detail = ""
        attempts_summary = [
            f"Ran {len(queries_run)} query variant(s) across {sources_found} source(s)",
            f"Produced {cards_produced} card(s) from {sources_extracted} extracted page(s)",
        ]
        recovery_actions = []
    else:
        failure_reason, failure_detail, attempts_summary, recovery_actions = (
            determine_failure_reason(
                sources_found=sources_found,
                sources_attempted=sources_attempted,
                sources_extracted=sources_extracted,
                passages_considered=passages_considered,
                filtered_no_support=filtered_no_support,
                filtered_low_quality=filtered_low_quality,
                rejected_by_source_quality=rejected_by_source_quality,
                rejected_by_missing_best_claim=rejected_by_missing_best_claim,
                counter_evidence_count=counter_evidence_count,
                candidates_generated=candidates_generated,
                tavily_errors=tavily_errors,
            )
        )

    _p9_notes: list[str] = []
    if p9_specialized_summary:
        _p9_notes.append(p9_specialized_summary)

    search_stage = SearchStageTrace(
        stage="search",
        queries_run=queries_run,
        roles_attempted=roles_attempted,
        urls_found=sources_found,
        urls_deduplicated=max(0, sources_found - sources_attempted),
        provider_errors=sanitize_errors(tavily_errors),
        notes=(
            [f"{len(possible_lead_urls)} possible lead(s) found but not fully extracted"]
            if possible_lead_urls else []
        ) + _p9_notes,
        # Pass 9 fields
        source_lanes_selected=list(p9_lanes or []),
        specialized_providers_attempted=p9_providers_attempted,
        specialized_results_found=p9_results_found,
        doi_matches=p9_doi_matches,
        crossref_enrichments=p9_crossref_enrichments,
        trusted_domain_searches=p9_trusted_domain_searches,
        metadata_only_excluded=p9_metadata_only_excluded,
        primary_source_candidates=p9_primary_candidates,
    )

    # Build user-facing extraction summary
    _p10_notes: list[str] = []
    if p10_extraction_summary:
        _p10_notes.append(p10_extraction_summary)
    elif p10_full_text_count > 0 or p10_abstract_only_count > 0:
        parts: list[str] = []
        if p10_full_text_count:
            parts.append(f"Extracted full text from {p10_full_text_count} source(s).")
        if p10_abstract_only_count:
            parts.append(f"{p10_abstract_only_count} source(s) available as abstract only.")
        if p10_partial_extraction_count:
            parts.append(f"Partial extraction from {p10_partial_extraction_count} source(s).")
        if parts:
            _p10_notes.append(" ".join(parts))

    extraction_stage = SearchStageTrace(
        stage="extraction",
        pages_fetched_ok=sources_extracted,
        extraction_successes=sources_extracted,
        extraction_failures=max(0, sources_attempted - sources_extracted),
        passages_considered=passages_considered,
        passages_rejected_relevance=filtered_no_support,
        passages_rejected_quality=filtered_low_quality,
        passages_rejected_validation=rejected_by_source_quality + rejected_by_missing_best_claim,
        passages_deduplicated=passages_deduplicated,
        cards_produced=cards_produced,
        reranker_applied=bool(retrieval_backend),
        reranker_backend=retrieval_backend,
        notes=_p10_notes,
        # Pass 10 fields
        document_types_encountered=list(p10_document_types or []),
        parsers_attempted=list(p10_parsers_attempted or []),
        parser_selected=p10_parser_selected,
        parser_failures=p10_parser_failures,
        fallback_count=p10_fallback_count,
        extraction_quality_warnings=list(p10_quality_warnings or []),
        full_text_count=p10_full_text_count,
        abstract_only_count=p10_abstract_only_count,
        snippet_only_count=p10_snippet_only_count,
        partial_extraction_count=p10_partial_extraction_count,
        metadata_only_count=p10_metadata_only_count,
        snapshot_success_count=p10_snapshot_success,
        snapshot_failure_count=p10_snapshot_failure,
        page_aware_candidates=p10_page_aware_candidates,
        offset_validation_failures=p10_offset_validation_failures,
        # Pass 11 verification fields
        cards_verified=p11_cards_verified,
        cards_supported=p11_cards_supported,
        cards_partially_supported=p11_cards_partially_supported,
        cards_unsupported=p11_cards_unsupported,
        cards_contradicted=p11_cards_contradicted,
        cards_insufficient_context=p11_cards_insufficient_context,
        deterministic_mismatches_found=p11_deterministic_mismatches,
        semantic_verifier_attempted=p11_semantic_attempted,
        semantic_verifier_backend=p11_semantic_backend,
        semantic_verifier_failures=p11_semantic_failures,
        abstract_context_warnings=p11_abstract_context_warnings,
        safer_tags_generated=p11_safer_tags_generated,
        # Pass 12 citation fields
        citation_records_created=p12_records_created,
        crossref_verified_records=p12_crossref_verified,
        citation_fields_enriched=p12_fields_enriched,
        citation_conflicts_found=p12_conflicts_found,
        citation_records_complete=p12_records_complete,
        citation_records_with_warnings=p12_records_with_warnings,
        citation_records_incomplete=p12_records_incomplete,
        legacy_citations_migrated=p12_legacy_migrated,
        citation_renderer_failures=p12_renderer_failures,
    )

    # Build verification summary note
    _p11_parts: list[str] = []
    if p11_verification_summary:
        _p11_parts.append(p11_verification_summary)
    elif p11_cards_verified > 0:
        if p11_cards_supported:
            _p11_parts.append(f"{p11_cards_supported} card(s) directly supported the claim.")
        if p11_cards_partially_supported:
            _p11_parts.append(
                f"{p11_cards_partially_supported} card(s) supported a narrower version of the claim."
            )
        if p11_cards_contradicted:
            _p11_parts.append(
                f"{p11_cards_contradicted} source(s) contradicted the requested claim "
                "(kept as counterevidence)."
            )

    return SearchTraceResult(
        stages=[search_stage, extraction_stage],
        failure_reason=failure_reason,
        failure_detail=failure_detail,
        attempts_summary=attempts_summary,
        recovery_actions=recovery_actions,
        stopped_early=stopped_early,
        total_queries=len(queries_run),
        total_urls_found=sources_found,
        total_cards=cards_produced,
        dedup_removed=passages_deduplicated,
        retrieval_backend=retrieval_backend,
        # Pass 9
        source_type_distribution=dict(p9_source_distribution or {}),
        specialized_summary=p9_specialized_summary,
        # Pass 10
        extraction_summary=(
            _p10_notes[0] if (_p10_notes and not p10_extraction_summary) else p10_extraction_summary
        ),
        # Pass 11
        verification_summary=" ".join(_p11_parts) if _p11_parts else "",
        # Pass 12
        citation_summary=p12_citation_summary or (
            f"Citation records created for {p12_records_created} card(s)."
            if p12_records_created > 0 else ""
        ),
    )
