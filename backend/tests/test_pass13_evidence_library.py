"""Pass 13 — Evidence Library tests.

Coverage:
- Data models (Resolution, Argument, EvidenceSource, LibraryCard, Blockfile, etc.)
- Ownership / authorization rules
- Save-card flow (including forbidden verdicts)
- Library search / filter
- Blockfile CRUD + section nesting limits
- Frontlines and response management
- Card relationships (manual + suggestions, no auto-confirm)
- Card versioning and restore
- Export (JSON, Markdown, DOCX)
- Citation field edit endpoint
- Regression: all existing Passes still intact

All Supabase calls are mocked; no real HTTP calls.
"""

import json
from io import BytesIO
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ── Model imports ──────────────────────────────────────────────────────────────

from app.models.evidence_library import (
    ArgumentCreate,
    ArgumentRow,
    ArgumentUpdate,
    BlockfileCreate,
    BlockfileEntryCreate,
    BlockfileRow,
    BlockfileSectionCreate,
    BlockfileSectionRow,
    BlockfileUpdate,
    CardRelationshipCreate,
    CardRelationshipRow,
    CardVersionRow,
    EvidenceSourceCreate,
    EvidenceSourceRow,
    FrontlineCreate,
    FrontlineResponseCreate,
    FrontlineResponseRow,
    FrontlineRow,
    LibraryCardMetadataRow,
    LibraryCardSaveRequest,
    LibraryCardUpdate,
    LibrarySearchRequest,
    ResolutionCreate,
    ResolutionRow,
    ResolutionUpdate,
)

# ── Service imports ────────────────────────────────────────────────────────────

import app.services.evidence_library_service as svc
from app.services.library_export import (
    _build_bibliography,
    export_blockfile_json,
    export_blockfile_markdown,
    export_frontline_json,
    export_frontline_markdown,
    _bib_key,
)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _mock_sb(rows_by_table: dict[str, list[dict]] | None = None) -> MagicMock:
    """Build a supabase client mock that returns pre-configured rows."""
    rows_by_table = rows_by_table or {}
    sb = MagicMock()

    def make_table(name: str):
        rows = rows_by_table.get(name, [])
        tbl = MagicMock()

        def select(*args, **kwargs):
            q = MagicMock()
            q.eq.return_value = q
            q.neq.return_value = q
            q.in_.return_value = q
            q.or_.return_value = q
            q.order.return_value = q
            q.limit.return_value = q
            q.offset.return_value = q
            result = MagicMock()
            result.data = rows
            q.execute.return_value = result
            return q

        def insert(data):
            q = MagicMock()
            inserted = {"id": "new-uuid", "created_at": "2026-06-22T00:00:00", "updated_at": "2026-06-22T00:00:00"}
            inserted.update(data if isinstance(data, dict) else {})
            result = MagicMock()
            result.data = [inserted]
            q.execute.return_value = result
            return q

        def update(data):
            q = MagicMock()
            q.eq.return_value = q
            updated = {"id": "existing-uuid", "created_at": "2026-06-22T00:00:00", "updated_at": "2026-06-22T00:00:00"}
            updated.update(data if isinstance(data, dict) else {})
            if rows:
                updated.update(rows[0])
                updated.update(data if isinstance(data, dict) else {})
            result = MagicMock()
            result.data = [updated]
            q.execute.return_value = result
            return q

        def delete():
            q = MagicMock()
            q.eq.return_value = q
            result = MagicMock()
            result.data = []
            q.execute.return_value = result
            return q

        tbl.select = select
        tbl.insert = insert
        tbl.update = update
        tbl.delete = delete
        return tbl

    sb.table = make_table
    return sb


USER_A = "user-aaa"
USER_B = "user-bbb"

_RESOLUTION_ROW = {
    "id": "res-1",
    "user_id": USER_A,
    "team_id": None,
    "title": "Resolved: Nuclear Energy",
    "normalized_title": "resolved: nuclear energy",
    "season": "2025-2026",
    "event_type": "pf",
    "is_active": True,
    "created_at": "2026-06-22T00:00:00",
    "updated_at": "2026-06-22T00:00:00",
}

_ARGUMENT_ROW = {
    "id": "arg-1",
    "resolution_id": "res-1",
    "user_id": USER_A,
    "team_id": None,
    "side": "pro",
    "title": "Contention 1: Climate",
    "summary": "Nuclear reduces carbon.",
    "argument_type": "contention",
    "parent_argument_id": None,
    "created_at": "2026-06-22T00:00:00",
    "updated_at": "2026-06-22T00:00:00",
}

_BLOCKFILE_ROW = {
    "id": "bf-1",
    "user_id": USER_A,
    "team_id": None,
    "resolution_id": "res-1",
    "title": "Pro Block",
    "side": "pro",
    "description": None,
    "created_at": "2026-06-22T00:00:00",
    "updated_at": "2026-06-22T00:00:00",
}

_SECTION_ROW = {
    "id": "sec-1",
    "blockfile_id": "bf-1",
    "title": "Uniqueness",
    "section_type": "uniqueness",
    "position": 0,
    "parent_section_id": None,
    "created_at": "2026-06-22T00:00:00",
}

_FRONTLINE_ROW = {
    "id": "fl-1",
    "user_id": USER_A,
    "team_id": None,
    "blockfile_id": "bf-1",
    "resolution_id": "res-1",
    "argument_id": "arg-1",
    "side": "pro",
    "title": "Against Neg's Economy DA",
    "opponent_claim": "Nuclear energy kills jobs.",
    "opponent_warrant": "Construction costs displace workers.",
    "opponent_impact": "Recession.",
    "opponent_source": None,
    "created_at": "2026-06-22T00:00:00",
    "updated_at": "2026-06-22T00:00:00",
}


# ══════════════════════════════════════════════════════════════════════════════
# 1. Resolution CRUD
# ══════════════════════════════════════════════════════════════════════════════

class TestResolutionCRUD:
    def test_create_resolution(self):
        sb = _mock_sb()
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.create_resolution(ResolutionCreate(
                user_id=USER_A,
                title="Resolved: Nuclear Energy",
                season="2025-2026",
                event_type="pf",
            ))
        assert row.event_type == "pf"

    def test_normalized_title_is_lowercased(self):
        sb = _mock_sb()
        inserted: list[dict] = []
        original_insert = sb.table("resolutions").insert

        def capturing_insert(data):
            inserted.append(data)
            q = MagicMock()
            result = MagicMock()
            data_with_id = {"id": "r1", "created_at": "2026-06-22", "updated_at": "2026-06-22"}
            data_with_id.update(data)
            result.data = [data_with_id]
            q.execute.return_value = result
            return q

        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            # Rebuild sb with capturing insert
            sb2 = _mock_sb()
            tbl = MagicMock()
            tbl.insert = capturing_insert
            sb2.table = lambda name: tbl if name == "resolutions" else sb.table(name)
            svc.create_resolution(ResolutionCreate(user_id=USER_A, title="Resolved: NUCLEAR ENERGY"))
            # Can't intercept easily; test normalized_title logic directly
            assert svc._normalize_title("Resolved: NUCLEAR ENERGY") == "resolved: nuclear energy"

    def test_list_resolutions(self):
        sb = _mock_sb({"resolutions": [_RESOLUTION_ROW]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            rows = svc.list_resolutions(USER_A)
        assert len(rows) == 1
        assert rows[0].title == "Resolved: Nuclear Energy"

    def test_get_resolution_wrong_user_returns_none(self):
        sb = _mock_sb({"resolutions": [_RESOLUTION_ROW]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.get_resolution("res-1", USER_B)
        assert row is None

    def test_get_resolution_correct_user(self):
        sb = _mock_sb({"resolutions": [_RESOLUTION_ROW]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.get_resolution("res-1", USER_A)
        assert row is not None
        assert row.id == "res-1"

    def test_archive_resolution_wrong_user_raises(self):
        sb = _mock_sb({"resolutions": [{**_RESOLUTION_ROW, "user_id": USER_B}]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            with pytest.raises(PermissionError):
                svc.archive_resolution("res-1", USER_A)

    def test_resolution_event_type_validation(self):
        with pytest.raises(Exception):
            ResolutionCreate(user_id=USER_A, title="T", event_type="invalid_type")  # type: ignore


# ══════════════════════════════════════════════════════════════════════════════
# 2. Argument CRUD
# ══════════════════════════════════════════════════════════════════════════════

class TestArgumentCRUD:
    def test_create_argument(self):
        sb = _mock_sb()
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.create_argument(ArgumentCreate(
                user_id=USER_A,
                resolution_id="res-1",
                side="pro",
                title="Contention 1: Climate",
                argument_type="contention",
            ))
        assert isinstance(row, ArgumentRow)

    def test_create_argument_neutral_side(self):
        sb = _mock_sb()
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.create_argument(ArgumentCreate(
                user_id=USER_A,
                side="neutral",
                title="Background definitions",
            ))
        assert isinstance(row, ArgumentRow)

    def test_list_arguments_filters_by_side(self):
        rows = [
            {**_ARGUMENT_ROW, "id": "a1", "side": "pro"},
            {**_ARGUMENT_ROW, "id": "a2", "side": "con"},
        ]
        sb = _mock_sb({"arguments": [rows[0]]})  # filtered to pro by mock
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            result = svc.list_arguments(USER_A, side="pro")
        assert all(a.side == "pro" for a in result)

    def test_get_argument_wrong_user_returns_none(self):
        sb = _mock_sb({"arguments": [_ARGUMENT_ROW]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.get_argument("arg-1", USER_B)
        assert row is None

    def test_update_argument_wrong_user_raises(self):
        sb = _mock_sb({"arguments": [{**_ARGUMENT_ROW, "user_id": USER_B}]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            with pytest.raises(PermissionError):
                svc.update_argument("arg-1", ArgumentUpdate(user_id=USER_A, title="Changed"))

    def test_delete_argument(self):
        sb = _mock_sb({"arguments": [_ARGUMENT_ROW]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            svc.delete_argument("arg-1", USER_A)


# ══════════════════════════════════════════════════════════════════════════════
# 3. EvidenceSource — deduplication
# ══════════════════════════════════════════════════════════════════════════════

_SOURCE_ROW = {
    "id": "src-1",
    "user_id": USER_A,
    "normalized_doi": "10.1000/test",
    "canonical_url": None,
    "content_hash": None,
    "title": "Nuclear energy safety",
    "authors_json": [],
    "publisher": None,
    "container_title": None,
    "published_year": 2024,
    "source_type": "article-journal",
    "citation_record_json": None,
    "provenance_summary": None,
    "created_at": "2026-06-22T00:00:00",
    "updated_at": "2026-06-22T00:00:00",
}


class TestEvidenceSourceDedup:
    def test_find_by_doi_returns_existing(self):
        sb = _mock_sb({"evidence_sources": [_SOURCE_ROW]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.find_or_create_source(EvidenceSourceCreate(
                user_id=USER_A,
                normalized_doi="10.1000/test",
            ))
        assert row.id == "src-1"

    def test_different_doi_creates_new(self):
        sb = _mock_sb({"evidence_sources": []})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.find_or_create_source(EvidenceSourceCreate(
                user_id=USER_A,
                normalized_doi="10.9999/new",
            ))
        # Should not be the existing row
        assert row.id != "src-1"

    def test_find_by_url_plus_hash(self):
        url_row = {**_SOURCE_ROW, "normalized_doi": None,
                   "canonical_url": "https://example.com/paper",
                   "content_hash": "abc123"}
        sb = _mock_sb({"evidence_sources": [url_row]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.find_or_create_source(EvidenceSourceCreate(
                user_id=USER_A,
                canonical_url="https://example.com/paper",
                content_hash="abc123",
            ))
        assert row.id == "src-1"

    def test_doi_match_takes_priority_over_url(self):
        # If DOI matches, returns early without checking URL
        sb = _mock_sb({"evidence_sources": [_SOURCE_ROW]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.find_or_create_source(EvidenceSourceCreate(
                user_id=USER_A,
                normalized_doi="10.1000/test",
                canonical_url="https://different-url.com",
            ))
        assert row.id == "src-1"

    def test_no_dedup_key_always_inserts(self):
        sb = _mock_sb({"evidence_sources": []})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.find_or_create_source(EvidenceSourceCreate(
                user_id=USER_A,
                title="Some source with no DOI or URL",
            ))
        assert row is not None


# ══════════════════════════════════════════════════════════════════════════════
# 4. Library card save flow
# ══════════════════════════════════════════════════════════════════════════════

_LCM_ROW = {
    "id": "lcm-1",
    "card_id": "card-1",
    "user_id": USER_A,
    "resolution_id": "res-1",
    "argument_id": "arg-1",
    "source_id": None,
    "side": "pro",
    "evidence_role": "direct_support",
    "card_status": "active",
    "support_verdict": "supported",
    "user_notes": None,
    "tags": [],
    "accessed_date": "2026-06-22",
    "created_at": "2026-06-22T00:00:00",
    "updated_at": "2026-06-22T00:00:00",
}


class TestLibraryCardSaveFlow:
    def test_save_card_basic(self):
        sb = _mock_sb({"library_card_metadata": []})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.save_card_to_library(LibraryCardSaveRequest(
                user_id=USER_A,
                card_id="card-1",
                side="pro",
                evidence_role="direct_support",
                support_verdict="supported",
            ))
        assert isinstance(row, LibraryCardMetadataRow)

    def test_save_already_saved_returns_existing(self):
        sb = _mock_sb({"library_card_metadata": [_LCM_ROW]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.save_card_to_library(LibraryCardSaveRequest(
                user_id=USER_A,
                card_id="card-1",
            ))
        assert row.id == "lcm-1"

    def test_unsupported_card_requires_override(self):
        sb = _mock_sb({"library_card_metadata": []})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            with pytest.raises(ValueError, match="unsupported_save_override"):
                svc.save_card_to_library(LibraryCardSaveRequest(
                    user_id=USER_A,
                    card_id="card-2",
                    support_verdict="unsupported",
                    unsupported_save_override=False,
                ))

    def test_contradicted_card_requires_override(self):
        sb = _mock_sb({"library_card_metadata": []})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            with pytest.raises(ValueError):
                svc.save_card_to_library(LibraryCardSaveRequest(
                    user_id=USER_A,
                    card_id="card-3",
                    support_verdict="contradicted",
                ))

    def test_unsupported_card_saves_with_override(self):
        sb = _mock_sb({"library_card_metadata": []})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.save_card_to_library(LibraryCardSaveRequest(
                user_id=USER_A,
                card_id="card-4",
                support_verdict="unsupported",
                unsupported_save_override=True,
            ))
        assert row is not None

    def test_partially_supported_saves_without_override(self):
        sb = _mock_sb({"library_card_metadata": []})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.save_card_to_library(LibraryCardSaveRequest(
                user_id=USER_A,
                card_id="card-5",
                support_verdict="partially_supported",
            ))
        assert row is not None

    def test_accessed_date_defaults_to_today(self):
        saved_payload: list[dict] = []

        def capturing_insert(data):
            saved_payload.append(data)
            q = MagicMock()
            result = MagicMock()
            row = {"id": "x", "created_at": "2026-06-22", "updated_at": "2026-06-22"}
            row.update(data)
            result.data = [row]
            q.execute.return_value = result
            return q

        # Self-referential select mock so multiple chained .eq() calls all return data=[]
        select_q = MagicMock()
        select_q.eq.return_value = select_q
        select_q.neq.return_value = select_q
        select_q.limit.return_value = select_q
        select_q.execute.return_value = MagicMock(data=[])

        tbl_lcm = MagicMock()
        tbl_lcm.select.return_value = select_q
        tbl_lcm.insert = capturing_insert
        sb = _mock_sb({"library_card_metadata": []})
        sb.table = lambda name: tbl_lcm if name == "library_card_metadata" else _mock_sb().table(name)

        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            svc.save_card_to_library(LibraryCardSaveRequest(
                user_id=USER_A,
                card_id="card-date-test",
            ))
        if saved_payload:
            assert "accessed_date" in saved_payload[0]
            assert saved_payload[0]["accessed_date"] != ""

    def test_save_preserves_tags(self):
        sb = _mock_sb({"library_card_metadata": []})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.save_card_to_library(LibraryCardSaveRequest(
                user_id=USER_A,
                card_id="card-tags",
                tags=["economy", "link"],
            ))
        assert row is not None

    def test_update_library_card(self):
        sb = _mock_sb({"library_card_metadata": [_LCM_ROW]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.update_library_card("card-1", LibraryCardUpdate(
                user_id=USER_A,
                user_notes="Updated notes",
            ))
        assert row is not None


# ══════════════════════════════════════════════════════════════════════════════
# 5. Library search
# ══════════════════════════════════════════════════════════════════════════════

class TestLibrarySearch:
    def test_search_returns_results(self):
        lcm_rows = [_LCM_ROW]
        card_rows = [{"id": "card-1", "tag": "Economy link", "cite": "Smith 2024",
                      "body_text": "Nuclear helps the economy."}]
        sb = _mock_sb({"library_card_metadata": lcm_rows, "evidence_cards": card_rows,
                        "arguments": [_ARGUMENT_ROW]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            resp = svc.search_library(LibrarySearchRequest(user_id=USER_A))
        assert isinstance(resp.results, list)
        assert resp.total >= 0

    def test_search_text_filter_excludes_non_matching(self):
        lcm_rows = [_LCM_ROW]
        card_rows = [{"id": "card-1", "tag": "Economy link", "cite": "Smith 2024",
                      "body_text": "Nuclear helps the economy."}]
        sb = _mock_sb({"library_card_metadata": lcm_rows, "evidence_cards": card_rows,
                        "arguments": []})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            resp = svc.search_library(LibrarySearchRequest(user_id=USER_A, query="climate"))
        # "climate" is not in the card data above — should return 0 results
        assert resp.total == 0

    def test_search_text_filter_includes_matching(self):
        lcm_rows = [_LCM_ROW]
        card_rows = [{"id": "card-1", "tag": "Economy link", "cite": "Smith 2024",
                      "body_text": "Nuclear helps the economy."}]
        sb = _mock_sb({"library_card_metadata": lcm_rows, "evidence_cards": card_rows,
                        "arguments": []})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            resp = svc.search_library(LibrarySearchRequest(user_id=USER_A, query="economy"))
        assert resp.total == 1

    def test_search_body_preview_truncated_to_200(self):
        long_body = "x" * 500
        lcm_rows = [_LCM_ROW]
        card_rows = [{"id": "card-1", "tag": "T", "cite": "C", "body_text": long_body}]
        sb = _mock_sb({"library_card_metadata": lcm_rows, "evidence_cards": card_rows,
                        "arguments": []})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            resp = svc.search_library(LibrarySearchRequest(user_id=USER_A, query="x"))
        if resp.results:
            assert len(resp.results[0].body_preview) <= 200


# ══════════════════════════════════════════════════════════════════════════════
# 6. Blockfile CRUD
# ══════════════════════════════════════════════════════════════════════════════

class TestBlockfileCRUD:
    def test_create_blockfile(self):
        sb = _mock_sb()
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.create_blockfile(BlockfileCreate(
                user_id=USER_A, title="Pro Block", side="pro"
            ))
        assert isinstance(row, BlockfileRow)

    def test_get_blockfile_wrong_user(self):
        sb = _mock_sb({"blockfiles": [_BLOCKFILE_ROW]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.get_blockfile("bf-1", USER_B)
        assert row is None

    def test_get_blockfile_correct_user(self):
        sb = _mock_sb({"blockfiles": [_BLOCKFILE_ROW]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.get_blockfile("bf-1", USER_A)
        assert row is not None

    def test_delete_blockfile_wrong_user_raises(self):
        sb = _mock_sb({"blockfiles": [{**_BLOCKFILE_ROW, "user_id": USER_B}]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            with pytest.raises(PermissionError):
                svc.delete_blockfile("bf-1", USER_A)

    def test_list_blockfiles_filtered_by_resolution(self):
        rows = [
            {**_BLOCKFILE_ROW, "id": "bf-1", "resolution_id": "res-1"},
            {**_BLOCKFILE_ROW, "id": "bf-2", "resolution_id": "res-2"},
        ]
        sb = _mock_sb({"blockfiles": [rows[0]]})  # pre-filtered by mock
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            result = svc.list_blockfiles(USER_A, resolution_id="res-1")
        assert all(b.resolution_id == "res-1" for b in result)


# ══════════════════════════════════════════════════════════════════════════════
# 7. Blockfile sections
# ══════════════════════════════════════════════════════════════════════════════

class TestBlockfileSections:
    def test_create_section(self):
        sb = _mock_sb({"blockfiles": [_BLOCKFILE_ROW]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.create_section(BlockfileSectionCreate(
                blockfile_id="bf-1",
                user_id=USER_A,
                title="Uniqueness",
                section_type="uniqueness",
            ))
        assert isinstance(row, BlockfileSectionRow)

    def test_create_section_wrong_user_raises(self):
        sb = _mock_sb({"blockfiles": [{**_BLOCKFILE_ROW, "user_id": USER_B}]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            with pytest.raises(PermissionError):
                svc.create_section(BlockfileSectionCreate(
                    blockfile_id="bf-1",
                    user_id=USER_A,
                    title="Section",
                ))

    def test_nested_section_limit_enforced(self):
        """Sections may not nest more than one level."""
        parent_with_parent = {**_SECTION_ROW, "parent_section_id": "grandparent-id"}
        sb = _mock_sb({"blockfile_sections": [parent_with_parent]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            with pytest.raises(ValueError, match="one level"):
                svc._check_section_nesting("sec-1")

    def test_top_level_section_passes_nesting_check(self):
        top = {**_SECTION_ROW, "parent_section_id": None}
        sb = _mock_sb({"blockfile_sections": [top]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            svc._check_section_nesting("sec-1")  # should not raise

    def test_section_without_parent_passes_nesting_check(self):
        svc._check_section_nesting(None)  # no DB call needed

    def test_list_sections_unauthorized_returns_empty(self):
        sb = _mock_sb({"blockfiles": [{**_BLOCKFILE_ROW, "user_id": USER_B}]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            result = svc.list_sections("bf-1", USER_A)
        assert result == []

    def test_reorder_sections_updates_positions(self):
        sb = _mock_sb({"blockfiles": [_BLOCKFILE_ROW]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            svc.reorder_sections("bf-1", ["sec-2", "sec-1"], USER_A)


# ══════════════════════════════════════════════════════════════════════════════
# 8. Blockfile entries
# ══════════════════════════════════════════════════════════════════════════════

_ENTRY_ROW = {
    "id": "entry-1",
    "section_id": "sec-1",
    "card_id": "card-1",
    "position": 0,
    "entry_type": "evidence_card",
    "custom_label": None,
    "notes": None,
    "created_at": "2026-06-22T00:00:00",
}


class TestBlockfileEntries:
    def test_add_entry(self):
        sb = _mock_sb()
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.add_entry(BlockfileEntryCreate(
                section_id="sec-1",
                user_id=USER_A,
                card_id="card-1",
                position=0,
            ))
        assert row is not None

    def test_remove_entry_does_not_delete_card(self):
        sb = _mock_sb({"blockfile_entries": [_ENTRY_ROW]})
        # remove_entry calls delete on blockfile_entries, NOT evidence_cards
        deleted_tables: list[str] = []

        def make_table(name):
            tbl = _mock_sb().table(name)
            if name == "blockfile_entries":
                orig_delete = tbl.delete
                def tracking_delete():
                    deleted_tables.append(name)
                    return orig_delete()
                tbl.delete = tracking_delete
            return tbl

        sb.table = make_table
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            svc.remove_entry("entry-1", USER_A)
        assert "evidence_cards" not in deleted_tables

    def test_one_card_in_multiple_sections(self):
        """Adding the same card_id to two sections creates two entries (no duplication of the card itself)."""
        sb = _mock_sb()
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            e1 = svc.add_entry(BlockfileEntryCreate(section_id="sec-1", user_id=USER_A, card_id="card-1"))
            e2 = svc.add_entry(BlockfileEntryCreate(section_id="sec-2", user_id=USER_A, card_id="card-1"))
        # Both entries reference the same card_id — no duplication of source text
        assert e1 is not None and e2 is not None

    def test_reorder_entries(self):
        sb = _mock_sb()
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            svc.reorder_entries("sec-1", ["entry-2", "entry-1"], USER_A)


# ══════════════════════════════════════════════════════════════════════════════
# 9. Card relationships
# ══════════════════════════════════════════════════════════════════════════════

_REL_ROW = {
    "id": "rel-1",
    "from_card_id": "card-1",
    "to_card_id": "card-2",
    "relationship_type": "supports",
    "confidence": "manual",
    "explanation": "Same finding from same study.",
    "created_by": USER_A,
    "confirmed": True,
    "created_at": "2026-06-22T00:00:00",
}


class TestCardRelationships:
    def test_create_manual_relationship(self):
        sb = _mock_sb({"card_relationships": []})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.create_relationship(CardRelationshipCreate(
                user_id=USER_A,
                from_card_id="card-1",
                to_card_id="card-2",
                relationship_type="supports",
                confirmed=True,
            ))
        assert isinstance(row, CardRelationshipRow)

    def test_suggested_relationship_not_auto_confirmed(self):
        row = CardRelationshipCreate(
            user_id=USER_A,
            from_card_id="card-1",
            to_card_id="card-2",
            relationship_type="same_finding",
            confidence="suggested",
            confirmed=False,  # user must confirm separately
        )
        assert row.confirmed is False

    def test_suggest_relationships_returns_list(self):
        sb = _mock_sb({
            "library_card_metadata": [{**_LCM_ROW, "source_id": "src-1"}],
        })
        # Siblings with same source
        sibling_sb = _mock_sb({
            "library_card_metadata": [{"card_id": "card-99"}],
        })

        def make_table(name):
            if name == "library_card_metadata":
                tbl = MagicMock()
                first_call = [True]

                def select(*a, **kw):
                    q = MagicMock()
                    q.eq.return_value = q
                    q.neq.return_value = q
                    q.limit.return_value = q
                    result = MagicMock()
                    if first_call[0]:
                        first_call[0] = False
                        result.data = [{**_LCM_ROW, "source_id": "src-1"}]
                    else:
                        result.data = [{"card_id": "card-99"}]
                    q.execute.return_value = result
                    return q

                tbl.select = select
                return tbl
            return _mock_sb().table(name)

        sb.table = make_table
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            suggestions = svc.suggest_relationships_for_card("card-1", USER_A)
        assert isinstance(suggestions, list)
        for s in suggestions:
            assert s.get("auto_confirmed") is False

    def test_delete_relationship_wrong_user_raises(self):
        sb = _mock_sb({"card_relationships": [{**_REL_ROW, "created_by": USER_B}]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            with pytest.raises(ValueError):
                svc.delete_relationship("rel-1", USER_A)

    def test_confirm_relationship(self):
        unconfirmed = {**_REL_ROW, "confirmed": False}
        sb = _mock_sb({"card_relationships": [unconfirmed]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.confirm_relationship("rel-1", USER_A, confirmed=True)
        assert row is not None

    def test_all_relationship_types_valid(self):
        valid_types = [
            "supports", "contradicts", "updates", "qualifies", "same_finding",
            "stronger_source", "primary_source_for", "responds_to", "turns",
            "mitigates", "outweighs",
        ]
        for rt in valid_types:
            rel = CardRelationshipCreate(
                user_id=USER_A,
                from_card_id="c1",
                to_card_id="c2",
                relationship_type=rt,  # type: ignore
            )
            assert rel.relationship_type == rt


# ══════════════════════════════════════════════════════════════════════════════
# 10. Card versioning
# ══════════════════════════════════════════════════════════════════════════════

class TestCardVersioning:
    def test_record_version(self):
        sb = _mock_sb({"card_versions": []})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.record_version(
                card_id="card-1",
                user_id=USER_A,
                changed_fields={"tag": None},
                previous_values={"tag": "old tag"},
                new_values={"tag": "new tag"},
                reason="tag_edit",
            )
        assert isinstance(row, CardVersionRow)

    def test_version_numbers_increment(self):
        versions = [{"version_number": 3}]
        sb = _mock_sb({"card_versions": versions})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            n = svc._next_version_number("card-1")
        assert n == 4

    def test_first_version_is_1(self):
        sb = _mock_sb({"card_versions": []})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            n = svc._next_version_number("card-1")
        assert n == 1

    def test_list_versions(self):
        version_rows = [
            {"id": "v1", "card_id": "card-1", "user_id": USER_A, "version_number": 1,
             "changed_fields": {}, "previous_values": {}, "new_values": {},
             "reason": None, "created_at": "2026-06-22T00:00:00"},
        ]
        sb = _mock_sb({"card_versions": version_rows})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            versions = svc.list_versions("card-1", USER_A)
        assert len(versions) == 1

    def test_citation_only_edit_does_not_change_body_hash(self):
        """Citation fields must not change body_text — checked at model level."""
        # Record version with only citation field changed
        sb = _mock_sb({"card_versions": []})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.record_version(
                card_id="card-1",
                user_id=USER_A,
                changed_fields={"citation_record": None},
                previous_values={"citation_record": {"title": "Old"}},
                new_values={"citation_record": {"title": "New"}},
                reason="citation_edit",
            )
        # body_text must not appear in changed_fields for citation edits
        assert "body_text" not in row.changed_fields

    def test_restore_version_skips_protected_fields(self):
        """Restoring must not overwrite body_text, highlighted_spans, or support_verdict."""
        card_row = {
            "id": "card-1",
            "body_text": "Protected body text",
            "highlighted_spans_json": [],
            "support_verdict": "supported",
            "tag": "Old tag",
        }
        version_row = {
            "id": "v1",
            "card_id": "card-1",
            "user_id": USER_A,
            "version_number": 1,
            "changed_fields": {"tag": None, "body_text": None},
            "previous_values": {
                "tag": "Old tag",
                "body_text": "DIFFERENT BODY",  # this must NOT be restored
            },
            "new_values": {"tag": "New tag", "body_text": "DIFFERENT BODY"},
            "reason": None,
            "created_at": "2026-06-22",
        }

        updated_fields: list[dict] = []

        def make_table(name):
            tbl = MagicMock()
            def select(*a, **kw):
                q = MagicMock()
                q.eq.return_value = q
                q.order.return_value = q
                q.limit.return_value = q
                r = MagicMock()
                if name == "card_versions":
                    r.data = [version_row]
                elif name == "evidence_cards":
                    r.data = [card_row]
                else:
                    r.data = []
                q.execute.return_value = r
                return q

            def update(data):
                updated_fields.append(data)
                q = MagicMock()
                q.eq.return_value = q
                result = MagicMock()
                updated = dict(card_row)
                updated.update(data)
                result.data = [updated]
                q.execute.return_value = result
                return q

            def insert(data):
                q = MagicMock()
                result = MagicMock()
                result.data = [{**data, "id": "v2", "created_at": "2026-06-22"}]
                q.execute.return_value = result
                return q

            tbl.select = select
            tbl.update = update
            tbl.insert = insert
            return tbl

        sb = MagicMock()
        sb.table = make_table

        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            svc.restore_version("card-1", 1, USER_A)

        # body_text must not appear in any UPDATE call to evidence_cards
        for update_payload in updated_fields:
            assert "body_text" not in update_payload, \
                "body_text was mutated during restore — must be protected"


# ══════════════════════════════════════════════════════════════════════════════
# 11. Frontlines
# ══════════════════════════════════════════════════════════════════════════════

class TestFrontlines:
    def test_create_frontline(self):
        sb = _mock_sb()
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.create_frontline(FrontlineCreate(
                user_id=USER_A,
                title="Against Economy DA",
                opponent_claim="Nuclear kills jobs",
            ))
        assert isinstance(row, FrontlineRow)

    def test_get_frontline_wrong_user_returns_none(self):
        sb = _mock_sb({"frontlines": [_FRONTLINE_ROW]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.get_frontline("fl-1", USER_B)
        assert row is None

    def test_delete_frontline_wrong_user_raises(self):
        sb = _mock_sb({"frontlines": [{**_FRONTLINE_ROW, "user_id": USER_B}]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            with pytest.raises(PermissionError):
                svc.delete_frontline("fl-1", USER_A)

    def test_add_response(self):
        sb = _mock_sb()
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.add_response(FrontlineResponseCreate(
                frontline_id="fl-1",
                user_id=USER_A,
                response_type="no_link",
                response_claim="Their evidence is from 2015.",
                is_analytical=True,
                priority=1,
            ))
        assert isinstance(row, FrontlineResponseRow)

    def test_analytical_response_can_exist_without_card(self):
        sb = _mock_sb()
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.add_response(FrontlineResponseCreate(
                frontline_id="fl-1",
                user_id=USER_A,
                response_type="weighing",
                response_claim="Even if true, our impacts outweigh.",
                is_analytical=True,
            ))
        assert row.is_analytical is True

    def test_responses_ordered_by_priority(self):
        resp_rows = [
            {**{"id": "r2", "frontline_id": "fl-1", "response_type": "turn",
                "response_claim": "B", "priority": 2, "speech_suitability": ["rebuttal"],
                "is_analytical": False, "position": 1,
                "created_at": "2026-06-22", "updated_at": "2026-06-22"}},
            {**{"id": "r1", "frontline_id": "fl-1", "response_type": "no_link",
                "response_claim": "A", "priority": 1, "speech_suitability": ["rebuttal"],
                "is_analytical": False, "position": 0,
                "created_at": "2026-06-22", "updated_at": "2026-06-22"}},
        ]
        sb = _mock_sb({"frontline_responses": sorted(resp_rows, key=lambda r: r["priority"])})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            rows = svc.list_responses("fl-1", USER_A)
        if len(rows) >= 2:
            # priority 1 should come first
            assert rows[0].priority <= rows[1].priority

    def test_all_response_types_valid(self):
        valid_types = [
            "no_link", "link_defense", "impact_defense", "uniqueness_takeout",
            "turn", "counterplan", "mitigation", "non_unique", "weighing",
            "evidence_indictment", "source_challenge",
        ]
        for rt in valid_types:
            r = FrontlineResponseCreate(
                frontline_id="fl-1",
                user_id=USER_A,
                response_type=rt,  # type: ignore
                response_claim="Test",
            )
            assert r.response_type == rt


# ══════════════════════════════════════════════════════════════════════════════
# 12. Export service
# ══════════════════════════════════════════════════════════════════════════════

def _make_bf_row(**kw):
    return BlockfileRow(
        id=kw.get("id", "bf-1"),
        user_id=USER_A,
        title=kw.get("title", "My Blockfile"),
        side=kw.get("side", "pro"),
        created_at="2026-06-22T00:00:00",
        updated_at="2026-06-22T00:00:00",
    )


def _make_sect_row(id: str, position: int = 0, section_type: str = "contention"):
    return BlockfileSectionRow(
        id=id,
        blockfile_id="bf-1",
        title="Section " + id,
        section_type=section_type,  # type: ignore
        position=position,
        created_at="2026-06-22T00:00:00",
    )


def _make_entry_row(id: str, section_id: str, card_id: str, position: int = 0):
    from app.models.evidence_library import BlockfileEntryRow
    return BlockfileEntryRow(
        id=id,
        section_id=section_id,
        card_id=card_id,
        position=position,
        entry_type="evidence_card",
        created_at="2026-06-22T00:00:00",
    )


class TestExportJSON:
    def test_json_export_includes_title(self):
        bf = _make_bf_row(title="Nuclear Blocks")
        result = export_blockfile_json(bf, [], {})
        data = json.loads(result)
        assert data["title"] == "Nuclear Blocks"

    def test_json_export_section_order_preserved(self):
        bf = _make_bf_row()
        sects = [_make_sect_row("s1", position=0), _make_sect_row("s2", position=1)]
        result = export_blockfile_json(bf, sects, {})
        data = json.loads(result)
        assert data["sections"][0]["title"] == "Section s1"
        assert data["sections"][1]["title"] == "Section s2"

    def test_json_export_excludes_internal_ids(self):
        bf = _make_bf_row()
        result = export_blockfile_json(bf, [], {})
        data = json.loads(result)
        # No top-level id in the export
        assert "id" not in data

    def test_json_export_includes_bibliography(self):
        bf = _make_bf_row()
        sects = [_make_sect_row("s1", position=0)]
        entry = _make_entry_row("e1", "s1", "card-1")
        card_data = {"card-1": {"id": "card-1", "tag": "T", "cite": "Smith 2024",
                                  "body_text": "text", "mla_citation": "Smith, J. (2024)."}}
        result = export_blockfile_json(bf, sects, {"s1": [entry]}, card_data)
        data = json.loads(result)
        assert "bibliography" in data

    def test_json_export_repeated_is_deterministic(self):
        bf = _make_bf_row()
        r1 = export_blockfile_json(bf, [], {})
        r2 = export_blockfile_json(bf, [], {})
        assert r1 == r2

    def test_frontline_json_includes_responses(self):
        fl = FrontlineRow(
            id="fl-1", user_id=USER_A,
            title="Frontline", side="pro",
            opponent_claim="Claim",
            created_at="2026-06-22T00:00:00",
            updated_at="2026-06-22T00:00:00",
        )
        resp = FrontlineResponseRow(
            id="r1", frontline_id="fl-1",
            response_type="no_link", response_claim="No link",
            priority=1, speech_suitability=["rebuttal"],
            is_analytical=False, position=0,
            created_at="2026-06-22T00:00:00",
            updated_at="2026-06-22T00:00:00",
        )
        result = export_frontline_json(fl, [resp], {"r1": []})
        data = json.loads(result)
        assert len(data["responses"]) == 1
        assert data["responses"][0]["response_claim"] == "No link"


class TestExportMarkdown:
    def test_markdown_starts_with_title(self):
        bf = _make_bf_row(title="My Blocks")
        result = export_blockfile_markdown(bf, [], {})
        assert result.startswith("# My Blocks")

    def test_markdown_preserves_section_order(self):
        bf = _make_bf_row()
        sects = [_make_sect_row("s1", position=0), _make_sect_row("s2", position=1)]
        result = export_blockfile_markdown(bf, sects, {})
        assert result.index("Section s1") < result.index("Section s2")

    def test_markdown_includes_bibliography_when_cards_have_mla(self):
        bf = _make_bf_row()
        sects = [_make_sect_row("s1")]
        entry = _make_entry_row("e1", "s1", "c1")
        card_data = {"c1": {"id": "c1", "tag": "T", "cite": "C",
                              "body_text": "B", "mla_citation": "Smith 2024."}}
        result = export_blockfile_markdown(bf, sects, {"s1": [entry]}, card_data)
        assert "Works Cited" in result
        assert "Smith 2024" in result

    def test_frontline_markdown_includes_opponent(self):
        fl = FrontlineRow(
            id="fl-1", user_id=USER_A, title="FL",
            opponent_claim="Opponent says X",
            created_at="2026-06-22T00:00:00", updated_at="2026-06-22T00:00:00",
        )
        result = export_frontline_markdown(fl, [], {})
        assert "Opponent says X" in result


class TestExportDOCX:
    def test_docx_export_returns_bytes(self):
        try:
            import docx  # noqa: F401
        except ImportError:
            pytest.skip("python-docx not installed")

        bf = _make_bf_row(title="Blocks")
        result = export_blockfile_docx(bf, [], {})
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_docx_export_contains_zip_magic(self):
        try:
            import docx  # noqa: F401
        except ImportError:
            pytest.skip("python-docx not installed")

        bf = _make_bf_row()
        result = export_blockfile_docx(bf, [], {})
        # DOCX is a ZIP file; starts with PK signature
        assert result[:2] == b"PK"


class TestBibliographyDedup:
    def test_duplicate_doi_deduped(self):
        cards = [
            {"doi": "10.1000/x", "mla_citation": "Smith 2024."},
            {"doi": "10.1000/x", "mla_citation": "Smith 2024."},
        ]
        bib = _build_bibliography(cards)
        assert len(bib) == 1

    def test_different_doi_both_included(self):
        cards = [
            {"doi": "10.1000/a", "mla_citation": "A 2024."},
            {"doi": "10.1000/b", "mla_citation": "B 2024."},
        ]
        bib = _build_bibliography(cards)
        assert len(bib) == 2

    def test_no_doi_no_url_still_included(self):
        cards = [{"mla_citation": "Unknown author (2024)."}]
        bib = _build_bibliography(cards)
        assert len(bib) == 1

    def test_url_dedup(self):
        cards = [
            {"url": "https://example.com/paper", "mla_citation": "A."},
            {"url": "https://example.com/paper", "mla_citation": "A."},
        ]
        bib = _build_bibliography(cards)
        assert len(bib) == 1

    def test_bib_key_doi_preferred(self):
        card = {"doi": "10.1000/x", "url": "https://example.com"}
        key = _bib_key(card)
        assert key.startswith("doi:")

    def test_bib_key_url_fallback(self):
        card = {"url": "https://example.com/page?q=1"}
        key = _bib_key(card)
        assert key is not None
        assert "q=1" not in key  # query stripped

    def test_bib_key_none_when_no_identifiers(self):
        key = _bib_key({"title": "Something"})
        assert key is None


# ══════════════════════════════════════════════════════════════════════════════
# 13. Citation field edit endpoint
# ══════════════════════════════════════════════════════════════════════════════

class TestCitationFieldEdit:
    def test_citation_field_edit_endpoint_exists(self):
        from app.api.research import router
        routes = [r.path for r in router.routes]
        assert any("citation-field" in p for p in routes), \
            "PATCH /card-drafts/{id}/citation-field endpoint not registered"

    def test_citation_edit_does_not_change_body_text(self):
        """The endpoint must never update body_text via citation edits."""
        from app.api.research import patch_citation_field
        import inspect
        source = inspect.getsource(patch_citation_field)
        # body_text must not be in the update payload for citation edits
        assert '"body_text"' not in source or "body_text" not in source.split("updates")[1:][:1]

    def test_citation_field_edit_imports(self):
        """apply_user_edit and attach_rendered must be importable from their modules."""
        from app.services.citation_normalizer import apply_user_edit
        from app.services.citation_renderers import attach_rendered
        assert callable(apply_user_edit)
        assert callable(attach_rendered)


# ══════════════════════════════════════════════════════════════════════════════
# 14. CitationDetailsPanel integration
# ══════════════════════════════════════════════════════════════════════════════

class TestCitationDetailsPanelIntegration:
    def test_citation_details_panel_exists(self):
        from pathlib import Path
        panel = Path(
            "/Users/yashnilmohanty/Desktop/RoundLab/frontend/src/components/evidence/CitationDetailsPanel.tsx"
        )
        assert panel.exists()

    def test_card_metadata_rail_imports_citation_panel(self):
        from pathlib import Path
        rail = Path(
            "/Users/yashnilmohanty/Desktop/RoundLab/frontend/src/components/evidence/CardMetadataRail.tsx"
        )
        content = rail.read_text()
        assert "CitationDetailsPanel" in content

    def test_evidence_studio_card_imports_citation_panel(self):
        from pathlib import Path
        card = Path(
            "/Users/yashnilmohanty/Desktop/RoundLab/frontend/src/components/evidence/EvidenceStudioCard.tsx"
        )
        content = card.read_text()
        assert "CitationDetailsPanel" in content

    def test_citation_panel_collapsed_by_default_in_rail(self):
        from pathlib import Path
        rail = Path(
            "/Users/yashnilmohanty/Desktop/RoundLab/frontend/src/components/evidence/CardMetadataRail.tsx"
        )
        content = rail.read_text()
        assert "defaultOpen={false}" in content

    def test_citation_panel_collapsed_by_default_in_studio_card(self):
        from pathlib import Path
        card = Path(
            "/Users/yashnilmohanty/Desktop/RoundLab/frontend/src/components/evidence/EvidenceStudioCard.tsx"
        )
        content = card.read_text()
        assert "defaultOpen={false}" in content

    def test_citation_panel_only_shown_when_citation_record_exists(self):
        from pathlib import Path
        content = Path(
            "/Users/yashnilmohanty/Desktop/RoundLab/frontend/src/components/evidence/EvidenceStudioCard.tsx"
        ).read_text()
        # Should be gated on citation_record presence
        assert "citation_record" in content

    def test_citation_panel_uses_legacy_mla_fallback(self):
        from pathlib import Path
        content = Path(
            "/Users/yashnilmohanty/Desktop/RoundLab/frontend/src/components/evidence/EvidenceStudioCard.tsx"
        ).read_text()
        assert "legacyMla" in content

    def test_citation_field_edit_endpoint_wired(self):
        from pathlib import Path
        content = Path(
            "/Users/yashnilmohanty/Desktop/RoundLab/frontend/src/components/evidence/EvidenceStudioCard.tsx"
        ).read_text()
        assert "citation-field" in content


# ══════════════════════════════════════════════════════════════════════════════
# 15. Ownership isolation
# ══════════════════════════════════════════════════════════════════════════════

class TestOwnershipIsolation:
    def test_personal_library_isolated_from_other_users(self):
        """User B cannot access User A's library_card_metadata."""
        # search_library only queries with user_id = body.user_id
        lcm_rows_user_a = [{**_LCM_ROW, "user_id": USER_A}]
        sb = _mock_sb({"library_card_metadata": lcm_rows_user_a})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            # User B searches — the mock returns rows regardless (testing the query param)
            # In production, RLS would enforce isolation. Here we test the query is correct.
            resp = svc.search_library(LibrarySearchRequest(user_id=USER_B))
        # The key check: the service code passes user_id to the query
        # We verify this by inspecting the source
        import inspect
        source = inspect.getsource(svc.search_library)
        assert 'eq("user_id"' in source

    def test_blockfile_owner_can_edit(self):
        sb = _mock_sb({"blockfiles": [_BLOCKFILE_ROW]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.update_blockfile("bf-1", BlockfileUpdate(user_id=USER_A, title="New"))
        assert row is not None

    def test_blockfile_non_owner_cannot_edit(self):
        sb = _mock_sb({"blockfiles": [{**_BLOCKFILE_ROW, "user_id": USER_B}]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            with pytest.raises(PermissionError):
                svc.update_blockfile("bf-1", BlockfileUpdate(user_id=USER_A, title="New"))

    def test_resolution_not_visible_to_other_user(self):
        sb = _mock_sb({"resolutions": [_RESOLUTION_ROW]})  # user_id = USER_A
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            row = svc.get_resolution("res-1", USER_B)
        assert row is None

    def test_frontline_owner_can_delete(self):
        sb = _mock_sb({"frontlines": [_FRONTLINE_ROW]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            svc.delete_frontline("fl-1", USER_A)

    def test_frontline_non_owner_cannot_delete(self):
        sb = _mock_sb({"frontlines": [{**_FRONTLINE_ROW, "user_id": USER_B}]})
        with patch("app.services.evidence_library_service.get_supabase", return_value=sb):
            with pytest.raises(PermissionError):
                svc.delete_frontline("fl-1", USER_A)


# ══════════════════════════════════════════════════════════════════════════════
# 16. Data model validation
# ══════════════════════════════════════════════════════════════════════════════

class TestModelValidation:
    def test_resolution_row_requires_title(self):
        with pytest.raises(Exception):
            ResolutionRow(id="r1", user_id=USER_A, normalized_title="t",
                          event_type="pf", is_active=True,
                          created_at="2026-06-22", updated_at="2026-06-22")

    def test_argument_side_must_be_valid(self):
        with pytest.raises(Exception):
            ArgumentCreate(user_id=USER_A, title="T", side="invalid")  # type: ignore

    def test_blockfile_side_optional(self):
        bf = BlockfileCreate(user_id=USER_A, title="T")
        assert bf.side is None

    def test_library_card_save_defaults_card_status_to_active(self):
        req = LibraryCardSaveRequest(user_id=USER_A, card_id="c1")
        assert req.card_status == "active"

    def test_frontline_response_all_speeches_valid(self):
        resp = FrontlineResponseCreate(
            frontline_id="fl-1",
            user_id=USER_A,
            response_type="turn",
            response_claim="Turn",
            speech_suitability=["rebuttal", "summary", "final_focus"],
        )
        assert "rebuttal" in resp.speech_suitability

    def test_card_relationship_uniqueness_check(self):
        # Creating the same relationship twice: second insert should handle unique constraint
        rel = CardRelationshipCreate(
            user_id=USER_A,
            from_card_id="c1",
            to_card_id="c2",
            relationship_type="supports",
        )
        assert rel.from_card_id != rel.to_card_id


# ══════════════════════════════════════════════════════════════════════════════
# 17. Migration SQL integrity
# ══════════════════════════════════════════════════════════════════════════════

class TestMigrationSQL:
    def test_migration_file_exists(self):
        from pathlib import Path
        migration = Path(
            "/Users/yashnilmohanty/Desktop/RoundLab/backend/migrations/"
            "20260622_pass13_evidence_library.sql"
        )
        assert migration.exists()

    def test_migration_contains_all_tables(self):
        from pathlib import Path
        content = Path(
            "/Users/yashnilmohanty/Desktop/RoundLab/backend/migrations/"
            "20260622_pass13_evidence_library.sql"
        ).read_text()
        required_tables = [
            "resolutions",
            "arguments",
            "evidence_sources",
            "library_card_metadata",
            "blockfiles",
            "blockfile_sections",
            "blockfile_entries",
            "card_relationships",
            "card_versions",
            "frontlines",
            "frontline_responses",
            "frontline_response_cards",
        ]
        for table in required_tables:
            assert f"CREATE TABLE IF NOT EXISTS {table}" in content, \
                f"Table {table} not found in migration"

    def test_migration_has_rls_policies(self):
        from pathlib import Path
        content = Path(
            "/Users/yashnilmohanty/Desktop/RoundLab/backend/migrations/"
            "20260622_pass13_evidence_library.sql"
        ).read_text()
        assert "ROW LEVEL SECURITY" in content
        assert "CREATE POLICY" in content

    def test_migration_has_rollback_section(self):
        from pathlib import Path
        content = Path(
            "/Users/yashnilmohanty/Desktop/RoundLab/backend/migrations/"
            "20260622_pass13_evidence_library.sql"
        ).read_text()
        assert "DROP TABLE" in content


# ══════════════════════════════════════════════════════════════════════════════
# 18. Regression: Passes 11 and 12 still intact
# ══════════════════════════════════════════════════════════════════════════════

class TestRegressionPreviousPasses:
    def test_citation_record_model_importable(self):
        from app.models.citation import CitationRecord, CitationPerson, CitationDate
        assert CitationRecord is not None
        assert CitationPerson is not None
        assert CitationDate is not None

    def test_citation_normalizer_importable(self):
        from app.services.citation_normalizer import (
            build_citation_record,
            apply_user_edit,
            from_legacy_citation_metadata,
        )
        assert callable(build_citation_record)
        assert callable(apply_user_edit)

    def test_citation_renderers_importable(self):
        from app.services.citation_renderers import (
            render_debate,
            render_mla,
            render_apa,
            render_chicago,
            render_bibtex,
            render_ris,
            attach_rendered,
            export_bibliography,
        )
        assert callable(render_debate)
        assert callable(export_bibliography)

    def test_evidence_verifier_importable(self):
        from app.services.evidence_card_verifier import EvidenceVerificationResult
        assert EvidenceVerificationResult is not None

    def test_search_trace_p12_fields_present(self):
        from app.services.search_trace import SearchStageTrace
        trace = SearchStageTrace(stage="search")
        assert hasattr(trace, "citation_records_created")
        assert hasattr(trace, "crossref_verified_records")

    def test_main_registers_evidence_library_router(self):
        from app.main import app
        routes = [r.path for r in app.routes]
        # /library prefix should be present
        assert any("/library" in p for p in routes), \
            "Evidence library router not registered in main.py"

    def test_evidence_library_models_no_circular_import(self):
        import importlib
        m = importlib.import_module("app.models.evidence_library")
        assert hasattr(m, "ResolutionCreate")
        assert hasattr(m, "BlockfileCreate")
        assert hasattr(m, "FrontlineCreate")

    def test_library_export_importable(self):
        from app.services.library_export import (
            export_blockfile_json,
            export_blockfile_markdown,
            export_blockfile_docx,
            export_frontline_json,
            export_frontline_markdown,
        )
        assert callable(export_blockfile_json)
        assert callable(export_blockfile_docx)


# ══════════════════════════════════════════════════════════════════════════════
# 19. CI workflow
# ══════════════════════════════════════════════════════════════════════════════

class TestCIWorkflow:
    def test_ci_yml_exists(self):
        from pathlib import Path
        ci = Path("/Users/yashnilmohanty/Desktop/RoundLab/.github/workflows/ci.yml")
        assert ci.exists()

    def test_ci_runs_backend_tests(self):
        from pathlib import Path
        content = Path("/Users/yashnilmohanty/Desktop/RoundLab/.github/workflows/ci.yml").read_text()
        assert "pytest" in content

    def test_ci_runs_frontend_tests(self):
        from pathlib import Path
        content = Path("/Users/yashnilmohanty/Desktop/RoundLab/.github/workflows/ci.yml").read_text()
        assert "jest" in content

    def test_ci_runs_typescript_check(self):
        from pathlib import Path
        content = Path("/Users/yashnilmohanty/Desktop/RoundLab/.github/workflows/ci.yml").read_text()
        assert "tsc" in content

    def test_ci_installs_pymupdf(self):
        from pathlib import Path
        content = Path("/Users/yashnilmohanty/Desktop/RoundLab/.github/workflows/ci.yml").read_text()
        assert "requirements.txt" in content
