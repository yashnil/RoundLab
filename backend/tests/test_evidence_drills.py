"""Tests for evidence drill generation — service + API endpoint."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.document import ClaimEvidenceCheckRow
from app.services.evidence_drill_generation import (
    generate_evidence_drills,
    _drill_for_unsupported,
    _drill_for_partially_supported,
    _drill_for_unverifiable,
)

client = TestClient(app)

SPEECH_ID = "aaaaaaaa-1111-0000-0000-000000000099"
USER_ID   = "bbbbbbbb-0000-0000-0000-000000000099"

FAKE_SPEECH = {
    "id": SPEECH_ID,
    "user_id": USER_ID,
    "title": "1AC Round Evidence Test",
    "speech_type": "constructive",
    "side": "pro",
    "judge_type": "flow",
    "topic": "Resolved: Test.",
    "audio_url": None,
    "status": "done",
    "created_at": "2026-06-09T00:00:00+00:00",
    "updated_at": "2026-06-09T00:00:00+00:00",
}


def _make_check(
    support_level: str,
    label: str = "C1: Economic Growth",
    claim: str = "Lower taxes increase investment",
    check_id: str = "check-001",
) -> ClaimEvidenceCheckRow:
    return ClaimEvidenceCheckRow(
        id=check_id,
        speech_id=SPEECH_ID,
        user_id=USER_ID,
        argument_label=label,
        claim_text=claim,
        evidence_text_from_speech="Smith 2023 finds GDP increases",
        matched_card_id=None,
        support_level=support_level,
        explanation="Test explanation",
        created_at="2026-06-09T00:00:00+00:00",
    )


# ── Service unit tests ────────────────────────────────────────────────────────

class TestDrillTemplates:
    def test_unsupported_produces_claim_precision(self):
        check = _make_check("unsupported")
        drill = _drill_for_unsupported(check)
        assert drill["skill_target"] == "claim_precision"
        assert "C1: Economic Growth" in drill["title"]
        assert len(drill["success_criteria"]) >= 3
        assert drill["difficulty"] == "beginner"
        assert 30 <= drill["time_limit_seconds"] <= 300

    def test_partially_supported_produces_evidence_alignment(self):
        check = _make_check("partially_supported")
        drill = _drill_for_partially_supported(check)
        assert drill["skill_target"] == "evidence_alignment"
        assert drill["difficulty"] == "intermediate"
        assert len(drill["instructions"].split("\n")) >= 4

    def test_unverifiable_produces_evidence_attribution(self):
        check = _make_check("unverifiable")
        drill = _drill_for_unverifiable(check)
        assert drill["skill_target"] == "evidence_attribution"
        assert "attribution" in drill["title"].lower() or "Attribution" in drill["title"]
        assert len(drill["success_criteria"]) >= 3


class TestGenerateEvidenceDrills:
    def test_empty_checks_returns_empty(self):
        assert generate_evidence_drills([]) == []

    def test_all_supported_returns_empty(self):
        checks = [_make_check("supported", check_id=f"c{i}") for i in range(3)]
        assert generate_evidence_drills(checks) == []

    def test_unsupported_first_in_priority(self):
        checks = [
            _make_check("partially_supported", label="C1", claim="Claim 1", check_id="c1"),
            _make_check("unsupported", label="C2", claim="Claim 2", check_id="c2"),
            _make_check("unverifiable", label="C3", claim="Claim 3", check_id="c3"),
        ]
        drills = generate_evidence_drills(checks, max_drills=3)
        # unsupported should be first
        assert drills[0]["skill_target"] == "claim_precision"

    def test_max_drills_respected(self):
        checks = [
            _make_check("unsupported", label=f"C{i}", claim=f"Claim {i}", check_id=f"c{i}")
            for i in range(5)
        ]
        drills = generate_evidence_drills(checks, max_drills=2)
        assert len(drills) <= 2

    def test_deduplication_skips_existing_source_weakness(self):
        check = _make_check("unsupported")
        first_pass = generate_evidence_drills([check])
        assert len(first_pass) == 1
        existing_sw = {first_pass[0]["source_weakness"]}
        second_pass = generate_evidence_drills([check], existing_source_weaknesses=existing_sw)
        assert len(second_pass) == 0

    def test_mixed_levels_all_get_drills(self):
        checks = [
            _make_check("unsupported", label="C1", claim="Claim 1", check_id="c1"),
            _make_check("partially_supported", label="C2", claim="Claim 2", check_id="c2"),
            _make_check("unverifiable", label="C3", claim="Claim 3", check_id="c3"),
        ]
        drills = generate_evidence_drills(checks, max_drills=3)
        targets = {d["skill_target"] for d in drills}
        assert "claim_precision" in targets
        assert "evidence_alignment" in targets
        assert "evidence_attribution" in targets

    def test_drill_rows_have_required_fields(self):
        check = _make_check("unsupported")
        drills = generate_evidence_drills([check])
        assert len(drills) == 1
        d = drills[0]
        for field in ("title", "skill_target", "description", "prompt", "instructions",
                      "success_criteria", "source_weakness", "difficulty", "time_limit_seconds"):
            assert field in d, f"Missing field: {field}"
        assert isinstance(d["success_criteria"], list)

    def test_evidence_skill_targets_are_valid_strings(self):
        """Skill targets must be plain strings (no enum objects)."""
        checks = [
            _make_check("unsupported", label="C1", claim="Claim 1", check_id="c1"),
            _make_check("partially_supported", label="C2", claim="Claim 2", check_id="c2"),
            _make_check("unverifiable", label="C3", claim="Claim 3", check_id="c3"),
        ]
        drills = generate_evidence_drills(checks, max_drills=3)
        for d in drills:
            assert isinstance(d["skill_target"], str)
            assert d["skill_target"] in (
                "evidence_alignment", "claim_precision", "evidence_attribution", "card_warranting"
            )

    def test_time_limit_within_allowed_range(self):
        """time_limit_seconds must be 30–300 to satisfy DB constraint."""
        for level in ("unsupported", "partially_supported", "unverifiable"):
            check = _make_check(level)
            drills = generate_evidence_drills([check])
            for d in drills:
                assert 30 <= d["time_limit_seconds"] <= 300


# ── API endpoint tests ────────────────────────────────────────────────────────

FAKE_CHECKS = [
    {
        "id": "check-001",
        "speech_id": SPEECH_ID,
        "user_id": USER_ID,
        "argument_label": "C1: Economic Growth",
        "claim_text": "Lower taxes increase investment",
        "evidence_text_from_speech": "Smith 2023",
        "matched_card_id": None,
        "support_level": "unsupported",
        "explanation": "Card does not match claim",
        "created_at": "2026-06-09T00:00:00+00:00",
    },
    {
        "id": "check-002",
        "speech_id": SPEECH_ID,
        "user_id": USER_ID,
        "argument_label": "C2: Innovation",
        "claim_text": "High taxes reduce entrepreneurship",
        "evidence_text_from_speech": "Jones 2022",
        "matched_card_id": None,
        "support_level": "unverifiable",
        "explanation": "No matching card found",
        "created_at": "2026-06-09T00:00:01+00:00",
    },
]


def _make_table_fn(
    existing_drill_rows: list[dict] | None = None,
    checks_data: list[dict] | None = None,
    inserted_collector: list[dict] | None = None,
):
    """
    Build a Supabase table-function mock.
    existing_drill_rows — rows returned by the single drills SELECT (source_weakness + order).
    checks_data — rows for claim_evidence_checks; defaults to FAKE_CHECKS.
    inserted_collector — if provided, collected inserted drill rows are appended here.
    """
    if existing_drill_rows is None:
        existing_drill_rows = []
    if checks_data is None:
        checks_data = FAKE_CHECKS

    def table_fn(name: str):
        t = MagicMock()
        t.select.return_value = t
        t.insert.return_value = t
        t.eq.return_value = t
        t.order.return_value = t
        t.limit.return_value = t

        def execute_fn():
            r = MagicMock()
            if name == "speeches":
                r.data = [FAKE_SPEECH]
            elif name == "claim_evidence_checks":
                r.data = checks_data
            elif name == "drills":
                if t.insert.called:
                    rows = t.insert.call_args[0][0]
                    if inserted_collector is not None:
                        inserted_collector.extend(rows)
                    r.data = rows
                else:
                    r.data = existing_drill_rows
            else:
                r.data = []
            return r

        t.execute = execute_fn
        return t

    return table_fn


class TestEvidenceDrillsEndpoint:
    @patch("app.api.documents.get_supabase")
    def test_generates_drills_from_checks(self, mock_sb):
        inserted: list[dict] = []
        sb = MagicMock()
        sb.table = _make_table_fn(existing_drill_rows=[], inserted_collector=inserted)
        mock_sb.return_value = sb

        resp = client.post(f"/speeches/{SPEECH_ID}/evidence-drills?user_id={USER_ID}")
        assert resp.status_code == 201
        data = resp.json()
        assert len(data) >= 1
        skill_targets = {d.get("skill_target") for d in data}
        assert "claim_precision" in skill_targets or "evidence_attribution" in skill_targets

    @patch("app.api.documents.get_supabase")
    def test_order_starts_at_1_when_no_existing_drills(self, mock_sb):
        """When no drills exist for the speech, first evidence drill gets order=1."""
        inserted: list[dict] = []
        sb = MagicMock()
        sb.table = _make_table_fn(existing_drill_rows=[], inserted_collector=inserted)
        mock_sb.return_value = sb

        resp = client.post(f"/speeches/{SPEECH_ID}/evidence-drills?user_id={USER_ID}")
        assert resp.status_code == 201
        assert len(inserted) >= 1
        assert inserted[0]["order"] == 1, f"Expected order=1, got {inserted[0]['order']}"

    @patch("app.api.documents.get_supabase")
    def test_order_sequential_for_multiple_drills(self, mock_sb):
        """Multiple evidence drills get sequential order values starting at next_order."""
        checks_all_bad = [
            {**FAKE_CHECKS[0], "id": "c1", "argument_label": "C1", "claim_text": "Claim 1"},
            {**FAKE_CHECKS[1], "id": "c2", "argument_label": "C2", "claim_text": "Claim 2",
             "support_level": "partially_supported"},
        ]
        inserted: list[dict] = []
        sb = MagicMock()
        sb.table = _make_table_fn(
            existing_drill_rows=[],
            checks_data=checks_all_bad,
            inserted_collector=inserted,
        )
        mock_sb.return_value = sb

        resp = client.post(f"/speeches/{SPEECH_ID}/evidence-drills?user_id={USER_ID}")
        assert resp.status_code == 201
        if len(inserted) >= 2:
            orders = [r["order"] for r in inserted]
            assert orders == sorted(orders), "Orders should be sequential ascending"
            assert orders[0] >= 1
            for a, b in zip(orders, orders[1:]):
                assert b == a + 1, f"Orders must be sequential: {orders}"

    @patch("app.api.documents.get_supabase")
    def test_order_offset_when_standard_drills_exist(self, mock_sb):
        """Evidence drills are assigned order > max(existing.order)."""
        inserted: list[dict] = []
        # Simulate 3 existing standard drills with orders 1, 2, 3
        existing = [
            {"source_weakness": "drop weakness", "order": 1},
            {"source_weakness": "clash weakness", "order": 2},
            {"source_weakness": "weighing weakness", "order": 3},
        ]
        sb = MagicMock()
        sb.table = _make_table_fn(existing_drill_rows=existing, inserted_collector=inserted)
        mock_sb.return_value = sb

        resp = client.post(f"/speeches/{SPEECH_ID}/evidence-drills?user_id={USER_ID}")
        assert resp.status_code == 201
        assert len(inserted) >= 1
        for row in inserted:
            assert row["order"] >= 4, f"Expected order >= 4, got {row['order']}"

    @patch("app.api.documents.get_supabase")
    def test_order_never_zero(self, mock_sb):
        """order is always >= 1, even if existing drills have unusual data."""
        # Simulate edge case: existing row has order=0 or negative (corrupted state)
        # The fix uses max(valid_orders where order >= 1) with floor of 1
        existing = [
            {"source_weakness": None, "order": 0},   # invalid row — should be ignored
        ]
        inserted: list[dict] = []
        sb = MagicMock()
        sb.table = _make_table_fn(existing_drill_rows=existing, inserted_collector=inserted)
        mock_sb.return_value = sb

        resp = client.post(f"/speeches/{SPEECH_ID}/evidence-drills?user_id={USER_ID}")
        assert resp.status_code == 201
        for row in inserted:
            assert row["order"] >= 1, f"order must be >= 1, got {row['order']}"

    @patch("app.api.documents.get_supabase")
    def test_404_when_speech_not_found(self, mock_sb):
        sb = MagicMock()

        def table_fn(name):
            t = MagicMock()
            t.select.return_value = t
            t.insert.return_value = t
            t.eq.return_value = t
            t.order.return_value = t
            t.limit.return_value = t

            def execute_fn():
                r = MagicMock()
                r.data = []
                return r

            t.execute = execute_fn
            return t

        sb.table = table_fn
        mock_sb.return_value = sb

        resp = client.post(f"/speeches/nonexistent/evidence-drills?user_id={USER_ID}")
        assert resp.status_code == 404

    @patch("app.api.documents.get_supabase")
    def test_422_when_no_checks(self, mock_sb):
        sb = MagicMock()

        def table_fn(name):
            t = MagicMock()
            t.select.return_value = t
            t.insert.return_value = t
            t.eq.return_value = t
            t.order.return_value = t
            t.limit.return_value = t

            def execute_fn():
                r = MagicMock()
                if name == "speeches":
                    r.data = [FAKE_SPEECH]
                else:
                    r.data = []
                return r

            t.execute = execute_fn
            return t

        sb.table = table_fn
        mock_sb.return_value = sb

        resp = client.post(f"/speeches/{SPEECH_ID}/evidence-drills?user_id={USER_ID}")
        assert resp.status_code == 422

    @patch("app.api.documents.get_supabase")
    def test_returns_empty_list_when_all_supported(self, mock_sb):
        all_supported = [
            {
                "id": "check-s1",
                "speech_id": SPEECH_ID,
                "user_id": USER_ID,
                "argument_label": "C1",
                "claim_text": "Lower taxes increase investment",
                "evidence_text_from_speech": "Smith 2023",
                "matched_card_id": "card-1",
                "support_level": "supported",
                "explanation": "Card fully supports claim",
                "created_at": "2026-06-09T00:00:00+00:00",
            }
        ]
        sb = MagicMock()
        sb.table = _make_table_fn(existing_drill_rows=[], checks_data=all_supported)
        mock_sb.return_value = sb

        resp = client.post(f"/speeches/{SPEECH_ID}/evidence-drills?user_id={USER_ID}")
        assert resp.status_code == 201
        assert resp.json() == []

    @patch("app.api.documents.get_supabase")
    def test_no_duplicate_drills_on_second_call(self, mock_sb):
        """Re-calling the endpoint does not insert duplicate drills for the same checks."""
        # The first drill's source_weakness from FAKE_CHECKS[0] (unsupported)
        # matches the dedup logic — so claim_precision should not be re-inserted
        existing_sw = (
            "Unsupported claim — uploaded card does not establish: "
            "Lower taxes increase investment"
        )
        existing = [{"source_weakness": existing_sw, "order": 1}]
        inserted: list[dict] = []
        sb = MagicMock()
        sb.table = _make_table_fn(existing_drill_rows=existing, inserted_collector=inserted)
        mock_sb.return_value = sb

        resp = client.post(f"/speeches/{SPEECH_ID}/evidence-drills?user_id={USER_ID}")
        assert resp.status_code == 201
        skill_targets = [d.get("skill_target") for d in inserted]
        assert "claim_precision" not in skill_targets
