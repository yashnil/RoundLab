"""Pass 16 — Evidence-use tracker tests.

Covers:
- Missing citation detection
- Unsupported tag detection
- Causal overclaim detection
- Card dumping detection
- Warrant explanation detection
- Freshness warning preserved
- Abstract-only limitation flagged
- Support verdict unchanged
- Evidence report generation
"""
from __future__ import annotations
import uuid
import pytest

from app.models.round_simulation import (
    EvidenceUseViolationType,
    RoundEvidenceUse,
    RoundPhaseType,
    RoundSide,
)
from app.services.evidence_use_tracker import (
    _detect_causal_overclaim,
    _detect_missing_citation,
    _detect_unsupported_tag,
    _detect_warrant_explanation,
    create_evidence_use_record,
    detect_card_dumping,
    generate_evidence_report,
)


# ── Citation detection ─────────────────────────────────────────────────────────

class TestDetectMissingCitation:
    def test_author_present_not_missing(self):
        assert not _detect_missing_citation("Smith 2024 argues that trade benefits.", "Smith 2024")

    def test_author_absent_is_missing(self):
        assert _detect_missing_citation("The evidence shows serious harms.", "Johnson 2023")

    def test_empty_cite_not_flagged(self):
        assert not _detect_missing_citation("Some transcript.", "")

    def test_case_insensitive_author(self):
        assert not _detect_missing_citation("smith argues the trade policy fails.", "Smith 2024")


# ── Unsupported tag detection ──────────────────────────────────────────────────

class TestDetectUnsupportedTag:
    def test_fully_supported_always_ok(self):
        assert not _detect_unsupported_tag("Strong claim.", "This proves trade harms.", "fully_supported")

    def test_not_supported_always_flagged(self):
        assert _detect_unsupported_tag("Strong claim.", "Evidence text.", "not_supported")

    def test_contradicts_always_flagged(self):
        assert _detect_unsupported_tag("Our claim.", "Text.", "contradicts")

    def test_partial_with_absolute_claim_flagged(self):
        ref = "This demonstrates that 100% of cases fail"
        assert _detect_unsupported_tag("Tag.", ref, "partially_supported")

    def test_partial_without_overclaim_not_flagged(self):
        ref = "The evidence suggests some correlation exists"
        assert not _detect_unsupported_tag("Tag.", ref, "partially_supported")


# ── Causal overclaim detection ─────────────────────────────────────────────────

class TestDetectCausalOverclaim:
    def test_100_percent_flagged(self):
        assert _detect_causal_overclaim("This guarantees 100% reduction in harm.")

    def test_guarantees_flagged(self):
        assert _detect_causal_overclaim("The policy guarantees economic growth.")

    def test_normal_claim_not_flagged(self):
        assert not _detect_causal_overclaim("The evidence suggests economic benefits.")

    def test_proves_all_flagged(self):
        assert _detect_causal_overclaim("This proves that all nations comply.")


# ── Warrant explanation detection ─────────────────────────────────────────────

class TestDetectWarrantExplanation:
    def test_this_means_detected(self):
        assert _detect_warrant_explanation("Smith argues X. This means the impact is Y.", "body")

    def test_the_warrant_is_detected(self):
        assert _detect_warrant_explanation("The warrant is that trade reduces conflict.", "body")

    def test_no_explanation_not_detected(self):
        assert not _detect_warrant_explanation("Read the card. Next argument.", "body")


# ── Card dumping detection ─────────────────────────────────────────────────────

class TestDetectCardDumping:
    def test_few_cards_not_flagged(self):
        result = detect_card_dumping("r1", "s1", ["c1", "c2"], "Full transcript text.")
        assert result == []

    def test_many_cards_without_explanation_flagged(self):
        cards = [f"c{i}" for i in range(6)]
        transcript = "Card one. Card two. Card three. Card four. Card five. Card six."
        result = detect_card_dumping("r1", "s1", cards, transcript)
        assert len(result) > 0

    def test_many_cards_with_explanation_not_flagged(self):
        cards = [f"c{i}" for i in range(6)]
        transcript = " ".join([
            "Smith argues trade harms. This means countries suffer.",
            "Johnson shows job losses. The warrant is that automation follows.",
            "Chen explains migration. This shows why labor markets shift.",
            "Davis on inequality. The link is wages decline.",
            "Brown on poverty. This means families lose income.",
            "White on health. The warrant here is air quality drops.",
        ])
        result = detect_card_dumping("r1", "s1", cards, transcript)
        assert result == []


# ── create_evidence_use_record ─────────────────────────────────────────────────

class TestCreateEvidenceUseRecord:
    def _card(self, verdict="fully_supported", freshness_warning=False) -> dict:
        return {
            "id": str(uuid.uuid4()),
            "cite": "Smith 2024",
            "tag": "Economic harms are significant",
            "body_text": "The evidence shows clear economic harms from the policy.",
            "intelligence_json": {
                "support_verdict": verdict,
                "freshness_warning": freshness_warning,
                "source_type": "article",
                "source_quality": "high",
            },
            "card_cutting_result_json": {},
        }

    def test_citation_given_when_author_mentioned(self):
        card = self._card()
        transcript = "Smith 2024 argues that trade harms are significant."
        use = create_evidence_use_record(
            "r1", "s1", card["id"], RoundSide.PRO, RoundPhaseType.FIRST_CONSTRUCTIVE,
            transcript, card
        )
        assert use.citation_given is True

    def test_citation_not_given_when_author_absent(self):
        card = self._card()
        transcript = "Our evidence shows economic harms."
        use = create_evidence_use_record(
            "r1", "s1", card["id"], RoundSide.PRO, RoundPhaseType.FIRST_CONSTRUCTIVE,
            transcript, card
        )
        assert use.citation_given is False
        assert EvidenceUseViolationType.MISSING_CITATION.value in use.violations

    def test_support_verdict_preserved_unchanged(self):
        card = self._card(verdict="partially_supported")
        use = create_evidence_use_record(
            "r1", "s1", card["id"], RoundSide.PRO, RoundPhaseType.FIRST_CONSTRUCTIVE,
            "Some transcript.", card
        )
        assert use.support_verdict == "partially_supported"

    def test_stale_evidence_flagged(self):
        card = self._card(freshness_warning=True)
        use = create_evidence_use_record(
            "r1", "s1", card["id"], RoundSide.PRO, RoundPhaseType.FIRST_CONSTRUCTIVE,
            "Smith 2024 on trade.", card
        )
        assert EvidenceUseViolationType.STALE_EVIDENCE.value in use.violations

    def test_not_supported_verdict_flagged(self):
        card = self._card(verdict="not_supported")
        use = create_evidence_use_record(
            "r1", "s1", card["id"], RoundSide.PRO, RoundPhaseType.FIRST_CONSTRUCTIVE,
            "Smith 2024 on trade.", card
        )
        assert use.flagged is True
        assert EvidenceUseViolationType.EVIDENCE_MISMATCH.value in use.violations

    def test_clean_card_not_flagged(self):
        card = self._card(verdict="fully_supported")
        use = create_evidence_use_record(
            "r1", "s1", card["id"], RoundSide.PRO, RoundPhaseType.FIRST_CONSTRUCTIVE,
            "Smith 2024 argues trade policy causes harm. This means countries suffer.",
            card
        )
        assert use.flagged is False
        assert use.violations == []


# ── Evidence report ────────────────────────────────────────────────────────────

class TestGenerateEvidenceReport:
    def _use(self, flagged=False, violations=None, citation=True, warrant=False, extended=False) -> RoundEvidenceUse:
        return RoundEvidenceUse(
            id=str(uuid.uuid4()),
            round_id="r1",
            speech_id="s1",
            card_id=str(uuid.uuid4()),
            speaker_side=RoundSide.PRO,
            phase=RoundPhaseType.FIRST_CONSTRUCTIVE,
            flagged=flagged,
            violations=violations or [],
            citation_given=citation,
            warrant_explained=warrant,
            extended_later=extended,
            created_at="2026-06-23T00:00:00",
        )

    def test_total_uses_counted(self):
        uses = [self._use(), self._use(), self._use()]
        report = generate_evidence_report(uses)
        assert report["total_uses"] == 3

    def test_flagged_uses_counted(self):
        uses = [self._use(flagged=True), self._use(flagged=False)]
        report = generate_evidence_report(uses)
        assert report["flagged_uses"] == 1

    def test_violation_counts_aggregated(self):
        uses = [
            self._use(flagged=True, violations=["missing_citation"]),
            self._use(flagged=True, violations=["missing_citation", "stale_evidence"]),
        ]
        report = generate_evidence_report(uses)
        assert report["violation_counts"]["missing_citation"] == 2
        assert report["violation_counts"]["stale_evidence"] == 1

    def test_empty_uses(self):
        report = generate_evidence_report([])
        assert report["total_uses"] == 0
        assert report["flagged_uses"] == 0
