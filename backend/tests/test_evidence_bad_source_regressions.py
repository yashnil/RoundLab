"""Regression fixtures for the exact bad-source failure modes we hit.

Each fixture is a realistic messy source. For every one we assert the cut/tag/
analysis pipeline produces a usable debate card: a real tagline (not a random
article phrase), coherent read-aloud highlights, reversible Medium/High, and
card-specific (non-generic) warrant/impact + entity-aware debate prep.
"""

import pytest

from app.services.card_cutting import (
    strip_page_chrome,
    find_evidence_start_index,
    generate_evidence_cut,
    derive_card_intelligence,
    deterministic_tagline_from_card,
    extract_case_entities,
    _FINITE_VERB_RE,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

CARNEGIE = (
    "U.S. relations with authoritarian regimes have long been shaped by strategic "
    "interest. In addition, each U.S. president has put their own imprint on such "
    "relations. Authoritarian governments rely on violence and repression to maintain "
    "political control, and Washington has often tolerated that repression when it "
    "served broader security goals during the Cold War and after."
)

RWANDA = (
    "In April 1994, the United Nations and the United States failed to intervene in "
    "Rwanda as the genocide unfolded. Despite clear warning signs from UN commanders on "
    "the ground, the international community withdrew peacekeepers. France launched a "
    "limited operation only after hundreds of thousands of Tutsi had already been killed. "
    "The delay allowed the genocide to continue for nearly one hundred days."
)

BOSNIA = (
    "In 1995, sustained U.S. and NATO airstrikes combined with diplomacy at Dayton forced "
    "Serb forces to the negotiating table. The credible threat of force changed the "
    "incentives of the warring parties and brought an end to the war in Bosnia. The Dayton "
    "Accords showed that intervention paired with diplomacy can stop mass atrocities."
)

GMU = (
    "Home > Programs > Conflict Resolution\n"
    "Humanitarian intervention is the use of military force to protect civilians from "
    "mass atrocities. Scholars argue that the responsibility to protect can override "
    "state sovereignty when a government commits genocide against its own people. "
    "Critics counter that intervention is often selective and politically motivated."
)

OZARK = (
    "Home > Journals > Ozark Historical Review > Vol. 42 (2022) > No. 1\n"
    "Ozark Historical Review\n"
    "\n"
    "Humanitarian Intervention and Just War Theory\n"
    "\n"
    "Authors\n"
    "Nathaniel R. King, University of Arkansas\n"
    "\n"
    "Recommended Citation\n"
    "King, N. R. (2022). Humanitarian Intervention. Ozark Historical Review, 42(1).\n"
    "\n"
    "Since the end of World War II, the United States has engaged in numerous military "
    "interventions abroad to protect civilian populations from atrocities. Humanitarian "
    "intervention is justified by appeal to just war theory when a state commits genocide. "
    "Armed intervention requires proportionality, last resort, and multilateral legitimacy."
)

_FIXTURES = {
    "carnegie": (CARNEGIE, "U.S. policy toward authoritarian regimes is driven by strategic interest",
                 "U.S. foreign policy", "direct_support"),
    "rwanda": (RWANDA, "nonintervention in Rwanda allowed genocide to continue",
               "humanitarian intervention", "example_support"),
    "bosnia": (BOSNIA, "intervention with diplomacy can end mass atrocities",
               "humanitarian intervention", "example_support"),
    "gmu": (GMU, "humanitarian intervention can override sovereignty to stop atrocities",
            "humanitarian intervention", "mechanism_support"),
    "ozark": (OZARK, "humanitarian intervention is justified to stop genocide",
              "humanitarian intervention", "example_support"),
}


def _clean(passage: str, claim: str) -> str:
    cleaned = strip_page_chrome(passage)
    start = find_evidence_start_index(cleaned, claim, "")
    return cleaned[start:] if start > 0 else cleaned


@pytest.mark.parametrize("name", list(_FIXTURES))
class TestBadSourceRegressions:
    def _cut(self, name, style="medium"):
        passage, claim, topic, role = _FIXTURES[name]
        body = _clean(passage, claim)
        return generate_evidence_cut(body, claim, role, use_llm=False, preferred_cut_style=style), body

    def test_read_aloud_passes_validator(self, name):
        cut, _ = self._cut(name)
        v = cut.read_aloud_validation
        assert v is not None and v.passed, (name, v.issues if v else None)

    def test_no_midword_or_connective_lead(self, name):
        cut, _ = self._cut(name)
        v = cut.read_aloud_validation
        assert "midword_start" not in v.issues and "midword_end" not in v.issues
        assert not v.read_aloud_text.lower().startswith("in addition")

    def test_medium_high_reversible(self, name):
        m1, _ = self._cut(name, "medium")
        _h, _ = self._cut(name, "high")
        m2, _ = self._cut(name, "medium")
        assert m1.cut_text_with_ellipses == m2.cut_text_with_ellipses

    def test_high_not_longer_than_medium(self, name):
        m, _ = self._cut(name, "medium")
        h, _ = self._cut(name, "high")
        assert len(h.cut_text_with_ellipses) <= len(m.cut_text_with_ellipses) + 5

    def test_no_chrome_or_title_in_body(self, name):
        cut, _ = self._cut(name)
        body = cut.cut_text_with_ellipses
        assert "Home >" not in body
        assert "Recommended Citation" not in body
        assert "Nathaniel R. King" not in body

    def test_tagline_is_a_real_claim(self, name):
        passage, claim, topic, role = _FIXTURES[name]
        cut, _ = self._cut(name)
        hl = cut.read_aloud_validation.read_aloud_text if cut.read_aloud_validation else ""
        tag = deterministic_tagline_from_card(topic, claim, hl, extract_case_entities(passage, topic), role)
        assert tag[:1].isupper()
        assert _FINITE_VERB_RE.search(tag), (name, tag)
        assert not tag.lower().startswith(("in addition", "however", "moreover"))
        assert len(tag.split()) <= 18

    def test_warrant_and_impact_specific(self, name):
        passage, claim, topic, role = _FIXTURES[name]
        cut, _ = self._cut(name)
        hl = cut.read_aloud_validation.read_aloud_text if cut.read_aloud_validation else ""
        intel = derive_card_intelligence(
            evidence_role=role, best_supported_claim=claim, overclaim_warning="",
            source_quality="high", debate_usefulness_score=7.0, is_snippet_source=False,
            citation_quality="complete", compression_ratio=cut.compression_ratio,
            cut_style=cut.cut_style, is_counter_evidence=False, claim=claim,
            topic=topic, passage=passage, highlighted_text=hl,
        )
        # No clunky/generic filler.
        blob = (intel.warrant_analysis + " " + intel.impact_analysis).lower()
        assert "highlighted line" not in blob
        assert "if the judge buys this" not in blob
        assert intel.warrant_analysis.strip() and intel.impact_analysis.strip()
        assert intel.weighing_angle.strip()

    def test_debate_prep_mentions_entity_for_example_cards(self, name):
        passage, claim, topic, role = _FIXTURES[name]
        # Entity injection into debate prep is designed for case/impact cards.
        if role not in ("example_support", "impact_support"):
            pytest.skip("entity-specific prep applies to example/impact cards")
        ents = [e for e in extract_case_entities(passage, topic) if "\n" not in e]
        if not ents:
            pytest.skip("no salient entity in this fixture")
        intel = derive_card_intelligence(
            evidence_role=role, best_supported_claim=claim, overclaim_warning="",
            source_quality="high", debate_usefulness_score=7.0, is_snippet_source=False,
            citation_quality="complete", compression_ratio=0.5, cut_style="medium_cut",
            is_counter_evidence=False, claim=claim, topic=topic, passage=passage,
            highlighted_text="",
        )
        prep_blob = " ".join([
            intel.warrant_analysis, intel.impact_analysis, intel.potential_weakness,
            intel.how_to_answer_weakness, intel.crossfire_answer,
        ])
        assert any(e in prep_blob for e in ents), (name, ents)

    def test_entities_never_span_newlines(self, name):
        passage, _claim, topic, _role = _FIXTURES[name]
        for e in extract_case_entities(passage, topic):
            assert "\n" not in e, (name, repr(e))
