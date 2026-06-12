"""Tests for the Evidence Set Planner (Part 1)."""

from app.services.evidence_set_planner import (
    EvidenceSetPlan,
    EvidenceSlot,
    plan_evidence_set,
)

_VALID_ROLES = {
    "direct_support", "mechanism_support", "example_support", "impact_support",
    "definition_support", "authority_support", "counter_evidence",
}


def _distinct(values: list[str]) -> bool:
    return len(values) == len(set(values))


def test_intervention_claim_five_distinct_slots():
    plan = plan_evidence_set(
        topic="Military intervention",
        claim="The US should use military force to stop human rights abuses by authoritarian regimes",
        side="pro",
        use_llm=False,
    )
    assert plan.planning_method == "deterministic"
    assert len(plan.slots) == 5
    funcs = [s.strategic_function for s in plan.slots]
    assert _distinct(funcs), f"strategic functions not distinct: {funcs}"


def test_section_230_claim_five_distinct_slots():
    plan = plan_evidence_set(
        topic="Internet law",
        claim="Section 230 shields platforms from liability for user content",
        side="pro",
        use_llm=False,
    )
    assert plan.planning_method == "deterministic"
    assert len(plan.slots) == 5
    funcs = [s.strategic_function for s in plan.slots]
    assert _distinct(funcs), f"strategic functions not distinct: {funcs}"


def test_slots_have_distinct_search_intents():
    for claim, topic in [
        ("The US should use military force against authoritarian regimes", "intervention"),
        ("Section 230 shields platforms from liability", "internet law"),
        ("Carbon taxes reduce emissions", "climate"),
    ]:
        plan = plan_evidence_set(topic=topic, claim=claim, side="pro", use_llm=False)
        intents = [s.search_intent for s in plan.slots]
        assert _distinct(intents), f"search intents not distinct for {claim!r}: {intents}"


def test_each_slot_has_sensible_role():
    plan = plan_evidence_set(
        topic="intervention",
        claim="Military force can stop atrocities",
        side="pro",
        use_llm=False,
    )
    for slot in plan.slots:
        assert slot.desired_evidence_role in _VALID_ROLES
        assert slot.target_claim.strip()
        assert slot.search_intent.strip()


def test_max_five_slots():
    plan = plan_evidence_set(
        topic="anything",
        claim="A broad policy claim that could span many sub-arguments",
        side="pro",
        use_llm=False,
    )
    assert len(plan.slots) <= 5


def test_generic_claim_five_distinct_slots():
    plan = plan_evidence_set(
        topic="Education policy",
        claim="Universal pre-K improves long-term student outcomes",
        side="pro",
        use_llm=False,
    )
    assert len(plan.slots) == 5
    funcs = [s.strategic_function for s in plan.slots]
    assert _distinct(funcs)
    intents = [s.search_intent for s in plan.slots]
    assert _distinct(intents)


def test_planning_method_deterministic_when_use_llm_false():
    plan = plan_evidence_set(
        topic="x", claim="y", side="pro", use_llm=False,
    )
    assert plan.planning_method == "deterministic"
    assert isinstance(plan, EvidenceSetPlan)
    assert all(isinstance(s, EvidenceSlot) for s in plan.slots)


def test_intervention_template_has_legal_and_historical_slots():
    plan = plan_evidence_set(
        topic="humanitarian intervention",
        claim="Force is justified to stop genocide",
        side="pro",
        use_llm=False,
    )
    slot_ids = {s.slot_id for s in plan.slots}
    assert "legal_warrant" in slot_ids
    assert "historical_example" in slot_ids
    # historical example slot should tolerate older sources
    hist = next(s for s in plan.slots if s.slot_id == "historical_example")
    assert hist.recency_policy == "historical_ok"


def test_section_230_template_has_counter_slot():
    plan = plan_evidence_set(
        topic="content moderation",
        claim="Section 230 immunity enables harm",
        side="pro",
        use_llm=False,
    )
    roles = {s.desired_evidence_role for s in plan.slots}
    assert "counter_evidence" in roles
