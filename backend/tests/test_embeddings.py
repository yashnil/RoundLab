"""Tests for the embeddings service.

All OpenAI API calls are mocked — no real API calls.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.embeddings import (
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    _normalize,
    embed_text,
    embed_texts,
    vector_to_pg_str,
)


# ── Fixtures / helpers ─────────────────────────────────────────────────────────

def _fake_embedding(n: int = EMBEDDING_DIM) -> list[float]:
    return [0.01 * i for i in range(n)]


def _mock_openai_response(embeddings: list[list[float]]):
    """Build a minimal mock that matches the OpenAI embeddings response shape."""
    mock_response = MagicMock()
    mock_response.data = [
        MagicMock(index=i, embedding=emb) for i, emb in enumerate(embeddings)
    ]
    return mock_response


# ── _normalize ─────────────────────────────────────────────────────────────────

class TestNormalize:
    def test_collapses_whitespace(self):
        result = _normalize("hello   world\n\nfoo")
        assert result == "hello world foo"

    def test_strips_leading_trailing(self):
        assert _normalize("  hello  ") == "hello"

    def test_truncates_to_max_chars(self):
        long_text = "a" * 30_000
        result = _normalize(long_text)
        assert len(result) <= 24_000

    def test_preserves_short_text_fully(self):
        text = "economic growth trade policy 2024"
        assert _normalize(text) == text


# ── embed_text ─────────────────────────────────────────────────────────────────

class TestEmbedText:
    def test_returns_list_of_correct_length(self):
        fake_emb = _fake_embedding()
        with patch("app.services.embeddings.openai.OpenAI") as MockOpenAI:
            client = MockOpenAI.return_value
            client.embeddings.create.return_value = _mock_openai_response([fake_emb])
            result = embed_text("trade policy claims growth")
        assert isinstance(result, list)
        assert len(result) == EMBEDDING_DIM

    def test_returns_floats(self):
        fake_emb = _fake_embedding()
        with patch("app.services.embeddings.openai.OpenAI") as MockOpenAI:
            client = MockOpenAI.return_value
            client.embeddings.create.return_value = _mock_openai_response([fake_emb])
            result = embed_text("some claim text here")
        assert all(isinstance(v, float) for v in result)

    def test_raises_for_empty_string(self):
        with pytest.raises(ValueError, match="must not be empty"):
            embed_text("")

    def test_raises_for_whitespace_only(self):
        with pytest.raises(ValueError, match="must not be empty"):
            embed_text("   ")

    def test_calls_correct_model(self):
        fake_emb = _fake_embedding()
        with patch("app.services.embeddings.openai.OpenAI") as MockOpenAI:
            client = MockOpenAI.return_value
            client.embeddings.create.return_value = _mock_openai_response([fake_emb])
            embed_text("some text")
            call_kwargs = client.embeddings.create.call_args[1]
        assert call_kwargs["model"] == EMBEDDING_MODEL

    def test_normalizes_input(self):
        fake_emb = _fake_embedding()
        captured_input = []
        with patch("app.services.embeddings.openai.OpenAI") as MockOpenAI:
            client = MockOpenAI.return_value
            def capture(**kwargs):
                captured_input.extend(kwargs["input"])
                return _mock_openai_response([fake_emb])
            client.embeddings.create.side_effect = capture
            embed_text("  hello   world  ")
        assert captured_input[0] == "hello world"


# ── embed_texts ────────────────────────────────────────────────────────────────

class TestEmbedTexts:
    def test_returns_correct_count(self):
        texts = ["text one", "text two", "text three"]
        fake_embs = [_fake_embedding() for _ in texts]
        with patch("app.services.embeddings.openai.OpenAI") as MockOpenAI:
            client = MockOpenAI.return_value
            client.embeddings.create.return_value = _mock_openai_response(fake_embs)
            result = embed_texts(texts)
        assert len(result) == 3

    def test_empty_input_returns_empty_list(self):
        result = embed_texts([])
        assert result == []

    def test_preserves_order(self):
        texts = ["alpha", "beta", "gamma"]
        # Each text gets a distinct embedding so we can verify ordering
        fake_embs = [[float(i)] * EMBEDDING_DIM for i in range(len(texts))]
        with patch("app.services.embeddings.openai.OpenAI") as MockOpenAI:
            client = MockOpenAI.return_value
            client.embeddings.create.return_value = _mock_openai_response(fake_embs)
            result = embed_texts(texts)
        assert result[0][0] == 0.0
        assert result[1][0] == 1.0
        assert result[2][0] == 2.0

    def test_makes_one_api_call_for_small_batch(self):
        texts = ["a", "b", "c"]
        fake_embs = [_fake_embedding() for _ in texts]
        with patch("app.services.embeddings.openai.OpenAI") as MockOpenAI:
            client = MockOpenAI.return_value
            client.embeddings.create.return_value = _mock_openai_response(fake_embs)
            embed_texts(texts)
        assert client.embeddings.create.call_count == 1

    def test_batches_large_input(self):
        # 120 texts with batch_size=50 should produce 3 calls
        texts = [f"text {i}" for i in range(120)]
        fake_embs_per_call = [_fake_embedding() for _ in range(50)]
        call_count = 0
        def make_response(**kwargs):
            nonlocal call_count
            n = len(kwargs["input"])
            call_count += 1
            return _mock_openai_response([_fake_embedding() for _ in range(n)])
        with patch("app.services.embeddings.openai.OpenAI") as MockOpenAI:
            client = MockOpenAI.return_value
            client.embeddings.create.side_effect = make_response
            result = embed_texts(texts)
        assert call_count == 3  # ceil(120/50)
        assert len(result) == 120

    def test_handles_whitespace_only_text(self):
        texts = ["real text", "   "]
        fake_embs = [_fake_embedding() for _ in texts]
        with patch("app.services.embeddings.openai.OpenAI") as MockOpenAI:
            client = MockOpenAI.return_value
            client.embeddings.create.return_value = _mock_openai_response(fake_embs)
            result = embed_texts(texts)
        assert len(result) == 2


# ── vector_to_pg_str ───────────────────────────────────────────────────────────

class TestVectorToPgStr:
    def test_correct_format(self):
        emb = [0.1, 0.2, 0.3]
        result = vector_to_pg_str(emb)
        assert result.startswith("[")
        assert result.endswith("]")
        assert "," in result

    def test_roundtrip_length(self):
        emb = _fake_embedding()
        s = vector_to_pg_str(emb)
        # Parse back to verify count
        values = [float(v) for v in s[1:-1].split(",")]
        assert len(values) == EMBEDDING_DIM

    def test_fixed_precision(self):
        emb = [1.0 / 3.0]
        s = vector_to_pg_str(emb)
        # Should have exactly 8 decimal places
        inner = s[1:-1]
        decimal_part = inner.split(".")[1]
        assert len(decimal_part) == 8
