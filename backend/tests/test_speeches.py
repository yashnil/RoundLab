from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

FAKE_ROW = {
    "id": "aaaaaaaa-0000-0000-0000-000000000001",
    "user_id": "bbbbbbbb-0000-0000-0000-000000000002",
    "title": "1AC Round 1",
    "speech_type": "constructive",
    "side": "pro",
    "judge_type": "flow",
    "topic": "Resolved: Test resolution.",
    "audio_url": None,
    "duration_seconds": None,
    "status": "pending",
    "created_at": "2026-05-25T00:00:00+00:00",
    "updated_at": "2026-05-25T00:00:00+00:00",
}

PAYLOAD = {
    "user_id": FAKE_ROW["user_id"],
    "title": FAKE_ROW["title"],
    "speech_type": FAKE_ROW["speech_type"],
    "side": FAKE_ROW["side"],
    "judge_type": FAKE_ROW["judge_type"],
    "topic": FAKE_ROW["topic"],
}


def test_create_speech():
    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [
        FAKE_ROW
    ]
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.post("/speeches", json=PAYLOAD)
    assert response.status_code == 201
    body = response.json()
    assert body["id"] == FAKE_ROW["id"]
    assert body["status"] == "pending"
    assert body["title"] == FAKE_ROW["title"]


def test_create_speech_db_error():
    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.side_effect = Exception(
        "db error"
    )
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.post("/speeches", json=PAYLOAD)
    assert response.status_code == 500
    assert "secret" not in response.text.lower()
    assert "key" not in response.text.lower()


def test_list_speeches():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
        FAKE_ROW
    ]
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.get(f"/speeches?user_id={FAKE_ROW['user_id']}")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert body[0]["id"] == FAKE_ROW["id"]


def test_list_speeches_missing_user_id():
    response = client.get("/speeches")
    assert response.status_code == 422


def test_get_speech():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        FAKE_ROW
    ]
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.get(f"/speeches/{FAKE_ROW['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == FAKE_ROW["id"]


def test_get_speech_not_found():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.get(f"/speeches/{FAKE_ROW['id']}")
    assert response.status_code == 404


def test_patch_speech_audio():
    patched_row = {**FAKE_ROW, "audio_url": "user-id/speech-id/audio.mp3"}
    mock_client = MagicMock()
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        patched_row
    ]
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.patch(
            f"/speeches/{FAKE_ROW['id']}",
            json={"audio_url": "user-id/speech-id/audio.mp3"},
        )
    assert response.status_code == 200
    assert response.json()["audio_url"] == "user-id/speech-id/audio.mp3"


def test_patch_speech_not_found():
    mock_client = MagicMock()
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.patch(
            f"/speeches/{FAKE_ROW['id']}",
            json={"audio_url": "user-id/speech-id/audio.mp3"},
        )
    assert response.status_code == 404


# ── DELETE /speeches/{id} ─────────────────────────────────────────────────────

def test_delete_speech():
    mock_client = MagicMock()
    # SELECT to verify exists (no audio_url)
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        FAKE_ROW
    ]
    # DELETE calls return empty data (we don't check their return values)
    mock_client.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.delete(f"/speeches/{FAKE_ROW['id']}")
    assert response.status_code == 200
    assert response.json()["deleted"] is True


def test_delete_speech_not_found():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.delete(f"/speeches/{FAKE_ROW['id']}")
    assert response.status_code == 404


def test_delete_speech_with_audio_removes_storage():
    row_with_audio = {**FAKE_ROW, "audio_url": "user-id/speech-id/audio.mp3"}
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        row_with_audio
    ]
    mock_client.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.delete(f"/speeches/{FAKE_ROW['id']}")
    assert response.status_code == 200
    mock_client.storage.from_.assert_called_with("audio")
    mock_client.storage.from_.return_value.remove.assert_called_once_with(
        ["user-id/speech-id/audio.mp3"]
    )


def test_delete_speech_db_error():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = Exception(
        "db error"
    )
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.delete(f"/speeches/{FAKE_ROW['id']}")
    assert response.status_code == 500


# ── POST /speeches/{id}/reset-audio ──────────────────────────────────────────

def test_reset_audio_success():
    row_with_audio = {**FAKE_ROW, "audio_url": "user-id/speech-id/audio.mp3"}
    reset_row = {**FAKE_ROW, "audio_url": None, "status": "pending"}
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        row_with_audio
    ]
    mock_client.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        reset_row
    ]
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.post(f"/speeches/{FAKE_ROW['id']}/reset-audio")
    assert response.status_code == 200
    body = response.json()
    assert body["audio_url"] is None
    assert body["status"] == "pending"
    mock_client.storage.from_.assert_called_with("audio")
    mock_client.storage.from_.return_value.remove.assert_called_once_with(
        ["user-id/speech-id/audio.mp3"]
    )


def test_reset_audio_no_audio():
    reset_row = {**FAKE_ROW, "audio_url": None, "status": "pending"}
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        FAKE_ROW  # no audio_url
    ]
    mock_client.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        reset_row
    ]
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.post(f"/speeches/{FAKE_ROW['id']}/reset-audio")
    assert response.status_code == 200
    assert response.json()["audio_url"] is None
    # Storage remove should NOT be called when no audio_url
    mock_client.storage.from_.return_value.remove.assert_not_called()


def test_reset_audio_not_found():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.post(f"/speeches/{FAKE_ROW['id']}/reset-audio")
    assert response.status_code == 404
