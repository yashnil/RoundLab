"""Tests for the analysis_jobs service, API, and the /analyze endpoint."""

from unittest.mock import MagicMock, patch, call

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import jobs as job_svc

client = TestClient(app)

SPEECH_ID = "aaaaaaaa-1111-0000-0000-00000000job1"
USER_ID   = "bbbbbbbb-0000-0000-0000-00000000job1"
JOB_ID    = "cccccccc-0000-0000-0000-00000000job1"

FAKE_SPEECH = {
    "id": SPEECH_ID,
    "user_id": USER_ID,
    "title": "Test Speech",
    "speech_type": "constructive",
    "side": "pro",
    "judge_type": "flow",
    "topic": "Resolved: Test.",
    "audio_url": "path/to/audio.mp3",
    "status": "pending",
    "created_at": "2026-06-09T00:00:00+00:00",
    "updated_at": "2026-06-09T00:00:00+00:00",
}

FAKE_JOB = {
    "id": JOB_ID,
    "user_id": USER_ID,
    "speech_id": SPEECH_ID,
    "drill_id": None,
    "document_id": None,
    "job_type": "speech_analysis",
    "status": "queued",
    "current_step": None,
    "progress": None,
    "error_message": None,
    "error_code": None,
    "result_json": None,
    "attempt_count": 1,
    "started_at": None,
    "completed_at": None,
    "created_at": "2026-06-09T00:00:00+00:00",
    "updated_at": "2026-06-09T00:00:00+00:00",
}


# ── Service unit tests ────────────────────────────────────────────────────────

class TestCreateJob:
    def test_defaults_to_queued(self):
        sb = MagicMock()
        sb.table.return_value.insert.return_value.execute.return_value.data = [FAKE_JOB.copy()]
        job = job_svc.create_job(sb, USER_ID, "speech_analysis", speech_id=SPEECH_ID)
        assert job["status"] == "queued"
        assert job["job_type"] == "speech_analysis"

    def test_inserts_speech_id(self):
        sb = MagicMock()
        inserted = []
        def execute():
            r = MagicMock()
            r.data = [FAKE_JOB.copy()]
            return r
        t = MagicMock()
        t.insert.side_effect = lambda row: (inserted.append(row), t)[1]
        t.execute = execute
        sb.table.return_value = t

        job_svc.create_job(sb, USER_ID, "speech_analysis", speech_id=SPEECH_ID)
        assert inserted[0].get("speech_id") == SPEECH_ID

    def test_omits_null_optional_ids(self):
        sb = MagicMock()
        inserted = []
        def execute():
            r = MagicMock()
            r.data = [FAKE_JOB.copy()]
            return r
        t = MagicMock()
        t.insert.side_effect = lambda row: (inserted.append(row), t)[1]
        t.execute = execute
        sb.table.return_value = t

        job_svc.create_job(sb, USER_ID, "speech_analysis", speech_id=SPEECH_ID)
        assert "drill_id" not in inserted[0]
        assert "document_id" not in inserted[0]


class TestUpdateJobProgress:
    def test_clamps_progress_above_100(self):
        sb = MagicMock()
        t = MagicMock()
        t.update.return_value = t
        t.eq.return_value = t
        t.execute.return_value = MagicMock()
        sb.table.return_value = t

        job_svc.update_job_progress(sb, JOB_ID, "generating_feedback", 150)
        # Should have been clamped to 100
        t.update.assert_called_once()
        payload = t.update.call_args[0][0]
        assert payload["progress"] == 100

    def test_clamps_progress_below_0(self):
        sb = MagicMock()
        t = MagicMock()
        t.update.return_value = t
        t.eq.return_value = t
        t.execute.return_value = MagicMock()
        sb.table.return_value = t

        job_svc.update_job_progress(sb, JOB_ID, "transcribing", -5)
        payload = t.update.call_args[0][0]
        assert payload["progress"] == 0

    def test_does_not_raise_on_db_error(self):
        sb = MagicMock()
        sb.table.side_effect = Exception("DB is down")
        # Should not raise
        job_svc.update_job_progress(sb, JOB_ID, "transcribing", 10)


class TestCompleteJob:
    def test_sets_status_succeeded(self):
        sb = MagicMock()
        t = MagicMock()
        t.update.return_value = t
        t.eq.return_value = t
        t.execute.return_value = MagicMock()
        sb.table.return_value = t

        job_svc.complete_job(sb, JOB_ID)
        payload = t.update.call_args[0][0]
        assert payload["status"] == "succeeded"
        assert payload["progress"] == 100
        assert "completed_at" in payload

    def test_stores_result_json(self):
        sb = MagicMock()
        t = MagicMock()
        t.update.return_value = t
        t.eq.return_value = t
        t.execute.return_value = MagicMock()
        sb.table.return_value = t

        job_svc.complete_job(sb, JOB_ID, result_json={"score": 72})
        payload = t.update.call_args[0][0]
        assert payload["result_json"] == {"score": 72}


class TestFailJob:
    def test_sets_status_failed(self):
        sb = MagicMock()
        t = MagicMock()
        t.update.return_value = t
        t.eq.return_value = t
        t.execute.return_value = MagicMock()
        sb.table.return_value = t

        job_svc.fail_job(sb, JOB_ID, "Transcription failed.", "transcription_failed")
        payload = t.update.call_args[0][0]
        assert payload["status"] == "failed"
        assert payload["error_message"] == "Transcription failed."
        assert payload["error_code"] == "transcription_failed"
        assert "completed_at" in payload


class TestGetJob:
    def test_returns_none_when_not_found(self):
        sb = MagicMock()
        t = MagicMock()
        t.select.return_value = t
        t.eq.return_value = t
        t.limit.return_value = t
        t.execute.return_value.data = []
        sb.table.return_value = t

        result = job_svc.get_job(sb, JOB_ID, USER_ID)
        assert result is None

    def test_returns_job_when_found(self):
        sb = MagicMock()
        t = MagicMock()
        t.select.return_value = t
        t.eq.return_value = t
        t.limit.return_value = t
        t.execute.return_value.data = [FAKE_JOB.copy()]
        sb.table.return_value = t

        result = job_svc.get_job(sb, JOB_ID, USER_ID)
        assert result is not None
        assert result["id"] == JOB_ID

    def test_user_isolation_different_user_gets_none(self):
        """
        Demonstrates that get_job always passes user_id to the .eq() filter.
        Isolation is enforced by the DB (RLS); here we verify the filter is applied.
        """
        sb = MagicMock()
        t = MagicMock()
        t.select.return_value = t
        eq_calls = []
        def capture_eq(col, val):
            eq_calls.append((col, val))
            return t
        t.eq.side_effect = capture_eq
        t.limit.return_value = t
        t.execute.return_value.data = []
        sb.table.return_value = t

        job_svc.get_job(sb, JOB_ID, "different-user-id")
        assert any(c == ("user_id", "different-user-id") for c in eq_calls)


class TestRetryJob:
    def _sb_for_retry(self, existing_status: str):
        sb = MagicMock()
        job_copy = {**FAKE_JOB, "status": existing_status}
        # First table call: get_job (select)
        # Second table call: update
        select_t = MagicMock()
        select_t.select.return_value = select_t
        select_t.eq.return_value = select_t
        select_t.limit.return_value = select_t
        select_t.execute.return_value.data = [job_copy]

        update_t = MagicMock()
        update_t.update.return_value = update_t
        update_t.eq.return_value = update_t
        updated = {**FAKE_JOB, "status": "queued", "attempt_count": 2}
        update_t.execute.return_value.data = [updated]

        call_count = [0]
        def table_fn(name):
            call_count[0] += 1
            # First call is from get_job, second is the update
            return select_t if call_count[0] == 1 else update_t
        sb.table.side_effect = table_fn
        return sb

    def test_retries_failed_job(self):
        sb = self._sb_for_retry("failed")
        result = job_svc.retry_job(sb, JOB_ID, USER_ID)
        assert result["status"] == "queued"
        assert result["attempt_count"] == 2

    def test_raises_for_succeeded_job(self):
        sb = MagicMock()
        t = MagicMock()
        t.select.return_value = t
        t.eq.return_value = t
        t.limit.return_value = t
        t.execute.return_value.data = [{**FAKE_JOB, "status": "succeeded"}]
        sb.table.return_value = t

        with pytest.raises(ValueError, match="only failed jobs"):
            job_svc.retry_job(sb, JOB_ID, USER_ID)

    def test_raises_for_running_job(self):
        sb = MagicMock()
        t = MagicMock()
        t.select.return_value = t
        t.eq.return_value = t
        t.limit.return_value = t
        t.execute.return_value.data = [{**FAKE_JOB, "status": "running"}]
        sb.table.return_value = t

        with pytest.raises(ValueError, match="only failed jobs"):
            job_svc.retry_job(sb, JOB_ID, USER_ID)

    def test_raises_for_unknown_job(self):
        sb = MagicMock()
        t = MagicMock()
        t.select.return_value = t
        t.eq.return_value = t
        t.limit.return_value = t
        t.execute.return_value.data = []
        sb.table.return_value = t

        with pytest.raises(ValueError, match="Job not found"):
            job_svc.retry_job(sb, JOB_ID, USER_ID)


# ── API endpoint tests ────────────────────────────────────────────────────────

def _make_table_fn(jobs_data=None, speech_data=None, tx_data=None):
    """Build a table() factory for the job API mock supabase."""
    def table_fn(name):
        t = MagicMock()
        t.select.return_value = t
        t.insert.return_value = t
        t.update.return_value = t
        t.eq.return_value = t
        t.limit.return_value = t
        t.order.return_value = t

        def execute_fn():
            r = MagicMock()
            if name == "speeches":
                r.data = speech_data if speech_data is not None else [FAKE_SPEECH]
            elif name == "transcripts":
                r.data = tx_data if tx_data is not None else []
            elif name == "analysis_jobs":
                r.data = jobs_data if jobs_data is not None else [FAKE_JOB]
            else:
                r.data = []
            return r

        t.execute = execute_fn
        return t
    return table_fn


class TestGetJobEndpoint:
    def test_returns_job(self):
        with patch("app.api.jobs.get_supabase") as mock_sb:
            mock_sb.return_value.table = _make_table_fn(jobs_data=[FAKE_JOB])
            r = client.get(f"/jobs/{JOB_ID}?user_id={USER_ID}")
        assert r.status_code == 200
        assert r.json()["id"] == JOB_ID

    def test_404_when_not_found(self):
        with patch("app.api.jobs.get_supabase") as mock_sb:
            mock_sb.return_value.table = _make_table_fn(jobs_data=[])
            r = client.get(f"/jobs/{JOB_ID}?user_id={USER_ID}")
        assert r.status_code == 404


class TestListSpeechJobsEndpoint:
    def test_returns_list(self):
        with patch("app.api.jobs.get_supabase") as mock_sb:
            mock_sb.return_value.table = _make_table_fn(jobs_data=[FAKE_JOB])
            r = client.get(f"/speeches/{SPEECH_ID}/jobs?user_id={USER_ID}")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert r.json()[0]["speech_id"] == SPEECH_ID


class TestAnalyzeSpeechEndpoint:
    def test_creates_job_and_returns_202(self):
        with (
            patch("app.api.speeches.get_supabase") as mock_sb,
            patch("app.services.analysis_pipeline.run_speech_analysis_pipeline"),
        ):
            mock_sb.return_value.table = _make_table_fn(
                jobs_data=[FAKE_JOB],
                speech_data=[FAKE_SPEECH],
                tx_data=[],
            )
            r = client.post(f"/speeches/{SPEECH_ID}/analyze?user_id={USER_ID}")
        assert r.status_code == 202
        body = r.json()
        assert "job_id" in body
        assert body["status"] in ("queued", "running")

    def test_404_for_unknown_speech(self):
        with patch("app.api.speeches.get_supabase") as mock_sb:
            mock_sb.return_value.table = _make_table_fn(
                speech_data=[],
                jobs_data=[],
                tx_data=[],
            )
            r = client.post(f"/speeches/{SPEECH_ID}/analyze?user_id={USER_ID}")
        assert r.status_code == 404

    def test_400_when_no_audio_and_no_transcript(self):
        speech_no_audio = {**FAKE_SPEECH, "audio_url": None}
        with patch("app.api.speeches.get_supabase") as mock_sb:
            mock_sb.return_value.table = _make_table_fn(
                speech_data=[speech_no_audio],
                jobs_data=[],
                tx_data=[],
            )
            r = client.post(f"/speeches/{SPEECH_ID}/analyze?user_id={USER_ID}")
        assert r.status_code == 400

    def test_returns_existing_active_job_without_creating_duplicate(self):
        running_job = {**FAKE_JOB, "status": "running"}
        with patch("app.api.speeches.get_supabase") as mock_sb:
            mock_sb.return_value.table = _make_table_fn(
                speech_data=[FAKE_SPEECH],
                jobs_data=[running_job],
                tx_data=[],
            )
            r = client.post(f"/speeches/{SPEECH_ID}/analyze?user_id={USER_ID}")
        assert r.status_code == 202
        assert r.json()["status"] == "running"


class TestRetryJobEndpoint:
    def test_400_for_succeeded_job(self):
        def table_fn(name):
            t = MagicMock()
            t.select.return_value = t
            t.eq.return_value = t
            t.limit.return_value = t
            t.execute.return_value.data = [{**FAKE_JOB, "status": "succeeded"}]
            return t

        with patch("app.api.jobs.get_supabase") as mock_sb:
            mock_sb.return_value.table = table_fn
            r = client.post(f"/jobs/{JOB_ID}/retry?user_id={USER_ID}")
        assert r.status_code == 400
        assert "only failed jobs" in r.json()["detail"]
