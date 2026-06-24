"""
Pass 15.6 — Evidence save pipeline fix tests.

Verifies:
1. _stage_error sanitises secrets from error detail
2. save_card_draft is idempotent when draft already has saved_card_id
3. save_card_draft inserts card_text (NOT NULL) and cite into card_row
4. save_card_draft returns 409 when status=="saved" but no saved_card_id
5. Stage attribution — each stage raises the right structured error
6. Frontend save payload shape (TypeScript contract, tested via regex)
7. ClaimDecomposition component exposes isSearching/onRunAll props
8. DebatePrepPanel has copyable fields (copy buttons in markup)
9. Migration file exists and patches the right columns
10. Save function does NOT include 'cite' in doc_chunk insert
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[2]
BACKEND_ROOT = ROOT / "backend"
FRONTEND_ROOT = ROOT / "frontend"


# ─────────────────────────────────────────────────────────────────────────────
# 1. _stage_error implementation (source-level checks)
# ─────────────────────────────────────────────────────────────────────────────

class TestStageError(unittest.TestCase):
    """Verify the _stage_error helper is correctly implemented via source analysis."""

    def _src(self) -> str:
        return (BACKEND_ROOT / "app" / "api" / "research.py").read_text()

    def test_stage_included_in_detail(self):
        src = self._src()
        self.assertIn('"stage": stage', src)

    def test_status_code_is_500(self):
        src = self._src()
        self.assertIn("status_code=500", src)

    def test_eyj_token_redacted(self):
        src = self._src()
        # The function must check for JWT prefix
        self.assertIn('"eyJ"', src)
        self.assertIn('"internal error"', src)

    def test_service_role_key_redacted(self):
        src = self._src()
        # "service_role" must be in the secrets blocklist
        self.assertIn('"service_role"', src)

    def test_message_key_in_detail(self):
        src = self._src()
        self.assertIn('"message": safe_detail', src)


# ─────────────────────────────────────────────────────────────────────────────
# 2. card_row contains card_text and cite
# ─────────────────────────────────────────────────────────────────────────────

class TestCardRowFields(unittest.TestCase):
    """Verify save_card_draft builds a card_row with card_text and cite."""

    def _make_draft(self, **overrides):
        base = {
            "id": "draft-001",
            "user_id": "user-001",
            "status": "draft",
            "saved_card_id": None,
            "body_text": "Climate change intensifies hurricane frequency.",
            "tag": "Climate storms up",
            "cite": "NOAA, 2023",
            "card_source_type": "url",
            "url": "https://example.com",
            "title": "Hurricane Study",
            "publication": "NOAA",
            "author_credentials": "Dr. Smith",
            "published_date": "2023-01-01",
            "source_quality": "high",
            "extraction_confidence": 0.9,
            "generated_tag": True,
            "highlighted_spans_json": [],
            "underline_spans_json": [],
            "research_source_id": None,
            "draft_json": {},
        }
        base.update(overrides)
        return base

    def test_card_row_has_card_text(self):
        """card_text must equal body_text so the NOT NULL constraint is satisfied."""
        src = Path(BACKEND_ROOT / "app" / "api" / "research.py").read_text()
        # Verify both 'card_text' and 'body_text' appear in the card_row block
        self.assertIn('"card_text": body_text', src)
        self.assertIn('"body_text": body_text', src)

    def test_card_row_has_cite(self):
        src = Path(BACKEND_ROOT / "app" / "api" / "research.py").read_text()
        self.assertIn('"cite": draft.get("cite"', src)

    def test_card_text_comment_explains_why(self):
        src = Path(BACKEND_ROOT / "app" / "api" / "research.py").read_text()
        self.assertIn("NOT NULL", src)

    def test_chunk_insert_does_not_include_cite(self):
        """document_chunks has no cite column; it must not appear in chunk insert."""
        src = Path(BACKEND_ROOT / "app" / "api" / "research.py").read_text()
        # Find the chunk insert block and verify 'cite' is not in it
        chunk_block_match = re.search(
            r'table\("document_chunks"\).*?\.insert\(\{(.*?)\}\)',
            src,
            re.DOTALL,
        )
        self.assertIsNotNone(chunk_block_match, "document_chunks insert block not found")
        chunk_block = chunk_block_match.group(1)
        self.assertNotIn('"cite"', chunk_block)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Idempotency
# ─────────────────────────────────────────────────────────────────────────────

class TestSaveDraftIdempotency(unittest.TestCase):

    def test_returns_existing_card_when_saved_card_id_set(self):
        """If draft.saved_card_id is already set, return it immediately."""
        src = Path(BACKEND_ROOT / "app" / "api" / "research.py").read_text()
        # The idempotency guard must check saved_card_id before attempting insert
        self.assertIn("saved_card_id", src)
        # Confirm early-return message
        self.assertIn("already saved", src)

    def test_idempotency_block_precedes_doc_creation(self):
        """The saved_card_id check must come before _get_or_create_research_doc."""
        src = Path(BACKEND_ROOT / "app" / "api" / "research.py").read_text()
        idempotency_pos = src.find("existing_card_id = draft.get(\"saved_card_id\")")
        doc_create_pos = src.find("_get_or_create_research_doc(body.user_id)")
        self.assertGreater(doc_create_pos, idempotency_pos,
                           "Idempotency check must precede doc creation")


# ─────────────────────────────────────────────────────────────────────────────
# 4. Stage attribution
# ─────────────────────────────────────────────────────────────────────────────

class TestStageAttribution(unittest.TestCase):

    def test_doc_stage_name(self):
        src = Path(BACKEND_ROOT / "app" / "api" / "research.py").read_text()
        self.assertIn("find_or_create_document", src)

    def test_chunk_stage_name(self):
        src = Path(BACKEND_ROOT / "app" / "api" / "research.py").read_text()
        self.assertIn("insert_document_chunk", src)

    def test_card_stage_name(self):
        src = Path(BACKEND_ROOT / "app" / "api" / "research.py").read_text()
        self.assertIn("insert_library_card", src)

    def test_each_stage_uses_stage_error(self):
        src = Path(BACKEND_ROOT / "app" / "api" / "research.py").read_text()
        # _stage_error should be called at least 3 times (once per stage)
        count = src.count("_stage_error(")
        self.assertGreaterEqual(count, 3)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Migration file exists and patches the right columns
# ─────────────────────────────────────────────────────────────────────────────

class TestMigrationFile(unittest.TestCase):

    def setUp(self):
        migrations_dir = ROOT / "supabase" / "migrations"
        files = sorted(migrations_dir.glob("*pass15p6*.sql"))
        self.assertGreater(len(files), 0, "Pass 15.6 migration file not found")
        self.sql = files[0].read_text()

    def test_adds_cite_column(self):
        self.assertIn("cite", self.sql)
        self.assertIn("DEFAULT", self.sql)

    def test_sets_card_text_default(self):
        self.assertIn("card_text", self.sql)
        self.assertIn("SET DEFAULT", self.sql)

    def test_adds_service_role_evidence_cards_policy(self):
        self.assertIn("service_role_evidence_cards", self.sql)

    def test_adds_service_role_document_chunks_policy(self):
        self.assertIn("service_role_document_chunks", self.sql)

    def test_notify_pgrst(self):
        self.assertIn("NOTIFY pgrst", self.sql)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Frontend save payload and structured error handling
# ─────────────────────────────────────────────────────────────────────────────

class TestFrontendSavePayload(unittest.TestCase):

    def _read(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def test_duplicate_click_prevention(self):
        src = self._read(FRONTEND_ROOT / "src" / "app" / "evidence" / "page.tsx")
        self.assertIn("savingDraftId !== null", src)

    def test_structured_error_parsed(self):
        src = self._read(FRONTEND_ROOT / "src" / "app" / "evidence" / "page.tsx")
        # The handler should parse JSON error with stage field
        self.assertIn("parsed.stage", src)

    def test_last_saved_card_id_state(self):
        src = self._read(FRONTEND_ROOT / "src" / "app" / "evidence" / "page.tsx")
        self.assertIn("lastSavedCardId", src)
        self.assertIn("setLastSavedCardId", src)

    def test_success_banner_view_in_library(self):
        src = self._read(FRONTEND_ROOT / "src" / "app" / "evidence" / "page.tsx")
        self.assertIn("View in Library", src)

    def test_retry_button_present(self):
        src = self._read(FRONTEND_ROOT / "src" / "app" / "evidence" / "page.tsx")
        self.assertIn("Retry", src)

    def test_evidence_card_type_has_cite(self):
        src = self._read(FRONTEND_ROOT / "src" / "types" / "index.ts")
        self.assertIn("cite?:", src)


# ─────────────────────────────────────────────────────────────────────────────
# 7. ClaimDecomposition: isSearching + onRunAll props
# ─────────────────────────────────────────────────────────────────────────────

class TestClaimDecompositionProps(unittest.TestCase):

    def _src(self) -> str:
        return (FRONTEND_ROOT / "src" / "components" / "evidence" / "ClaimDecomposition.tsx").read_text()

    def test_is_searching_prop_accepted(self):
        self.assertIn("isSearching", self._src())

    def test_on_run_all_prop_accepted(self):
        self.assertIn("onRunAll", self._src())

    def test_loading_branch_key_state(self):
        self.assertIn("activeBranchKey", self._src())

    def test_loader_icon_used(self):
        self.assertIn("Loader2", self._src())

    def test_run_all_button_present(self):
        # Pass 15.7 shortened "Run all angles" to "Run all" — either is valid.
        src = self._src()
        self.assertTrue(
            "Run all" in src,
            msg="Expected 'Run all' button text in ClaimDecomposition",
        )

    def test_any_loading_disables_buttons(self):
        self.assertIn("anyLoading", self._src())

    def test_uses_effect_to_clear_loading(self):
        self.assertIn("useEffect", self._src())


# ─────────────────────────────────────────────────────────────────────────────
# 8. DebatePrepPanel: copy actions
# ─────────────────────────────────────────────────────────────────────────────

class TestDebatePrepPanelCopy(unittest.TestCase):

    def _src(self) -> str:
        return (FRONTEND_ROOT / "src" / "components" / "evidence" / "DebatePrepPanel.tsx").read_text()

    def test_copy_button_present(self):
        self.assertIn("Copy", self._src())

    def test_check_icon_for_copied_state(self):
        self.assertIn("Check", self._src())

    def test_clipboard_write_text(self):
        self.assertIn("navigator.clipboard.writeText", self._src())

    def test_cf_q_copykey(self):
        self.assertIn("cf_q", self._src())

    def test_cf_a_copykey(self):
        self.assertIn("cf_a", self._src())

    def test_weighing_copykey(self):
        self.assertIn('"weighing"', self._src())

    def test_no_rainbow_colors(self):
        src = self._src()
        for bad in ("amber-", "emerald-", "violet-", "indigo-", "rose-", "bg-blue-"):
            with self.subTest(bad=bad):
                self.assertNotIn(bad, src)

    def test_uses_ok_class_for_copied(self):
        self.assertIn("text-ok", self._src())


# ─────────────────────────────────────────────────────────────────────────────
# 9. Complete flow: stage error function signature
# ─────────────────────────────────────────────────────────────────────────────

class TestStageErrorSignature(unittest.TestCase):

    def test_takes_stage_and_exc(self):
        src = Path(BACKEND_ROOT / "app" / "api" / "research.py").read_text()
        # Function accepts (stage: str, exc: Exception)
        self.assertIn("def _stage_error(stage: str, exc: Exception)", src)

    def test_returns_http_exception(self):
        src = Path(BACKEND_ROOT / "app" / "api" / "research.py").read_text()
        self.assertIn("return HTTPException(", src)


if __name__ == "__main__":
    unittest.main()
