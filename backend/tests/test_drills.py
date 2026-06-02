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
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = [
        MagicMock(data=[FAKE_SPEECH]),    # speech
        MagicMock(data=[]),               # no feedback
    ]
    with patch("app.api.drills.get_supabase", return_value=mock_client):
        response = client.post(f"/speeches/{SPEECH_ID}/generate-drills")
    assert response.status_code == 400
    assert "feedback" in response.json()["detail"].lower()


def test_generate_drills_short_transcript():
    """Returns 400 if transcript is too short."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = [
        MagicMock(data=[FAKE_SPEECH]),
        MagicMock(data=[FAKE_FEEDBACK_ROW]),
        MagicMock(data=[{"text": "Too short.", "word_count": 5}]),  # short transcript
    ]
    with patch("app.api.drills.get_supabase", return_value=mock_client):
        response = client.post(f"/speeches/{SPEECH_ID}/generate-drills")
    assert response.status_code == 400
    assert "short" in response.json()["detail"].lower()


def test_generate_drills_not_found():
    """Returns 404 if speech does not exist."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    with patch("app.api.drills.get_supabase", return_value=mock_client):
        response = client.post(f"/speeches/{SPEECH_ID}/generate-drills")
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
    # speech, feedback, transcript, argmap fetches — all use .limit(1).execute()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = [
        MagicMock(data=[FAKE_SPEECH]),
        MagicMock(data=[FAKE_FEEDBACK_ROW]),
        MagicMock(data=[FAKE_TRANSCRIPT]),
        MagicMock(data=[FAKE_ARGUMENT_MAP]),
    ]
    mock_client.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.return_value.data = FAKE_DRILLS

    with (
        patch("app.api.drills.get_supabase", return_value=mock_client),
        patch("app.api.drills.generate_drills", return_value=fake_drill_items),
    ):
        response = client.post(f"/speeches/{SPEECH_ID}/generate-drills")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3


def test_generate_drills_llm_error():
    """Returns 500 if drill generation service raises."""
    from app.services.drill_generation import DrillGenerationError

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = [
        MagicMock(data=[FAKE_SPEECH]),
        MagicMock(data=[FAKE_FEEDBACK_ROW]),
        MagicMock(data=[FAKE_TRANSCRIPT]),
    ]
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [FAKE_ARGUMENT_MAP]

    with (
        patch("app.api.drills.get_supabase", return_value=mock_client),
        patch("app.api.drills.generate_drills", side_effect=DrillGenerationError("LLM failed")),
    ):
        response = client.post(f"/speeches/{SPEECH_ID}/generate-drills")

    assert response.status_code == 500


# ── get drills tests ──────────────────────────────────────────────────────────

def test_get_drills_success():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = FAKE_DRILLS
    with patch("app.api.drills.get_supabase", return_value=mock_client):
        response = client.get(f"/speeches/{SPEECH_ID}/drills")
    assert response.status_code == 200
    assert len(response.json()) == 3


def test_get_drills_empty():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
    with patch("app.api.drills.get_supabase", return_value=mock_client):
        response = client.get(f"/speeches/{SPEECH_ID}/drills")
    assert response.status_code == 200
    assert response.json() == []


# ── patch drill tests ─────────────────────────────────────────────────────────

def test_patch_drill_status():
    updated = {**FAKE_DRILL_ROW, "status": "attempted"}
    mock_client = MagicMock()
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [updated]
    with patch("app.api.drills.get_supabase", return_value=mock_client):
        response = client.patch(f"/drills/{DRILL_ID}", json={"status": "attempted"})
    assert response.status_code == 200
    assert response.json()["status"] == "attempted"


def test_patch_drill_invalid_status():
    with patch("app.api.drills.get_supabase", return_value=MagicMock()):
        response = client.patch(f"/drills/{DRILL_ID}", json={"status": "invalid_status"})
    assert response.status_code == 400


def test_patch_drill_not_found():
    mock_client = MagicMock()
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []
    with patch("app.api.drills.get_supabase", return_value=mock_client):
        response = client.patch(f"/drills/{DRILL_ID}", json={"status": "completed"})
    assert response.status_code == 404


def test_patch_drill_no_fields():
    """Returns 400 if body has no updatable fields."""
    with patch("app.api.drills.get_supabase", return_value=MagicMock()):
        response = client.patch(f"/drills/{DRILL_ID}", json={})
    assert response.status_code == 400
