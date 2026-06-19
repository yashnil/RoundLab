"""Assignment API tests — focused on server-side permission enforcement.

The backend uses the service-role client (RLS-bypassing), so these verify the
in-code role gates in app/api/assignments.py.
"""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

TEAM_ID = "team-1"
COACH_ID = "coach-1"
STUDENT_ID = "student-1"
OTHER_ID = "student-2"
RECIPIENT_ID = "rec-1"


def _role_mock(role: str | None):
    """A team_members table mock resolving _member_role to `role`."""
    m = MagicMock()
    data = [{"role": role}] if role is not None else []
    m.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = data
    return m


# ── create_assignment ──────────────────────────────────────────────────────────


def test_create_assignment_rejects_student():
    sb = MagicMock()
    sb.table.return_value = _role_mock("student")
    with patch("app.api.assignments.get_supabase", return_value=sb):
        resp = client.post("/assignments", json={
            "team_id": TEAM_ID, "created_by": STUDENT_ID, "title": "Summary rep",
            "recipient_user_ids": [STUDENT_ID],
        })
    assert resp.status_code == 403
    assert "coach" in resp.json()["detail"].lower()


def test_create_assignment_rejects_non_member():
    sb = MagicMock()
    sb.table.return_value = _role_mock(None)
    with patch("app.api.assignments.get_supabase", return_value=sb):
        resp = client.post("/assignments", json={
            "team_id": TEAM_ID, "created_by": "stranger", "title": "x",
            "recipient_user_ids": [STUDENT_ID],
        })
    assert resp.status_code == 403


def test_create_assignment_coach_success():
    sb = MagicMock()
    role = _role_mock("coach")

    a_insert = MagicMock()
    a_insert.insert.return_value.execute.return_value.data = [{
        "id": "a-1", "team_id": TEAM_ID, "created_by": COACH_ID, "title": "Summary rep",
        "kind": "speech", "speech_type": "summary", "side": None, "judge_type": "flow",
        "topic": None, "goal": "Collapse and weigh", "success_criteria": ["Weigh on magnitude"],
        "due_date": None, "created_at": "2026-06-18T00:00:00+00:00",
    }]
    r_insert = MagicMock()
    r_insert.insert.return_value.execute.return_value.data = [
        {"id": RECIPIENT_ID, "user_id": STUDENT_ID, "status": "assigned"},
    ]
    sb.table.side_effect = [role, a_insert, r_insert]

    with patch("app.api.assignments.get_supabase", return_value=sb):
        resp = client.post("/assignments", json={
            "team_id": TEAM_ID, "created_by": COACH_ID, "title": "Summary rep",
            "kind": "speech", "speech_type": "summary", "judge_type": "flow",
            "goal": "Collapse and weigh", "success_criteria": ["Weigh on magnitude"],
            "recipient_user_ids": [STUDENT_ID],
        })
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Summary rep"
    assert data["recipients"][0]["user_id"] == STUDENT_ID


def test_create_assignment_requires_recipients():
    sb = MagicMock()
    sb.table.return_value = _role_mock("coach")
    with patch("app.api.assignments.get_supabase", return_value=sb):
        resp = client.post("/assignments", json={
            "team_id": TEAM_ID, "created_by": COACH_ID, "title": "x", "recipient_user_ids": [],
        })
    assert resp.status_code == 400


# ── submit (student owns their own row) ─────────────────────────────────────────


def test_submit_rejects_other_students_assignment():
    sb = MagicMock()
    rec = MagicMock()
    rec.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"id": RECIPIENT_ID, "user_id": OTHER_ID, "status": "assigned"}
    ]
    sb.table.return_value = rec
    with patch("app.api.assignments.get_supabase", return_value=sb):
        resp = client.post(
            f"/assignments/recipients/{RECIPIENT_ID}/submit",
            json={"user_id": STUDENT_ID, "speech_id": "sp-1"},
        )
    assert resp.status_code == 403


# ── review (coach-only) ─────────────────────────────────────────────────────────


def test_review_rejects_student():
    sb = MagicMock()
    rec = MagicMock()
    rec.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"id": RECIPIENT_ID, "user_id": STUDENT_ID, "assignments": {"team_id": TEAM_ID}}
    ]
    sb.table.side_effect = [rec, _role_mock("student")]
    with patch("app.api.assignments.get_supabase", return_value=sb):
        resp = client.post(
            f"/assignments/recipients/{RECIPIENT_ID}/review",
            json={"user_id": STUDENT_ID, "action": "reviewed"},
        )
    assert resp.status_code == 403


def test_review_invalid_action():
    sb = MagicMock()
    rec = MagicMock()
    rec.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"id": RECIPIENT_ID, "user_id": STUDENT_ID, "assignments": {"team_id": TEAM_ID}}
    ]
    sb.table.return_value = rec
    with patch("app.api.assignments.get_supabase", return_value=sb):
        resp = client.post(
            f"/assignments/recipients/{RECIPIENT_ID}/review",
            json={"user_id": COACH_ID, "action": "nonsense"},
        )
    assert resp.status_code == 400


# ── coach-only read endpoints ───────────────────────────────────────────────────


def test_review_queue_rejects_student():
    sb = MagicMock()
    sb.table.return_value = _role_mock("student")
    with patch("app.api.assignments.get_supabase", return_value=sb):
        resp = client.get(f"/teams/{TEAM_ID}/review-queue", params={"user_id": STUDENT_ID})
    assert resp.status_code == 403


def test_readiness_rejects_non_member():
    sb = MagicMock()
    sb.table.return_value = _role_mock(None)
    with patch("app.api.assignments.get_supabase", return_value=sb):
        resp = client.get(f"/teams/{TEAM_ID}/readiness", params={"user_id": "stranger"})
    assert resp.status_code == 403


def test_student_profile_rejects_student():
    sb = MagicMock()
    sb.table.return_value = _role_mock("student")
    with patch("app.api.assignments.get_supabase", return_value=sb):
        resp = client.get(
            f"/teams/{TEAM_ID}/students/{STUDENT_ID}", params={"user_id": OTHER_ID}
        )
    assert resp.status_code == 403


def test_list_assignments_rejects_non_member():
    sb = MagicMock()
    sb.table.return_value = _role_mock(None)
    with patch("app.api.assignments.get_supabase", return_value=sb):
        resp = client.get(f"/teams/{TEAM_ID}/assignments", params={"user_id": "stranger"})
    assert resp.status_code == 403
