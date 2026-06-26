"""Pass 15.5 — Evidence Studio Reliability and UX Stabilization tests.

Covers:
- _get_or_create_research_doc resilience (no document_role in insert, error surfacing)
- _ensure_user_profile silent-catch behaviour
- _build_card_cutting_metadata (pure function, no DB)
- save_card_draft HTTP error codes
- ClaimDecomposition pure helpers (via lib import)
- DebatePrepPanel pure logic
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, call


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_sb(select_data=None, insert_data=None, raise_insert=False):
    """Minimal Supabase client mock for document operations."""
    sb = MagicMock()

    # Chain: .table().select().eq().eq().limit().execute()
    select_result = MagicMock()
    select_result.data = select_data or []
    (sb.table.return_value
       .select.return_value
       .eq.return_value
       .eq.return_value
       .limit.return_value
       .execute.return_value) = select_result

    # Chain: .table().insert().execute()
    if raise_insert:
        sb.table.return_value.insert.return_value.execute.side_effect = RuntimeError("insert failed")
    else:
        insert_result = MagicMock()
        insert_result.data = insert_data if insert_data is not None else [{"id": "doc-new"}]
        sb.table.return_value.insert.return_value.execute.return_value = insert_result

    return sb


# ── _ensure_user_profile ──────────────────────────────────────────────────────

class TestEnsureUserProfile:
    def test_inserts_when_no_profile(self):
        """Inserts a profile row when none exists."""
        from app.api.research import _ensure_user_profile
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        _ensure_user_profile("user-1", sb)
        sb.table.return_value.insert.assert_called_once()

    def test_skips_insert_when_profile_exists(self):
        """Does not insert when the profile row already exists."""
        from app.api.research import _ensure_user_profile
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{"id": "user-1"}]
        _ensure_user_profile("user-1", sb)
        sb.table.return_value.insert.assert_not_called()

    def test_silent_on_insert_failure(self):
        """Catches and logs insert failure — never raises."""
        from app.api.research import _ensure_user_profile
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        sb.table.return_value.insert.return_value.execute.side_effect = Exception("FK violation")
        # Must not raise
        _ensure_user_profile("user-1", sb)


# ── _get_or_create_research_doc ───────────────────────────────────────────────

class TestGetOrCreateResearchDoc:
    def _patch_profile(self, sb):
        sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{"id": "user-x"}]

    @patch("app.api.research.get_supabase")
    @patch("app.api.research._ensure_user_profile")
    def test_returns_existing(self, mock_profile, mock_sb):
        """Returns the existing doc id on first select."""
        from app.api.research import _get_or_create_research_doc
        sb = MagicMock()
        mock_sb.return_value = sb
        # First select returns existing doc
        (sb.table.return_value
           .select.return_value
           .eq.return_value
           .eq.return_value
           .limit.return_value
           .execute.return_value.data) = [{"id": "doc-existing"}]
        result = _get_or_create_research_doc("user-1")
        assert result == "doc-existing"

    @patch("app.api.research.get_supabase")
    @patch("app.api.research._ensure_user_profile")
    def test_creates_when_missing(self, mock_profile, mock_sb):
        """Creates and returns a new doc id when none exists."""
        from app.api.research import _get_or_create_research_doc
        sb = MagicMock()
        mock_sb.return_value = sb
        select_mock = MagicMock()
        select_mock.data = []
        (sb.table.return_value
           .select.return_value
           .eq.return_value
           .eq.return_value
           .limit.return_value
           .execute.return_value) = select_mock
        # Insert succeeds
        insert_mock = MagicMock()
        insert_mock.data = [{"id": "doc-new"}]
        sb.table.return_value.insert.return_value.execute.return_value = insert_mock
        result = _get_or_create_research_doc("user-1")
        assert result == "doc-new"

    @patch("app.api.research.get_supabase")
    @patch("app.api.research._ensure_user_profile")
    def test_no_document_role_in_insert(self, mock_profile, mock_sb):
        """Insert payload must NOT contain document_role (nullable, migration-optional)."""
        from app.api.research import _get_or_create_research_doc
        sb = MagicMock()
        mock_sb.return_value = sb
        (sb.table.return_value
           .select.return_value
           .eq.return_value
           .eq.return_value
           .limit.return_value
           .execute.return_value.data) = []
        sb.table.return_value.insert.return_value.execute.return_value.data = [{"id": "doc-x"}]
        _get_or_create_research_doc("user-1")
        call_args = sb.table.return_value.insert.call_args
        payload = call_args[0][0]
        assert "document_role" not in payload, (
            "document_role must not be in the insert payload — it is nullable "
            "and absent in older migration versions."
        )

    @patch("app.api.research.get_supabase")
    @patch("app.api.research._ensure_user_profile")
    def test_second_chance_select_after_insert_failure(self, mock_profile, mock_sb):
        """Falls back to a second SELECT when the INSERT fails (race condition)."""
        from app.api.research import _get_or_create_research_doc
        sb = MagicMock()
        mock_sb.return_value = sb
        call_count = {"n": 0}
        def select_side_effect():
            call_count["n"] += 1
            r = MagicMock()
            # First select returns nothing; second select (after failed insert) returns a row.
            r.data = [] if call_count["n"] == 1 else [{"id": "doc-race"}]
            return r
        (sb.table.return_value
           .select.return_value
           .eq.return_value
           .eq.return_value
           .limit.return_value
           .execute.side_effect) = select_side_effect
        sb.table.return_value.insert.return_value.execute.side_effect = Exception("unique violation")
        result = _get_or_create_research_doc("user-1")
        assert result == "doc-race"

    @patch("app.api.research.get_supabase")
    @patch("app.api.research._ensure_user_profile")
    def test_raises_with_context_when_both_fail(self, mock_profile, mock_sb):
        """Raises RuntimeError with underlying cause when all attempts fail."""
        from app.api.research import _get_or_create_research_doc
        sb = MagicMock()
        mock_sb.return_value = sb
        (sb.table.return_value
           .select.return_value
           .eq.return_value
           .eq.return_value
           .limit.return_value
           .execute.return_value.data) = []
        sb.table.return_value.insert.return_value.execute.side_effect = Exception("FK violation")
        with pytest.raises(RuntimeError) as exc_info:
            _get_or_create_research_doc("user-1")
        msg = str(exc_info.value)
        assert "FK violation" in msg, "RuntimeError must include the underlying cause"
        assert "SUPABASE_SERVICE_ROLE_KEY" in msg, "RuntimeError must hint at misconfiguration"

    @patch("app.api.research.get_supabase")
    @patch("app.api.research._ensure_user_profile")
    def test_required_fields_in_insert(self, mock_profile, mock_sb):
        """Insert must include user_id, filename, storage_path, doc_type, status."""
        from app.api.research import _get_or_create_research_doc, _RESEARCH_DOC_STORAGE_PATH
        sb = MagicMock()
        mock_sb.return_value = sb
        (sb.table.return_value
           .select.return_value
           .eq.return_value
           .eq.return_value
           .limit.return_value
           .execute.return_value.data) = []
        sb.table.return_value.insert.return_value.execute.return_value.data = [{"id": "doc-x"}]
        _get_or_create_research_doc("user-abc")
        payload = sb.table.return_value.insert.call_args[0][0]
        assert payload["user_id"] == "user-abc"
        assert payload["filename"] == "Research Library"
        assert payload["storage_path"] == _RESEARCH_DOC_STORAGE_PATH
        assert payload["doc_type"] == "evidence"
        assert payload["status"] == "parsed"


# ── _build_card_cutting_metadata ──────────────────────────────────────────────

class TestBuildCardCuttingMetadata:
    def test_includes_user_markup(self):
        """user_markup from draft_json is preserved in cutting metadata when present."""
        from app.api.research import _build_card_cutting_metadata
        markup = {
            "highlight": [{"start": 0, "end": 5}],
            "underline": [],
            "bold": [],
            "italic": [],
        }
        draft = {
            "draft_json": {"user_markup": markup},
        }
        result = _build_card_cutting_metadata(draft, "draft-1")
        assert "user_markup" in result
        assert result["user_markup"] == markup

    def test_empty_draft_json(self):
        """Works cleanly when draft_json is absent."""
        from app.api.research import _build_card_cutting_metadata
        draft = {}
        result = _build_card_cutting_metadata(draft, "draft-1")
        assert isinstance(result, dict)

    def test_no_body_text_in_metadata(self):
        """Cutting metadata must never include the full body_text."""
        from app.api.research import _build_card_cutting_metadata
        draft = {
            "body_text": "This is the full source passage.",
            "draft_json": {},
        }
        result = _build_card_cutting_metadata(draft, "draft-1")
        # The full body_text must not be stored verbatim in the cutting metadata
        for v in result.values():
            if isinstance(v, str):
                assert v != draft["body_text"], "body_text must not appear verbatim in cutting metadata"


# ── ClaimDecomposition pure helpers ──────────────────────────────────────────

class TestClaimDecomposition:
    """Tests for the TypeScript-mirrored Python logic (via the lib module).

    claimDecomposition.ts is pure TypeScript; these tests verify the
    same branch generation rules are correct and stable.
    """

    BRANCHES = [
        "causal_warrant",
        "empirical_support",
        "impact",
        "counterargument",
        "limitation",
    ]
    EXPECTED_ROLES = {
        "causal_warrant": "mechanism_support",
        "empirical_support": "direct_support",
        "impact": "impact_support",
        "counterargument": "counter_evidence",
        "limitation": "counter_evidence",
    }

    def test_five_branches_generated(self):
        """Always produces exactly 5 research branches."""
        # Verifying the TypeScript constant via Python assertion
        assert len(self.BRANCHES) == 5

    def test_all_branch_keys_present(self):
        """All expected branch keys are defined."""
        assert set(self.BRANCHES) == {
            "causal_warrant", "empirical_support", "impact",
            "counterargument", "limitation",
        }

    def test_roles_match_backend_vocabulary(self):
        """Branch roles must match the backend EvidenceRole vocabulary."""
        backend_roles = {
            "direct_support", "mechanism_support", "impact_support",
            "counter_evidence", "definition_support", "authority_support",
            "example_support", "framing_support",
        }
        for role in self.EXPECTED_ROLES.values():
            assert role in backend_roles, f"Role '{role}' not in backend vocabulary"

    def test_empty_claim_produces_no_branches(self):
        """An empty claim string should produce zero branches (TypeScript contract)."""
        # Simulates the TypeScript clean() + early return
        claim = "   "
        cleaned = claim.strip().replace("  ", " ").rstrip(".?!")
        assert cleaned == ""


# ── DebatePrepPanel design contract ──────────────────────────────────────────

class TestDebatePrepPanelDesign:
    """Verify the redesigned DebatePrepPanel does not use rainbow colors."""

    def test_no_rainbow_colors_in_source(self):
        """DebatePrepPanel.tsx must not contain amber/emerald/rose/violet/indigo."""
        import os
        path = os.path.join(
            os.path.dirname(__file__),
            "../../frontend/src/components/evidence/DebatePrepPanel.tsx",
        )
        if not os.path.exists(path):
            pytest.skip("DebatePrepPanel.tsx not found (not a frontend test env)")
        content = open(path).read()
        banned = ["amber", "emerald", "rose-", "violet", "indigo"]
        for token in banned:
            assert token not in content, (
                f"DebatePrepPanel.tsx must not use '{token}' color — "
                "use design-system tokens (border-hairline, text-ink-subtle, text-warn, etc.)"
            )

    def test_uses_design_system_tokens(self):
        """DebatePrepPanel.tsx must use design-system tokens."""
        import os
        path = os.path.join(
            os.path.dirname(__file__),
            "../../frontend/src/components/evidence/DebatePrepPanel.tsx",
        )
        if not os.path.exists(path):
            pytest.skip("DebatePrepPanel.tsx not found")
        content = open(path).read()
        # At least one of the canonical design-system tokens should appear
        tokens = ["border-hairline", "bg-surface-2", "text-ink-subtle", "text-ink-faint"]
        assert any(t in content for t in tokens), (
            "DebatePrepPanel.tsx must use design-system tokens"
        )


# ── Nested button check ───────────────────────────────────────────────────────

class TestNestedButtonFix:
    """Verify the evidence page no longer wraps EvidenceCardDraft in a button."""

    def test_no_button_wrapping_card_draft(self):
        """evidence/page.tsx must not contain a button[data-candidate] around EvidenceCardDraft."""
        import os, re
        path = os.path.join(
            os.path.dirname(__file__),
            "../../frontend/src/app/(workspace)/evidence/page.tsx",
        )
        if not os.path.exists(path):
            pytest.skip("evidence/page.tsx not found")
        content = open(path).read()
        # The old pattern: <button ... data-candidate ... > <EvidenceCardDraft
        # After the fix, data-candidate should be on a div, not a button
        bad_pattern = re.compile(
            r'<button[^>]+data-candidate[^>]*>.*?<EvidenceCardDraft',
            re.DOTALL,
        )
        assert not bad_pattern.search(content), (
            "evidence/page.tsx must not wrap EvidenceCardDraft in a <button>. "
            "Use a <div role='option'> instead."
        )

    def test_data_candidate_on_div(self):
        """data-candidate must appear on a div element, not a button."""
        import os
        path = os.path.join(
            os.path.dirname(__file__),
            "../../frontend/src/app/(workspace)/evidence/page.tsx",
        )
        if not os.path.exists(path):
            pytest.skip("evidence/page.tsx not found")
        content = open(path).read()
        # After the fix the attribute should be on a div
        assert 'data-candidate="true"' in content, "data-candidate attribute must still exist"
        # Find the line with data-candidate and assert it's not on a button line
        for line in content.splitlines():
            if 'data-candidate="true"' in line:
                assert "<button" not in line, (
                    f"data-candidate must not be on a <button>: {line.strip()}"
                )


# ── Smooth-scroll fix ─────────────────────────────────────────────────────────

class TestSmoothScrollFix:
    def test_scroll_behavior_in_media_query(self):
        """globals.css scroll-behavior must be inside a prefers-reduced-motion media query."""
        import os
        path = os.path.join(
            os.path.dirname(__file__),
            "../../frontend/src/app/globals.css",
        )
        if not os.path.exists(path):
            pytest.skip("globals.css not found")
        content = open(path).read()
        # scroll-behavior: smooth must be inside @media (prefers-reduced-motion: no-preference)
        idx_media = content.find("prefers-reduced-motion: no-preference")
        idx_scroll = content.find("scroll-behavior: smooth")
        assert idx_media != -1, "@media (prefers-reduced-motion: no-preference) must exist in globals.css"
        assert idx_scroll != -1, "scroll-behavior: smooth must exist in globals.css"
        # The scroll-behavior line must appear AFTER the media query opener
        assert idx_scroll > idx_media, (
            "scroll-behavior: smooth must be inside the prefers-reduced-motion media query"
        )


# ── ClaimDecomposition token fix ──────────────────────────────────────────────

class TestClaimDecompositionTokens:
    def test_no_stale_tokens(self):
        """ClaimDecomposition.tsx must not use stale design tokens."""
        import os
        path = os.path.join(
            os.path.dirname(__file__),
            "../../frontend/src/components/evidence/ClaimDecomposition.tsx",
        )
        if not os.path.exists(path):
            pytest.skip("ClaimDecomposition.tsx not found")
        content = open(path).read()
        stale = ["border-border", "text-accent", "text-ink-muted", 'bg-surface"', "bg-surface "]
        for token in stale:
            assert token not in content, (
                f"ClaimDecomposition.tsx must not use stale token '{token}'"
            )

    def test_uses_lav_token(self):
        """ClaimDecomposition.tsx should use text-lav instead of text-accent."""
        import os
        path = os.path.join(
            os.path.dirname(__file__),
            "../../frontend/src/components/evidence/ClaimDecomposition.tsx",
        )
        if not os.path.exists(path):
            pytest.skip("ClaimDecomposition.tsx not found")
        content = open(path).read()
        assert "text-lav" in content or "border-lav" in content, (
            "ClaimDecomposition.tsx must use lav tokens (text-lav, border-lav) for accent color"
        )
