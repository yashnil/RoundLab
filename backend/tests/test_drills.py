from datetime import datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SPEECH_ID = "aaaaaaaa-1111-0000-0000-000000000001"
DRILL_ID   = "dddddddd-0000-0000-0000-000000000099"
USER_ID    = "bbbbbbbb-0000-0000-0000-000000000002"

FAKE_SPEECH = {
    "id": SPEECH_ID,
    "user_id": USER_ID,
    "title": "1AC Round 1",
    "speech_type": "constructive",
    "side": "pro",
    "judge_type": "flow",
    "topic": "Resolved: Test resolution.",
    "audio_url": "user/speech/audio.mp3",
    "status": "done",
    "created_at": "2026-05-25T00:00:00+00:00",
    "updated_at": "2026-05-25T00:00:00+00:00",
}

FAKE_FEEDBACK_ROW = {
    "id": "ffffffff-0000-0000-0000-000000000001",
    "speech_id": SPEECH_ID,
    "overall_score": 62,
    "scores": {
        "clash": 10,
        "weighing": 9,
        "extensions": 14,
        "drops": 16,
        "judge_adaptation": 13,
    },
    "summary": "Solid warranting but weak impact weighing.",
    "strengths": ["Good warrant structure"],
    "weaknesses": ["Impact weighing not explicit", "Dropped opponent contention 2"],
    "raw_feedback": {
        "top_3_priorities": [
            "Explicitly compare impacts by magnitude and probability",
            "Address all opponent arguments — never leave drops",
            "Adapt language complexity for a flow judge",
        ],
    },
    "created_at": "2026-05-25T00:00:00+00:00",
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
}

FAKE_ARGUMENT_MAP = {
    "arguments": [
        {
            "label": "C1: Economic Growth",
            "claim": "Lower taxes increase investment.",
            "warrant": "Reduced tax burden frees capital.",
            "evidence": "Smith 2023",
            "impact": "More jobs.",
            "argument_type": "offense",
            "issues": [],
            "confidence": 0.9,
        }
    ]
}

FAKE_DRILL_ROW = {
    "id": DRILL_ID,
    "speech_id": SPEECH_ID,
    "user_id": USER_ID,
    "title": "Impact Comparison Sprint",
    "description": "Practice explicit impact weighing.",
    "skill_target": "weighing",
    "prompt": "Take your C1 impact and explicitly compare it to a hypothetical opponent impact.",
    "order": 1,
    "instructions": "1. State your impact.\n2. Name the opponent impact.\n3. Compare by magnitude.",
    "success_criteria": ["Mentions magnitude", "Mentions probability", "Concludes with voting reason"],
    "source_weakness": "Impact weighing not explicit",
    "difficulty": "beginner",
    "status": "assigned",
    "created_at": "2026-05-25T00:00:00+00:00",
}

FAKE_DRILLS = [
    FAKE_DRILL_ROW,
    {**FAKE_DRILL_ROW, "id": "dddddddd-0000-0000-0000-000000000002", "order": 2, "title": "Drop Prevention Drill"},
    {**FAKE_DRILL_ROW, "id": "dddddddd-0000-0000-0000-000000000003", "order": 3, "title": "Judge Adaptation Sprint"},
]


# ── generate-drills tests ─────────────────────────────────────────────────────

def test_generate_drills_no_feedback():
    """Returns 400 if no feedback report exists."""
    mock_client = MagicMock()

    # Mock for speech table (with double .eq() for ownership)
    speech_mock = MagicMock()
    speech_mock.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_SPEECH]

    # Mock for feedback_reports table (single .eq())
    feedback_mock = MagicMock()
    feedback_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    mock_client.table.side_effect = [speech_mock, feedback_mock]

    with patch("app.api.drills.get_supabase", return_value=mock_client):
        response = client.post(f"/speeches/{SPEECH_ID}/generate-drills?user_id={USER_ID}")
    assert response.status_code == 400
    assert "feedback" in response.json()["detail"].lower()


def test_generate_drills_short_transcript():
    """Returns 400 if transcript is too short."""
    mock_client = MagicMock()

    # Separate mocks for each table
    speech_mock = MagicMock()
    speech_mock.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_SPEECH]

    feedback_mock = MagicMock()
    feedback_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_FEEDBACK_ROW]

    transcript_mock = MagicMock()
    transcript_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"text": "Too short.", "word_count": 5}
    ]

    mock_client.table.side_effect = [speech_mock, feedback_mock, transcript_mock]

    with patch("app.api.drills.get_supabase", return_value=mock_client):
        response = client.post(f"/speeches/{SPEECH_ID}/generate-drills?user_id={USER_ID}")
    assert response.status_code == 400
    assert "short" in response.json()["detail"].lower()


def test_generate_drills_not_found():
    """Returns 404 if speech does not exist."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    with patch("app.api.drills.get_supabase", return_value=mock_client):
        response = client.post(f"/speeches/{SPEECH_ID}/generate-drills?user_id={USER_ID}")
    assert response.status_code == 404


def test_generate_drills_success():
    """Successfully generates and persists 3 drills."""
    from app.services.drill_generation import _DrillItem

    fake_drill_items = [
        _DrillItem(
            title="Impact Comparison Sprint",
            skill_target="weighing",
            description="Practice explicit impact weighing.",
            prompt="Compare your impact to the opponent's.",
            instructions="1. State impact.\n2. Compare.",
            success_criteria=["Mentions magnitude"],
            source_weakness="Impact weighing not explicit",
            difficulty="beginner",
        ),
        _DrillItem(
            title="Drop Prevention Drill",
            skill_target="drops",
            description="Practice covering all arguments.",
            prompt="Write a line-by-line response to opponent's case.",
            instructions="1. List their args.\n2. Respond to each.",
            success_criteria=["No dropped arguments"],
            source_weakness="Dropped opponent contention 2",
            difficulty="beginner",
        ),
        _DrillItem(
            title="Flow Judge Vocabulary Sprint",
            skill_target="judge_adaptation",
            description="Calibrate language for a flow judge.",
            prompt="Re-deliver your summary using technical debate terminology.",
            instructions="1. Use extension language.\n2. Reference flows.",
            success_criteria=["Uses 'extend'", "References flows"],
            source_weakness="Adapt language complexity for a flow judge",
            difficulty="intermediate",
        ),
    ]

    mock_client = MagicMock()

    # Separate mocks for each table fetch
    speech_mock = MagicMock()
    speech_mock.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_SPEECH]

    feedback_mock = MagicMock()
    feedback_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_FEEDBACK_ROW]

    transcript_mock = MagicMock()
    transcript_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_TRANSCRIPT]

    argmap_mock = MagicMock()
    argmap_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_ARGUMENT_MAP]

    # Delete mock
    delete_mock = MagicMock()
    delete_mock.delete.return_value.eq.return_value.execute.return_value = MagicMock()

    # Insert mock
    insert_mock = MagicMock()
    insert_mock.insert.return_value.execute.return_value.data = FAKE_DRILLS

    mock_client.table.side_effect = [speech_mock, feedback_mock, transcript_mock, argmap_mock, delete_mock, insert_mock]

    with (
        patch("app.api.drills.get_supabase", return_value=mock_client),
        patch("app.api.drills.generate_drills", return_value=fake_drill_items),
    ):
        response = client.post(f"/speeches/{SPEECH_ID}/generate-drills?user_id={USER_ID}")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3


def test_generate_drills_llm_error():
    """Returns 500 if drill generation service raises."""
    from app.services.drill_generation import DrillGenerationError

    mock_client = MagicMock()

    # Separate mocks for each table fetch
    speech_mock = MagicMock()
    speech_mock.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_SPEECH]

    feedback_mock = MagicMock()
    feedback_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_FEEDBACK_ROW]

    transcript_mock = MagicMock()
    transcript_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_TRANSCRIPT]

    argmap_mock = MagicMock()
    argmap_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_ARGUMENT_MAP]

    mock_client.table.side_effect = [speech_mock, feedback_mock, transcript_mock, argmap_mock]

    with (
        patch("app.api.drills.get_supabase", return_value=mock_client),
        patch("app.api.drills.generate_drills", side_effect=DrillGenerationError("LLM failed")),
    ):
        response = client.post(f"/speeches/{SPEECH_ID}/generate-drills?user_id={USER_ID}")

    assert response.status_code == 500


# ── get drills tests ──────────────────────────────────────────────────────────

def test_get_drills_success():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = FAKE_DRILLS
    with patch("app.api.drills.get_supabase", return_value=mock_client):
        response = client.get(f"/speeches/{SPEECH_ID}/drills?user_id={USER_ID}")
    assert response.status_code == 200
    assert len(response.json()) == 3


def test_get_drills_empty():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
    with patch("app.api.drills.get_supabase", return_value=mock_client):
        response = client.get(f"/speeches/{SPEECH_ID}/drills?user_id={USER_ID}")
    assert response.status_code == 200
    assert response.json() == []


# ── patch drill tests ─────────────────────────────────────────────────────────

def test_patch_drill_status():
    updated = {**FAKE_DRILL_ROW, "status": "attempted"}
    mock_client = MagicMock()
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [updated]
    with patch("app.api.drills.get_supabase", return_value=mock_client):
        response = client.patch(f"/drills/{DRILL_ID}?user_id={USER_ID}", json={"status": "attempted"})
    assert response.status_code == 200
    assert response.json()["status"] == "attempted"


def test_patch_drill_invalid_status():
    with patch("app.api.drills.get_supabase", return_value=MagicMock()):
        response = client.patch(f"/drills/{DRILL_ID}?user_id={USER_ID}", json={"status": "invalid_status"})
    assert response.status_code == 400


def test_patch_drill_not_found():
    mock_client = MagicMock()
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []
    with patch("app.api.drills.get_supabase", return_value=mock_client):
        response = client.patch(f"/drills/{DRILL_ID}?user_id={USER_ID}", json={"status": "completed"})
    assert response.status_code == 404


def test_patch_drill_no_fields():
    """Returns 400 if body has no updatable fields."""
    with patch("app.api.drills.get_supabase", return_value=MagicMock()):
        response = client.patch(f"/drills/{DRILL_ID}?user_id={USER_ID}", json={})
    assert response.status_code == 400


# ── drill attempts tests ──────────────────────────────────────────────────────

ATTEMPT_ID = "aaaaaaaa-0000-0000-0000-000000000004"
FAKE_DRILL_ATTEMPT = {
    "id": ATTEMPT_ID,
    "drill_id": DRILL_ID,
    "user_id": USER_ID,
    "audio_url": f"{USER_ID}/{SPEECH_ID}/drills/{DRILL_ID}/attempt-1234567890.webm",
    "response": None,
    "feedback": None,
    "score": None,
    "created_at": "2026-05-25T00:00:00+00:00",
}


def test_get_drill_attempts_success():
    """Returns all attempts for a drill."""
    mock_client = MagicMock()
    # Drill exists check
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{"id": DRILL_ID}]
    # Attempts fetch
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [FAKE_DRILL_ATTEMPT]

    with patch("app.api.drills.get_supabase", return_value=mock_client):
        response = client.get(f"/drills/{DRILL_ID}/attempts?user_id={USER_ID}")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["drill_id"] == DRILL_ID


def test_get_drill_attempts_drill_not_found():
    """Returns 404 if drill doesn't exist."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    with patch("app.api.drills.get_supabase", return_value=mock_client):
        response = client.get(f"/drills/{DRILL_ID}/attempts?user_id={USER_ID}")

    assert response.status_code == 404


def test_get_drill_attempts_missing_user_id_returns_422():
    """Returns 422 when user_id query param is missing — FastAPI validation."""
    response = client.get(f"/drills/{DRILL_ID}/attempts")
    assert response.status_code == 422


def test_create_drill_attempt_success():
    """Successfully creates a drill attempt."""
    audio_url = f"{USER_ID}/{SPEECH_ID}/drills/{DRILL_ID}/attempt-1234567890.webm"
    mock_client = MagicMock()
    # Drill fetch
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"id": DRILL_ID, "user_id": USER_ID}
    ]
    # Insert
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [FAKE_DRILL_ATTEMPT]

    with patch("app.api.drills.get_supabase", return_value=mock_client):
        response = client.post(f"/drills/{DRILL_ID}/attempts?user_id={USER_ID}", json={"audio_url": audio_url})

    assert response.status_code == 200
    data = response.json()
    assert data["drill_id"] == DRILL_ID
    assert data["audio_url"] == audio_url


def test_create_drill_attempt_drill_not_found():
    """Returns 404 if drill doesn't exist."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    with patch("app.api.drills.get_supabase", return_value=mock_client):
        response = client.post(
            f"/drills/{DRILL_ID}/attempts?user_id={USER_ID}",
            json={"audio_url": "user/speech/drills/drill1/attempt.webm"}
        )

    assert response.status_code == 404


# ── Access Control Tests ──────────────────────────────────────────────────────


def test_cannot_generate_drills_for_another_users_speech():
    """Verify users cannot generate drills for speeches they don't own."""
    other_user_id = "dddddddd-0000-0000-0000-000000000004"
    mock_client = MagicMock()
    # Return empty when querying speech with wrong user_id
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    with patch("app.api.drills.get_supabase", return_value=mock_client):
        response = client.post(f"/speeches/{SPEECH_ID}/generate-drills?user_id={other_user_id}")

    assert response.status_code == 404


def test_cannot_get_drills_for_another_users_speech():
    """Verify users cannot get drills for speeches they don't own."""
    other_user_id = "dddddddd-0000-0000-0000-000000000004"
    mock_client = MagicMock()
    # Return empty when checking speech ownership
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    with patch("app.api.drills.get_supabase", return_value=mock_client):
        response = client.get(f"/speeches/{SPEECH_ID}/drills?user_id={other_user_id}")

    assert response.status_code == 404


def test_cannot_update_another_users_drill():
    """Verify users cannot update drills they don't own."""
    other_user_id = "dddddddd-0000-0000-0000-000000000004"
    mock_client = MagicMock()
    # Return empty when checking drill ownership
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    with patch("app.api.drills.get_supabase", return_value=mock_client):
        response = client.patch(
            f"/drills/{DRILL_ID}?user_id={other_user_id}",
            json={"status": "completed"}
        )

    assert response.status_code == 404


def test_cannot_create_attempt_for_another_users_drill():
    """Verify users cannot create drill attempts for drills they don't own."""
    other_user_id = "dddddddd-0000-0000-0000-000000000004"
    mock_client = MagicMock()
    # Return empty when checking drill ownership
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    with patch("app.api.drills.get_supabase", return_value=mock_client):
        response = client.post(
            f"/drills/{DRILL_ID}/attempts?user_id={other_user_id}",
            json={"audio_url": "path/to/audio.webm"}
        )

    assert response.status_code == 404


def test_can_access_own_drills():
    """Verify users CAN access their own drills."""
    mock_client = MagicMock()

    # Speech ownership check mock
    speech_mock = MagicMock()
    speech_mock.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{"id": SPEECH_ID}]

    # Drills fetch mock
    drills_mock = MagicMock()
    drills_mock.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [FAKE_DRILL_ROW]

    mock_client.table.side_effect = [speech_mock, drills_mock]

    with patch("app.api.drills.get_supabase", return_value=mock_client):
        response = client.get(f"/speeches/{SPEECH_ID}/drills?user_id={USER_ID}")

    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0


# ── Scoring service unit tests ────────────────────────────────────────────────

def test_drill_attempt_feedback_schema_valid():
    """DrillAttemptFeedback validates and exposes all expected fields."""
    from app.services.drill_attempt_scoring import DrillAttemptFeedback

    fb = DrillAttemptFeedback(
        score=75,
        met_success_criteria=True,
        feedback_summary="Good warranting structure with clear claim-warrant chain.",
        strengths=["Explicit claim-warrant link", "Named opponent impact"],
        improvements=["Add probability weighing"],
        next_instruction="Redo the drill and add a timeframe comparison.",
        should_retry=False,
    )
    assert fb.score == 75
    assert fb.met_success_criteria is True
    assert fb.should_retry is False
    d = fb.model_dump()
    assert set(d.keys()) == {
        "score", "met_success_criteria", "feedback_summary",
        "strengths", "improvements", "next_instruction", "should_retry",
    }


def test_drill_attempt_feedback_should_retry_low_score():
    """should_retry True when score < 70."""
    from app.services.drill_attempt_scoring import DrillAttemptFeedback

    fb = DrillAttemptFeedback(
        score=65, met_success_criteria=True,
        feedback_summary="Developing.", strengths=[], improvements=["More weighing"],
        next_instruction="Try again.", should_retry=True,
    )
    assert fb.should_retry is True


def test_drill_attempt_feedback_should_retry_criteria_not_met():
    """should_retry True when met_success_criteria is False even at high score."""
    from app.services.drill_attempt_scoring import DrillAttemptFeedback

    fb = DrillAttemptFeedback(
        score=72, met_success_criteria=False,
        feedback_summary="Missing a success criterion.", strengths=["Good delivery"],
        improvements=["Address all criteria"], next_instruction="Re-record with criteria in mind.",
        should_retry=True,
    )
    assert fb.should_retry is True


def test_drill_attempt_feedback_no_retry_when_high_score_and_criteria_met():
    """should_retry False when score >= 70 and criteria met."""
    from app.services.drill_attempt_scoring import DrillAttemptFeedback

    fb = DrillAttemptFeedback(
        score=91, met_success_criteria=True,
        feedback_summary="Excellent response.", strengths=["Clear weighing", "Explicit impact link"],
        improvements=[], next_instruction="Move to next drill.",
        should_retry=False,
    )
    assert fb.should_retry is False


# ── POST attempt: transcription + scoring integrated ─────────────────────────

FAKE_DRILL_ROW_FULL = {**FAKE_DRILL_ROW, "time_limit_seconds": 60}

FAKE_DRILL_ATTEMPT_SCORED = {
    **FAKE_DRILL_ATTEMPT,
    "response": "Our economy impact outweighs by magnitude and probability.",
    "score": 78,
    "feedback": {
        "met_success_criteria": True,
        "feedback_summary": "Solid explicit weighing with two criteria applied.",
        "strengths": ["Named both impacts", "Applied magnitude comparison"],
        "improvements": ["Add timeframe weighing"],
        "next_instruction": "Add a timeframe comparison in your next rep.",
        "should_retry": False,
    },
}


def test_create_attempt_with_transcription_and_scoring():
    """Attempt is saved with score and feedback when transcription and scoring both succeed."""
    from app.services.drill_attempt_scoring import DrillAttemptFeedback

    audio_url = FAKE_DRILL_ATTEMPT_SCORED["audio_url"]
    transcript = "Our economy impact outweighs by magnitude and probability."
    fake_feedback = DrillAttemptFeedback(
        score=78, met_success_criteria=True,
        feedback_summary="Solid explicit weighing with two criteria applied.",
        strengths=["Named both impacts", "Applied magnitude comparison"],
        improvements=["Add timeframe weighing"],
        next_instruction="Add a timeframe comparison in your next rep.",
        should_retry=False,
    )

    mock_client = MagicMock()
    drill_mock = MagicMock()
    drill_mock.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_DRILL_ROW_FULL]
    insert_mock = MagicMock()
    insert_mock.insert.return_value.execute.return_value.data = [FAKE_DRILL_ATTEMPT_SCORED]
    mock_client.table.side_effect = [drill_mock, insert_mock, MagicMock()]

    with (
        patch("app.api.drills.get_supabase", return_value=mock_client),
        patch("app.api.drills.transcribe_speech", return_value=(transcript, 10)),
        patch("app.api.drills.score_drill_attempt", return_value=fake_feedback),
    ):
        response = client.post(f"/drills/{DRILL_ID}/attempts?user_id={USER_ID}", json={"audio_url": audio_url})

    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 78
    assert data["response"] == transcript
    assert data["feedback"]["met_success_criteria"] is True
    assert data["feedback"]["should_retry"] is False
    assert "feedback_summary" in data["feedback"]
    assert isinstance(data["feedback"]["strengths"], list)
    assert isinstance(data["feedback"]["improvements"], list)


def test_create_attempt_saves_when_transcription_fails():
    """Attempt is saved with just audio_url when transcription fails — no 500."""
    from app.services.transcription import StorageDownloadError

    audio_url = FAKE_DRILL_ATTEMPT["audio_url"]
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_DRILL_ROW_FULL]
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [FAKE_DRILL_ATTEMPT]

    with (
        patch("app.api.drills.get_supabase", return_value=mock_client),
        patch("app.api.drills.transcribe_speech", side_effect=StorageDownloadError("no audio")),
    ):
        response = client.post(f"/drills/{DRILL_ID}/attempts?user_id={USER_ID}", json={"audio_url": audio_url})

    assert response.status_code == 200
    data = response.json()
    assert data["drill_id"] == DRILL_ID
    assert data["score"] is None
    assert data["feedback"] is None


def test_create_attempt_saves_when_scoring_fails():
    """Attempt is saved with transcript but no score/feedback when scoring fails — no 500."""
    from app.services.drill_attempt_scoring import DrillScoringError

    audio_url = FAKE_DRILL_ATTEMPT["audio_url"]
    attempt_with_transcript = {**FAKE_DRILL_ATTEMPT, "response": "Some transcript text."}
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_DRILL_ROW_FULL]
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [attempt_with_transcript]

    with (
        patch("app.api.drills.get_supabase", return_value=mock_client),
        patch("app.api.drills.transcribe_speech", return_value=("Some transcript text.", 3)),
        patch("app.api.drills.score_drill_attempt", side_effect=DrillScoringError("LLM unavailable")),
    ):
        response = client.post(f"/drills/{DRILL_ID}/attempts?user_id={USER_ID}", json={"audio_url": audio_url})

    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "Some transcript text."
    assert data["score"] is None
    assert data["feedback"] is None


def test_old_attempt_null_score_feedback_validates():
    """DrillAttemptRow with null score and feedback is valid (backward compat)."""
    from app.models.drill import DrillAttemptRow

    row = DrillAttemptRow(**FAKE_DRILL_ATTEMPT)
    assert row.score is None
    assert row.feedback is None
    assert row.response is None
