"""Tests for Evidence RAG v1 — semantic retrieval and upgraded support checks.

All external calls (OpenAI, Supabase) are mocked.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.document import EvidenceCardRow, EvidenceSupportLevel, RetrievalMode, SemanticChunkResult
from app.services.evidence_support_check import (
    SupportCheckResult,
    _rank_candidates,
    _retrieve_semantic_candidates,
    check_claim_support,
)


# ── Factories ──────────────────────────────────────────────────────────────────

def _make_card(
    card_id: str = "card-1",
    card_text: str = "Trade agreements reduce tariffs and increase GDP growth.",
    author: str = "Smith",
    year: int = 2023,
) -> EvidenceCardRow:
    return EvidenceCardRow(
        id=card_id,
        document_id="doc-1",
        user_id="user-1",
        chunk_id=None,
        tag="Trade",
        author=author,
        source="Journal of Economics",
        year=year,
        card_text=card_text,
        claim_summary=None,
        attribution_complete=bool(author and year),
        metadata_json={},
        created_at="2026-06-09T00:00:00Z",
    )


def _make_chunk(
    chunk_id: str = "chunk-1",
    chunk_text: str = "Trade agreements lead to GDP growth by reducing tariff barriers.",
    similarity: float = 0.82,
) -> SemanticChunkResult:
    return SemanticChunkResult(
        id=chunk_id,
        document_id="doc-1",
        user_id="user-1",
        chunk_text=chunk_text,
        chunk_index=0,
        heading=None,
        page_number=None,
        metadata_json={},
        created_at="2026-06-09T00:00:00Z",
        similarity=similarity,
    )


def _mock_llm_response(level: str, explanation: str, rationale: str = "", missing: str | None = None):
    mock_result = MagicMock()
    mock_result.support_level = level
    mock_result.explanation = explanation
    mock_result.support_rationale = rationale
    mock_result.missing_link = missing

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.parsed = mock_result
    return mock_response


# ── _rank_candidates (keyword path) ───────────────────────────────────────────

class TestRankCandidates:
    def test_returns_sorted_by_overlap(self):
        cards = [
            _make_card("c1", "nuclear energy climate change carbon emissions"),
            _make_card("c2", "trade agreements GDP tariffs growth economics"),
        ]
        ranked = _rank_candidates("trade agreements GDP", None, cards)
        assert ranked[0][1].id == "c2"

    def test_filters_below_min_overlap(self):
        cards = [_make_card("c1", "completely unrelated content about sports")]
        ranked = _rank_candidates("nuclear energy policy", None, cards)
        assert len(ranked) == 0

    def test_combines_claim_and_evidence_text(self):
        card = _make_card("c1", "nuclear deterrence stability arms control policy")
        ranked = _rank_candidates("deterrence policy", "arms control stabilizes nations", [card])
        assert len(ranked) == 1

    def test_returns_empty_for_empty_cards(self):
        assert _rank_candidates("some claim", None, []) == []


# ── _retrieve_semantic_candidates ─────────────────────────────────────────────

class TestRetrieveSemanticCandidates:
    def test_returns_empty_on_embed_failure(self):
        with patch("app.services.embeddings.embed_text", side_effect=Exception("API down")):
            result = _retrieve_semantic_candidates("some claim", None, "user-1")
        assert result == []

    def test_returns_empty_when_rpc_fails(self):
        fake_emb = [0.1] * 1536
        fake_pg_str = "[" + ",".join(["0.10000000"] * 1536) + "]"
        with patch("app.services.embeddings.embed_text", return_value=fake_emb), \
             patch("app.services.embeddings.vector_to_pg_str", return_value=fake_pg_str), \
             patch("app.services.supabase_client.get_supabase") as mock_sb:
            mock_sb.return_value.rpc.return_value.execute.side_effect = Exception("RPC error")
            result = _retrieve_semantic_candidates("some claim", None, "user-1")
        assert result == []

    def test_returns_candidates_on_success(self):
        fake_emb = [0.1] * 1536
        fake_pg_str = "[" + ",".join(["0.10000000"] * 1536) + "]"
        chunk_row = {
            "id": "chunk-1",
            "document_id": "doc-1",
            "user_id": "user-1",
            "chunk_text": "Trade agreements reduce tariffs.",
            "chunk_index": 0,
            "heading": None,
            "page_number": None,
            "metadata_json": {},
            "created_at": "2026-06-09T00:00:00Z",
            "similarity": 0.85,
        }
        with patch("app.services.embeddings.embed_text", return_value=fake_emb), \
             patch("app.services.embeddings.vector_to_pg_str", return_value=fake_pg_str), \
             patch("app.services.supabase_client.get_supabase") as mock_sb:
            mock_sb.return_value.rpc.return_value.execute.return_value = MagicMock(data=[chunk_row])
            result = _retrieve_semantic_candidates("trade agreements lower tariffs", None, "user-1")
        assert len(result) == 1
        assert result[0].id == "chunk-1"
        assert result[0].similarity == 0.85

    def test_passes_user_id_to_rpc(self):
        fake_emb = [0.1] * 1536
        fake_pg_str = "[" + ",".join(["0.10000000"] * 1536) + "]"
        captured_params = {}
        def capture_rpc(name, params):
            captured_params.update(params)
            mock = MagicMock()
            mock.execute.return_value = MagicMock(data=[])
            return mock
        with patch("app.services.embeddings.embed_text", return_value=fake_emb), \
             patch("app.services.embeddings.vector_to_pg_str", return_value=fake_pg_str), \
             patch("app.services.supabase_client.get_supabase") as mock_sb:
            mock_sb.return_value.rpc.side_effect = capture_rpc
            _retrieve_semantic_candidates("claim text", None, "target-user-id")
        assert captured_params.get("match_user_id") == "target-user-id"


# ── check_claim_support ────────────────────────────────────────────────────────

class TestCheckClaimSupport:
    def test_unverifiable_when_no_library(self):
        result = check_claim_support("some claim", None, [])
        assert result.support_level == EvidenceSupportLevel.UNVERIFIABLE
        assert result.retrieval_mode == RetrievalMode.NONE

    def test_semantic_path_used_when_user_id_provided(self):
        cards = [_make_card()]
        chunk = _make_chunk(similarity=0.80)

        fake_emb = [0.1] * 1536
        fake_pg_str = "[" + ",".join(["0.10000000"] * 1536) + "]"
        chunk_row = {
            "id": chunk.id,
            "document_id": "doc-1",
            "user_id": "user-1",
            "chunk_text": chunk.chunk_text,
            "chunk_index": 0,
            "heading": None,
            "page_number": None,
            "metadata_json": {},
            "created_at": "2026-06-09T00:00:00Z",
            "similarity": 0.80,
        }
        mock_response = _mock_llm_response(
            "supported",
            "The card says 'GDP growth'.",
            "Card directly matches.",
            None,
        )
        with patch("app.services.embeddings.embed_text", return_value=fake_emb), \
             patch("app.services.embeddings.vector_to_pg_str", return_value=fake_pg_str), \
             patch("app.services.supabase_client.get_supabase") as mock_sb, \
             patch("app.services.evidence_support_check.openai.OpenAI") as MockOpenAI:
            mock_sb.return_value.rpc.return_value.execute.return_value = MagicMock(data=[chunk_row])
            MockOpenAI.return_value.beta.chat.completions.parse.return_value = mock_response
            result = check_claim_support(
                "trade agreements increase GDP",
                None,
                cards,
                user_id="user-1",
            )
        assert result.retrieval_mode == RetrievalMode.SEMANTIC
        assert result.support_level == "supported"
        assert len(result.matched_chunk_ids) == 1
        assert result.top_similarity == 0.80

    def test_keyword_fallback_when_no_semantic_results(self):
        cards = [_make_card(card_text="trade agreements lower tariffs increase growth")]
        fake_emb = [0.1] * 1536
        fake_pg_str = "[" + ",".join(["0.10000000"] * 1536) + "]"
        mock_llm_response = _mock_llm_response("supported", "Card matches.")

        with patch("app.services.embeddings.embed_text", return_value=fake_emb), \
             patch("app.services.embeddings.vector_to_pg_str", return_value=fake_pg_str), \
             patch("app.services.supabase_client.get_supabase") as mock_sb, \
             patch("app.services.evidence_support_check.openai.OpenAI") as MockOpenAI:
            # Semantic returns no results
            mock_sb.return_value.rpc.return_value.execute.return_value = MagicMock(data=[])
            MockOpenAI.return_value.beta.chat.completions.parse.return_value = mock_llm_response
            result = check_claim_support(
                "trade agreements lower tariffs",
                None,
                cards,
                user_id="user-1",
            )
        assert result.retrieval_mode == RetrievalMode.KEYWORD

    def test_keyword_fallback_when_no_user_id(self):
        cards = [_make_card(card_text="nuclear deterrence stability international relations")]
        mock_llm_response = _mock_llm_response("partially_supported", "Card partially matches.")

        with patch("app.services.evidence_support_check.openai.OpenAI") as MockOpenAI:
            MockOpenAI.return_value.beta.chat.completions.parse.return_value = mock_llm_response
            result = check_claim_support(
                "nuclear deterrence prevents war",
                None,
                cards,
                user_id=None,  # no user_id → keyword only
            )
        assert result.retrieval_mode == RetrievalMode.KEYWORD

    def test_unverifiable_when_no_keyword_matches_and_no_semantic(self):
        cards = [_make_card(card_text="completely unrelated sports content")]
        fake_emb = [0.1] * 1536
        fake_pg_str = "[" + ",".join(["0.10000000"] * 1536) + "]"
        with patch("app.services.embeddings.embed_text", return_value=fake_emb), \
             patch("app.services.embeddings.vector_to_pg_str", return_value=fake_pg_str), \
             patch("app.services.supabase_client.get_supabase") as mock_sb:
            mock_sb.return_value.rpc.return_value.execute.return_value = MagicMock(data=[])
            result = check_claim_support(
                "nuclear non-proliferation treaty",
                None,
                cards,
                user_id="user-1",
            )
        assert result.support_level == EvidenceSupportLevel.UNVERIFIABLE

    def test_retrieved_snippets_populated_on_semantic_path(self):
        cards = [_make_card()]
        fake_emb = [0.1] * 1536
        fake_pg_str = "[" + ",".join(["0.10000000"] * 1536) + "]"
        chunk_row = {
            "id": "chunk-abc",
            "document_id": "doc-1",
            "user_id": "user-1",
            "chunk_text": "Trade policy evidence snippet here.",
            "chunk_index": 0,
            "heading": "Contention 1",
            "page_number": None,
            "metadata_json": {},
            "created_at": "2026-06-09T00:00:00Z",
            "similarity": 0.75,
        }
        mock_response = _mock_llm_response("supported", "Evidence matches.", "Direct support.", None)

        with patch("app.services.embeddings.embed_text", return_value=fake_emb), \
             patch("app.services.embeddings.vector_to_pg_str", return_value=fake_pg_str), \
             patch("app.services.supabase_client.get_supabase") as mock_sb, \
             patch("app.services.evidence_support_check.openai.OpenAI") as MockOpenAI:
            mock_sb.return_value.rpc.return_value.execute.return_value = MagicMock(data=[chunk_row])
            MockOpenAI.return_value.beta.chat.completions.parse.return_value = mock_response
            result = check_claim_support("trade policy claim", None, cards, user_id="user-1")

        assert len(result.retrieved_snippets) == 1
        snippet = result.retrieved_snippets[0]
        assert snippet["chunk_id"] == "chunk-abc"
        assert snippet["similarity"] == 0.75
        assert "snippet" in snippet

    def test_support_rationale_and_missing_link_populated(self):
        cards = [_make_card()]
        fake_emb = [0.1] * 1536
        fake_pg_str = "[" + ",".join(["0.10000000"] * 1536) + "]"
        chunk_row = {
            "id": "chunk-1",
            "document_id": "doc-1",
            "user_id": "user-1",
            "chunk_text": "GDP evidence here.",
            "chunk_index": 0,
            "heading": None,
            "page_number": None,
            "metadata_json": {},
            "created_at": "2026-06-09T00:00:00Z",
            "similarity": 0.60,
        }
        mock_response = _mock_llm_response(
            "partially_supported",
            "Card covers topic but not magnitude.",
            "Card supports general direction.",
            "Need a card that proves the 10% GDP increase specifically.",
        )
        with patch("app.services.embeddings.embed_text", return_value=fake_emb), \
             patch("app.services.embeddings.vector_to_pg_str", return_value=fake_pg_str), \
             patch("app.services.supabase_client.get_supabase") as mock_sb, \
             patch("app.services.evidence_support_check.openai.OpenAI") as MockOpenAI:
            mock_sb.return_value.rpc.return_value.execute.return_value = MagicMock(data=[chunk_row])
            MockOpenAI.return_value.beta.chat.completions.parse.return_value = mock_response
            result = check_claim_support("GDP grows 10%", None, cards, user_id="user-1")

        assert result.support_rationale == "Card supports general direction."
        assert result.missing_link == "Need a card that proves the 10% GDP increase specifically."

    def test_no_outside_knowledge_in_prompt(self):
        """Verify the LLM system prompt explicitly prohibits outside knowledge."""
        from app.services.evidence_support_check import _SYSTEM_PROMPT_V2
        assert "outside knowledge" in _SYSTEM_PROMPT_V2.lower()

    def test_only_uploaded_library_used(self):
        """Verify that the support check result message references uploaded library."""
        result = check_claim_support("any claim", None, [])
        assert "uploaded" in result.explanation.lower() or result.support_level == EvidenceSupportLevel.UNVERIFIABLE
