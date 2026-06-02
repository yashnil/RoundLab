from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SPEECH_ID = "aaaaaaaa-0000-0000-0000-000000000001"

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
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = [
        MagicMock(data=[FAKE_SPEECH]),
        MagicMock(data=[]),  # no transcript
    ]
    with patch("app.api.feedback_reports.get_supabase", return_value=mock_client):
        response = client.post(f"/speeches/{SPEECH_ID}/generate-feedback")
    assert response.status_code == 400
    assert "transcript" in response.json()["detail"].lower()


def test_generate_no_argument_map():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = [
        MagicMock(data=[FAKE_SPEECH]),
        MagicMock(data=[FAKE_TRANSCRIPT]),
        MagicMock(data=[]),  # no argument map
    ]
    with patch("app.api.feedback_reports.get_supabase", return_value=mock_client):
        response = client.post(f"/speeches/{SPEECH_ID}/generate-feedback")
    assert response.status_code == 400
    assert "argument map" in response.json()["detail"].lower()


def test_generate_success():
    from app.models.feedback_report import FeedbackScores
    from app.services.feedback_generation import _FeedbackOutput

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = [
        MagicMock(data=[FAKE_SPEECH]),
        MagicMock(data=[FAKE_TRANSCRIPT]),
        MagicMock(data=[FAKE_ARGUMENT_MAP_ROW]),
    ]
    mock_client.table.return_value.upsert.return_value.execute.return_value.data = [
        FAKE_FEEDBACK_ROW
    ]

    fake_output = _FeedbackOutput(
        overall_score=72,
        scores=FeedbackScores(**FAKE_SCORES),
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
        response = client.post(f"/speeches/{SPEECH_ID}/generate-feedback")

    assert response.status_code == 200
    body = response.json()
    assert body["speech_id"] == SPEECH_ID
    assert body["overall_score"] == 72
    assert body["scores"]["clash"] == 14
    assert len(body["strengths"]) == 2
    assert body["raw_feedback"]["decision_logic"] == "Pro winning on C1 but C2 is underdeveloped."


def test_get_feedback_success():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        FAKE_FEEDBACK_ROW
    ]
    with patch("app.api.feedback_reports.get_supabase", return_value=mock_client):
        response = client.get(f"/speeches/{SPEECH_ID}/feedback")
    assert response.status_code == 200
    body = response.json()
    assert body["speech_id"] == SPEECH_ID
    assert body["overall_score"] == 72
    assert body["scores"]["weighing"] == 12


def test_get_feedback_not_found():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    with patch("app.api.feedback_reports.get_supabase", return_value=mock_client):
        response = client.get(f"/speeches/{SPEECH_ID}/feedback")
    assert response.status_code == 404


def test_generate_short_transcript():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = [
        MagicMock(data=[FAKE_SPEECH]),
        MagicMock(data=[FAKE_TRANSCRIPT_SHORT]),  # < 50 words
    ]
    with patch("app.api.feedback_reports.get_supabase", return_value=mock_client):
        response = client.post(f"/speeches/{SPEECH_ID}/generate-feedback")
    assert response.status_code == 400
    assert "too short" in response.json()["detail"].lower()


def test_generate_score_derived_from_categories():
    """overall_score stored must be sum of category scores, ignoring LLM self-report."""
    from app.models.feedback_report import FeedbackScores
    from app.services.feedback_generation import _FeedbackOutput

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = [
        MagicMock(data=[FAKE_SPEECH]),
        MagicMock(data=[FAKE_TRANSCRIPT]),
        MagicMock(data=[FAKE_ARGUMENT_MAP_ROW]),
    ]
    mock_client.table.return_value.upsert.return_value.execute.return_value.data = [
        FAKE_FEEDBACK_ROW
    ]

    # LLM reports overall_score=99 but the sum of FAKE_SCORES is 72 — handler must ignore 99.
    fake_output = _FeedbackOutput(
        overall_score=99,
        scores=FeedbackScores(**FAKE_SCORES),
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
        client.post(f"/speeches/{SPEECH_ID}/generate-feedback")

    upserted = mock_client.table.return_value.upsert.call_args.args[0]
    expected = FAKE_SCORES["clash"] + FAKE_SCORES["weighing"] + FAKE_SCORES["extensions"] + FAKE_SCORES["drops"] + FAKE_SCORES["judge_adaptation"]
    assert upserted["overall_score"] == expected
    assert upserted["overall_score"] != 99


def test_generate_llm_error():
    from app.services.feedback_generation import FeedbackGenerationError

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = [
        MagicMock(data=[FAKE_SPEECH]),
        MagicMock(data=[FAKE_TRANSCRIPT]),
        MagicMock(data=[FAKE_ARGUMENT_MAP_ROW]),
    ]

    with patch("app.api.feedback_reports.get_supabase", return_value=mock_client), patch(
        "app.api.feedback_reports.generate_feedback",
        side_effect=FeedbackGenerationError("OpenAI unavailable"),
    ):
        response = client.post(f"/speeches/{SPEECH_ID}/generate-feedback")

    assert response.status_code == 500
    assert "openai" in response.json()["detail"].lower()
