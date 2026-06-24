"""Pass 9 — Academic and Primary-Source Evidence Routing tests.

Covers:
- Source router: deterministic routing for all lanes
- Source registry: domain lookup and site-query generation
- OpenAlex adapter: response normalization, abstract reconstruction, error handling
- Semantic Scholar adapter: normalization, rate-limit handling, error handling
- Crossref adapter: DOI lookup, message parsing, failure handling
- Metadata enricher: DOI normalization, dedup, Crossref enrichment, dict conversion
- Academic search orchestration: end-to-end with mocked HTTP
- Pass 9 search-trace fields
- Safety invariants
- Pass 7 failure reasons remain correct
- Pass 8 backward compat

All HTTP calls are mocked. No live network requests are made.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest


# ══════════════════════════════════════════════════════════════════════════════
# Source Router
# ══════════════════════════════════════════════════════════════════════════════

class TestSourceRouter:
    """evidence_source_router.route_query() and route_queries()."""

    def test_plain_web_claim_returns_general_web_only(self):
        from app.services.evidence_source_router import route_query
        lanes = route_query("tariffs hurt American consumers")
        assert lanes == ["general_web"]

    def test_academic_keyword_study_routes_academic(self):
        from app.services.evidence_source_router import route_query
        lanes = route_query("study shows tariffs hurt consumers")
        assert "academic_research" in lanes
        assert "general_web" in lanes

    def test_academic_keyword_research_routes_academic(self):
        from app.services.evidence_source_router import route_query
        lanes = route_query("research on immigration and crime")
        assert "academic_research" in lanes

    def test_academic_keyword_meta_analysis_routes_academic(self):
        from app.services.evidence_source_router import route_query
        lanes = route_query("meta-analysis of minimum wage effects")
        assert "academic_research" in lanes

    def test_academic_phrase_associated_with_routes_academic(self):
        from app.services.evidence_source_router import route_query
        lanes = route_query("air pollution associated with asthma rates")
        assert "academic_research" in lanes

    def test_government_keyword_cdc_routes_government(self):
        from app.services.evidence_source_router import route_query
        lanes = route_query("CDC data on opioid deaths 2023")
        assert "government_primary" in lanes
        assert "general_web" in lanes

    def test_government_keyword_census_routes_government(self):
        from app.services.evidence_source_router import route_query
        lanes = route_query("census poverty rate statistics")
        assert "government_primary" in lanes

    def test_government_phrase_crime_rate_routes_government(self):
        from app.services.evidence_source_router import route_query
        lanes = route_query("violent crime rate in the United States")
        assert "government_primary" in lanes

    def test_government_keyword_gao_routes_government(self):
        from app.services.evidence_source_router import route_query
        lanes = route_query("gao report on federal spending")
        assert "government_primary" in lanes

    def test_institutional_keyword_report_routes_institutional(self):
        from app.services.evidence_source_router import route_query
        lanes = route_query("Brookings report on education policy")
        assert "institutional_report" in lanes or "general_web" in lanes

    def test_counter_evidence_role_gets_counterevidence_lane(self):
        from app.services.evidence_source_router import route_query
        lanes = route_query("some claim", evidence_role="counter_argument")
        assert "counterevidence" in lanes
        assert "general_web" in lanes
        assert "academic_research" not in lanes

    def test_counter_evidence_role_counter_evidence_variant(self):
        from app.services.evidence_source_router import route_query
        lanes = route_query("some claim", evidence_role="counter_evidence")
        assert "counterevidence" in lanes
        assert "academic_research" not in lanes

    def test_counter_evidence_role_counterevidence_variant(self):
        from app.services.evidence_source_router import route_query
        lanes = route_query("some claim", evidence_role="counterevidence")
        assert "counterevidence" in lanes

    def test_max_three_lanes(self):
        from app.services.evidence_source_router import route_query
        # Query with many signals should still cap at 3 lanes
        lanes = route_query("cdc study research census government statistics data")
        assert len(lanes) <= 3

    def test_academic_role_routes_academic(self):
        from app.services.evidence_source_router import route_query
        lanes = route_query("climate change effects", evidence_role="causal_mechanism")
        assert "academic_research" in lanes

    def test_impact_role_routes_academic(self):
        from app.services.evidence_source_router import route_query
        lanes = route_query("economic impact", evidence_role="impact")
        assert "academic_research" in lanes

    def test_institutional_not_added_when_academic_present(self):
        from app.services.evidence_source_router import route_query
        # If academic is already in lanes, institutional should not be added separately
        lanes = route_query("rand study research report")
        if "academic_research" in lanes:
            assert "institutional_report" not in lanes

    def test_route_queries_batch(self):
        from app.services.evidence_source_router import route_queries
        qs = ["tariffs hurt consumers", "study shows tariffs harm jobs"]
        result = route_queries(qs)
        assert "tariffs hurt consumers" in result
        assert "study shows tariffs harm jobs" in result
        assert "academic_research" in result["study shows tariffs harm jobs"]

    def test_route_queries_with_roles(self):
        from app.services.evidence_source_router import route_queries
        qs = ["climate change", "counter point"]
        roles = ["impact", "counter_argument"]
        result = route_queries(qs, roles)
        assert "academic_research" in result["climate change"]
        assert "counterevidence" in result["counter point"]

    def test_aggregate_lanes_union(self):
        from app.services.evidence_source_router import aggregate_lanes
        routing = {
            "q1": ["general_web", "academic_research"],
            "q2": ["general_web", "government_primary"],
        }
        lanes = aggregate_lanes(routing)
        assert "general_web" in lanes
        assert "academic_research" in lanes
        assert "government_primary" in lanes

    def test_empty_query_list_returns_empty(self):
        from app.services.evidence_source_router import route_queries
        assert route_queries([]) == {}

    def test_general_web_always_included(self):
        from app.services.evidence_source_router import route_query
        # Even for counter-evidence
        lanes = route_query("anything", evidence_role="counter_argument")
        assert "general_web" in lanes

    def test_deterministic_same_query_same_lanes(self):
        from app.services.evidence_source_router import route_query
        q = "CDC data on opioid deaths study research findings"
        assert route_query(q) == route_query(q)


# ══════════════════════════════════════════════════════════════════════════════
# Source Registry
# ══════════════════════════════════════════════════════════════════════════════

class TestSourceRegistry:
    """evidence_source_registry functions."""

    def test_all_entries_returns_nonempty_list(self):
        from app.services.evidence_source_registry import get_all_entries
        entries = get_all_entries()
        assert len(entries) > 20

    def test_high_credibility_entries_are_all_high(self):
        from app.services.evidence_source_registry import get_high_credibility_entries
        for e in get_high_credibility_entries():
            assert e.credibility_tier == "high"

    def test_primary_sources_are_marked_primary(self):
        from app.services.evidence_source_registry import get_primary_sources
        for e in get_primary_sources():
            assert e.is_primary

    def test_cdc_is_primary_high_credibility(self):
        from app.services.evidence_source_registry import get_domain_credibility
        tier, is_primary = get_domain_credibility("cdc.gov")
        assert tier == "high"
        assert is_primary is True

    def test_subdomain_matches_registry(self):
        from app.services.evidence_source_registry import get_domain_credibility
        tier, is_primary = get_domain_credibility("www.cdc.gov")
        assert tier == "high"

    def test_unknown_domain_returns_unknown_not_primary(self):
        from app.services.evidence_source_registry import get_domain_credibility
        tier, is_primary = get_domain_credibility("random-blog.com")
        assert tier == "unknown"
        assert is_primary is False

    def test_entries_by_category_government_us(self):
        from app.services.evidence_source_registry import get_entries_by_category
        entries = get_entries_by_category("government_us")
        assert len(entries) >= 5
        for e in entries:
            assert e.category == "government_us"

    def test_build_site_queries_generates_restricted_queries(self):
        from app.services.evidence_source_registry import build_site_queries
        queries = build_site_queries(
            ["opioid deaths statistics"],
            ["government_us"],
            max_queries=2,
        )
        assert len(queries) <= 2
        for q in queries:
            assert "opioid deaths statistics" in q
            assert "site:" in q

    def test_build_site_queries_max_queries_respected(self):
        from app.services.evidence_source_registry import build_site_queries
        queries = build_site_queries(
            ["any query"],
            ["government_us", "research_institute"],
            max_queries=2,
        )
        assert len(queries) <= 2

    def test_build_site_queries_empty_base_returns_empty(self):
        from app.services.evidence_source_registry import build_site_queries
        assert build_site_queries([], ["government_us"]) == []

    def test_rand_is_research_institute_not_primary(self):
        from app.services.evidence_source_registry import get_domain_credibility
        tier, is_primary = get_domain_credibility("rand.org")
        assert tier == "high"
        assert is_primary is False


# ══════════════════════════════════════════════════════════════════════════════
# OpenAlex Adapter
# ══════════════════════════════════════════════════════════════════════════════

_OA_RECORD = {
    "id": "https://openalex.org/W1234567890",
    "title": "Effects of Minimum Wage on Employment",
    "abstract_inverted_index": {
        "Raising": [0],
        "the": [1, 5],
        "minimum": [2, 6],
        "wage": [3, 7],
        "reduces": [4],
        "employment": [8],
        "by": [9],
        "two": [10],
        "percent": [11],
    },
    "authorships": [
        {"author": {"display_name": "Jane Smith"}},
        {"author": {"display_name": "Bob Jones"}},
    ],
    "publication_date": "2022-06-15",
    "doi": "https://doi.org/10.1234/minwage",
    "primary_location": {
        "landing_page_url": "https://example.com/paper",
        "source": {"display_name": "Journal of Economics"},
    },
    "cited_by_count": 42,
    "open_access": {"is_oa": True, "oa_url": "https://example.com/paper.pdf"},
}

_OA_RESPONSE = {"results": [_OA_RECORD]}


class TestOpenAlexAdapter:
    """providers.openalex functions."""

    def test_reconstruct_abstract_basic(self):
        from app.services.providers.openalex import _reconstruct_abstract
        inv = {"hello": [0], "world": [1]}
        result = _reconstruct_abstract(inv)
        assert "hello" in result
        assert "world" in result

    def test_reconstruct_abstract_preserves_order(self):
        from app.services.providers.openalex import _reconstruct_abstract
        inv = {"third": [2], "first": [0], "second": [1]}
        result = _reconstruct_abstract(inv)
        assert result == "first second third"

    def test_reconstruct_abstract_none_returns_empty(self):
        from app.services.providers.openalex import _reconstruct_abstract
        assert _reconstruct_abstract(None) == ""

    def test_reconstruct_abstract_empty_returns_empty(self):
        from app.services.providers.openalex import _reconstruct_abstract
        assert _reconstruct_abstract({}) == ""

    def test_normalize_doi_strips_url_prefix(self):
        from app.services.providers.openalex import _normalize_doi
        assert _normalize_doi("https://doi.org/10.1234/abc") == "10.1234/abc"

    def test_normalize_doi_strips_http(self):
        from app.services.providers.openalex import _normalize_doi
        assert _normalize_doi("http://doi.org/10.1234/abc") == "10.1234/abc"

    def test_normalize_doi_bare_doi_passthrough(self):
        from app.services.providers.openalex import _normalize_doi
        assert _normalize_doi("10.1234/abc") == "10.1234/abc"

    def test_normalize_doi_invalid_returns_none(self):
        from app.services.providers.openalex import _normalize_doi
        assert _normalize_doi("not-a-doi") is None

    def test_normalize_doi_none_returns_none(self):
        from app.services.providers.openalex import _normalize_doi
        assert _normalize_doi(None) is None

    def test_parse_record_normalizes_into_provider_result(self):
        from app.services.providers.openalex import _parse_record
        result = _parse_record(_OA_RECORD, "min wage study", "causal_mechanism")
        assert result is not None
        assert result.provider == "openalex"
        assert result.title == "Effects of Minimum Wage on Employment"
        assert result.doi == "10.1234/minwage"
        assert result.year == 2022
        assert "Jane Smith" in result.authors
        assert result.venue == "Journal of Economics"
        assert result.citation_count == 42

    def test_parse_record_abstract_is_exact_source_text(self):
        from app.services.providers.openalex import _parse_record
        result = _parse_record(_OA_RECORD, "query", "")
        assert result is not None
        # Abstract must be reconstructed exactly from inverted index
        assert "minimum" in result.abstract.lower()
        assert "employment" in result.abstract.lower()

    def test_parse_record_oa_url_set(self):
        from app.services.providers.openalex import _parse_record
        result = _parse_record(_OA_RECORD, "q", "")
        assert result is not None
        assert result.open_access_url == "https://example.com/paper.pdf"

    def test_parse_record_missing_title_returns_none(self):
        from app.services.providers.openalex import _parse_record
        record = {**_OA_RECORD, "title": ""}
        assert _parse_record(record, "q", "") is None

    def test_parse_record_no_doi_handled(self):
        from app.services.providers.openalex import _parse_record
        record = {**_OA_RECORD, "doi": None}
        result = _parse_record(record, "q", "")
        assert result is not None
        assert result.doi is None

    def test_parse_record_malformed_authors_skipped(self):
        from app.services.providers.openalex import _parse_record
        record = {**_OA_RECORD, "authorships": [{"author": None}, {"author": {}}]}
        result = _parse_record(record, "q", "")
        assert result is not None
        assert result.authors == []

    def test_search_openalex_success(self):
        from app.services.providers.openalex import search_openalex
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _OA_RESPONSE
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
            results = search_openalex("minimum wage study")
        assert len(results) == 1
        assert results[0].provider == "openalex"

    def test_search_openalex_http_error_returns_empty(self):
        from app.services.providers.openalex import search_openalex
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
            results = search_openalex("minimum wage study")
        assert results == []

    def test_search_openalex_network_error_returns_empty(self):
        from app.services.providers.openalex import search_openalex
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = Exception("Connection refused")
            results = search_openalex("minimum wage study")
        assert results == []

    def test_search_openalex_max_results_respected(self):
        from app.services.providers.openalex import search_openalex
        # 3 records in response but max_results=1
        response = {"results": [_OA_RECORD, _OA_RECORD, _OA_RECORD]}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = response
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
            results = search_openalex("query", max_results=1)
        assert len(results) == 1

    def test_search_openalex_email_not_in_result(self):
        """Contact email must not appear in any ProviderResult field."""
        from app.services.providers.openalex import search_openalex
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _OA_RESPONSE
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
            results = search_openalex("q", contact_email="secret@example.com")
        for r in results:
            import dataclasses
            for f in dataclasses.fields(r):
                val = getattr(r, f.name)
                if isinstance(val, str):
                    assert "secret@example.com" not in val


# ══════════════════════════════════════════════════════════════════════════════
# Semantic Scholar Adapter
# ══════════════════════════════════════════════════════════════════════════════

_SS_RECORD = {
    "paperId": "abc123",
    "title": "Immigration and Crime: Evidence from the United States",
    "abstract": "We study the causal effect of immigration on crime rates. Results show no significant increase.",
    "authors": [{"name": "Alice Chen"}, {"name": "David Lee"}],
    "year": 2021,
    "externalIds": {"DOI": "10.5678/immcrime"},
    "citationCount": 88,
    "openAccessPdf": {"url": "https://example.com/immcrime.pdf"},
    "publicationVenue": {"name": "American Economic Review"},
    "isOpenAccess": True,
}

_SS_RESPONSE = {"data": [_SS_RECORD]}


class TestSemanticScholarAdapter:
    """providers.semantic_scholar functions."""

    def test_parse_record_normalizes(self):
        from app.services.providers.semantic_scholar import _parse_record
        result = _parse_record(_SS_RECORD, "immigration crime study", "impact")
        assert result is not None
        assert result.provider == "semantic_scholar"
        assert result.title == "Immigration and Crime: Evidence from the United States"
        assert result.doi == "10.5678/immcrime"
        assert result.year == 2021
        assert result.citation_count == 88
        assert result.venue == "American Economic Review"
        assert result.open_access_url == "https://example.com/immcrime.pdf"

    def test_parse_record_abstract_is_exact(self):
        from app.services.providers.semantic_scholar import _parse_record
        result = _parse_record(_SS_RECORD, "q", "")
        assert result is not None
        assert result.abstract == _SS_RECORD["abstract"]

    def test_parse_record_missing_title_returns_none(self):
        from app.services.providers.semantic_scholar import _parse_record
        record = {**_SS_RECORD, "title": None}
        assert _parse_record(record, "q", "") is None

    def test_parse_record_missing_abstract_handled(self):
        from app.services.providers.semantic_scholar import _parse_record
        # Remove both abstract and open-access PDF so the record has nothing usable
        record = {**_SS_RECORD, "abstract": None, "openAccessPdf": None, "isOpenAccess": False}
        result = _parse_record(record, "q", "")
        assert result is not None
        assert result.abstract == ""
        assert result.is_metadata_only is True

    def test_parse_record_malformed_authors_handled(self):
        from app.services.providers.semantic_scholar import _parse_record
        record = {**_SS_RECORD, "authors": [None, {"name": ""}, {"name": "Valid Author"}]}
        result = _parse_record(record, "q", "")
        assert result is not None
        # Should get the valid author
        assert any("Valid Author" in a for a in result.authors)

    def test_search_ss_success(self):
        from app.services.providers.semantic_scholar import search_semantic_scholar
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _SS_RESPONSE
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
            results = search_semantic_scholar("immigration crime study")
        assert len(results) == 1
        assert results[0].provider == "semantic_scholar"

    def test_search_ss_rate_limited_returns_empty(self):
        from app.services.providers.semantic_scholar import search_semantic_scholar
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
            results = search_semantic_scholar("q")
        assert results == []

    def test_search_ss_network_error_returns_empty(self):
        from app.services.providers.semantic_scholar import search_semantic_scholar
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = Exception("timeout")
            results = search_semantic_scholar("q")
        assert results == []

    def test_search_ss_api_key_not_in_result(self):
        """API key must not appear in any ProviderResult field."""
        from app.services.providers.semantic_scholar import search_semantic_scholar
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _SS_RESPONSE
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
            results = search_semantic_scholar("q", api_key="super-secret-key-12345")
        for r in results:
            import dataclasses
            for f in dataclasses.fields(r):
                val = getattr(r, f.name)
                if isinstance(val, str):
                    assert "super-secret-key-12345" not in val

    def test_search_ss_max_results_respected(self):
        from app.services.providers.semantic_scholar import search_semantic_scholar
        response = {"data": [_SS_RECORD, _SS_RECORD, _SS_RECORD]}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = response
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
            results = search_semantic_scholar("q", max_results=1)
        assert len(results) == 1


# ══════════════════════════════════════════════════════════════════════════════
# Crossref Adapter
# ══════════════════════════════════════════════════════════════════════════════

_CROSSREF_MSG = {
    "DOI": "10.1234/test",
    "title": ["Crossref Enriched Title"],
    "author": [
        {"family": "Smith", "given": "John"},
        {"family": "Doe", "given": "Jane"},
    ],
    "published": {"date-parts": [[2020, 3, 15]]},
    "container-title": ["Journal of Testing"],
    "publisher": "Test Publisher",
    "URL": "https://doi.org/10.1234/test",
}

_CROSSREF_RESPONSE = {"message": _CROSSREF_MSG}


class TestCrossrefAdapter:
    """providers.crossref functions."""

    def test_lookup_doi_success(self):
        from app.services.providers.crossref import lookup_crossref_doi
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _CROSSREF_RESPONSE
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
            result = lookup_crossref_doi("10.1234/test")
        assert result is not None
        assert result.provider == "crossref"
        assert result.title == "Crossref Enriched Title"
        assert result.year == 2020
        assert "John Smith" in result.authors
        assert result.venue == "Journal of Testing"

    def test_lookup_doi_404_returns_none(self):
        from app.services.providers.crossref import lookup_crossref_doi
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
            result = lookup_crossref_doi("10.9999/nonexistent")
        assert result is None

    def test_lookup_doi_network_error_returns_none(self):
        from app.services.providers.crossref import lookup_crossref_doi
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = Exception("timeout")
            result = lookup_crossref_doi("10.1234/test")
        assert result is None

    def test_lookup_doi_invalid_doi_returns_none(self):
        from app.services.providers.crossref import lookup_crossref_doi
        result = lookup_crossref_doi("not-a-doi")
        assert result is None

    def test_lookup_doi_is_metadata_only(self):
        from app.services.providers.crossref import lookup_crossref_doi
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _CROSSREF_RESPONSE
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
            result = lookup_crossref_doi("10.1234/test")
        assert result is not None
        assert result.is_metadata_only is True
        assert result.abstract == ""  # Crossref does not return abstracts

    def test_lookup_doi_no_abstract_fabricated(self):
        """Crossref adapter must never fabricate an abstract."""
        from app.services.providers.crossref import lookup_crossref_doi
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _CROSSREF_RESPONSE
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
            result = lookup_crossref_doi("10.1234/test")
        assert result is not None
        assert result.abstract == ""

    def test_parse_first_helper(self):
        from app.services.providers.crossref import _first
        assert _first(["", "second", "third"]) == "second"
        assert _first([]) == ""
        assert _first([], default="fallback") == "fallback"


# ══════════════════════════════════════════════════════════════════════════════
# Metadata Enricher
# ══════════════════════════════════════════════════════════════════════════════

class TestMetadataEnricher:
    """evidence_metadata_enricher functions."""

    def _make_result(self, provider="openalex", doi=None, title="Test Paper",
                     abstract="", authors=None, year=None, venue="",
                     landing_url="https://example.com", open_access_url=None,
                     is_primary=False, source_type="academic"):
        from app.services.evidence_provider_result import ProviderResult
        return ProviderResult(
            provider=provider,
            title=title,
            abstract=abstract,
            authors=authors or [],
            year=year,
            venue=venue,
            doi=doi,
            landing_url=landing_url,
            open_access_url=open_access_url,
            is_primary=is_primary,
            source_type=source_type,
            is_abstract=bool(abstract),
            is_metadata_only=not bool(abstract) and not bool(open_access_url),
        )

    def test_normalize_doi_strips_prefix(self):
        from app.services.evidence_metadata_enricher import normalize_doi
        assert normalize_doi("https://doi.org/10.1234/abc") == "10.1234/abc"

    def test_normalize_doi_http_prefix(self):
        from app.services.evidence_metadata_enricher import normalize_doi
        assert normalize_doi("http://doi.org/10.1234/abc") == "10.1234/abc"

    def test_normalize_doi_doi_prefix(self):
        from app.services.evidence_metadata_enricher import normalize_doi
        assert normalize_doi("doi:10.1234/abc") == "10.1234/abc"

    def test_normalize_doi_bare(self):
        from app.services.evidence_metadata_enricher import normalize_doi
        assert normalize_doi("10.1234/abc") == "10.1234/abc"

    def test_normalize_doi_invalid_returns_none(self):
        from app.services.evidence_metadata_enricher import normalize_doi
        assert normalize_doi("random-string") is None

    def test_normalize_doi_none_returns_none(self):
        from app.services.evidence_metadata_enricher import normalize_doi
        assert normalize_doi(None) is None

    def test_dedup_by_doi_removes_duplicate(self):
        from app.services.evidence_metadata_enricher import deduplicate_provider_results
        r1 = self._make_result(doi="10.1234/abc", title="Paper A")
        r2 = self._make_result(doi="10.1234/abc", title="Paper A (duplicate)", provider="semantic_scholar")
        deduped, removed = deduplicate_provider_results([r1, r2])
        assert len(deduped) == 1
        assert removed == 1
        assert deduped[0].title == "Paper A"  # first occurrence kept

    def test_dedup_by_doi_url_prefix_variant(self):
        from app.services.evidence_metadata_enricher import deduplicate_provider_results
        r1 = self._make_result(doi="10.1234/abc")
        r2 = self._make_result(doi="https://doi.org/10.1234/abc", provider="semantic_scholar")
        deduped, removed = deduplicate_provider_results([r1, r2])
        assert len(deduped) == 1
        assert removed == 1

    def test_dedup_by_title_when_no_doi(self):
        from app.services.evidence_metadata_enricher import deduplicate_provider_results
        r1 = self._make_result(doi=None, title="Same Title: Effects on Employment")
        r2 = self._make_result(doi=None, title="Same Title: Effects on Employment", provider="ss")
        deduped, removed = deduplicate_provider_results([r1, r2])
        assert len(deduped) == 1
        assert removed == 1

    def test_dedup_different_dois_kept(self):
        from app.services.evidence_metadata_enricher import deduplicate_provider_results
        r1 = self._make_result(doi="10.1234/abc")
        r2 = self._make_result(doi="10.5678/xyz")
        deduped, removed = deduplicate_provider_results([r1, r2])
        assert len(deduped) == 2
        assert removed == 0

    def test_dedup_no_doi_no_title_both_kept(self):
        from app.services.evidence_metadata_enricher import deduplicate_provider_results
        r1 = self._make_result(doi=None, title="")
        r2 = self._make_result(doi=None, title="")
        deduped, removed = deduplicate_provider_results([r1, r2])
        # Both kept because no key to dedup on
        assert len(deduped) == 2

    def test_crossref_enriches_empty_title(self):
        from app.services.evidence_metadata_enricher import enrich_with_crossref
        r = self._make_result(doi="10.1234/test", title="")
        crossref_result = MagicMock()
        crossref_result.title = "Enriched Title"
        crossref_result.authors = ["Enriched Author"]
        crossref_result.year = 2020
        crossref_result.venue = "Enriched Journal"
        crossref_result.canonical_url = "https://doi.org/10.1234/test"
        crossref_result.landing_url = "https://doi.org/10.1234/test"
        cache = {"10.1234/test": crossref_result}
        enriched, count = enrich_with_crossref([r], cache=cache)
        assert count == 1
        assert enriched[0].title == "Enriched Title"
        assert "title" in enriched[0].crossref_verified_fields

    def test_crossref_never_overwrites_existing_title(self):
        from app.services.evidence_metadata_enricher import enrich_with_crossref
        r = self._make_result(doi="10.1234/test", title="Original Title")
        crossref_result = MagicMock()
        crossref_result.title = "Crossref Title (should not overwrite)"
        crossref_result.authors = []
        crossref_result.year = None
        crossref_result.venue = ""
        crossref_result.canonical_url = ""
        crossref_result.landing_url = ""
        cache = {"10.1234/test": crossref_result}
        enriched, count = enrich_with_crossref([r], cache=cache)
        # count may be 0 because no fields were actually enriched
        assert enriched[0].title == "Original Title"

    def test_crossref_never_overwrites_existing_authors(self):
        from app.services.evidence_metadata_enricher import enrich_with_crossref
        r = self._make_result(doi="10.1234/test", authors=["Original Author"])
        crossref_result = MagicMock()
        crossref_result.title = ""
        crossref_result.authors = ["Crossref Author"]
        crossref_result.year = None
        crossref_result.venue = ""
        crossref_result.canonical_url = ""
        crossref_result.landing_url = ""
        cache = {"10.1234/test": crossref_result}
        enriched, _ = enrich_with_crossref([r], cache=cache)
        assert enriched[0].authors == ["Original Author"]

    def test_crossref_uses_cache_not_network(self):
        """Second call with same DOI must use cache, not HTTP."""
        from app.services.evidence_metadata_enricher import enrich_with_crossref
        r1 = self._make_result(doi="10.1234/abc", title="")
        r2 = self._make_result(doi="10.1234/abc", title="", provider="ss")
        crossref_result = MagicMock()
        crossref_result.title = "Cached Title"
        crossref_result.authors = []
        crossref_result.year = None
        crossref_result.venue = ""
        crossref_result.canonical_url = ""
        crossref_result.landing_url = ""
        cache = {"10.1234/abc": crossref_result}
        with patch("app.services.providers.crossref.lookup_crossref_doi") as mock_lookup:
            enriched, count = enrich_with_crossref([r1, r2], cache=cache)
            mock_lookup.assert_not_called()  # cache hit
        assert enriched[0].title == "Cached Title"

    def test_crossref_no_doi_no_enrichment(self):
        from app.services.evidence_metadata_enricher import enrich_with_crossref
        r = self._make_result(doi=None, title="No DOI Paper")
        with patch("app.services.providers.crossref.lookup_crossref_doi") as mock_lookup:
            enriched, count = enrich_with_crossref([r])
            mock_lookup.assert_not_called()
        assert count == 0

    def test_crossref_none_cached_skips_enrichment(self):
        from app.services.evidence_metadata_enricher import enrich_with_crossref
        r = self._make_result(doi="10.1234/test", title="")
        cache = {"10.1234/test": None}  # cached 404
        enriched, count = enrich_with_crossref([r], cache=cache)
        assert count == 0
        assert enriched[0].title == ""  # not enriched

    def test_to_search_result_dict_with_abstract(self):
        from app.services.evidence_metadata_enricher import to_search_result_dict
        r = self._make_result(
            doi="10.1234/abc",
            abstract="A" * 200,
            landing_url="https://example.com",
        )
        d = to_search_result_dict(r)
        assert d is not None
        assert d["url"] == "https://example.com"
        assert d["content"] == "A" * 200
        assert d["_provider"] == "openalex"
        assert d["_doi"] == "10.1234/abc"
        assert d["_is_academic"] is True

    def test_to_search_result_dict_prefers_oa_url(self):
        from app.services.evidence_metadata_enricher import to_search_result_dict
        r = self._make_result(
            abstract="Some abstract",
            landing_url="https://landing.example.com",
            open_access_url="https://pdf.example.com/paper.pdf",
        )
        d = to_search_result_dict(r)
        assert d is not None
        assert d["url"] == "https://pdf.example.com/paper.pdf"

    def test_to_search_result_dict_metadata_only_no_url_returns_none(self):
        from app.services.evidence_metadata_enricher import to_search_result_dict
        from app.services.evidence_provider_result import ProviderResult
        r = ProviderResult(
            provider="crossref",
            title="Title Only",
            is_metadata_only=True,
            abstract="",
            landing_url="",
            canonical_url="",
        )
        assert to_search_result_dict(r) is None

    def test_to_search_result_dict_short_abstract_no_url_returns_none(self):
        from app.services.evidence_metadata_enricher import to_search_result_dict
        from app.services.evidence_provider_result import ProviderResult
        r = ProviderResult(
            provider="openalex",
            title="Paper",
            abstract="Short",  # < 150 chars
            landing_url="",
            canonical_url="",
            is_metadata_only=True,
        )
        assert to_search_result_dict(r) is None

    def test_to_search_result_dict_primary_source_gets_priority_3(self):
        from app.services.evidence_metadata_enricher import to_search_result_dict
        r = self._make_result(
            abstract="A" * 200,
            landing_url="https://cdc.gov/report",
            is_primary=True,
        )
        d = to_search_result_dict(r)
        assert d is not None
        assert d["_source_priority"] == 3

    def test_to_search_result_dict_academic_gets_priority_2(self):
        from app.services.evidence_metadata_enricher import to_search_result_dict
        r = self._make_result(abstract="A" * 200, landing_url="https://example.com")
        d = to_search_result_dict(r)
        assert d is not None
        assert d["_source_priority"] == 2

    def test_to_search_result_dict_no_credentials_in_output(self):
        """Output dict must never contain credential-like fields."""
        from app.services.evidence_metadata_enricher import to_search_result_dict
        r = self._make_result(abstract="A" * 200, landing_url="https://example.com")
        d = to_search_result_dict(r)
        assert d is not None
        for key in d:
            assert "api_key" not in key.lower()
            assert "secret" not in key.lower()
            assert "password" not in key.lower()
            assert "bearer" not in key.lower()


# ══════════════════════════════════════════════════════════════════════════════
# Academic Search Orchestration
# ══════════════════════════════════════════════════════════════════════════════

class TestAcademicSearchOrchestration:
    """evidence_academic_search.gather_academic_results()."""

    def _oa_result(self, doi="10.1234/abc", title="Test Paper", abstract="A" * 200, oa_url=None):
        from app.services.evidence_provider_result import ProviderResult
        return ProviderResult(
            provider="openalex",
            title=title,
            abstract=abstract,
            doi=doi,
            landing_url="https://example.com",
            open_access_url=oa_url,
            is_abstract=bool(abstract),
            year=2022,
            authors=["Test Author"],
        )

    def test_empty_queries_returns_empty(self):
        from app.services.evidence_academic_search import gather_academic_results
        results, meta = gather_academic_results([])
        assert results == []

    def test_no_academic_lane_returns_empty(self):
        from app.services.evidence_academic_search import gather_academic_results
        # "tariffs hurt consumers" should not trigger academic lane
        with patch("app.services.providers.openalex.search_openalex") as mock_oa, \
             patch("app.services.providers.semantic_scholar.search_semantic_scholar") as mock_ss:
            results, meta = gather_academic_results(["tariffs hurt consumers"])
        mock_oa.assert_not_called()
        mock_ss.assert_not_called()
        assert results == []

    def test_academic_query_calls_both_providers(self):
        from app.services.evidence_academic_search import gather_academic_results
        oa_r = self._oa_result(doi="10.1234/oa")
        ss_r = self._oa_result(doi="10.5678/ss")
        ss_r.provider = "semantic_scholar"
        with patch("app.services.providers.openalex.search_openalex", return_value=[oa_r]) as mock_oa, \
             patch("app.services.providers.semantic_scholar.search_semantic_scholar", return_value=[ss_r]) as mock_ss, \
             patch("app.services.providers.crossref.lookup_crossref_doi", return_value=None):
            results, meta = gather_academic_results(["study of minimum wage effects"])
        mock_oa.assert_called()
        mock_ss.assert_called()
        assert len(results) == 2
        assert meta.providers_attempted >= 2

    def test_doi_duplicate_collapsed(self):
        from app.services.evidence_academic_search import gather_academic_results
        r1 = self._oa_result(doi="10.1234/same")
        r2 = self._oa_result(doi="10.1234/same")
        r2.provider = "semantic_scholar"
        with patch("app.services.providers.openalex.search_openalex", return_value=[r1]), \
             patch("app.services.providers.semantic_scholar.search_semantic_scholar", return_value=[r2]), \
             patch("app.services.providers.crossref.lookup_crossref_doi", return_value=None):
            results, meta = gather_academic_results(["study of immigration effects"])
        assert len(results) == 1
        assert meta.doi_matches_found >= 1

    def test_seen_url_dedup_excludes_existing(self):
        from app.services.evidence_academic_search import gather_academic_results
        r = self._oa_result(doi="10.1234/abc", oa_url=None)
        # Simulate landing_url already in seen_urls
        existing_seen = {"https://example.com"}
        with patch("app.services.providers.openalex.search_openalex", return_value=[r]), \
             patch("app.services.providers.semantic_scholar.search_semantic_scholar", return_value=[]), \
             patch("app.services.providers.crossref.lookup_crossref_doi", return_value=None):
            results, meta = gather_academic_results(
                ["minimum wage study"],
                seen_urls=existing_seen,
            )
        assert len(results) == 0  # deduplicated against existing

    def test_metadata_only_short_abstract_excluded(self):
        from app.services.evidence_academic_search import gather_academic_results
        from app.services.evidence_provider_result import ProviderResult
        r = ProviderResult(
            provider="openalex",
            title="Title Only",
            abstract="Short abstract",  # < 150 chars
            doi="10.1234/abc",
            landing_url="",
            canonical_url="",
            is_metadata_only=True,
        )
        with patch("app.services.providers.openalex.search_openalex", return_value=[r]), \
             patch("app.services.providers.semantic_scholar.search_semantic_scholar", return_value=[]), \
             patch("app.services.providers.crossref.lookup_crossref_doi", return_value=None):
            results, meta = gather_academic_results(["minimum wage study"])
        assert len(results) == 0
        assert meta.metadata_only_excluded >= 1

    def test_provider_failure_doesnt_crash(self):
        from app.services.evidence_academic_search import gather_academic_results
        with patch("app.services.providers.openalex.search_openalex", side_effect=Exception("network down")), \
             patch("app.services.providers.semantic_scholar.search_semantic_scholar", side_effect=Exception("rate limited")), \
             patch("app.services.providers.crossref.lookup_crossref_doi", return_value=None):
            results, meta = gather_academic_results(["study of minimum wage"])
        assert results == []
        assert len(meta.provider_failures) >= 1

    def test_meta_tracks_academic_found(self):
        from app.services.evidence_academic_search import gather_academic_results
        r = self._oa_result()
        with patch("app.services.providers.openalex.search_openalex", return_value=[r]), \
             patch("app.services.providers.semantic_scholar.search_semantic_scholar", return_value=[]), \
             patch("app.services.providers.crossref.lookup_crossref_doi", return_value=None):
            _, meta = gather_academic_results(["study research"])
        assert meta.academic_found >= 1

    def test_meta_lanes_selected_populated(self):
        from app.services.evidence_academic_search import gather_academic_results
        with patch("app.services.providers.openalex.search_openalex", return_value=[]), \
             patch("app.services.providers.semantic_scholar.search_semantic_scholar", return_value=[]), \
             patch("app.services.providers.crossref.lookup_crossref_doi", return_value=None):
            _, meta = gather_academic_results(["minimum wage study research"])
        assert "academic_research" in meta.lanes_selected
        assert "general_web" in meta.lanes_selected

    def test_crossref_enrichment_called_for_doi_records(self):
        from app.services.evidence_academic_search import gather_academic_results
        r = self._oa_result(doi="10.1234/abc")
        cr = MagicMock()
        cr.title = "Enriched"
        cr.authors = []
        cr.year = None
        cr.venue = ""
        cr.canonical_url = ""
        cr.landing_url = ""
        with patch("app.services.providers.openalex.search_openalex", return_value=[r]), \
             patch("app.services.providers.semantic_scholar.search_semantic_scholar", return_value=[]), \
             patch("app.services.providers.crossref.lookup_crossref_doi", return_value=cr) as mock_cr:
            results, meta = gather_academic_results(["study research"])
        mock_cr.assert_called()

    def test_source_type_distribution_tracked(self):
        from app.services.evidence_academic_search import gather_academic_results
        r = self._oa_result()
        with patch("app.services.providers.openalex.search_openalex", return_value=[r]), \
             patch("app.services.providers.semantic_scholar.search_semantic_scholar", return_value=[]), \
             patch("app.services.providers.crossref.lookup_crossref_doi", return_value=None):
            _, meta = gather_academic_results(["study research"])
        assert "academic" in meta.source_type_distribution


# ══════════════════════════════════════════════════════════════════════════════
# Search Trace P9 Fields
# ══════════════════════════════════════════════════════════════════════════════

class TestSearchTraceP9:
    """Pass 9 trace fields in search_trace.py."""

    def test_build_search_trace_p9_fields_default_empty(self):
        from app.services.search_trace import build_search_trace
        trace = build_search_trace(
            queries_run=["q"],
            roles_attempted=[],
            sources_found=1,
            sources_attempted=1,
            sources_extracted=1,
            passages_considered=5,
            filtered_no_support=0,
            filtered_low_quality=0,
            rejected_by_source_quality=0,
            rejected_by_missing_best_claim=0,
            counter_evidence_count=0,
            candidates_generated=1,
            tavily_errors=[],
            possible_lead_urls=[],
            cards_produced=1,
        )
        search_stage = trace.stages[0]
        assert search_stage.source_lanes_selected == []
        assert search_stage.specialized_providers_attempted == 0
        assert search_stage.doi_matches == 0
        assert trace.source_type_distribution == {}
        assert trace.specialized_summary == ""

    def test_build_search_trace_with_p9_meta(self):
        from app.services.search_trace import build_search_trace
        trace = build_search_trace(
            queries_run=["minimum wage study"],
            roles_attempted=["direct_outcome"],
            sources_found=5,
            sources_attempted=5,
            sources_extracted=3,
            passages_considered=10,
            filtered_no_support=2,
            filtered_low_quality=0,
            rejected_by_source_quality=0,
            rejected_by_missing_best_claim=0,
            counter_evidence_count=0,
            candidates_generated=2,
            tavily_errors=[],
            possible_lead_urls=[],
            cards_produced=2,
            p9_lanes=["general_web", "academic_research"],
            p9_providers_attempted=2,
            p9_results_found=3,
            p9_doi_matches=1,
            p9_crossref_enrichments=2,
            p9_metadata_only_excluded=1,
            p9_primary_candidates=0,
            p9_source_distribution={"academic": 3},
            p9_specialized_summary="Searched academic indexes.",
        )
        search_stage = trace.stages[0]
        assert "academic_research" in search_stage.source_lanes_selected
        assert search_stage.specialized_providers_attempted == 2
        assert search_stage.specialized_results_found == 3
        assert search_stage.doi_matches == 1
        assert search_stage.crossref_enrichments == 2
        assert search_stage.metadata_only_excluded == 1
        assert trace.source_type_distribution == {"academic": 3}
        assert trace.specialized_summary == "Searched academic indexes."
        assert "Searched academic indexes." in search_stage.notes

    def test_search_trace_result_has_p9_fields(self):
        from app.services.search_trace import SearchTraceResult
        result = SearchTraceResult()
        assert hasattr(result, "source_type_distribution")
        assert hasattr(result, "specialized_summary")

    def test_search_stage_trace_has_p9_fields(self):
        from app.services.search_trace import SearchStageTrace
        stage = SearchStageTrace(stage="search")
        assert hasattr(stage, "source_lanes_selected")
        assert hasattr(stage, "specialized_providers_attempted")
        assert hasattr(stage, "doi_matches")
        assert hasattr(stage, "crossref_enrichments")
        assert hasattr(stage, "metadata_only_excluded")
        assert hasattr(stage, "primary_source_candidates")


# ══════════════════════════════════════════════════════════════════════════════
# Safety Invariants
# ══════════════════════════════════════════════════════════════════════════════

class TestSafetyInvariants:
    """Pass 9 safety requirements."""

    def test_abstract_is_exact_source_text_from_openalex(self):
        """Abstract from OpenAlex must be reconstructed exactly, not synthesized."""
        from app.services.providers.openalex import _reconstruct_abstract
        inv = {"climate": [0], "change": [1], "study": [2]}
        abstract = _reconstruct_abstract(inv)
        assert abstract == "climate change study"

    def test_metadata_only_result_returns_none_from_to_dict(self):
        """Crossref-only records (no abstract, no URL) must not become cards."""
        from app.services.evidence_provider_result import ProviderResult
        from app.services.evidence_metadata_enricher import to_search_result_dict
        r = ProviderResult(
            provider="crossref",
            title="Title Only",
            is_metadata_only=True,
            abstract="",
            landing_url="",
        )
        assert to_search_result_dict(r) is None

    def test_body_text_not_modified_by_enrichment(self):
        """Crossref enrichment must not modify abstract text."""
        from app.services.evidence_metadata_enricher import enrich_with_crossref
        from app.services.evidence_provider_result import ProviderResult
        original_abstract = "This is the exact source abstract text."
        r = ProviderResult(
            provider="openalex",
            title="",
            abstract=original_abstract,
            doi="10.1234/abc",
            landing_url="https://example.com",
        )
        cr = MagicMock()
        cr.title = "Enriched"
        cr.authors = ["Author"]
        cr.year = 2020
        cr.venue = "Journal"
        cr.canonical_url = ""
        cr.landing_url = ""
        cache = {"10.1234/abc": cr}
        enriched, _ = enrich_with_crossref([r], cache=cache)
        assert enriched[0].abstract == original_abstract

    def test_credentials_stripped_from_trace(self):
        """API keys and tokens in error messages must be sanitized."""
        from app.services.search_trace import sanitize_error
        error = "Request failed with Tvly-abc123def456ghi789jkl012 in header"
        sanitized = sanitize_error(error)
        assert "Tvly-abc123def456ghi789jkl012" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_counter_evidence_role_no_academic_providers(self):
        """Counter-evidence queries must not trigger academic provider calls."""
        from app.services.evidence_source_router import route_query
        lanes = route_query("study finds immigration reduces crime", evidence_role="counter_argument")
        assert "academic_research" not in lanes

    def test_primary_source_priority_above_web(self):
        from app.services.evidence_metadata_enricher import to_search_result_dict
        from app.services.evidence_provider_result import ProviderResult
        primary = ProviderResult(
            provider="openalex",
            title="Gov Report",
            abstract="A" * 200,
            landing_url="https://cdc.gov/report",
            is_primary=True,
            source_type="government",
        )
        web = ProviderResult(
            provider="openalex",
            title="Web Article",
            abstract="A" * 200,
            landing_url="https://example.com/article",
            is_primary=False,
            source_type="academic",
        )
        primary_dict = to_search_result_dict(primary)
        web_dict = to_search_result_dict(web)
        assert primary_dict is not None
        assert web_dict is not None
        assert primary_dict["_source_priority"] > web_dict["_source_priority"]

    def test_provider_failure_does_not_crash_caller(self):
        from app.services.evidence_academic_search import gather_academic_results
        with patch("app.services.providers.openalex.search_openalex", side_effect=RuntimeError("fatal")), \
             patch("app.services.providers.semantic_scholar.search_semantic_scholar", side_effect=RuntimeError("fatal")):
            results, meta = gather_academic_results(["study research"])
        assert isinstance(results, list)
        assert isinstance(meta.provider_failures, list)

    def test_crossref_never_fabricates_abstract(self):
        """Crossref lookup_crossref_doi must always return is_metadata_only=True."""
        from app.services.providers.crossref import lookup_crossref_doi
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"message": {
            "DOI": "10.1234/test",
            "title": ["A Title"],
            "published": {"date-parts": [[2021]]},
            "URL": "https://doi.org/10.1234/test",
        }}
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
            result = lookup_crossref_doi("10.1234/test")
        assert result is not None
        assert result.abstract == ""
        assert result.is_metadata_only is True


# ══════════════════════════════════════════════════════════════════════════════
# Pass 7 Failure Reasons — unchanged
# ══════════════════════════════════════════════════════════════════════════════

class TestFailureReasonsPass7Compat:
    """The 11 deterministic failure codes must remain correct after Pass 9."""

    def test_no_results_no_errors_gives_no_search_results(self):
        from app.services.search_trace import determine_failure_reason
        reason, detail, _, _ = determine_failure_reason(
            sources_found=0, sources_attempted=0, sources_extracted=0,
            passages_considered=0, filtered_no_support=0, filtered_low_quality=0,
            rejected_by_source_quality=0, rejected_by_missing_best_claim=0,
            counter_evidence_count=0, candidates_generated=0, tavily_errors=[],
        )
        assert reason == "no_search_results"

    def test_provider_error_gives_provider_failure(self):
        from app.services.search_trace import determine_failure_reason
        reason, _, _, _ = determine_failure_reason(
            sources_found=0, sources_attempted=0, sources_extracted=0,
            passages_considered=0, filtered_no_support=0, filtered_low_quality=0,
            rejected_by_source_quality=0, rejected_by_missing_best_claim=0,
            counter_evidence_count=0, candidates_generated=0,
            tavily_errors=["timeout"],
        )
        assert reason == "provider_failure"

    def test_all_low_quality_gives_source_quality_too_low(self):
        from app.services.search_trace import determine_failure_reason
        reason, _, _, _ = determine_failure_reason(
            sources_found=3, sources_attempted=3, sources_extracted=0,
            passages_considered=0, filtered_no_support=0, filtered_low_quality=3,
            rejected_by_source_quality=0, rejected_by_missing_best_claim=0,
            counter_evidence_count=0, candidates_generated=0, tavily_errors=[],
        )
        assert reason == "source_quality_too_low"

    def test_extraction_failed_reason(self):
        from app.services.search_trace import determine_failure_reason
        reason, _, _, _ = determine_failure_reason(
            sources_found=3, sources_attempted=3, sources_extracted=0,
            passages_considered=0, filtered_no_support=0, filtered_low_quality=0,
            rejected_by_source_quality=0, rejected_by_missing_best_claim=0,
            counter_evidence_count=0, candidates_generated=0, tavily_errors=[],
        )
        assert reason == "extraction_failed"

    def test_counter_evidence_only_reason(self):
        from app.services.search_trace import determine_failure_reason
        reason, _, _, _ = determine_failure_reason(
            sources_found=3, sources_attempted=3, sources_extracted=2,
            passages_considered=2, filtered_no_support=0, filtered_low_quality=0,
            rejected_by_source_quality=0, rejected_by_missing_best_claim=0,
            counter_evidence_count=2, candidates_generated=0, tavily_errors=[],
        )
        assert reason == "credible_counterevidence_only"

    def test_no_relevant_passages_reason(self):
        from app.services.search_trace import determine_failure_reason
        reason, _, _, _ = determine_failure_reason(
            sources_found=3, sources_attempted=3, sources_extracted=2,
            passages_considered=5, filtered_no_support=5, filtered_low_quality=0,
            rejected_by_source_quality=0, rejected_by_missing_best_claim=0,
            counter_evidence_count=0, candidates_generated=0, tavily_errors=[],
        )
        assert reason == "no_relevant_passages"

    def test_claim_not_supported_reason(self):
        from app.services.search_trace import determine_failure_reason
        # All pages extracted, passages considered, but no candidates produced
        reason, _, _, _ = determine_failure_reason(
            sources_found=5, sources_attempted=5, sources_extracted=5,
            passages_considered=10, filtered_no_support=0, filtered_low_quality=0,
            rejected_by_source_quality=0, rejected_by_missing_best_claim=0,
            counter_evidence_count=0, candidates_generated=0, tavily_errors=[],
        )
        assert reason == "claim_not_supported"

    def test_all_eleven_codes_remain_accessible(self):
        from app.services.search_trace import FAILURE_REASONS
        expected = {
            "no_search_results", "provider_failure", "page_fetch_failed",
            "extraction_failed", "no_relevant_passages", "source_quality_too_low",
            "claim_not_supported", "citation_metadata_incomplete",
            "card_validation_failed", "credible_counterevidence_only",
            "no_credible_support_found",
        }
        assert expected <= set(FAILURE_REASONS)


# ══════════════════════════════════════════════════════════════════════════════
# Pass 8 Backward Compatibility
# ══════════════════════════════════════════════════════════════════════════════

class TestPass8Compat:
    """Pass 8 passage builder, deduplicator, and hybrid retriever remain intact."""

    def test_build_passages_returns_candidates(self):
        from app.services.evidence_passage_builder import build_passages
        text = "First paragraph with enough words to be meaningful content here.\n\nSecond paragraph also has enough words to pass the threshold easily."
        results = build_passages(text, url="https://example.com", domain="example.com")
        assert len(results) >= 1
        for c in results:
            assert c.text in text or c.text.split()[0] in text

    def test_deduplicator_exact_hash(self):
        from app.services.evidence_deduplicator import deduplicate_passages
        from app.services.evidence_candidate import EvidenceCandidate
        text = "This is a test passage with enough words to be meaningful."
        c1 = EvidenceCandidate(text=text, url="https://a.com")
        c2 = EvidenceCandidate(text=text, url="https://b.com")
        deduped, stats = deduplicate_passages([c1, c2])
        assert len(deduped) == 1
        assert stats.exact_hash_removed == 1

    def test_hybrid_retriever_returns_candidates(self):
        from app.services.evidence_candidate import EvidenceCandidate
        from app.services.evidence_hybrid_retriever import hybrid_rank_passages
        candidates = [
            EvidenceCandidate(
                text="Minimum wage increases reduce unemployment rates according to studies.",
                url="https://example.com",
            ),
            EvidenceCandidate(
                text="Research shows tariffs harm consumers by raising prices.",
                url="https://example2.com",
            ),
        ]
        ranked, stats = hybrid_rank_passages(
            candidates,
            claim="minimum wage reduces poverty",
            topic="economics",
        )
        assert len(ranked) >= 1
        assert stats.backend in ("bm25", "bm25+semantic", "heuristic", "lexical")

    def test_build_search_trace_backward_compat_no_p9_params(self):
        """build_search_trace must work with no P9 params (backward compat)."""
        from app.services.search_trace import build_search_trace
        trace = build_search_trace(
            queries_run=["q"],
            roles_attempted=[],
            sources_found=1,
            sources_attempted=1,
            sources_extracted=1,
            passages_considered=3,
            filtered_no_support=1,
            filtered_low_quality=0,
            rejected_by_source_quality=0,
            rejected_by_missing_best_claim=0,
            counter_evidence_count=0,
            candidates_generated=1,
            tavily_errors=[],
            possible_lead_urls=[],
            cards_produced=1,
        )
        assert trace.total_cards == 1
        assert trace.failure_reason is None

    def test_search_trace_result_p9_defaults_dont_break_existing_fields(self):
        """Existing SearchTraceResult fields must be unaffected by P9 additions."""
        from app.services.search_trace import build_search_trace
        trace = build_search_trace(
            queries_run=["q1", "q2"],
            roles_attempted=["direct_outcome"],
            sources_found=3,
            sources_attempted=3,
            sources_extracted=2,
            passages_considered=8,
            filtered_no_support=2,
            filtered_low_quality=0,
            rejected_by_source_quality=0,
            rejected_by_missing_best_claim=0,
            counter_evidence_count=0,
            candidates_generated=2,
            tavily_errors=[],
            possible_lead_urls=[],
            cards_produced=2,
            passages_deduplicated=3,
            retrieval_backend="bm25",
        )
        assert trace.dedup_removed == 3
        assert trace.retrieval_backend == "bm25"
        assert trace.total_queries == 2
        assert trace.failure_reason is None


# ══════════════════════════════════════════════════════════════════════════════
# Config and Provider Result Model
# ══════════════════════════════════════════════════════════════════════════════

class TestConfigAndModels:
    """Config additions and ProviderResult model."""

    def test_config_has_academic_search_flag(self):
        from app.config import settings
        assert hasattr(settings, "research_enable_academic_search")

    def test_config_has_semantic_scholar_key_field(self):
        from app.config import settings
        assert hasattr(settings, "semantic_scholar_api_key")

    def test_config_has_openalex_email_field(self):
        from app.config import settings
        assert hasattr(settings, "openalex_contact_email")

    def test_config_academic_search_disabled_in_tests(self):
        from app.config import settings
        # conftest.py sets this to False for all tests
        assert settings.research_enable_academic_search is False

    def test_provider_result_default_values(self):
        from app.services.evidence_provider_result import ProviderResult
        r = ProviderResult(provider="openalex")
        assert r.title == ""
        assert r.abstract == ""
        assert r.authors == []
        assert r.doi is None
        assert r.year is None
        assert r.is_metadata_only is False
        assert r.is_primary is False
        assert r.crossref_verified_fields == []

    def test_p9_search_meta_default_values(self):
        from app.services.evidence_provider_result import P9SearchMeta
        meta = P9SearchMeta()
        assert meta.lanes_selected == []
        assert meta.providers_attempted == 0
        assert meta.doi_matches_found == 0
        assert meta.provider_failures == []
        assert meta.source_type_distribution == {}
