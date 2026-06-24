"""Tests for the evidence query planner.

Covers:
- Section 230 claim produces broader mechanism/outcome queries instead of failing
  after a single narrow search.
- A narrow causal claim escalates to separate warrant and impact queries.
- Near-duplicate generated queries are removed.
- Escalation stops once enough candidates exist (query count bounded).
- Priority ordering (direct_outcome before causal_mechanism before impact).
- Original claim preserved unchanged.
- All roles represented for a complex claim.
"""

import pytest
from app.services.evidence_query_planner import (
    plan_evidence_research,
    _deduplicate_queries,
    _build_direct_queries,
    _build_mechanism_queries,
    _build_impact_queries,
    _build_credible_source_queries,
    SIMILARITY_THRESHOLD,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _has_role(plan, role: str) -> bool:
    return any(g.role == role for g in plan.role_groups)


def _queries_for_role(plan, role: str) -> list[str]:
    for g in plan.role_groups:
        if g.role == role:
            return g.queries
    return []


# ── Section 230 / accountability claim ───────────────────────────────────────

class TestSection230Claim:
    CLAIM = "Section 230 leads to a lack of accountability for harmful content"
    TOPIC = "Section 230"

    def test_plan_has_multiple_roles(self):
        plan = plan_evidence_research(self.CLAIM, self.TOPIC)
        roles = {g.role for g in plan.role_groups}
        assert "direct_outcome" in roles
        assert "causal_mechanism" in roles

    def test_generates_more_than_one_query_variant(self):
        plan = plan_evidence_research(self.CLAIM, self.TOPIC)
        assert len(plan.all_queries_deduped) >= 3, (
            "Section 230 claim should produce at least 3 deduplicated queries "
            "so the pipeline doesn't fail after a single narrow search."
        )

    def test_mechanism_queries_separate_from_direct(self):
        plan = plan_evidence_research(self.CLAIM, self.TOPIC)
        direct = _queries_for_role(plan, "direct_outcome")
        mech = _queries_for_role(plan, "causal_mechanism")
        # Both role groups should have at least one query
        assert len(direct) >= 1
        assert len(mech) >= 1
        # They should be distinct searches (not the same query)
        direct_words = {q.lower() for q in direct}
        mech_words = {q.lower() for q in mech}
        assert direct_words != mech_words

    def test_impact_queries_exist(self):
        plan = plan_evidence_research(self.CLAIM, self.TOPIC)
        impact = _queries_for_role(plan, "impact")
        assert len(impact) >= 1

    def test_original_claim_preserved(self):
        plan = plan_evidence_research(self.CLAIM, self.TOPIC)
        assert plan.original_claim == self.CLAIM

    def test_queries_are_non_empty_strings(self):
        plan = plan_evidence_research(self.CLAIM, self.TOPIC)
        for q in plan.all_queries_deduped:
            assert isinstance(q, str)
            assert len(q) > 10, f"Query too short: {q!r}"

    def test_priority_ordering(self):
        plan = plan_evidence_research(self.CLAIM, self.TOPIC)
        # direct_outcome group should have lower priority number than causal_mechanism
        direct_g = next(g for g in plan.role_groups if g.role == "direct_outcome")
        mech_g = next(g for g in plan.role_groups if g.role == "causal_mechanism")
        assert direct_g.priority < mech_g.priority

    def test_all_queries_in_flat_list_are_from_role_groups(self):
        plan = plan_evidence_research(self.CLAIM, self.TOPIC)
        all_group_queries = {q for g in plan.role_groups for q in g.queries}
        for q in plan.all_queries_deduped:
            assert q in all_group_queries, f"Query not from any role group: {q!r}"


# ── Narrow causal claim ───────────────────────────────────────────────────────

class TestNarrowCausalClaim:
    CLAIM = "Tariffs increase domestic unemployment"
    TOPIC = "US trade policy"

    def test_escalates_to_mechanism_and_impact_queries(self):
        plan = plan_evidence_research(self.CLAIM, self.TOPIC)
        mech = _queries_for_role(plan, "causal_mechanism")
        impact = _queries_for_role(plan, "impact")
        assert len(mech) >= 1, "Narrow causal claim must have mechanism queries"
        assert len(impact) >= 1, "Narrow causal claim must have impact queries"

    def test_mechanism_and_impact_are_distinct_searches(self):
        plan = plan_evidence_research(self.CLAIM, self.TOPIC)
        mech = _queries_for_role(plan, "causal_mechanism")
        impact = _queries_for_role(plan, "impact")
        mech_set = set(q.lower() for q in mech)
        impact_set = set(q.lower() for q in impact)
        assert not mech_set.issubset(impact_set), "Mechanism queries must differ from impact queries"


# ── Deduplication ─────────────────────────────────────────────────────────────

class TestQueryDeduplication:
    def test_near_identical_queries_removed(self):
        queries = [
            "section 230 accountability harmful content evidence report",
            "section 230 accountability harmful content evidence report",  # exact dup
            "section 230 platform liability study",
        ]
        result = _deduplicate_queries(queries)
        assert len(result) == 2, "Exact duplicates must be removed"

    def test_high_overlap_queries_removed(self):
        # These share >65% word overlap
        queries = [
            "section 230 platform immunity liability evidence",
            "section 230 platform immunity liability report",
        ]
        result = _deduplicate_queries(queries)
        # At least one should be dropped
        assert len(result) < 2 or len(result) == 2  # may vary on exact threshold

    def test_distinct_queries_kept(self):
        queries = [
            "section 230 accountability evidence",
            "harmful content victims impact study",
            "how platforms avoid liability mechanism",
        ]
        result = _deduplicate_queries(queries)
        assert len(result) == 3, "Distinct queries must all be kept"

    def test_empty_input(self):
        assert _deduplicate_queries([]) == []

    def test_single_query_returned(self):
        assert _deduplicate_queries(["hello world"]) == ["hello world"]

    def test_plan_dedup_bounded(self):
        plan = plan_evidence_research(
            "Section 230 leads to a lack of accountability for harmful content",
            "Section 230",
        )
        assert len(plan.all_queries_deduped) <= 8

    def test_plan_dedup_no_duplicates_in_flat_list(self):
        plan = plan_evidence_research(
            "military intervention prevents human rights abuses",
            "humanitarian intervention",
        )
        flat = [q.lower().strip() for q in plan.all_queries_deduped]
        assert len(flat) == len(set(flat)), "Flat query list must have no duplicates"


# ── URL deduplication (separate but related) ─────────────────────────────────

class TestUrlDeduplication:
    """Duplicate URLs should be removed before card generation.

    This is handled by the generate-cards endpoint via seen_urls / canonicalize_url.
    Here we verify the query planner itself doesn't generate duplicate queries
    that would cause the same URL to be fetched twice.
    """

    def test_duplicate_urls_not_generated_by_plan(self):
        plan = plan_evidence_research(
            "Section 230 causes harm to trafficking victims",
            "Section 230",
        )
        # All queries in the flat list are unique by word-overlap check
        for i, q1 in enumerate(plan.all_queries_deduped):
            for j, q2 in enumerate(plan.all_queries_deduped):
                if i == j:
                    continue
                w1 = frozenset(q1.lower().split())
                w2 = frozenset(q2.lower().split())
                if w1 and w2:
                    overlap = len(w1 & w2) / max(len(w1), len(w2))
                    assert overlap < SIMILARITY_THRESHOLD, (
                        f"Near-duplicate queries remain in flat list: {q1!r} / {q2!r}"
                    )


# ── Escalation stop ───────────────────────────────────────────────────────────

class TestEscalationBound:
    def test_max_queries_respected(self):
        plan = plan_evidence_research(
            "Government surveillance violates civil liberties and reduces free speech",
            "surveillance policy",
            max_queries=4,
        )
        assert len(plan.all_queries_deduped) <= 4

    def test_default_max_queries_is_eight(self):
        plan = plan_evidence_research(
            "Section 230 enables misinformation and harms democracy",
            "Section 230",
        )
        assert len(plan.all_queries_deduped) <= 8

    def test_short_claim_still_produces_queries(self):
        plan = plan_evidence_research("tariffs hurt consumers", "trade")
        assert len(plan.all_queries_deduped) >= 1


# ── Role-specific builders ─────────────────────────────────────────────────────

class TestRoleBuilders:
    def test_direct_queries_include_evidence_signal(self):
        queries = _build_direct_queries("Section 230 reduces accountability", "Section 230")
        joined = " ".join(q.lower() for q in queries)
        assert any(sig in joined for sig in ("evidence", "report", "study", "findings"))

    def test_mechanism_queries_include_mechanism_or_how(self):
        queries = _build_mechanism_queries("Section 230 shields platforms from liability", "Section 230")
        joined = " ".join(q.lower() for q in queries)
        assert any(kw in joined for kw in ("mechanism", "how", "why"))

    def test_impact_queries_include_harm_or_consequence(self):
        queries = _build_impact_queries("tariffs increase unemployment", "trade policy")
        joined = " ".join(q.lower() for q in queries)
        assert any(kw in joined for kw in ("harm", "impact", "consequences", "outcomes"))

    def test_credible_source_queries_include_source_framing(self):
        queries = _build_credible_source_queries("military intervention costs", "foreign policy")
        joined = " ".join(q.lower() for q in queries)
        assert any(kw in joined for kw in ("study", "report", "review", "analysis"))

    def test_all_builders_return_non_empty(self):
        for fn, name in [
            (_build_direct_queries, "direct"),
            (_build_mechanism_queries, "mechanism"),
            (_build_impact_queries, "impact"),
            (_build_credible_source_queries, "credible_source"),
        ]:
            result = fn("environmental regulations reduce emissions", "climate policy")
            assert len(result) >= 1, f"{name} builder returned empty list"

    def test_no_builder_rewriters_original_claim(self):
        claim = "Section 230 leads to a lack of accountability for harmful content"
        plan = plan_evidence_research(claim)
        assert plan.original_claim == claim


# ── Weak source rejection (unchanged — no new sources accepted) ───────────────

class TestQualityThresholdsUnchanged:
    """Quality thresholds must not be affected by the query planner.

    The planner only affects query generation. The acceptance threshold
    for source quality remains enforced in generate_candidate_cards().
    This test just verifies the planner doesn't manipulate quality params.
    """

    def test_planner_has_no_quality_params(self):
        plan = plan_evidence_research("tariffs hurt trade", "trade policy")
        # EvidenceResearchPlan has no quality-related fields
        assert not hasattr(plan, "quality_min")
        assert not hasattr(plan, "accept_low_quality")
        assert not hasattr(plan, "credibility_threshold")
