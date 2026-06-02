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
    "warrant": "Reduced tax burden frees capital for private sector deployment.",
    "evidence": "Smith et al. 2023: GDP growth 2%",
    "impact": "More jobs and long-term prosperity.",
    "argument_type": "offense",
    "issues": ["undeveloped impact"],
    "confidence": 0.9,
}

FAKE_ARGUMENT_MAP_ROW = {
    "id": "dddddddd-0000-0000-0000-000000000004",
    "speech_id": SPEECH_ID,
    "arguments": [FAKE_ARGUMENT_ITEM],
    "created_at": "2026-05-25T00:00:00+00:00",
}


def _make_mock_client(speech_data, transcript_data):
    """Build a mock supabase client that returns different data for speech vs transcript selects."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = [
        MagicMock(data=speech_data),
        MagicMock(data=transcript_data),
    ]
    return mock_client


def test_extract_no_transcript():
    mock_client = _make_mock_client(
        speech_data=[FAKE_SPEECH],
        transcript_data=[],
    )
    with patch("app.api.argument_maps.get_supabase", return_value=mock_client):
        response = client.post(f"/speeches/{SPEECH_ID}/extract-arguments")
    assert response.status_code == 400
    assert "transcript" in response.json()["detail"].lower()


def test_extract_success():
    from app.models.argument_map import ArgumentItem

    mock_client = _make_mock_client(
        speech_data=[FAKE_SPEECH],
        transcript_data=[FAKE_TRANSCRIPT],
    )
    mock_client.table.return_value.upsert.return_value.execute.return_value.data = [
        FAKE_ARGUMENT_MAP_ROW
    ]

    fake_items = [ArgumentItem(**FAKE_ARGUMENT_ITEM)]

    with patch("app.api.argument_maps.get_supabase", return_value=mock_client), patch(
        "app.api.argument_maps.extract_arguments", return_value=fake_items
    ):
        response = client.post(f"/speeches/{SPEECH_ID}/extract-arguments")

    assert response.status_code == 200
    body = response.json()
    assert body["speech_id"] == SPEECH_ID
    assert len(body["arguments"]) == 1
    assert body["arguments"][0]["label"] == "C1: Economic Growth"
    assert body["arguments"][0]["argument_type"] == "offense"


def test_get_argument_map_success():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        FAKE_ARGUMENT_MAP_ROW
    ]
    with patch("app.api.argument_maps.get_supabase", return_value=mock_client):
        response = client.get(f"/speeches/{SPEECH_ID}/argument-map")
    assert response.status_code == 200
    body = response.json()
    assert body["speech_id"] == SPEECH_ID
    assert body["arguments"][0]["claim"] == "Lower taxes increase investment."


def test_extract_short_transcript():
    mock_client = _make_mock_client(
        speech_data=[FAKE_SPEECH],
        transcript_data=[FAKE_TRANSCRIPT_SHORT],
    )
    with patch("app.api.argument_maps.get_supabase", return_value=mock_client):
        response = client.post(f"/speeches/{SPEECH_ID}/extract-arguments")
    assert response.status_code == 400
    assert "too short" in response.json()["detail"].lower()


def test_get_argument_map_not_found():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    with patch("app.api.argument_maps.get_supabase", return_value=mock_client):
        response = client.get(f"/speeches/{SPEECH_ID}/argument-map")
    assert response.status_code == 404
