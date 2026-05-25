from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_supabase_health_reachable():
    mock_client = MagicMock()
    with patch("app.api.health.get_supabase", return_value=mock_client):
        response = client.get("/health/supabase")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "reachable"}


def test_supabase_health_unreachable():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.limit.return_value.execute.side_effect = Exception(
        "connection refused"
    )
    with patch("app.api.health.get_supabase", return_value=mock_client):
        response = client.get("/health/supabase")
    assert response.status_code == 200
    assert response.json() == {"status": "error", "database": "unreachable"}
