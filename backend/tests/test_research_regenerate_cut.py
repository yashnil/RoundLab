"""Tests for the POST /research/regenerate-cut endpoint.

The endpoint re-cuts a passage at a requested cut style. No auth or DB needed —
the passage is supplied in the request body. generate_evidence_cut is mocked so
no LLM is called.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.models.research import EvidenceCutResult, SelectedSpan

client = TestClient(app)

PASSAGE = (
    "Section 230 grants platforms broad immunity from civil liability. "
    "Courts have consistently held that platforms are not publishers. "
    "Critics argue this protection should be reformed."
)


def _fake_cut(cut_style: str, text: str = PASSAGE) -> EvidenceCutResult:
    return EvidenceCutResult(
        original_passage=PASSAGE,
        selected_spans=[SelectedSpan(start=0, end=len(text), text=text, sentence_index=0)],
        cut_text=text,
        cut_text_with_ellipses=text,
        compression_ratio=len(text) / max(len(PASSAGE), 1),
        confidence=0.8,
        cut_style="full" if cut_style == "full" else "medium_cut",
        validation_passed=True,
    )


class TestRegenerateCutEndpoint:
    def test_regenerate_cut_full_style(self):
        with patch(
            "app.api.research.generate_evidence_cut",
            return_value=_fake_cut("full"),
        ) as mock_cut:
            resp = client.post(
                "/research/regenerate-cut",
                json={
                    "original_passage": PASSAGE,
                    "claim": "Section 230 facilitates harm",
                    "cut_style": "full",
                    "use_llm": False,
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["cut_style_applied"] == "full"
        assert data["cut"]["cut_style"] == "full"
        # preferred_cut_style was forwarded
        _, kwargs = mock_cut.call_args
        assert kwargs["preferred_cut_style"] == "full"

    def test_regenerate_cut_aggressive_style(self):
        with patch(
            "app.api.research.generate_evidence_cut",
            return_value=_fake_cut("aggressive", "Section 230 grants platforms broad immunity"),
        ) as mock_cut:
            resp = client.post(
                "/research/regenerate-cut",
                json={
                    "original_passage": PASSAGE,
                    "claim": "Section 230 facilitates harm",
                    "evidence_role": "mechanism_support",
                    "cut_style": "aggressive",
                    "use_llm": False,
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["cut_style_applied"] == "aggressive"
        _, kwargs = mock_cut.call_args
        assert kwargs["preferred_cut_style"] == "aggressive"
        assert kwargs["use_llm"] is False

    def test_regenerate_cut_missing_passage_422(self):
        resp = client.post(
            "/research/regenerate-cut",
            json={"original_passage": "   ", "claim": "x", "cut_style": "medium"},
        )
        assert resp.status_code == 422

    def test_regenerate_cut_omitted_passage_422(self):
        resp = client.post(
            "/research/regenerate-cut",
            json={"claim": "x"},
        )
        assert resp.status_code == 422
