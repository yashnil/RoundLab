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
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        FAKE_ROW
    ]
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.get(f"/speeches/{FAKE_ROW['id']}?user_id={FAKE_ROW['user_id']}")
    assert response.status_code == 200
    assert response.json()["id"] == FAKE_ROW["id"]


def test_get_speech_not_found():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.get(f"/speeches/{FAKE_ROW['id']}?user_id={FAKE_ROW['user_id']}")
    assert response.status_code == 404


def test_patch_speech_audio():
    patched_row = {**FAKE_ROW, "audio_url": "user-id/speech-id/audio.mp3"}
    mock_client = MagicMock()
    mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        patched_row
    ]
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.patch(
            f"/speeches/{FAKE_ROW['id']}?user_id={FAKE_ROW['user_id']}",
            json={"audio_url": "user-id/speech-id/audio.mp3"},
        )
    assert response.status_code == 200
    assert response.json()["audio_url"] == "user-id/speech-id/audio.mp3"


def test_patch_speech_not_found():
    mock_client = MagicMock()
    mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.patch(
            f"/speeches/{FAKE_ROW['id']}?user_id={FAKE_ROW['user_id']}",
            json={"audio_url": "user-id/speech-id/audio.mp3"},
        )
    assert response.status_code == 404


# ── DELETE /speeches/{id} ─────────────────────────────────────────────────────

def test_delete_speech():
    mock_client = MagicMock()
    # SELECT to verify exists (no audio_url)
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        FAKE_ROW
    ]
    # DELETE calls return empty data (we don't check their return values)
    mock_client.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.delete(f"/speeches/{FAKE_ROW['id']}?user_id={FAKE_ROW['user_id']}")
    assert response.status_code == 200
    assert response.json()["deleted"] is True


def test_delete_speech_not_found():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.delete(f"/speeches/{FAKE_ROW['id']}?user_id={FAKE_ROW['user_id']}")
    assert response.status_code == 404


def test_delete_speech_with_audio_removes_storage():
    row_with_audio = {**FAKE_ROW, "audio_url": "user-id/speech-id/audio.mp3"}
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        row_with_audio
    ]
    mock_client.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.delete(f"/speeches/{FAKE_ROW['id']}?user_id={FAKE_ROW['user_id']}")
    assert response.status_code == 200
    mock_client.storage.from_.assert_called_with("audio")
    mock_client.storage.from_.return_value.remove.assert_called_once_with(
        ["user-id/speech-id/audio.mp3"]
    )


def test_delete_speech_db_error():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.side_effect = Exception(
        "db error"
    )
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.delete(f"/speeches/{FAKE_ROW['id']}?user_id={FAKE_ROW['user_id']}")
    assert response.status_code == 500


# ── POST /speeches/{id}/reset-audio ──────────────────────────────────────────

def test_reset_audio_success():
    row_with_audio = {**FAKE_ROW, "audio_url": "user-id/speech-id/audio.mp3"}
    reset_row = {**FAKE_ROW, "audio_url": None, "status": "pending"}
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        row_with_audio
    ]
    mock_client.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        reset_row
    ]
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.post(f"/speeches/{FAKE_ROW['id']}/reset-audio?user_id={FAKE_ROW['user_id']}")
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
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        FAKE_ROW  # no audio_url
    ]
    mock_client.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        reset_row
    ]
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.post(f"/speeches/{FAKE_ROW['id']}/reset-audio?user_id={FAKE_ROW['user_id']}")
    assert response.status_code == 200
    assert response.json()["audio_url"] is None
    # Storage remove should NOT be called when no audio_url
    mock_client.storage.from_.return_value.remove.assert_not_called()


def test_reset_audio_not_found():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.post(f"/speeches/{FAKE_ROW['id']}/reset-audio?user_id={FAKE_ROW['user_id']}")
    assert response.status_code == 404


# ── Access Control Tests ──────────────────────────────────────────────────────


def test_cannot_get_another_users_speech():
    """Verify users cannot access speeches they don't own."""
    other_user_id = "cccccccc-0000-0000-0000-000000000003"
    mock_client = MagicMock()
    # Return empty when querying with wrong user_id
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.get(f"/speeches/{FAKE_ROW['id']}?user_id={other_user_id}")
    assert response.status_code == 404


def test_cannot_update_another_users_speech():
    """Verify users cannot update speeches they don't own."""
    other_user_id = "cccccccc-0000-0000-0000-000000000003"
    mock_client = MagicMock()
    # Return empty when updating with wrong user_id
    mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.patch(
            f"/speeches/{FAKE_ROW['id']}?user_id={other_user_id}",
            json={"audio_url": "path/to/audio.webm"},
        )
    assert response.status_code == 404


def test_cannot_delete_another_users_speech():
    """Verify users cannot delete speeches they don't own."""
    other_user_id = "cccccccc-0000-0000-0000-000000000003"
    mock_client = MagicMock()
    # Return empty when fetching with wrong user_id
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.delete(f"/speeches/{FAKE_ROW['id']}?user_id={other_user_id}")
    assert response.status_code == 404


def test_can_access_own_speech():
    """Verify users CAN access their own speeches."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        FAKE_ROW
    ]
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.get(f"/speeches/{FAKE_ROW['id']}?user_id={FAKE_ROW['user_id']}")
    assert response.status_code == 200
    assert response.json()["id"] == FAKE_ROW["id"]


# ── Re-record relationship tests ──────────────────────────────────────────────

PARENT_SPEECH_ID = "pppppppp-0000-0000-0000-000000000001"
SOURCE_DRILL_ID  = "dddddddd-0000-0000-0000-000000000002"

RERECORD_ROW = {
    **FAKE_ROW,
    "id": "rrrrrrrr-0000-0000-0000-000000000099",
    "title": "Re-record: 1AC Round 1",
    "parent_speech_id": PARENT_SPEECH_ID,
    "source_drill_id": SOURCE_DRILL_ID,
}

FAKE_ORIG_FEEDBACK = {
    "overall_score": 62,
    "scores": {"clash": 10, "weighing": 9, "extensions": 14, "drops": 16, "judge_adaptation": 13},
    "weaknesses": ["Impact weighing not explicit"],
}
FAKE_NEW_FEEDBACK = {
    "overall_score": 70,
    "scores": {"clash": 10, "weighing": 13, "extensions": 14, "drops": 16, "judge_adaptation": 17},
    "weaknesses": ["Evidence comparison still thin"],
}


def test_create_speech_with_rerecord_fields():
    """Creating a speech with parent_speech_id/source_drill_id persists them."""
    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [RERECORD_ROW]
    payload = {
        **PAYLOAD,
        "parent_speech_id": PARENT_SPEECH_ID,
        "source_drill_id": SOURCE_DRILL_ID,
    }
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.post("/speeches", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["parent_speech_id"] == PARENT_SPEECH_ID
    assert body["source_drill_id"] == SOURCE_DRILL_ID


def test_create_speech_without_rerecord_fields():
    """Creating a speech without re-record fields still works (nulls)."""
    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [FAKE_ROW]
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.post("/speeches", json=PAYLOAD)
    assert response.status_code == 201
    body = response.json()
    assert body.get("parent_speech_id") is None
    assert body.get("source_drill_id") is None


def test_comparison_no_parent():
    """Returns has_parent=False when speech has no parent_speech_id."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"parent_speech_id": None, "source_drill_id": None}
    ]
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.get(f"/speeches/{FAKE_ROW['id']}/comparison?user_id={FAKE_ROW['user_id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["has_parent"] is False


def test_comparison_not_found():
    """Returns 404 when speech does not exist."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.get(f"/speeches/{FAKE_ROW['id']}/comparison?user_id={FAKE_ROW['user_id']}")
    assert response.status_code == 404


def test_comparison_with_scores():
    """Returns correct deltas when both feedback reports exist."""
    mock_client = MagicMock()

    # Speech fetch
    speech_mock = MagicMock()
    speech_mock.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"parent_speech_id": PARENT_SPEECH_ID, "source_drill_id": SOURCE_DRILL_ID}
    ]

    # New feedback
    new_fb_mock = MagicMock()
    new_fb_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_NEW_FEEDBACK]

    # Original feedback
    orig_fb_mock = MagicMock()
    orig_fb_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [FAKE_ORIG_FEEDBACK]

    # Source drill
    drill_mock = MagicMock()
    drill_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"skill_target": "weighing"}
    ]

    mock_client.table.side_effect = [speech_mock, new_fb_mock, orig_fb_mock, drill_mock]

    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.get(f"/speeches/{RERECORD_ROW['id']}/comparison?user_id={FAKE_ROW['user_id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["has_parent"] is True
    assert body["overall_delta"] == 8    # 70 - 62
    assert body["skill_delta"] == 4      # 13 - 9 (weighing improved)
    assert body["source_drill_skill"] == "weighing"
    assert "improvement" in body["summary"].lower() or "improved" in body["summary"].lower()


def test_comparison_missing_feedback_graceful():
    """Returns has_parent=True with null scores when feedback reports are missing."""
    mock_client = MagicMock()

    speech_mock = MagicMock()
    speech_mock.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"parent_speech_id": PARENT_SPEECH_ID, "source_drill_id": None}
    ]

    # Both feedback reports missing
    fb_mock = MagicMock()
    fb_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    mock_client.table.side_effect = [speech_mock, fb_mock, fb_mock, MagicMock()]

    with patch("app.api.speeches.get_supabase", return_value=mock_client):
        response = client.get(f"/speeches/{FAKE_ROW['id']}/comparison?user_id={FAKE_ROW['user_id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["has_parent"] is True
    assert body["overall_delta"] is None
    assert body["skill_delta"] is None


def test_comparison_summary_helpers():
    """Unit-test the comparison summary/next_action builder helpers."""
    from app.api.speeches import _build_comparison_summary, _derive_next_action

    assert "+8" in _build_comparison_summary(8, "weighing", 4) or "improved" in _build_comparison_summary(8, "weighing", 4).lower()
    assert "steady" in _build_comparison_summary(0, None, None).lower()
    assert "dipped" in _build_comparison_summary(-3, None, None).lower()
    assert "great" in _derive_next_action(8).lower()
    assert "keep" in _derive_next_action(2).lower()
    assert "another" in _derive_next_action(-1).lower() or "record" in _derive_next_action(-1).lower()
