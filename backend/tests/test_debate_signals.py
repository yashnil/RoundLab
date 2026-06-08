"""Tests for the deterministic DebateSignalDetector and IssueCalibrator.

All tests are pure — no LLM calls, no network, no Supabase.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from app.services.debate_signal_detection import (
    DebateSignal,
    DebateSignalReport,
    QualityGateReport,
    detect_debate_signals,
    format_signal_injection,
    has_named_evidence,
    _detect_new_argument,
    _detect_no_clash,
    _detect_weak_evidence,
    _detect_weak_extension,
    _detect_missing_warrant,
    _assess_quality_gate,
)
from app.services.issue_calibrator import calibrate_structured_issues


# ── Sample transcripts ─────────────────────────────────────────────────────────

_GOOD_CONSTRUCTIVE = (
    "Good afternoon. We affirm the resolution. We provide two contentions.\n"
    "Contention One: Economic burden. Research from the RAND Corporation in 2023 finds that "
    "basing expenditure crowds out domestic defense industrial investment. "
    "The warrant is opportunity cost: every dollar allocated to foreign basing cannot "
    "simultaneously strengthen the homeland industrial base. "
    "The impact is erosion of American deterrence capacity.\n"
    "Contention Two: Escalation risk. The Carnegie Endowment for International Peace documented "
    "in 2024 that Chinese military provocations spike by 34 percent after joint exercises. "
    "The mechanism is deterrence instability. "
    "The impact is elevated risk of conventional miscalculation."
)

_WEAK_CONSTRUCTIVE = (
    "We affirm that the United States should reduce its military presence in East Asia.\n"
    "Contention One: The bases cost too much money. The United States spends a lot of money "
    "on military bases every year. This is unsustainable. The impact is that America will be "
    "economically weaker.\n"
    "Contention Two: The military presence causes tension. Having soldiers in East Asia makes "
    "countries like China angry. When countries get angry, bad things happen. "
    "This could lead to a conflict, which would be very harmful."
)

_VAGUE_EVIDENCE_CONSTRUCTIVE = (
    "We affirm the resolution.\n"
    "Contention One: Studies show that maintaining military bases in East Asia costs tens of "
    "billions annually. Many experts believe this spending is inefficient. "
    "The warrant is resource misallocation. The impact is long-run fiscal drag.\n"
    "Contention Two: Experts say that a large foreign military presence provokes rivals. "
    "Various think tank reports indicate that incidents near US bases are increasing. "
    "The impact is elevated escalation risk."
)

_FINAL_FOCUS_NEW_EVIDENCE = (
    "In this final focus, we crystallize the round.\n"
    "Extend our Contention One on alliance credibility. The affirmative never answered "
    "the Harvard Belfer Center evidence. This argument is uncontested.\n"
    "But most critically, consider the Taiwan contingency. New evidence from the Center for "
    "Strategic and International Studies, published in 2026, uses wargaming simulations to "
    "show that withdrawal makes Taiwan conflict 60 percent more likely. "
    "Vote Negative to prevent great power war."
)

_NO_CLASH_REBUTTAL = (
    "Thank you. The Negative team will now present our rebuttal.\n"
    "We stand firmly on our Contention One: American military presence is the cornerstone "
    "of regional stability. Our evidence from the Heritage Foundation demonstrates "
    "conclusively that the US alliance system has preserved peace for over 70 years.\n"
    "We also extend our Contention Two on alliance economics. Our military experts confirm "
    "that presence and readiness are inseparable. Our case is strong. "
    "For these reasons, we urge a Negative ballot."
)

_ENGAGED_REBUTTAL = (
    "The Negative team addresses the Affirmative case.\n"
    "On their Contention One, economic burden: The affirmative's RAND evidence grossly "
    "understates the economic returns. The Peterson Institute's 2022 report finds that "
    "US alliances generate trade benefits worth 250 billion dollars annually. "
    "Cross-apply this against their C1. The economic argument flows Negative.\n"
    "On their Contention Two, escalation risk: The Carnegie Endowment evidence is misread. "
    "Their mechanism is flawed. The deterrence instability warrant fails because forward "
    "presence deters rather than provokes. Extend our response."
)


# ── detect_debate_signals ──────────────────────────────────────────────────────

class TestDetectDebateSignals:
    def test_good_constructive_no_signals(self):
        report = detect_debate_signals(_GOOD_CONSTRUCTIVE, "constructive")
        assert report.signals == []
        assert report.quality_gate.recommended_issue_budget == 0

    def test_good_constructive_quality_gate(self):
        report = detect_debate_signals(_GOOD_CONSTRUCTIVE, "constructive")
        assert report.quality_gate.has_named_evidence is True
        assert report.quality_gate.has_clear_warrant_language is True
        assert report.quality_gate.has_impact_language is True

    def test_weak_constructive_budget_high(self):
        report = detect_debate_signals(_WEAK_CONSTRUCTIVE, "constructive")
        # Budget > 1 for a speech with no named sources (even if it has "causes" language)
        assert report.quality_gate.recommended_issue_budget >= 2

    def test_weak_constructive_weak_evidence_signal(self):
        report = detect_debate_signals(_WEAK_CONSTRUCTIVE, "constructive")
        signal_types = [s.issue_type for s in report.signals]
        assert "weak_evidence" in signal_types

    def test_vague_evidence_constructive_signal(self):
        report = detect_debate_signals(_VAGUE_EVIDENCE_CONSTRUCTIVE, "constructive")
        signal_types = [s.issue_type for s in report.signals]
        assert "weak_evidence" in signal_types

    def test_final_focus_new_argument_detected(self):
        report = detect_debate_signals(_FINAL_FOCUS_NEW_EVIDENCE, "final_focus")
        signal_types = [s.issue_type for s in report.signals]
        assert "new_argument" in signal_types

    def test_final_focus_new_argument_is_high_confidence(self):
        report = detect_debate_signals(_FINAL_FOCUS_NEW_EVIDENCE, "final_focus")
        new_arg = next((s for s in report.signals if s.issue_type == "new_argument"), None)
        assert new_arg is not None
        assert new_arg.confidence == "high"

    def test_no_clash_rebuttal_detected(self):
        report = detect_debate_signals(_NO_CLASH_REBUTTAL, "rebuttal")
        signal_types = [s.issue_type for s in report.signals]
        assert "no_clash" in signal_types

    def test_no_clash_rebuttal_is_high_confidence(self):
        report = detect_debate_signals(_NO_CLASH_REBUTTAL, "rebuttal")
        nc = next((s for s in report.signals if s.issue_type == "no_clash"), None)
        assert nc is not None
        assert nc.confidence == "high"

    def test_engaged_rebuttal_no_no_clash(self):
        report = detect_debate_signals(_ENGAGED_REBUTTAL, "rebuttal")
        signal_types = [s.issue_type for s in report.signals]
        assert "no_clash" not in signal_types

    def test_no_new_argument_in_constructive(self):
        """new_argument signal should never fire for constructive speeches."""
        text = "New evidence from RAND Corporation shows that basing costs are high."
        report = detect_debate_signals(text, "constructive")
        signal_types = [s.issue_type for s in report.signals]
        assert "new_argument" not in signal_types

    def test_no_no_clash_in_constructive(self):
        """no_clash should not fire for constructive speeches."""
        report = detect_debate_signals(_NO_CLASH_REBUTTAL, "constructive")
        signal_types = [s.issue_type for s in report.signals]
        assert "no_clash" not in signal_types

    def test_speech_type_stored_in_report(self):
        report = detect_debate_signals(_GOOD_CONSTRUCTIVE, "constructive")
        assert report.speech_type == "constructive"


# ── _detect_new_argument ───────────────────────────────────────────────────────

class TestDetectNewArgument:
    def test_fires_for_final_focus(self):
        sig = _detect_new_argument("New evidence from CSIS shows X.", "final_focus")
        assert sig is not None
        assert sig.issue_type == "new_argument"

    def test_fires_for_summary(self):
        sig = _detect_new_argument("New evidence from RAND shows X.", "summary")
        assert sig is not None

    def test_does_not_fire_for_rebuttal(self):
        sig = _detect_new_argument("New evidence from CSIS shows X.", "rebuttal")
        assert sig is None

    def test_does_not_fire_for_constructive(self):
        sig = _detect_new_argument("New evidence from RAND shows X.", "constructive")
        assert sig is None

    def test_fires_for_new_card(self):
        sig = _detect_new_argument("We have a new card from the Belfer Center.", "final_focus")
        assert sig is not None

    def test_fires_for_for_the_first_time(self):
        sig = _detect_new_argument("For the first time, we introduce the Taiwan data.", "summary")
        assert sig is not None

    def test_does_not_fire_without_pattern(self):
        sig = _detect_new_argument("Extend our Belfer Center evidence from the constructive.", "final_focus")
        assert sig is None


# ── _detect_no_clash ───────────────────────────────────────────────────────────

class TestDetectNoClash:
    def test_fires_for_own_case_only_rebuttal(self):
        sig = _detect_no_clash(_NO_CLASH_REBUTTAL, "rebuttal")
        assert sig is not None
        assert sig.issue_type == "no_clash"
        assert sig.confidence == "high"

    def test_does_not_fire_for_engaged_rebuttal(self):
        sig = _detect_no_clash(_ENGAGED_REBUTTAL, "rebuttal")
        assert sig is None

    def test_does_not_fire_for_constructive(self):
        sig = _detect_no_clash(_NO_CLASH_REBUTTAL, "constructive")
        assert sig is None

    def test_does_not_fire_for_final_focus(self):
        sig = _detect_no_clash(_NO_CLASH_REBUTTAL, "final_focus")
        assert sig is None

    def test_does_not_fire_for_summary(self):
        """no_clash is rebuttal-specific — summaries legitimately extend own case."""
        text = "We collapse to two voting issues. Extend our Contention One. Our case is strong."
        sig = _detect_no_clash(text, "summary")
        assert sig is None


# ── _detect_weak_evidence ──────────────────────────────────────────────────────

class TestDetectWeakEvidence:
    def test_fires_for_studies_show(self):
        sig = _detect_weak_evidence("Studies show that basing costs are high.", "constructive")
        assert sig is not None
        assert sig.issue_type == "weak_evidence"
        assert sig.confidence == "high"

    def test_fires_for_experts_say(self):
        sig = _detect_weak_evidence("Experts say the policy is inefficient.", "constructive")
        assert sig is not None

    def test_does_not_fire_when_named_source_nearby(self):
        text = "Research from the RAND Corporation in 2023 shows that studies confirm basing costs."
        sig = _detect_weak_evidence(text, "constructive")
        # RAND nearby → should not flag the vague phrasing as weak
        assert sig is None or sig.confidence != "high"

    def test_fires_medium_for_no_named_sources_in_constructive(self):
        sig = _detect_weak_evidence(_WEAK_CONSTRUCTIVE, "constructive")
        assert sig is not None
        assert sig.issue_type == "weak_evidence"
        assert sig.confidence == "medium"

    def test_does_not_fire_medium_for_good_constructive(self):
        sig = _detect_weak_evidence(_GOOD_CONSTRUCTIVE, "constructive")
        assert sig is None

    def test_does_not_fire_medium_for_non_constructive(self):
        # Medium "no named sources" check only for constructive
        sig = _detect_weak_evidence(_WEAK_CONSTRUCTIVE, "rebuttal")
        # Vague patterns might still trigger but not medium constructive check
        # Just verify it doesn't crash
        assert sig is None or isinstance(sig, DebateSignal)


# ── _assess_quality_gate ───────────────────────────────────────────────────────

class TestAssessQualityGate:
    def test_strong_constructive_budget_zero(self):
        gate = _assess_quality_gate(_GOOD_CONSTRUCTIVE, "constructive")
        assert gate.recommended_issue_budget == 0
        assert gate.has_named_evidence is True
        assert gate.has_clear_warrant_language is True
        assert gate.has_impact_language is True

    def test_weak_constructive_budget_elevated(self):
        gate = _assess_quality_gate(_WEAK_CONSTRUCTIVE, "constructive")
        # No named evidence → budget at least 2
        assert gate.has_named_evidence is False
        assert gate.recommended_issue_budget >= 2

    def test_vague_evidence_constructive_budget_two(self):
        gate = _assess_quality_gate(_VAGUE_EVIDENCE_CONSTRUCTIVE, "constructive")
        # has warrant language ("the warrant is"), no named evidence → budget 2
        assert gate.recommended_issue_budget == 2


# ── _has_named_evidence ────────────────────────────────────────────────────────

class TestHasNamedEvidence:
    def test_rand_with_year(self):
        assert has_named_evidence("The RAND Corporation in 2023 found that...") is True

    def test_carnegie_with_year(self):
        assert has_named_evidence("Carnegie Endowment for International Peace documented in 2024.") is True

    def test_belfer_with_year(self):
        assert has_named_evidence("Harvard Belfer Center scholars, writing in 2022, document...") is True

    def test_no_named_source(self):
        assert has_named_evidence("Studies show that basing is expensive.") is False

    def test_named_org_no_year(self):
        result = has_named_evidence("Research from the Brookings Institution.")
        assert isinstance(result, bool)


# ── format_signal_injection ────────────────────────────────────────────────────

class TestFormatSignalInjection:
    def test_empty_signals_with_budget_zero_gives_gate_instructions(self):
        report = DebateSignalReport(
            speech_type="constructive",
            signals=[],
            quality_gate=QualityGateReport(
                has_named_evidence=True,
                has_clear_warrant_language=True,
                has_impact_language=True,
                recommended_issue_budget=0,
            ),
        )
        text = format_signal_injection(report)
        assert "Do NOT invent" in text or "strong speech" in text.lower()

    def test_high_confidence_signal_shows_mandatory(self):
        report = DebateSignalReport(
            speech_type="final_focus",
            signals=[
                DebateSignal(
                    issue_type="new_argument",
                    confidence="high",
                    evidence="New evidence from CSIS...",
                    reason="Final focus introduces new source.",
                )
            ],
            quality_gate=QualityGateReport(
                has_named_evidence=True,
                has_clear_warrant_language=False,
                has_impact_language=True,
                recommended_issue_budget=2,
            ),
        )
        text = format_signal_injection(report)
        assert "MANDATORY" in text
        assert "new_argument" in text

    def test_no_signals_budget_four_returns_empty(self):
        report = DebateSignalReport(
            speech_type="rebuttal",
            signals=[],
            quality_gate=QualityGateReport(
                has_named_evidence=False,
                has_clear_warrant_language=False,
                has_impact_language=False,
                recommended_issue_budget=4,
            ),
        )
        # No signals and no gate guidance needed
        text = format_signal_injection(report)
        assert text == ""


# ── calibrate_structured_issues ───────────────────────────────────────────────

def _make_issue(issue_type: str, severity: str = "high") -> dict:
    return {
        "issue_type": issue_type,
        "severity": severity,
        "title": f"Test {issue_type}",
        "explanation": "Test explanation.",
        "why_it_matters": "Test why it matters.",
        "recommendation": "Test recommendation.",
        "affected_argument_labels": [],
        "recommended_drill_type": "warranting",
    }


def _make_signal(issue_type: str, confidence: str = "high") -> DebateSignal:
    return DebateSignal(
        issue_type=issue_type,
        confidence=confidence,
        evidence="test evidence",
        reason="test reason",
    )


def _make_report(
    signals: list[DebateSignal],
    budget: int = 4,
    has_named: bool = False,
    has_warrant: bool = False,
    has_impact: bool = False,
    speech_type: str = "constructive",
) -> DebateSignalReport:
    return DebateSignalReport(
        speech_type=speech_type,
        signals=signals,
        quality_gate=QualityGateReport(
            has_named_evidence=has_named,
            has_clear_warrant_language=has_warrant,
            has_impact_language=has_impact,
            recommended_issue_budget=budget,
        ),
    )


class TestCalibrateStructuredIssues:
    # ── Deduplication ──────────────────────────────────────────────────────────

    def test_deduplicates_same_issue_type(self):
        issues = [_make_issue("missing_warrant", "high"), _make_issue("missing_warrant", "medium")]
        result = calibrate_structured_issues(issues, _make_report([]), "constructive")
        types = [i["issue_type"] for i in result]
        assert types.count("missing_warrant") == 1

    def test_dedup_keeps_highest_severity(self):
        issues = [_make_issue("missing_warrant", "medium"), _make_issue("missing_warrant", "high")]
        result = calibrate_structured_issues(issues, _make_report([]), "constructive")
        assert result[0]["severity"] == "high"

    def test_dedup_preserves_distinct_types(self):
        issues = [_make_issue("missing_warrant"), _make_issue("weak_evidence")]
        result = calibrate_structured_issues(issues, _make_report([]), "constructive")
        assert len(result) == 2

    # ── Signal injection ───────────────────────────────────────────────────────

    def test_adds_missing_high_confidence_signal(self):
        issues = []  # LLM produced nothing
        signals = [_make_signal("no_clash", "high")]
        result = calibrate_structured_issues(issues, _make_report(signals, budget=4), "rebuttal")
        types = [i["issue_type"] for i in result]
        assert "no_clash" in types

    def test_adds_missing_medium_confidence_signal(self):
        issues = []
        signals = [_make_signal("weak_evidence", "medium")]
        result = calibrate_structured_issues(issues, _make_report(signals, budget=4), "constructive")
        types = [i["issue_type"] for i in result]
        assert "weak_evidence" in types

    def test_does_not_duplicate_existing_issue(self):
        issues = [_make_issue("no_clash")]
        signals = [_make_signal("no_clash", "high")]
        result = calibrate_structured_issues(issues, _make_report(signals, budget=4), "rebuttal")
        types = [i["issue_type"] for i in result]
        assert types.count("no_clash") == 1

    def test_does_not_add_low_confidence_signal(self):
        issues = []
        signals = [_make_signal("no_weighing", "low")]
        result = calibrate_structured_issues(issues, _make_report(signals, budget=4), "summary")
        types = [i["issue_type"] for i in result]
        assert "no_weighing" not in types

    # ── Quality gate suppression ───────────────────────────────────────────────

    def test_budget_zero_suppresses_unsupported_quality_fps(self):
        """Strong speech (budget=0) — LLM FPs are suppressed."""
        issues = [_make_issue("missing_warrant"), _make_issue("weak_evidence")]
        report = _make_report([], budget=0, has_named=True, has_warrant=True, has_impact=True)
        result = calibrate_structured_issues(issues, report, "constructive")
        types = [i["issue_type"] for i in result]
        assert "missing_warrant" not in types
        assert "weak_evidence" not in types

    def test_budget_zero_keeps_structural_issues(self):
        """Even with budget=0, structural issues (no_clash) survive."""
        issues = [_make_issue("no_clash"), _make_issue("missing_warrant")]
        report = _make_report([], budget=0)
        result = calibrate_structured_issues(issues, report, "rebuttal")
        types = [i["issue_type"] for i in result]
        assert "no_clash" in types

    def test_budget_zero_keeps_signal_backed_quality(self):
        """With budget=0, quality issues that have a signal are kept."""
        issues = [_make_issue("weak_evidence")]
        signals = [_make_signal("weak_evidence", "high")]
        report = _make_report(signals, budget=0)
        result = calibrate_structured_issues(issues, report, "constructive")
        types = [i["issue_type"] for i in result]
        assert "weak_evidence" in types

    def test_budget_one_keeps_one_quality_issue(self):
        issues = [_make_issue("missing_warrant"), _make_issue("unclear_impact")]
        report = _make_report([], budget=1)
        result = calibrate_structured_issues(issues, report, "constructive")
        quality_count = sum(1 for i in result if i["issue_type"] in {"missing_warrant", "unclear_impact"})
        assert quality_count <= 1

    def test_budget_four_does_not_suppress(self):
        issues = [_make_issue("missing_warrant"), _make_issue("weak_evidence"), _make_issue("unclear_impact")]
        report = _make_report([], budget=4)
        result = calibrate_structured_issues(issues, report, "constructive")
        assert len(result) == 3

    # ── Severity ordering ──────────────────────────────────────────────────────

    def test_result_sorted_high_to_low(self):
        issues = [_make_issue("unclear_impact", "low"), _make_issue("missing_warrant", "high")]
        result = calibrate_structured_issues(issues, _make_report([]), "constructive")
        assert result[0]["severity"] == "high"
        assert result[1]["severity"] == "low"

    # ── End-to-end scenario tests ──────────────────────────────────────────────

    def test_good_constructive_fp_suppressed(self):
        """Simulate good_constructive: model generates FPs, calibrator removes them."""
        issues = [_make_issue("missing_warrant"), _make_issue("weak_evidence")]
        report = detect_debate_signals(_GOOD_CONSTRUCTIVE, "constructive")
        result = calibrate_structured_issues(issues, report, "constructive")
        # budget=0, no signals → suppress all quality FPs
        types = [i["issue_type"] for i in result]
        assert "missing_warrant" not in types
        assert "weak_evidence" not in types

    def test_no_clash_rebuttal_signal_added(self):
        """Simulate no_clash_rebuttal: LLM generates nothing, calibrator adds no_clash."""
        issues = []  # LLM output nothing
        report = detect_debate_signals(_NO_CLASH_REBUTTAL, "rebuttal")
        result = calibrate_structured_issues(issues, report, "rebuttal")
        types = [i["issue_type"] for i in result]
        assert "no_clash" in types

    def test_missing_warrant_constructive_dedup_and_signal(self):
        """Simulate missing_warrant_constructive: LLM duplicates missing_warrant, detector adds weak_evidence."""
        issues = [_make_issue("missing_warrant", "high"), _make_issue("missing_warrant", "medium")]
        report = detect_debate_signals(_WEAK_CONSTRUCTIVE, "constructive")
        result = calibrate_structured_issues(issues, report, "constructive")
        types = [i["issue_type"] for i in result]
        # Dedup: one missing_warrant
        assert types.count("missing_warrant") == 1
        # Detector adds weak_evidence (medium signal)
        assert "weak_evidence" in types

    def test_empty_input_with_no_signals_returns_empty(self):
        issues = []
        report = _make_report([], budget=4)
        result = calibrate_structured_issues(issues, report, "constructive")
        assert result == []

    def test_synonym_normalization(self):
        """Synonyms from the metrics mapper are normalized before calibration."""
        issues = [{"issue_type": "circular_argument", "severity": "high",
                   "title": "t", "explanation": "e", "why_it_matters": "w",
                   "recommendation": "r", "affected_argument_labels": [],
                   "recommended_drill_type": "warranting"}]
        result = calibrate_structured_issues(issues, _make_report([]), "constructive")
        assert result[0]["issue_type"] == "missing_warrant"


# ── Sample transcripts for new detectors ──────────────────────────────────────

_WEAK_EXTENSION_SUMMARY = (
    "We extend our Contention One. Extend it through. This argument still stands "
    "and the negative never answered it. The impact is erosion of American deterrence capacity. "
    "Vote affirmative.\n"
    "We also extend our Contention Two. Carry through our escalation contention. "
    "This argument still applies. The impact is risk of great power war. "
    "Both of our arguments are clean. Extend both contentions. Vote affirmative."
)

_GOOD_EXTENSION_SUMMARY = (
    "We collapse to our Contention One on fiscal burden. Extend our RAND 2023 evidence. "
    "The warrant is opportunity cost: the mechanism here is that every dollar allocated to "
    "foreign basing cannot simultaneously fund the homeland industrial base. "
    "This is because the defense budget is zero-sum. Therefore the impact — "
    "erosion of deterrence capacity — flows cleanly to us. "
    "The negative never responded to the RAND warrant, which means the internal link stands. "
    "Vote affirmative."
)

_MISSING_WARRANT_CONSTRUCTIVE = (
    "We negate the resolution. The United States should maintain its military presence in East Asia.\n"
    "Contention One: Regional stability. American military bases provide regional stability. "
    "Without them, the region will become more dangerous. "
    "The impact is increased risk of conflict and instability across East Asia.\n"
    "Contention Two: Alliance credibility. Our alliances depend on forward presence. "
    "If we withdraw, our allies will not trust us. "
    "The impact is that our alliance system will collapse and America will be isolated.\n"
    "For these reasons, we urge a negative ballot."
)


# ── _detect_weak_extension ─────────────────────────────────────────────────────

class TestDetectWeakExtension:
    def test_fires_for_summary_with_extension_no_warrant(self):
        sig = _detect_weak_extension(_WEAK_EXTENSION_SUMMARY, "summary")
        assert sig is not None
        assert sig.issue_type == "weak_extension"
        assert sig.confidence == "high"

    def test_fires_for_final_focus_with_extension_no_warrant(self):
        text = (
            "Extend our Contention One. This argument still stands. "
            "The impact is deterrence erosion. Vote negative."
        )
        sig = _detect_weak_extension(text, "final_focus")
        assert sig is not None
        assert sig.issue_type == "weak_extension"

    def test_fires_for_final_focus_with_space_variant(self):
        """Accept 'final focus' (with space) as a late-speech type."""
        text = "Extend our C1. Still stands. Vote affirmative."
        sig = _detect_weak_extension(text, "final focus")
        assert sig is not None
        assert sig.issue_type == "weak_extension"

    def test_does_not_fire_for_constructive(self):
        """Constructives should never trigger weak_extension."""
        sig = _detect_weak_extension(_WEAK_EXTENSION_SUMMARY, "constructive")
        assert sig is None

    def test_does_not_fire_for_rebuttal(self):
        sig = _detect_weak_extension(_WEAK_EXTENSION_SUMMARY, "rebuttal")
        assert sig is None

    def test_does_not_fire_when_no_extension_language(self):
        text = (
            "We argue that the affirmative does not meet its burden. "
            "The impacts are clear and flow negative."
        )
        sig = _detect_weak_extension(text, "summary")
        assert sig is None

    def test_does_not_fire_for_good_extension_summary(self):
        """A summary with full warrant re-establishment should not trigger."""
        sig = _detect_weak_extension(_GOOD_EXTENSION_SUMMARY, "summary")
        assert sig is None

    def test_via_detect_debate_signals_fires_for_weak_extension(self):
        report = detect_debate_signals(_WEAK_EXTENSION_SUMMARY, "summary")
        signal_types = [s.issue_type for s in report.signals]
        assert "weak_extension" in signal_types

    def test_via_detect_debate_signals_no_weak_extension_for_good_summary(self):
        report = detect_debate_signals(_GOOD_EXTENSION_SUMMARY, "summary")
        signal_types = [s.issue_type for s in report.signals]
        assert "weak_extension" not in signal_types


# ── _detect_missing_warrant ────────────────────────────────────────────────────

class TestDetectMissingWarrant:
    def test_fires_for_constructive_claim_no_mechanism(self):
        sig = _detect_missing_warrant(_MISSING_WARRANT_CONSTRUCTIVE, "constructive")
        assert sig is not None
        assert sig.issue_type == "missing_warrant"
        assert sig.confidence == "high"

    def test_fires_for_weak_constructive(self):
        sig = _detect_missing_warrant(_WEAK_CONSTRUCTIVE, "constructive")
        assert sig is not None
        assert sig.issue_type == "missing_warrant"

    def test_does_not_fire_for_good_constructive(self):
        """Strong constructive with named evidence + warrant + impact should not fire."""
        sig = _detect_missing_warrant(_GOOD_CONSTRUCTIVE, "constructive")
        assert sig is None

    def test_does_not_fire_for_summary(self):
        sig = _detect_missing_warrant(_WEAK_EXTENSION_SUMMARY, "summary")
        assert sig is None

    def test_does_not_fire_for_rebuttal(self):
        sig = _detect_missing_warrant(_WEAK_CONSTRUCTIVE, "rebuttal")
        assert sig is None

    def test_does_not_fire_when_causal_language_present(self):
        text = (
            "We argue that bases are expensive. The mechanism is opportunity cost: "
            "the warrant is that every dollar spent overseas cannot be spent domestically. "
            "The impact is deterrence erosion."
        )
        sig = _detect_missing_warrant(text, "constructive")
        assert sig is None

    def test_via_detect_debate_signals_fires_for_missing_warrant(self):
        report = detect_debate_signals(_MISSING_WARRANT_CONSTRUCTIVE, "constructive")
        signal_types = [s.issue_type for s in report.signals]
        assert "missing_warrant" in signal_types

    def test_via_detect_debate_signals_not_in_good_constructive(self):
        report = detect_debate_signals(_GOOD_CONSTRUCTIVE, "constructive")
        signal_types = [s.issue_type for s in report.signals]
        assert "missing_warrant" not in signal_types


# ── Calibration for new signal types ──────────────────────────────────────────

class TestCalibrateNewSignals:
    def test_calibration_adds_weak_extension(self):
        """Calibrator injects weak_extension when LLM missed it."""
        issues = []
        signals = [_make_signal("weak_extension", "high")]
        result = calibrate_structured_issues(issues, _make_report(signals, budget=4, speech_type="summary"), "summary")
        types = [i["issue_type"] for i in result]
        assert "weak_extension" in types

    def test_calibration_adds_missing_warrant(self):
        """Calibrator injects missing_warrant when LLM missed it."""
        issues = []
        signals = [_make_signal("missing_warrant", "high")]
        result = calibrate_structured_issues(issues, _make_report(signals, budget=4), "constructive")
        types = [i["issue_type"] for i in result]
        assert "missing_warrant" in types

    def test_budget_zero_suppresses_unsupported_missing_warrant(self):
        """Quality gate (budget=0) suppresses LLM-invented missing_warrant on strong speech."""
        issues = [_make_issue("missing_warrant")]
        report = _make_report([], budget=0, has_named=True, has_warrant=True, has_impact=True)
        result = calibrate_structured_issues(issues, report, "constructive")
        types = [i["issue_type"] for i in result]
        assert "missing_warrant" not in types

    def test_budget_zero_does_not_suppress_signal_backed_missing_warrant(self):
        """Even with budget=0, missing_warrant backed by a detector signal is kept."""
        issues = [_make_issue("missing_warrant")]
        signals = [_make_signal("missing_warrant", "high")]
        report = _make_report(signals, budget=0)
        result = calibrate_structured_issues(issues, report, "constructive")
        types = [i["issue_type"] for i in result]
        assert "missing_warrant" in types

    def test_dedup_weak_extension_and_missing_warrant(self):
        """Duplicate weak_extension and missing_warrant are deduped correctly."""
        issues = [
            _make_issue("weak_extension", "medium"),
            _make_issue("weak_extension", "high"),
            _make_issue("missing_warrant", "high"),
            _make_issue("missing_warrant", "medium"),
        ]
        result = calibrate_structured_issues(issues, _make_report([]), "summary")
        types = [i["issue_type"] for i in result]
        assert types.count("weak_extension") == 1
        assert types.count("missing_warrant") == 1
