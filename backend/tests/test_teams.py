from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

USER_ID = "user-coach-1"
STUDENT_ID = "user-student-1"
TEAM_ID = "team-123"
INVITE_CODE = "DEBATE24"


def test_create_team_success():
    """Successfully creates a team with invite code."""
    mock_supabase = MagicMock()

    # Check invite code doesn't exist
    check_mock = MagicMock()
    check_mock.select.return_value.eq.return_value.execute.return_value.data = []

    # Create team
    team_mock = MagicMock()
    team_mock.insert.return_value.execute.return_value.data = [
        {
            "id": TEAM_ID,
            "name": "Test Team",
            "invite_code": INVITE_CODE,
            "created_by": USER_ID,
            "created_at": "2026-06-02T00:00:00+00:00",
        }
    ]

    # Add coach
    coach_mock = MagicMock()
    coach_mock.insert.return_value.execute.return_value.data = [
        {
            "id": "member-1",
            "team_id": TEAM_ID,
            "user_id": USER_ID,
            "role": "coach",
            "created_at": "2026-06-02T00:00:00+00:00",
        }
    ]

    mock_supabase.table.side_effect = [check_mock, team_mock, coach_mock]

    with patch("app.api.teams.get_supabase", return_value=mock_supabase):
        response = client.post(
            "/teams",
            json={"name": "Test Team", "created_by": USER_ID},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Team"
    assert data["invite_code"] == INVITE_CODE
    assert data["created_by"] == USER_ID


def test_join_team_success():
    """Successfully joins a team with valid invite code."""
    mock_supabase = MagicMock()

    # Find team by invite code
    team_mock = MagicMock()
    team_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"id": TEAM_ID}
    ]

    # Check not already a member
    existing_mock = MagicMock()
    existing_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

    # Add member
    member_mock = MagicMock()
    member_mock.insert.return_value.execute.return_value.data = [
        {
            "id": "member-2",
            "team_id": TEAM_ID,
            "user_id": STUDENT_ID,
            "role": "student",
            "created_at": "2026-06-02T00:00:00+00:00",
        }
    ]

    mock_supabase.table.side_effect = [team_mock, existing_mock, member_mock]

    with patch("app.api.teams.get_supabase", return_value=mock_supabase):
        response = client.post(
            "/teams/join",
            json={"invite_code": INVITE_CODE, "user_id": STUDENT_ID},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["team_id"] == TEAM_ID
    assert data["user_id"] == STUDENT_ID
    assert data["role"] == "student"


def test_join_team_invalid_code():
    """Returns 404 for invalid invite code."""
    mock_supabase = MagicMock()

    team_mock = MagicMock()
    team_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    mock_supabase.table.return_value = team_mock

    with patch("app.api.teams.get_supabase", return_value=mock_supabase):
        response = client.post(
            "/teams/join",
            json={"invite_code": "INVALID", "user_id": STUDENT_ID},
        )

    assert response.status_code == 404
    assert "invalid invite code" in response.json()["detail"].lower()


def test_join_team_already_member():
    """Returns 400 if user is already a member."""
    mock_supabase = MagicMock()

    # Find team
    team_mock = MagicMock()
    team_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"id": TEAM_ID}
    ]

    # User is already a member
    existing_mock = MagicMock()
    existing_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        {"id": "member-1"}
    ]

    mock_supabase.table.side_effect = [team_mock, existing_mock]

    with patch("app.api.teams.get_supabase", return_value=mock_supabase):
        response = client.post(
            "/teams/join",
            json={"invite_code": INVITE_CODE, "user_id": STUDENT_ID},
        )

    assert response.status_code == 400
    assert "already a member" in response.json()["detail"].lower()


def test_get_user_teams():
    """Returns all teams for a user."""
    mock_supabase = MagicMock()

    teams_mock = MagicMock()
    teams_mock.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "team_id": TEAM_ID,
            "role": "coach",
            "teams": {
                "id": TEAM_ID,
                "name": "Test Team",
                "invite_code": INVITE_CODE,
            },
        },
        {
            "team_id": "team-456",
            "role": "student",
            "teams": {
                "id": "team-456",
                "name": "Another Team",
                "invite_code": "SPEECH25",
            },
        },
    ]

    mock_supabase.table.return_value = teams_mock

    with patch("app.api.teams.get_supabase", return_value=mock_supabase):
        response = client.get(f"/teams/users/{USER_ID}")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["team_name"] == "Test Team"
    assert data[0]["role"] == "coach"
    assert data[1]["team_name"] == "Another Team"
    assert data[1]["role"] == "student"


def test_get_team_dashboard_member():
    """Coach can view team dashboard."""
    mock_supabase = MagicMock()

    # Verify membership
    membership_mock = MagicMock()
    membership_mock.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"role": "coach"}
    ]

    # Get team info
    team_mock = MagicMock()
    team_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {
            "id": TEAM_ID,
            "name": "Test Team",
            "invite_code": INVITE_CODE,
        }
    ]

    # Get members
    members_mock = MagicMock()
    members_mock.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "user_id": USER_ID,
            "role": "coach",
            "profiles": {"display_name": "Coach User"},
        },
        {
            "user_id": STUDENT_ID,
            "role": "student",
            "profiles": {"display_name": "Student User"},
        },
    ]

    # Student speeches
    speeches_mock = MagicMock()
    speeches_mock.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "speech-1", "status": "done", "created_at": "2026-06-01T00:00:00+00:00"},
        {"id": "speech-2", "status": "pending", "created_at": "2026-06-02T00:00:00+00:00"},
    ]

    # Student drills
    drills_mock = MagicMock()
    drills_mock.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "drill-1"},
    ]

    # Student attempts
    attempts_mock = MagicMock()
    attempts_mock.select.return_value.eq.return_value.execute.return_value.count = 3

    mock_supabase.table.side_effect = [
        membership_mock,
        team_mock,
        members_mock,
        speeches_mock,
        drills_mock,
        attempts_mock,
    ]

    with patch("app.api.teams.get_supabase", return_value=mock_supabase):
        response = client.get(f"/teams/{TEAM_ID}/dashboard?user_id={USER_ID}")

    assert response.status_code == 200
    data = response.json()
    assert data["team_name"] == "Test Team"
    assert data["invite_code"] == INVITE_CODE
    assert data["member_count"] == 2
    assert len(data["students"]) == 1
    assert data["students"][0]["user_id"] == STUDENT_ID
    assert data["students"][0]["speech_count"] == 2
    assert data["students"][0]["feedback_ready_count"] == 1


def test_get_team_dashboard_non_member():
    """Non-members cannot view team dashboard."""
    mock_supabase = MagicMock()

    # User is not a member
    membership_mock = MagicMock()
    membership_mock.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    mock_supabase.table.return_value = membership_mock

    with patch("app.api.teams.get_supabase", return_value=mock_supabase):
        response = client.get(f"/teams/{TEAM_ID}/dashboard?user_id=non-member")

    assert response.status_code == 403
    assert "not a member" in response.json()["detail"].lower()
