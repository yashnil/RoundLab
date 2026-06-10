"""Tests for the Shareable Coach Report endpoints."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app

client = TestClient(app)

# ── Fake data ──────────────────────────────────────────────────────────────────

SPEECH_ID = "aaaaaaaa-0000-0000-0000-000000000001"
USER_ID = "bbbbbbbb-0000-0000-0000-000000000002"
OTHER_USER = "cccccccc-0000-0000-0000-000000000003"
SHARE_ID = "dddddddd-0000-0000-0000-000000000004"
FAKE_TOKEN = "x" * 43  # 43-char URL-safe token

_DONE_SPEECH = {
    "id": SPEECH_ID,
    "user_id": USER_ID,
    "speech_type": "constructive",
    "side": "pro",
    "judge_type": "flow",
    "topic": "Resolved: Test.",
    "status": "done",
    "created_at": "2026-06-09T00:00:00+00:00",
    "parent_speech_id": None,
}

_PENDING_SPEECH = {**_DONE_SPEECH, "status": "pending"}

_SHARE_ROW = {
    "id": SHARE_ID,
    "speech_id": SPEECH_ID,
    "user_id": USER_ID,
    "share_token": FAKE_TOKEN,
    "title": None,
    "include_transcript": True,
    "include_flow": True,
    "include_feedback": True,
    "include_drills": True,
    "include_delivery": True,
    "include_evidence_summary": False,
    "include_improvement": True,
    "expires_at": None,
    "revoked_at": None,
    "created_at": "2026-06-09T00:00:00+00:00",
    "updated_at": "2026-06-09T00:00:00+00:00",
}

CREATE_BODY = {
    "user_id": USER_ID,
    "include_transcript": True,
    "include_flow": True,
    "include_feedback": True,
    "include_drills": True,
    "include_delivery": True,
    "include_evidence_summary": False,
    "include_improvement": True,
}


# ── create_or_update_share ─────────────────────────────────────────────────────

class TestCreateShare:
    def _mock_sb(self, speech_row, existing_share_rows=None, insert_result=None, update_result=None):
        sb = MagicMock()
        speech_q = sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value
        speech_q.data = [speech_row] if speech_row else []

        existing_q = sb.table.return_value.select.return_value.eq.return_value.eq.return_value.is_.return_value.limit.return_value.execute.return_value
        existing_q.data = existing_share_rows or []

        if insert_result is not None:
            sb.table.return_value.insert.return_value.execute.return_value.data = [insert_result]
        if update_result is not None:
            sb.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [update_result]
        return sb

    def test_create_share_success(self):
        sb = MagicMock()
        # speech lookup
        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [_DONE_SPEECH]
        # no existing share
        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.is_.return_value.limit.return_value.execute.return_value.data = []
        # insert succeeds
        sb.table.return_value.insert.return_value.execute.return_value.data = [_SHARE_ROW]

        with patch("app.api.shared_reports.get_supabase", return_value=sb):
            resp = client.post(f"/speeches/{SPEECH_ID}/share", json=CREATE_BODY)
        assert resp.status_code == 200
        body = resp.json()
        assert body["share_token"] == FAKE_TOKEN

    def test_create_share_requires_ownership(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        with patch("app.api.shared_reports.get_supabase", return_value=sb):
            resp = client.post(f"/speeches/{SPEECH_ID}/share", json={**CREATE_BODY, "user_id": OTHER_USER})
        assert resp.status_code == 404

    def test_create_share_requires_completed_report(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [_PENDING_SPEECH]
        with patch("app.api.shared_reports.get_supabase", return_value=sb):
            resp = client.post(f"/speeches/{SPEECH_ID}/share", json=CREATE_BODY)
        assert resp.status_code == 400
        assert "completed" in resp.json()["detail"].lower()

    def test_token_is_long_enough(self):
        """Token must be at least 40 characters (secrets.token_urlsafe(32) = 43 chars)."""
        from app.api.shared_reports import _make_token
        token = _make_token()
        assert len(token) >= 40

    def test_token_is_unique(self):
        """Two consecutive calls should not produce the same token."""
        from app.api.shared_reports import _make_token
        assert _make_token() != _make_token()

    def test_evidence_summary_excluded_by_default(self):
        """Default include_evidence_summary must be False."""
        body = {**CREATE_BODY, "include_evidence_summary": False}
        assert body["include_evidence_summary"] is False

    def test_updates_existing_share_instead_of_creating(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [_DONE_SPEECH]
        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.is_.return_value.limit.return_value.execute.return_value.data = [_SHARE_ROW]
        updated_row = {**_SHARE_ROW, "include_transcript": False}
        sb.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [updated_row]
        with patch("app.api.shared_reports.get_supabase", return_value=sb):
            resp = client.post(f"/speeches/{SPEECH_ID}/share", json={**CREATE_BODY, "include_transcript": False})
        assert resp.status_code == 200
        # insert should NOT have been called
        sb.table.return_value.insert.assert_not_called()


# ── get_shared_report (public) ─────────────────────────────────────────────────

class TestGetSharedReport:
    def _full_mock(self, share_row, speech_row=None, fb_row=None, tx_row=None,
                   args_row=None, drills_rows=None, dm_row=None, checks_rows=None):
        sb = MagicMock()

        def table_side(name):
            t = MagicMock()
            mock_chain = MagicMock()

            if name == "shared_reports":
                mock_chain.execute.return_value.data = [share_row] if share_row else []
            elif name == "speeches":
                mock_chain.execute.return_value.data = [speech_row] if speech_row else []
            elif name == "feedback_reports":
                mock_chain.execute.return_value.data = [fb_row] if fb_row else []
            elif name == "transcripts":
                mock_chain.execute.return_value.data = [tx_row] if tx_row else []
            elif name == "argument_maps":
                mock_chain.execute.return_value.data = [args_row] if args_row else []
            elif name == "drills":
                mock_chain.execute.return_value.data = drills_rows or []
            elif name == "delivery_metrics":
                mock_chain.execute.return_value.data = [dm_row] if dm_row else []
            elif name == "claim_evidence_checks":
                mock_chain.execute.return_value.data = checks_rows or []
            else:
                mock_chain.execute.return_value.data = []

            t.select.return_value = mock_chain
            mock_chain.eq.return_value = mock_chain
            mock_chain.is_.return_value = mock_chain
            mock_chain.limit.return_value = mock_chain
            mock_chain.order.return_value = mock_chain
            return t

        sb.table.side_effect = table_side
        return sb

    def test_returns_sanitized_report(self):
        speech = {**_DONE_SPEECH, "parent_speech_id": None}
        fb = {
            "overall_score": 72,
            "scores": {"clash": 15, "weighing": 14, "extensions": 15, "drops": 14, "judge_adaptation": 14},
            "summary": "Good constructive.",
            "strengths": ["Clear claims"],
            "weaknesses": ["Weak warrants"],
            "raw_feedback": {"top_3_priorities": ["Warrant better"], "structured_issues": []},
        }
        sb = self._full_mock(_SHARE_ROW, speech_row=speech, fb_row=fb)
        with patch("app.api.shared_reports.get_supabase", return_value=sb):
            resp = client.get(f"/shared-reports/{FAKE_TOKEN}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["speech_type"] == "constructive"
        assert body["feedback"]["overall_score"] == 72
        # privacy: no user_id, no audio_url
        assert "user_id" not in body
        assert "audio_url" not in body

    def test_revoked_token_returns_410(self):
        revoked = {**_SHARE_ROW, "revoked_at": "2026-06-09T01:00:00+00:00"}
        sb = self._full_mock(revoked, speech_row=_DONE_SPEECH)
        with patch("app.api.shared_reports.get_supabase", return_value=sb):
            resp = client.get(f"/shared-reports/{FAKE_TOKEN}")
        assert resp.status_code == 410
        assert "revoked" in resp.json()["detail"].lower()

    def test_expired_token_returns_410(self):
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        expired = {**_SHARE_ROW, "expires_at": past}
        sb = self._full_mock(expired, speech_row=_DONE_SPEECH)
        with patch("app.api.shared_reports.get_supabase", return_value=sb):
            resp = client.get(f"/shared-reports/{FAKE_TOKEN}")
        assert resp.status_code == 410
        assert "expired" in resp.json()["detail"].lower()

    def test_unknown_token_returns_404(self):
        sb = self._full_mock(None)
        with patch("app.api.shared_reports.get_supabase", return_value=sb):
            resp = client.get("/shared-reports/nonexistenttoken")
        assert resp.status_code == 404

    def test_include_flags_control_sections(self):
        share_no_feedback = {**_SHARE_ROW, "include_feedback": False}
        speech = {**_DONE_SPEECH, "parent_speech_id": None}
        sb = self._full_mock(share_no_feedback, speech_row=speech)
        with patch("app.api.shared_reports.get_supabase", return_value=sb):
            resp = client.get(f"/shared-reports/{FAKE_TOKEN}")
        assert resp.status_code == 200
        assert resp.json()["feedback"] is None
        assert resp.json()["include_flags"]["feedback"] is False

    def test_evidence_summary_excluded_when_flag_false(self):
        share = {**_SHARE_ROW, "include_evidence_summary": False}
        speech = {**_DONE_SPEECH, "parent_speech_id": None}
        sb = self._full_mock(share, speech_row=speech)
        with patch("app.api.shared_reports.get_supabase", return_value=sb):
            resp = client.get(f"/shared-reports/{FAKE_TOKEN}")
        assert resp.status_code == 200
        assert resp.json()["evidence_summary"] is None

    def test_no_private_storage_or_user_fields(self):
        speech = {**_DONE_SPEECH, "parent_speech_id": None}
        fb = {
            "overall_score": 70, "scores": {}, "summary": "OK", "strengths": [], "weaknesses": [],
            "raw_feedback": {},
        }
        sb = self._full_mock(_SHARE_ROW, speech_row=speech, fb_row=fb)
        with patch("app.api.shared_reports.get_supabase", return_value=sb):
            resp = client.get(f"/shared-reports/{FAKE_TOKEN}")
        body_str = resp.text
        assert "audio_url" not in body_str
        assert USER_ID not in body_str  # user_id must not leak

    def test_future_expiry_allows_access(self):
        future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        valid = {**_SHARE_ROW, "expires_at": future}
        speech = {**_DONE_SPEECH, "parent_speech_id": None}
        sb = self._full_mock(valid, speech_row=speech)
        with patch("app.api.shared_reports.get_supabase", return_value=sb):
            resp = client.get(f"/shared-reports/{FAKE_TOKEN}")
        assert resp.status_code == 200


# ── revoke_share ───────────────────────────────────────────────────────────────

class TestRevokeShare:
    def test_revoke_sets_revoked_at(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [_SHARE_ROW]
        sb.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            {**_SHARE_ROW, "revoked_at": "2026-06-09T02:00:00+00:00"}
        ]
        with patch("app.api.shared_reports.get_supabase", return_value=sb):
            resp = client.delete(f"/shared-reports/{SHARE_ID}", params={"user_id": USER_ID})
        assert resp.status_code == 200
        assert resp.json()["revoked"] is True

    def test_revoke_wrong_user_returns_404(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        with patch("app.api.shared_reports.get_supabase", return_value=sb):
            resp = client.delete(f"/shared-reports/{SHARE_ID}", params={"user_id": OTHER_USER})
        assert resp.status_code == 404
