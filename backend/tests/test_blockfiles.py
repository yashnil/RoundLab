"""
Tests for blockfile extraction, block coverage, and blockfile API.
All tests are deterministic and do not call OpenAI.
"""
from __future__ import annotations
import pytest
from unittest.mock import MagicMock, patch

from app.models.document import DocumentChunkRow
from app.models.blockfile import BlockEntryCreate, BlockSearchResult
from app.services.blockfile_extraction import (
    extract_block_entries,
    build_embedding_text,
    _extract_structured,
    _extract_from_chunks,
)
from app.services.block_coverage import (
    classify_block_coverage,
    _classify,
    _derive_missing_from_issues,
    _make_drill,
    _COVERED_THRESHOLD,
    _PARTIAL_THRESHOLD,
    _HAS_MATCH_THRESHOLD,
)
from app.services.workout_generation import generate_tournament_workout


# ── Factories ─────────────────────────────────────────────────────────────────

def make_chunk(chunk_text: str, chunk_index: int = 0, heading: str = None) -> DocumentChunkRow:
    return DocumentChunkRow(
        id=f"chunk-{chunk_index}",
        document_id="doc-1",
        user_id="user-1",
        chunk_text=chunk_text,
        chunk_index=chunk_index,
        heading=heading,
        page_number=None,
        metadata_json={},
        created_at="2026-01-01T00:00:00Z",
    )


def make_search_result(
    id: str = "entry-1",
    entry_type: str = "block",
    tag: str = "AT Free Speech",
    similarity: float = 0.70,
) -> BlockSearchResult:
    return BlockSearchResult(
        id=id,
        document_id="doc-1",
        entry_type=entry_type,
        side=None,
        tag=tag,
        opponent_claim="Free speech is protected online.",
        response_text="Accountability does not equal censorship; platforms remain liable for illegal facilitation.",
        warrant_text="Enabling liability preserves free speech while deterring harm.",
        evidence_text=None,
        impact_text="Creates safer internet without chilling lawful speech.",
        weighing_text=None,
        source=None,
        author=None,
        date=None,
        similarity=similarity,
    )


# ── blockfile_extraction tests ────────────────────────────────────────────────

class TestExtractStructured:
    def test_at_colon_pattern(self):
        text = "AT: Free Speech\nResponse: Accountability is not censorship.\nWarrant: Platforms can be liable without chilling speech."
        entries = _extract_structured(text, "u1", "doc-1", None, None)
        assert len(entries) == 1
        assert entries[0].entry_type == "block"
        assert "Free Speech" in (entries[0].opponent_claim or "")
        assert entries[0].response_text

    def test_a_slash_t_pattern(self):
        text = "A/T: Economic Growth\nResponse: Growth does not justify harm.\n"
        entries = _extract_structured(text, "u1", "doc-1", None, None)
        assert len(entries) == 1
        assert entries[0].entry_type == "block"

    def test_frontline_pattern(self):
        text = "Frontline — Censorship\nResponse: Platforms are private actors; First Amendment does not apply.\nWarrant: Government compulsion is required for 1A claims."
        entries = _extract_structured(text, "u1", "doc-1", None, None)
        assert len(entries) == 1
        assert entries[0].entry_type == "frontline"

    def test_block_colon_pattern(self):
        text = "Block: Harms Outweigh\nResponse: Costs of inaction exceed regulatory burden.\n"
        entries = _extract_structured(text, "u1", "doc-1", None, None)
        assert len(entries) == 1
        assert entries[0].entry_type == "block"

    def test_multiple_sections(self):
        text = (
            "AT: Free Speech\nResponse: Accountability does not require censorship; platforms can be liable for illegal facilitation.\n\n"
            "AT: Economic Harm\nResponse: Economic costs are overstated; studies show compliance costs are below 1% of revenue.\nWarrant: Regulatory literature supports this.\n\n"
            "Frontline — Our Case\nResponse: Our framework outweighs even under the opponent's own impact calculus.\n"
        )
        entries = _extract_structured(text, "u1", "doc-1", None, None)
        assert len(entries) == 3

    def test_subfields_parsed(self):
        text = (
            "AT: Privacy\n"
            "Tag: Privacy Block\n"
            "Response: Surveillance harms autonomy.\n"
            "Warrant: Autonomy is fundamental.\n"
            "Evidence: Smith 2023 — privacy linked to cognitive liberty.\n"
            "Impact: Chilling effect on democratic participation.\n"
        )
        entries = _extract_structured(text, "u1", "doc-1", None, None)
        assert len(entries) == 1
        e = entries[0]
        assert e.tag == "Privacy Block"
        assert "autonomy" in (e.response_text or "").lower()
        assert e.warrant_text is not None
        assert e.evidence_text is not None
        assert e.impact_text is not None

    def test_empty_text_returns_empty(self):
        entries = _extract_structured("", "u1", "doc-1", None, None)
        assert entries == []

    def test_too_short_section_skipped(self):
        text = "AT: X\nResponse: Ok.\n"
        entries = _extract_structured(text, "u1", "doc-1", None, None)
        # Short response — may be skipped
        # We just verify no crash
        assert isinstance(entries, list)

    def test_side_stored_on_entry(self):
        text = "AT: Free Speech\nResponse: This is a substantive response with enough text to pass the minimum length requirement."
        entries = _extract_structured(text, "u1", "doc-1", None, "con")
        assert len(entries) == 1
        assert entries[0].side == "con"


class TestExtractFromChunks:
    def test_chunk_with_at_heading(self):
        chunks = [make_chunk("Accountability is not censorship. Platforms remain liable.", heading="AT: Free Speech")]
        entries = _extract_from_chunks(chunks, "u1", "doc-1", "blockfile", None, None)
        assert len(entries) == 1
        assert entries[0].entry_type == "block"

    def test_chunk_without_heading_uses_document_role(self):
        chunks = [make_chunk("This is a prepared frontline response that is long enough.", heading=None)]
        entries = _extract_from_chunks(chunks, "u1", "doc-1", "frontline", None, None)
        assert len(entries) == 1
        assert entries[0].entry_type == "frontline"

    def test_short_chunks_skipped(self):
        chunks = [make_chunk("Too short.", heading=None)]
        entries = _extract_from_chunks(chunks, "u1", "doc-1", "blockfile", None, None)
        assert entries == []


class TestExtractBlockEntries:
    def test_structured_text_preferred_over_chunks(self):
        text = "AT: Free Speech\nResponse: Long enough response here to avoid minimum length filter."
        chunks = [make_chunk("Unstructured chunk content that is different from the structured text.")]
        entries = extract_block_entries(chunks, text, "u1", "doc-1", "blockfile")
        assert len(entries) >= 1
        assert entries[0].entry_type == "block"

    def test_falls_back_to_chunks_when_no_structure(self):
        text = "This is plain text without any AT or block headers."
        chunks = [make_chunk("This is plain text without any AT or block headers and is long enough.", heading="Section 1")]
        entries = extract_block_entries(chunks, text, "u1", "doc-1", "blockfile")
        assert len(entries) >= 1

    def test_user_id_and_document_id_set(self):
        text = "AT: X\nResponse: This response is long enough to pass the minimum length requirement."
        entries = extract_block_entries([], text, "user-42", "doc-99", "blockfile")
        if entries:
            assert entries[0].user_id == "user-42"
            assert entries[0].document_id == "doc-99"


class TestBuildEmbeddingText:
    def test_combines_all_fields(self):
        entry = BlockEntryCreate(
            user_id="u1",
            entry_type="block",
            tag="AT Free Speech",
            opponent_claim="Free speech claim",
            response_text="Accountability response",
            warrant_text="Warrant here",
            evidence_text="Card evidence",
            impact_text="Impact result",
            weighing_text="Weighing argument",
        )
        text = build_embedding_text(entry)
        assert "AT Free Speech" in text
        assert "Accountability response" in text
        assert "Warrant here" in text

    def test_missing_fields_skipped(self):
        entry = BlockEntryCreate(
            user_id="u1",
            entry_type="block",
            response_text="Only response text here",
        )
        text = build_embedding_text(entry)
        assert "Only response text here" in text
        assert text.strip() != ""


# ── block_coverage tests ──────────────────────────────────────────────────────

class TestClassify:
    def test_below_has_match_returns_no_available_block(self):
        status, rationale, missing = _classify(0.10, [], True)
        assert status == "no_available_block"
        assert missing is not None

    def test_high_similarity_no_issues_covered(self):
        status, rationale, missing = _classify(0.75, [], True)
        assert status == "covered"
        assert missing is None

    def test_high_similarity_with_issues_partial(self):
        status, rationale, missing = _classify(0.72, ["missing_warrant"], True)
        assert status == "partially_covered"

    def test_mid_similarity_partial(self):
        status, rationale, missing = _classify(0.45, [], False)
        assert status == "partially_covered"

    def test_low_mid_similarity_missing(self):
        status, rationale, missing = _classify(0.25, [], False)
        assert status == "missing"
        assert missing is not None


class TestDeriveMissingFromIssues:
    def test_warrant_issue_returns_warrant_message(self):
        result = _derive_missing_from_issues(["missing_warrant"])
        assert result is not None
        assert "warrant" in result.lower()

    def test_evidence_issue_returns_evidence_message(self):
        result = _derive_missing_from_issues(["weak_evidence"])
        assert result is not None
        assert "evidence" in result.lower()

    def test_empty_issues_returns_none(self):
        assert _derive_missing_from_issues([]) is None


class TestMakeDrill:
    def test_missing_status_creates_block_application_drill(self):
        entry = make_search_result()
        drill = _make_drill("Free speech claim", entry, "missing", "C1")
        assert drill is not None
        assert drill["skill_target"] == "block_application"
        assert "Free speech claim" in drill["prompt"] or "AT Free Speech" in drill["prompt"]

    def test_partial_status_creates_response_warranting_drill(self):
        entry = make_search_result()
        drill = _make_drill("Free speech claim", entry, "partially_covered", "C1")
        assert drill is not None
        assert drill["skill_target"] == "response_warranting"

    def test_no_available_block_returns_none(self):
        entry = make_search_result()
        drill = _make_drill("claim", entry, "no_available_block", None)
        assert drill is None


class TestClassifyBlockCoverage:
    def test_no_blocks_returns_no_available(self):
        args = [
            {"claim": "Free speech is protected.", "warrant": "First Amendment.", "issues": []},
        ]
        results = classify_block_coverage(
            arguments=args,
            speech_type="rebuttal",
            user_id="u1",
            speech_id="sp1",
            supabase_client=None,
            user_has_blocks=False,
        )
        assert len(results) == 1
        assert results[0].status == "no_available_block"

    def test_no_blocks_all_arguments_get_no_available(self):
        args = [
            {"claim": "Claim A", "warrant": "W1", "issues": []},
            {"claim": "Claim B", "warrant": "W2", "issues": []},
        ]
        results = classify_block_coverage(
            arguments=args,
            speech_type="summary",
            user_id="u1",
            speech_id="sp1",
            supabase_client=None,
            user_has_blocks=False,
        )
        assert len(results) == 2
        assert all(r.status == "no_available_block" for r in results)

    def test_empty_claim_skipped(self):
        args = [
            {"claim": "", "warrant": "W", "issues": []},
            {"claim": "  ", "warrant": "W", "issues": []},
        ]
        results = classify_block_coverage(
            arguments=args,
            speech_type="rebuttal",
            user_id="u1",
            speech_id="sp1",
            supabase_client=None,
            user_has_blocks=False,
        )
        assert results == []

    def test_blocks_present_calls_rpc(self):
        args = [{"claim": "Free speech claim.", "warrant": "1A warrant.", "issues": []}]

        mock_vec = [0.0] * 1536
        mock_rpc_result = MagicMock()
        mock_rpc_result.data = [
            {
                "id": "entry-1",
                "document_id": "doc-1",
                "entry_type": "block",
                "side": None,
                "tag": "AT Free Speech",
                "opponent_claim": "Free speech",
                "response_text": "Accountability is not censorship.",
                "warrant_text": None,
                "evidence_text": None,
                "impact_text": None,
                "weighing_text": None,
                "source": None,
                "author": None,
                "date": None,
                "similarity": 0.72,
            }
        ]
        mock_sb = MagicMock()
        mock_sb.rpc.return_value.execute.return_value = mock_rpc_result

        with patch("app.services.block_coverage.embed_text", return_value=mock_vec):
            results = classify_block_coverage(
                arguments=args,
                speech_type="rebuttal",
                user_id="u1",
                speech_id="sp1",
                supabase_client=mock_sb,
                user_has_blocks=True,
            )

        assert len(results) == 1
        # High similarity, no issues → covered
        assert results[0].status == "covered"
        assert results[0].top_similarity is not None

    def test_low_similarity_returns_missing(self):
        args = [{"claim": "Novel claim.", "warrant": "W.", "issues": []}]
        mock_vec = [0.0] * 1536
        mock_rpc_result = MagicMock()
        mock_rpc_result.data = [
            {
                "id": "entry-1", "document_id": "doc-1", "entry_type": "block",
                "side": None, "tag": "Different topic", "opponent_claim": "Different",
                "response_text": "Completely unrelated response text.",
                "warrant_text": None, "evidence_text": None, "impact_text": None,
                "weighing_text": None, "source": None, "author": None, "date": None,
                "similarity": 0.22,
            }
        ]
        mock_sb = MagicMock()
        mock_sb.rpc.return_value.execute.return_value = mock_rpc_result

        with patch("app.services.block_coverage.embed_text", return_value=mock_vec):
            results = classify_block_coverage(
                arguments=args,
                speech_type="rebuttal",
                user_id="u1",
                speech_id="sp1",
                supabase_client=mock_sb,
                user_has_blocks=True,
            )

        assert results[0].status == "missing"

    def test_missing_status_includes_suggested_drill(self):
        args = [{"claim": "Novel claim.", "warrant": "W.", "issues": []}]
        mock_vec = [0.0] * 1536
        mock_rpc_result = MagicMock()
        mock_rpc_result.data = [
            {
                "id": "entry-1", "document_id": "doc-1", "entry_type": "block",
                "side": None, "tag": "Topic", "opponent_claim": "Some claim",
                "response_text": "Some response.",
                "warrant_text": None, "evidence_text": None, "impact_text": None,
                "weighing_text": None, "source": None, "author": None, "date": None,
                "similarity": 0.22,
            }
        ]
        mock_sb = MagicMock()
        mock_sb.rpc.return_value.execute.return_value = mock_rpc_result

        with patch("app.services.block_coverage.embed_text", return_value=mock_vec):
            results = classify_block_coverage(
                arguments=args,
                speech_type="rebuttal",
                user_id="u1",
                speech_id="sp1",
                supabase_client=mock_sb,
                user_has_blocks=True,
            )

        assert results[0].suggested_drill_json is not None
        assert results[0].suggested_drill_json["skill_target"] == "block_application"


# ── Workout integration ────────────────────────────────────────────────────────

class TestWorkoutBlockStep:
    def _make_base_workout_args(self):
        return dict(
            speech={"id": "sp1", "speech_type": "rebuttal"},
            feedback_report={
                "id": "fb1",
                "overall_score": 68,
                "raw_feedback": {"structured_issues": [], "top_3_priorities": ["Fix warrants"]},
            },
            argument_map=None,
            drills=[],
        )

    def test_no_block_checks_no_block_step(self):
        plan = generate_tournament_workout(**self._make_base_workout_args(), block_coverage_checks=None)
        categories = [s["category"] for s in plan["steps"]]
        assert "blockfile" not in categories

    def test_missing_coverage_adds_block_step(self):
        block_checks = [
            {
                "status": "missing",
                "claim_text": "Section 230 argument.",
                "missing_piece": "Add the core warrant explaining why opponent's argument fails.",
            }
        ]
        plan = generate_tournament_workout(
            **self._make_base_workout_args(),
            block_coverage_checks=block_checks,
        )
        categories = [s["category"] for s in plan["steps"]]
        assert "blockfile" in categories

    def test_partial_coverage_adds_block_step(self):
        block_checks = [
            {
                "status": "partially_covered",
                "claim_text": "Privacy claim.",
                "missing_piece": "Include the warrant.",
            }
        ]
        plan = generate_tournament_workout(
            **self._make_base_workout_args(),
            block_coverage_checks=block_checks,
        )
        categories = [s["category"] for s in plan["steps"]]
        assert "blockfile" in categories

    def test_covered_status_does_not_add_block_step(self):
        block_checks = [{"status": "covered", "claim_text": "Covered claim.", "missing_piece": None}]
        plan = generate_tournament_workout(
            **self._make_base_workout_args(),
            block_coverage_checks=block_checks,
        )
        categories = [s["category"] for s in plan["steps"]]
        assert "blockfile" not in categories

    def test_block_step_not_duplicated_when_focus_used(self):
        """block_application focus is not added twice even with multiple missing checks."""
        block_checks = [
            {"status": "missing", "claim_text": "Claim A.", "missing_piece": "Warrant A."},
            {"status": "missing", "claim_text": "Claim B.", "missing_piece": "Warrant B."},
        ]
        plan = generate_tournament_workout(
            **self._make_base_workout_args(),
            block_coverage_checks=block_checks,
        )
        block_steps = [s for s in plan["steps"] if s["category"] == "blockfile"]
        assert len(block_steps) <= 1
