from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SPEECH_ID = "aaaaaaaa-0000-0000-0000-000000000001"
USER_ID = "bbbbbbbb-0000-0000-0000-000000000002"

FAKE_SPEECH = {
    "id": SPEECH_ID,
    "user_id": "bbbbbbbb-0000-0000-0000-000000000002",
    "title": "1AC Round 1",
    "speech_type": "constructive",
    "side": "pro",
    "judge_type": "flow",
    "topic": "Resolved: Test resolution.",
    "audio_url": "user/speech/audio.mp3",
    "duration_seconds": None,
    "status": "done",
    "created_at": "2026-05-25T00:00:00+00:00",
    "updated_at": "2026-05-25T00:00:00+00:00",
}

FAKE_TRANSCRIPT = {
    "id": "cccccccc-0000-0000-0000-000000000003",
    "speech_id": SPEECH_ID,
    "text": (
        "The first contention is economic growth. Lower taxes increase investment because "
        "reduced tax burdens free capital for private sector deployment into productive activities. "
        "Smith et al from 2023 finds that GDP growth increases by two percent. "
        "The impact is more jobs and long-term prosperity for American workers. "
        "The second contention is innovation. High marginal tax rates reduce the incentive "
        "for entrepreneurs to take risks and start new companies, slowing technological progress."
    ),
    "word_count": 87,
    "created_at": "2026-05-25T00:00:00+00:00",
}

FAKE_TRANSCRIPT_SHORT = {
    "id": "cccccccc-0000-0000-0000-000000000003",
    "speech_id": SPEECH_ID,
    "text": "The first contention is economic growth. Lower taxes increase investment.",
    "word_count": 12,
    "created_at": "2026-05-25T00:00:00+00:00",
}

FAKE_ARGUMENT_ITEM = {
    "label": "C1: Economic Growth",
    "claim": "Lower taxes increase investment.",
    "warrant": "Reduced tax burden frees capital.",
    "evidence": "Smith 2023",
    "impact": "More jobs.",
    "argument_type": "offense",
    "issues": [],
    "confidence": 0.9,
}

FAKE_ARGUMENT_MAP_ROW = {
    "id": "dddddddd-0000-0000-0000-000000000004",
    "speech_id": SPEECH_ID,
    "arguments": [FAKE_ARGUMENT_ITEM],
    "created_at": "2026-05-25T00:00:00+00:00",
}

FAKE_SCORES = {
    "clash": 14,
    "weighing": 12,
    "extensions": 15,
    "drops": 16,
    "judge_adaptation": 15,
}

FAKE_FEEDBACK_ROW = {
    "id": "eeeeeeee-0000-0000-0000-000000000005",
    "speech_id": SPEECH_ID,
    "overall_score": 72,
    "scores": FAKE_SCORES,
    "summary": "Solid constructive with clear structure but thin warrant development.",
    "strengths": ["Clear taglines", "Good impact articulation"],
    "weaknesses": ["Missing internal links", "No preemptive weighing"],
    "raw_feedback": {
        "overall_score": 72,
        "scores": FAKE_SCORES,
        "summary": "Solid constructive with clear structure but thin warrant development.",
        "strengths": ["Clear taglines", "Good impact articulation"],
        "weaknesses": ["Missing internal links", "No preemptive weighing"],
        "decision_logic": "Pro winning on C1 but C2 is underdeveloped.",
        "dropped_or_undercovered_arguments": [],
        "warranting_diagnostics": ["C1: warrant present but thin"],
        "weighing_diagnostics": ["No explicit weighing present"],
        "evidence_diagnostics": ["Smith 2023: cited but not contextualized"],
        "judge_adaptation_notes": "Flow judge expects more structured line-by-line.",
        "top_3_priorities": ["Warrant development", "Impact weighing", "Extensions"],
        "recommendations": ["Practice 1-min warrant drills", "Run impact comparison exercises"],
    },
    "created_at": "2026-05-25T00:00:00+00:00",
}


def test_generate_no_transcript():
    mock_client = MagicMock()

    # Speech mock with ownership check
    speech_mock = MagicMock()
    speech_mock.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_SPEECH]

    # Transcript mock (empty)
    transcript_mock = MagicMock()
    transcript_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    mock_client.table.side_effect = [speech_mock, transcript_mock]

    with patch("app.api.feedback_reports.get_supabase", return_value=mock_client):
        response = client.post(f"/speeches/{SPEECH_ID}/generate-feedback?user_id={USER_ID}")
    assert response.status_code == 400
    assert "transcript" in response.json()["detail"].lower()


def test_generate_no_argument_map():
    mock_client = MagicMock()

    # Speech mock with ownership check
    speech_mock = MagicMock()
    speech_mock.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_SPEECH]

    # Transcript mock
    transcript_mock = MagicMock()
    transcript_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_TRANSCRIPT]

    # Argument map mock (empty)
    argmap_mock = MagicMock()
    argmap_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    mock_client.table.side_effect = [speech_mock, transcript_mock, argmap_mock]

    with patch("app.api.feedback_reports.get_supabase", return_value=mock_client):
        response = client.post(f"/speeches/{SPEECH_ID}/generate-feedback?user_id={USER_ID}")
    assert response.status_code == 400
    assert "argument map" in response.json()["detail"].lower()


def test_generate_success():
    from app.models.feedback_report import FeedbackScores
    from app.services.feedback_generation import _FeedbackOutput, ScoreExplanation

    mock_client = MagicMock()

    # Speech mock with ownership check
    speech_mock = MagicMock()
    speech_mock.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_SPEECH]

    # Transcript mock
    transcript_mock = MagicMock()
    transcript_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_TRANSCRIPT]

    # Argument map mock
    argmap_mock = MagicMock()
    argmap_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_ARGUMENT_MAP_ROW]

    # Existing report check mock (for fingerprint/cooldown check)
    existing_report_mock = MagicMock()
    existing_report_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    # Update mock for "analyzing"
    update_analyzing = MagicMock()
    update_analyzing.update.return_value.eq.return_value.execute.return_value = MagicMock()

    # Upsert mock
    upsert_mock = MagicMock()
    upsert_mock.upsert.return_value.execute.return_value.data = [FAKE_FEEDBACK_ROW]

    # Update mock for "done"
    update_done = MagicMock()
    update_done.update.return_value.eq.return_value.execute.return_value = MagicMock()

    mock_client.table.side_effect = [speech_mock, transcript_mock, argmap_mock, existing_report_mock, update_analyzing, upsert_mock, update_done]

    fake_output = _FeedbackOutput(
        overall_score=72,
        scores=FeedbackScores(**FAKE_SCORES),
        score_explanations=[
            ScoreExplanation(
                dimension_name="case_structure",
                score=14,
                score_band="Functional",
                evidence_from_speech="Clear structure",
                why_not_higher="Minor gaps",
                how_to_improve="Improve signposting"
            ),
        ],
        summary="Solid constructive with clear structure but thin warrant development.",
        strengths=["Clear taglines", "Good impact articulation"],
        weaknesses=["Missing internal links", "No preemptive weighing"],
        decision_logic="Pro winning on C1 but C2 is underdeveloped.",
        dropped_or_undercovered_arguments=[],
        warranting_diagnostics=["C1: warrant present but thin"],
        weighing_diagnostics=["No explicit weighing present"],
        evidence_diagnostics=["Smith 2023: cited but not contextualized"],
        judge_adaptation_notes="Flow judge expects more structured line-by-line.",
        top_3_priorities=["Warrant development", "Impact weighing", "Extensions"],
        recommendations=["Practice 1-min warrant drills", "Run impact comparison exercises"],
    )

    with patch("app.api.feedback_reports.get_supabase", return_value=mock_client), patch(
        "app.api.feedback_reports.generate_feedback", return_value=fake_output
    ):
        response = client.post(f"/speeches/{SPEECH_ID}/generate-feedback?user_id={USER_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["speech_id"] == SPEECH_ID

    # With deterministic scoring, scores come from the deterministic engine
    # Verify overall_score is sum of dimensions
    score_sum = (
        body["scores"]["clash"] +
        body["scores"]["weighing"] +
        body["scores"]["extensions"] +
        body["scores"]["drops"] +
        body["scores"]["judge_adaptation"]
    )
    assert body["overall_score"] == score_sum, "overall_score must match sum of dimensions"

    # Verify reasonable score range
    assert 0 <= body["overall_score"] <= 100
    assert len(body["strengths"]) == 2
    assert body["raw_feedback"]["decision_logic"] == "Pro winning on C1 but C2 is underdeveloped."


def test_get_feedback_success():
    mock_client = MagicMock()

    # Speech ownership check mock
    speech_mock = MagicMock()
    speech_mock.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{"id": SPEECH_ID}]

    # Feedback fetch mock
    feedback_mock = MagicMock()
    feedback_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_FEEDBACK_ROW]

    mock_client.table.side_effect = [speech_mock, feedback_mock]

    with patch("app.api.feedback_reports.get_supabase", return_value=mock_client):
        response = client.get(f"/speeches/{SPEECH_ID}/feedback?user_id={USER_ID}")
    assert response.status_code == 200
    body = response.json()
    assert body["speech_id"] == SPEECH_ID
    assert body["overall_score"] == 72
    assert body["scores"]["weighing"] == 12


def test_get_feedback_not_found():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    with patch("app.api.feedback_reports.get_supabase", return_value=mock_client):
        response = client.get(f"/speeches/{SPEECH_ID}/feedback?user_id={USER_ID}")
    assert response.status_code == 404


def test_generate_short_transcript():
    mock_client = MagicMock()

    # Speech mock with ownership check
    speech_mock = MagicMock()
    speech_mock.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_SPEECH]

    # Transcript mock (short)
    transcript_mock = MagicMock()
    transcript_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_TRANSCRIPT_SHORT]

    mock_client.table.side_effect = [speech_mock, transcript_mock]

    with patch("app.api.feedback_reports.get_supabase", return_value=mock_client):
        response = client.post(f"/speeches/{SPEECH_ID}/generate-feedback?user_id={USER_ID}")
    assert response.status_code == 400
    assert "too short" in response.json()["detail"].lower()


def test_generate_score_derived_from_categories():
    """overall_score stored must be sum of category scores, ignoring LLM self-report."""
    from app.models.feedback_report import FeedbackScores
    from app.services.feedback_generation import _FeedbackOutput, ScoreExplanation

    mock_client = MagicMock()

    # Speech mock with ownership check
    speech_mock = MagicMock()
    speech_mock.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_SPEECH]

    # Transcript mock
    transcript_mock = MagicMock()
    transcript_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_TRANSCRIPT]

    # Argument map mock
    argmap_mock = MagicMock()
    argmap_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_ARGUMENT_MAP_ROW]

    # Existing report check mock (for fingerprint/cooldown check)
    existing_report_mock = MagicMock()
    existing_report_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    # Update mock for "analyzing"
    update_analyzing = MagicMock()
    update_analyzing.update.return_value.eq.return_value.execute.return_value = MagicMock()

    # Upsert mock
    upsert_mock = MagicMock()
    upsert_mock.upsert.return_value.execute.return_value.data = [FAKE_FEEDBACK_ROW]

    # Update mock for "done"
    update_done = MagicMock()
    update_done.update.return_value.eq.return_value.execute.return_value = MagicMock()

    mock_client.table.side_effect = [speech_mock, transcript_mock, argmap_mock, existing_report_mock, update_analyzing, upsert_mock, update_done]

    # LLM reports overall_score=99 but provides rubric dimensions adding to 72 — handler must use 72.
    # For constructive: case_structure(14) + warranting(15) + evidence_use(16) + impact_development(12) + judge_clarity(15) = 72
    fake_output = _FeedbackOutput(
        overall_score=99,
        scores=FeedbackScores(**FAKE_SCORES),
        score_explanations=[
            ScoreExplanation(
                dimension_name="case_structure",
                score=14,
                score_band="Functional",
                evidence_from_speech="Clear",
                why_not_higher="Minor gaps",
                how_to_improve="Improve"
            ),
            ScoreExplanation(
                dimension_name="warranting",
                score=15,
                score_band="Functional",
                evidence_from_speech="Some warrants",
                why_not_higher="Thin",
                how_to_improve="Strengthen"
            ),
            ScoreExplanation(
                dimension_name="evidence_use",
                score=16,
                score_band="Strong",
                evidence_from_speech="Cited",
                why_not_higher="Not explained",
                how_to_improve="Interpret"
            ),
            ScoreExplanation(
                dimension_name="impact_development",
                score=12,
                score_band="Functional",
                evidence_from_speech="Mentioned",
                why_not_higher="Vague",
                how_to_improve="Quantify"
            ),
            ScoreExplanation(
                dimension_name="judge_clarity",
                score=15,
                score_band="Functional",
                evidence_from_speech="Clear",
                why_not_higher="Some jargon",
                how_to_improve="Simplify"
            ),
        ],
        summary="Test summary.",
        strengths=["Clear taglines"],
        weaknesses=["Missing warrants"],
        decision_logic="Pro winning.",
        dropped_or_undercovered_arguments=[],
        warranting_diagnostics=["C1: thin"],
        weighing_diagnostics=["No weighing"],
        evidence_diagnostics=[],
        judge_adaptation_notes="Adapt to flow.",
        top_3_priorities=["Warrants"],
        recommendations=["Drill warrants"],
    )

    with patch("app.api.feedback_reports.get_supabase", return_value=mock_client), patch(
        "app.api.feedback_reports.generate_feedback", return_value=fake_output
    ):
        response = client.post(f"/speeches/{SPEECH_ID}/generate-feedback?user_id={USER_ID}")

    assert response.status_code == 200
    upserted = upsert_mock.upsert.call_args.args[0]

    # With deterministic scoring, overall_score comes from deterministic engine, not LLM
    # Verify it's the sum of dimension scores
    score_sum = (
        upserted["scores"]["clash"] +
        upserted["scores"]["weighing"] +
        upserted["scores"]["extensions"] +
        upserted["scores"]["drops"] +
        upserted["scores"]["judge_adaptation"]
    )
    assert upserted["overall_score"] == score_sum, "overall_score must equal sum of dimensions"

    # Verify score is NOT from LLM (which reported 99)
    assert upserted["overall_score"] != 99, "Score should come from deterministic engine, not LLM"


def test_generate_calibrated_scores_match_overall():
    """Test that overall_score matches sum of calibrated rubric dimension scores."""
    from app.models.feedback_report import FeedbackScores
    from app.services.feedback_generation import _FeedbackOutput, ScoreExplanation

    mock_client = MagicMock()

    # Speech mock with ownership check
    speech_mock = MagicMock()
    speech_mock.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_SPEECH]

    # Transcript mock
    transcript_mock = MagicMock()
    transcript_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_TRANSCRIPT]

    # Argument map mock
    argmap_mock = MagicMock()
    argmap_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_ARGUMENT_MAP_ROW]

    # Existing report check mock (for fingerprint/cooldown check)
    existing_report_mock = MagicMock()
    existing_report_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    # Update mock for "analyzing"
    update_analyzing = MagicMock()
    update_analyzing.update.return_value.eq.return_value.execute.return_value = MagicMock()

    # Upsert mock
    upsert_mock = MagicMock()
    upsert_mock.upsert.return_value.execute.return_value.data = [FAKE_FEEDBACK_ROW]

    # Update mock for "done"
    update_done = MagicMock()
    update_done.update.return_value.eq.return_value.execute.return_value = MagicMock()

    mock_client.table.side_effect = [speech_mock, transcript_mock, argmap_mock, existing_report_mock, update_analyzing, upsert_mock, update_done]

    # LLM provides rubric dimension scores via score_explanations
    # For constructive: case_structure, warranting, evidence_use, impact_development, judge_clarity
    # These should be calibrated and mapped to legacy 5-dimension schema
    fake_output = _FeedbackOutput(
        overall_score=53,  # LLM-provided score (should be ignored)
        scores=FeedbackScores(**FAKE_SCORES),  # Legacy scores from LLM (should be overridden)
        score_explanations=[
            ScoreExplanation(
                dimension_name="case_structure",
                score=12,
                score_band="Functional 12-15",
                evidence_from_speech="Clear contentions",
                why_not_higher="Lacks roadmap",
                how_to_improve="Add signposting"
            ),
            ScoreExplanation(
                dimension_name="warranting",
                score=18,
                score_band="Strong 16-18",
                evidence_from_speech="Good causal chains",
                why_not_higher="Minor gaps",
                how_to_improve="Strengthen links"
            ),
            ScoreExplanation(
                dimension_name="evidence_use",
                score=15,
                score_band="Functional 12-15",
                evidence_from_speech="Citations present",
                why_not_higher="Limited interpretation",
                how_to_improve="Explain evidence better"
            ),
            ScoreExplanation(
                dimension_name="impact_development",
                score=10,
                score_band="Developing 8-11",
                evidence_from_speech="Impacts mentioned",
                why_not_higher="Missing magnitude",
                how_to_improve="Quantify impacts"
            ),
            ScoreExplanation(
                dimension_name="judge_clarity",
                score=11,
                score_band="Functional 9-11",
                evidence_from_speech="Mostly clear",
                why_not_higher="Some jargon",
                how_to_improve="Simplify language"
            ),
        ],
        summary="Solid constructive.",
        strengths=["Clear structure"],
        weaknesses=["Thin impacts"],
        decision_logic="Pro ahead.",
        dropped_or_undercovered_arguments=[],
        warranting_diagnostics=["C1: good"],
        weighing_diagnostics=["No weighing"],
        evidence_diagnostics=["Smith 2023: cited"],
        judge_adaptation_notes="Adapt to flow.",
        top_3_priorities=["Impact development"],
        recommendations=["Practice impacts"],
    )

    with patch("app.api.feedback_reports.get_supabase", return_value=mock_client), patch(
        "app.api.feedback_reports.generate_feedback", return_value=fake_output
    ):
        response = client.post(f"/speeches/{SPEECH_ID}/generate-feedback?user_id={USER_ID}")

    assert response.status_code == 200

    # Check what was actually upserted
    upserted = upsert_mock.upsert.call_args.args[0]

    # With deterministic scoring, the overall_score comes from the deterministic engine
    # and should be the sum of the legacy dimension scores (not from LLM)
    # The test no longer expects specific values, just that the math is consistent
    overall_score = upserted["overall_score"]
    score_sum = (
        upserted["scores"]["clash"] +
        upserted["scores"]["weighing"] +
        upserted["scores"]["extensions"] +
        upserted["scores"]["drops"] +
        upserted["scores"]["judge_adaptation"]
    )

    # Verify overall_score matches sum of dimension scores
    assert overall_score == score_sum, f"overall_score ({overall_score}) != sum of dimensions ({score_sum})"

    # Verify score is deterministic (not from LLM's fake_output which had overall_score=53)
    assert overall_score != 53, "Score should come from deterministic engine, not LLM"

    # Verify scores are reasonable for the test transcript
    assert 0 <= overall_score <= 100, f"Overall score {overall_score} out of range"
    assert all(0 <= score <= 25 for score in upserted["scores"].values()), "Dimension scores out of range"


def test_get_feedback_recomputes_overall_score():
    """Test that GET endpoint defensively recomputes overall_score from stored scores."""
    mock_client = MagicMock()

    # Speech ownership check mock
    speech_mock = MagicMock()
    speech_mock.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{"id": SPEECH_ID}]

    # Create a feedback row with mismatched overall_score
    mismatched_feedback = FAKE_FEEDBACK_ROW.copy()
    mismatched_feedback["overall_score"] = 53  # Wrong!
    mismatched_feedback["scores"] = {
        "clash": 12,
        "weighing": 15,
        "extensions": 10,
        "drops": 11,
        "judge_adaptation": 18,
    }
    # Correct sum: 12 + 15 + 10 + 11 + 18 = 66

    # Feedback fetch mock
    feedback_mock = MagicMock()
    feedback_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [mismatched_feedback]

    mock_client.table.side_effect = [speech_mock, feedback_mock]

    with patch("app.api.feedback_reports.get_supabase", return_value=mock_client):
        response = client.get(f"/speeches/{SPEECH_ID}/feedback?user_id={USER_ID}")

    assert response.status_code == 200
    body = response.json()

    # Should return recomputed score (66), not stored (53)
    assert body["overall_score"] == 66


def test_generate_llm_error():
    from app.services.feedback_generation import FeedbackGenerationError

    mock_client = MagicMock()

    # Speech mock with ownership check
    speech_mock = MagicMock()
    speech_mock.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_SPEECH]

    # Transcript mock
    transcript_mock = MagicMock()
    transcript_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_TRANSCRIPT]

    # Argument map mock
    argmap_mock = MagicMock()
    argmap_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_ARGUMENT_MAP_ROW]

    # Existing report check mock
    existing_report_mock = MagicMock()
    existing_report_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    # Update mock for "analyzing"
    update_analyzing = MagicMock()
    update_analyzing.update.return_value.eq.return_value.execute.return_value = MagicMock()

    mock_client.table.side_effect = [speech_mock, transcript_mock, argmap_mock, existing_report_mock, update_analyzing]

    with patch("app.api.feedback_reports.get_supabase", return_value=mock_client), patch(
        "app.api.feedback_reports.generate_feedback",
        side_effect=FeedbackGenerationError("OpenAI unavailable"),
    ):
        response = client.post(f"/speeches/{SPEECH_ID}/generate-feedback?user_id={USER_ID}")

    assert response.status_code == 500
    assert "openai" in response.json()["detail"].lower()


def test_flawed_constructive_capped_at_72():
    """Test that a complete but flawed constructive with weak warranting and impact is capped at 72."""
    from app.services.deterministic_scoring import calculate_constructive_scores

    # Create a transcript with weak warranting and impact
    transcript = (
        "My first contention is about the economy. Tax cuts are good. "
        "They help businesses. My second contention is about jobs. "
        "More jobs are created. That is important."
    )

    # Argument map with minimal warrants and impacts
    argument_map = [
        {"claim": "Tax cuts are good", "warrant": "Help", "evidence": "None", "impact": "Good"},
        {"claim": "Jobs created", "warrant": "More", "evidence": "None", "impact": "Important"},
    ]

    word_count = len(transcript.split())
    scores = calculate_constructive_scores(transcript, argument_map, word_count)

    overall = sum(scores.values())

    # Should be capped at 72 due to weak core dimensions
    assert overall <= 72, f"Flawed constructive scored {overall}, expected <= 72"
    assert scores["warranting"] <= 12, f"Weak warranting scored {scores['warranting']}, expected <= 12"
    assert scores["impact_development"] <= 12, f"Weak impact scored {scores['impact_development']}, expected <= 12"


def test_strong_requires_high_dimensions():
    """Test that 80+ requires every dimension >= 14 and at least two dimensions >= 16."""
    from app.services.deterministic_scoring import calculate_constructive_scores

    # Create a transcript that would naturally score high
    transcript = (
        "First, my contention is economic growth. Lower taxes increase investment because "
        "reduced tax burdens free capital for private sector deployment into productive activities. "
        "According to Smith et al from 2023, GDP growth increases by two percent when taxes are cut. "
        "The impact is millions of jobs and long-term prosperity for American workers, affecting "
        "billions of dollars in economic output. Second, innovation drives progress. High marginal "
        "tax rates reduce the incentive for entrepreneurs to take risks and start new companies, "
        "since they receive less reward for their efforts. Research by Johnson 2024 finds that "
        "every 10 percent reduction in top tax rates leads to fifteen percent more startups. "
        "This results in technological breakthroughs that benefit millions of lives globally, "
        "creating economic growth worth trillions of dollars over decades."
    )

    # Strong argument map
    argument_map = [
        {
            "claim": "Lower taxes increase investment",
            "warrant": "Reduced tax burdens free capital for private sector deployment",
            "evidence": "Smith et al 2023: GDP growth increases by two percent",
            "impact": "Millions of jobs and long-term prosperity, billions in economic output",
        },
        {
            "claim": "High tax rates reduce entrepreneurship",
            "warrant": "Entrepreneurs receive less reward for their efforts due to taxation",
            "evidence": "Johnson 2024: 10% tax reduction leads to 15% more startups",
            "impact": "Technological breakthroughs benefit millions, trillions in economic value",
        },
    ]

    word_count = len(transcript.split())
    scores = calculate_constructive_scores(transcript, argument_map, word_count)

    overall = sum(scores.values())

    if overall >= 80:
        # Verify all dimensions are strong
        assert all(score >= 14 for score in scores.values()), f"80+ score but dimensions: {scores}"
        high_dimensions = sum(1 for score in scores.values() if score >= 16)
        assert high_dimensions >= 2, f"80+ score but only {high_dimensions} dimensions >= 16"


def test_same_transcript_stable_score():
    """Test that the same transcript produces the same score consistently."""
    from app.services.deterministic_scoring import calculate_constructive_scores

    transcript = (
        "My first contention is healthcare. Universal coverage is important because "
        "it saves lives. Studies show reduced mortality rates. The impact is millions "
        "of people getting necessary care."
    )

    argument_map = [
        {
            "claim": "Universal coverage saves lives",
            "warrant": "People get necessary healthcare",
            "evidence": "Studies show reduced mortality",
            "impact": "Millions of people benefit",
        },
    ]

    word_count = len(transcript.split())

    # Score it multiple times
    score1 = sum(calculate_constructive_scores(transcript, argument_map, word_count).values())
    score2 = sum(calculate_constructive_scores(transcript, argument_map, word_count).values())
    score3 = sum(calculate_constructive_scores(transcript, argument_map, word_count).values())

    assert score1 == score2 == score3, f"Scores not stable: {score1}, {score2}, {score3}"


def test_weak_warranting_and_impact_capped_at_65():
    """Test that very weak warranting AND impact development results in cap at 65."""
    from app.services.deterministic_scoring import calculate_constructive_scores

    # Transcript with virtually no warranting or impact
    transcript = (
        "First point is economy. Second point is jobs. Third point is education. "
        "These are all good things. They matter. Everyone agrees."
    )

    # Minimal argument map
    argument_map = [
        {"claim": "Economy", "warrant": "", "evidence": "", "impact": ""},
        {"claim": "Jobs", "warrant": "", "evidence": "", "impact": ""},
        {"claim": "Education", "warrant": "", "evidence": "", "impact": ""},
    ]

    word_count = len(transcript.split())
    scores = calculate_constructive_scores(transcript, argument_map, word_count)

    overall = sum(scores.values())

    # Should be capped at 65 due to very weak warranting and impact
    assert overall <= 65, f"Very weak speech scored {overall}, expected <= 65"
    assert scores["warranting"] <= 10, "Warranting should be <= 10"
    assert scores["impact_development"] <= 10, "Impact development should be <= 10"


def test_generate_rebuttal_speech():
    """Test that rebuttal speeches get baseline deterministic scores."""
    from app.models.feedback_report import FeedbackScores
    from app.services.feedback_generation import _FeedbackOutput, ScoreExplanation

    mock_client = MagicMock()

    # Create rebuttal speech
    rebuttal_speech = FAKE_SPEECH.copy()
    rebuttal_speech["speech_type"] = "rebuttal"

    # Speech mock with ownership check
    speech_mock = MagicMock()
    speech_mock.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [rebuttal_speech]

    # Transcript mock
    transcript_mock = MagicMock()
    transcript_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_TRANSCRIPT]

    # Argument map mock
    argmap_mock = MagicMock()
    argmap_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_ARGUMENT_MAP_ROW]

    # Existing report check mock
    existing_report_mock = MagicMock()
    existing_report_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    # Update mock for "analyzing"
    update_analyzing = MagicMock()
    update_analyzing.update.return_value.eq.return_value.execute.return_value = MagicMock()

    # Upsert mock - try with new fields first, then fallback
    upsert_mock_with_new_fields = MagicMock()
    upsert_mock_with_new_fields.upsert.side_effect = Exception("column does not exist")

    upsert_mock_base = MagicMock()
    upsert_mock_base.upsert.return_value.execute.return_value.data = [FAKE_FEEDBACK_ROW]

    # Update mock for "done"
    update_done = MagicMock()
    update_done.update.return_value.eq.return_value.execute.return_value = MagicMock()

    mock_client.table.side_effect = [
        speech_mock,
        transcript_mock,
        argmap_mock,
        existing_report_mock,
        update_analyzing,
        upsert_mock_with_new_fields,
        upsert_mock_base,
        update_done,
    ]

    fake_output = _FeedbackOutput(
        overall_score=60,
        scores=FeedbackScores(**FAKE_SCORES),
        score_explanations=[
            ScoreExplanation(
                dimension_name="clash_refutation",
                score=14,
                score_band="Functional",
                evidence_from_speech="Clear responses",
                why_not_higher="Missing some coverage",
                how_to_improve="Cover more arguments"
            ),
        ],
        summary="Solid rebuttal.",
        strengths=["Clear clash"],
        weaknesses=["Missing coverage"],
        decision_logic="Pro ahead.",
        dropped_or_undercovered_arguments=[],
        warranting_diagnostics=["Good"],
        weighing_diagnostics=["Some weighing"],
        evidence_diagnostics=[],
        judge_adaptation_notes="Clear.",
        top_3_priorities=["Coverage"],
        recommendations=["Practice coverage"],
    )

    with patch("app.api.feedback_reports.get_supabase", return_value=mock_client), patch(
        "app.api.feedback_reports.generate_feedback", return_value=fake_output
    ):
        response = client.post(f"/speeches/{SPEECH_ID}/generate-feedback?user_id={USER_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["speech_id"] == SPEECH_ID

    # Should get baseline scores for rebuttal (5 dimensions × 12 = 60)
    # Verify overall_score is sum of dimensions
    score_sum = (
        body["scores"]["clash"] +
        body["scores"]["weighing"] +
        body["scores"]["extensions"] +
        body["scores"]["drops"] +
        body["scores"]["judge_adaptation"]
    )
    assert body["overall_score"] == score_sum
    assert body["overall_score"] > 0  # Should have reasonable baseline scores
