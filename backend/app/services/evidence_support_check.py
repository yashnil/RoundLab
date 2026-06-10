"""Evidence support check service — Evidence RAG v1.

Two-path retrieval:

  SEMANTIC path (preferred):
    1. Embed the claim + evidence text from speech.
    2. Call match_document_chunks RPC to find top-8 semantically similar chunks.
    3. Feed retrieved snippets into LLM classifier.
    4. Return support level, explanation, rationale, missing_link, and snippets.

  KEYWORD fallback:
    Used when:
      - user_id not provided (backward compat)
      - RPC returns no results (chunks not yet embedded)
      - Embedding service unavailable
    Behavior identical to the original keyword-overlap classifier.

Support levels:
  supported           — uploaded chunk clearly supports the exact claim/warrant
  partially_supported — chunk is relevant but does not prove specific magnitude/impact
  unsupported         — chunk contradicts or is completely irrelevant to the claim
  unverifiable        — no matching chunk/card found at all
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

import openai
from pydantic import BaseModel

from app.config import settings
from app.models.document import (
    EvidenceCardRow,
    EvidenceSupportLevel,
    RetrievalMode,
    SemanticChunkResult,
)

logger = logging.getLogger(__name__)

# Keyword fallback: minimum word-overlap score to consider a card a candidate
_MIN_OVERLAP_SCORE = 2
# Maximum candidates sent to LLM
_MAX_CANDIDATES = 5

# Semantic: chunks returned below this similarity are treated as no-match
_SEMANTIC_SIMILARITY_THRESHOLD = 0.30
_SEMANTIC_MATCH_COUNT = 8

# Snippet character limit sent to LLM per chunk (keeps prompts tight)
_SNIPPET_CHARS = 600


# ── SupportCheckResult ─────────────────────────────────────────────────────────

@dataclass
class SupportCheckResult:
    support_level: str
    explanation: str
    matched_card: Optional[EvidenceCardRow] = None
    matched_chunk_ids: list[str] = field(default_factory=list)
    top_similarity: Optional[float] = None
    retrieved_snippets: list[dict[str, Any]] = field(default_factory=list)
    support_rationale: Optional[str] = None
    missing_link: Optional[str] = None
    retrieval_mode: str = RetrievalMode.NONE


# ── Keyword ranking (fallback) ─────────────────────────────────────────────────

_STOP_WORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "to", "of", "in",
    "on", "at", "by", "for", "with", "from", "this", "that",
    "it", "its", "they", "their", "and", "or", "but", "not",
    "if", "as", "so", "than", "more", "less", "such", "also",
})


def _keywords(text: str) -> set[str]:
    words = re.findall(r"\b[a-z]{3,}\b", text.lower())
    return {w for w in words if w not in _STOP_WORDS}


def _overlap_score(query_kw: set[str], card_text: str) -> int:
    return len(query_kw & _keywords(card_text))


def _rank_candidates(
    claim: str,
    evidence_from_speech: Optional[str],
    cards: list[EvidenceCardRow],
) -> list[tuple[int, EvidenceCardRow]]:
    query = f"{claim} {evidence_from_speech or ''}"
    query_kw = _keywords(query)
    if not query_kw:
        return []
    scored = [(_overlap_score(query_kw, c.card_text), c) for c in cards]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [(s, c) for s, c in scored if s >= _MIN_OVERLAP_SCORE]


# ── Semantic retrieval ─────────────────────────────────────────────────────────

def _retrieve_semantic_candidates(
    claim: str,
    evidence_from_speech: Optional[str],
    user_id: str,
) -> list[SemanticChunkResult]:
    """Embed the query and call match_document_chunks RPC.

    Returns an empty list (not an error) when:
      - embedding service fails
      - no chunks have embeddings yet
      - no chunks exceed the similarity threshold
    """
    try:
        from app.services.embeddings import embed_text, vector_to_pg_str
    except ImportError:
        logger.warning("evidence_support_check: embeddings module not available")
        return []

    try:
        query = f"{claim} {evidence_from_speech or ''}".strip()
        embedding = embed_text(query)
        embedding_str = vector_to_pg_str(embedding)
    except Exception as exc:
        logger.warning("evidence_support_check: embed_text failed | %s", exc)
        return []

    try:
        from app.services.supabase_client import get_supabase
        result = get_supabase().rpc(
            "match_document_chunks",
            {
                "query_embedding": embedding_str,
                "match_user_id": user_id,
                "match_count": _SEMANTIC_MATCH_COUNT,
                "similarity_threshold": _SEMANTIC_SIMILARITY_THRESHOLD,
            },
        ).execute()
        rows = result.data or []
        candidates = []
        for row in rows:
            try:
                candidates.append(SemanticChunkResult(**row))
            except Exception:
                pass
        logger.info(
            "evidence_support_check: semantic retrieval | user_id=%s candidates=%d",
            user_id,
            len(candidates),
        )
        return candidates
    except Exception as exc:
        logger.warning("evidence_support_check: RPC failed | %s", exc)
        return []


# ── LLM classification — semantic path ────────────────────────────────────────

class _SupportCheckOutputV2(BaseModel):
    support_level: str
    explanation: str
    support_rationale: str
    missing_link: Optional[str] = None


_SYSTEM_PROMPT_V2 = """\
You are a debate coach reviewing whether an uploaded evidence library supports a debater's claim.

RULES — follow exactly:
1. Base your judgment ONLY on the provided evidence snippets below. Do not use outside knowledge.
2. The snippets come from the debater's own uploaded case files — no other sources exist.
3. Choose exactly one support_level:
   - supported: a snippet clearly establishes the specific claim and its mechanism
   - partially_supported: a snippet is relevant to the topic but does not prove the exact claim, magnitude, or impact
   - unsupported: snippets contradict the claim or are completely irrelevant
   - unverifiable: no provided snippet addresses the claim at all
4. In explanation and support_rationale, quote or closely paraphrase actual snippet text.
   Do NOT invent evidence, references, or sources not present in the snippets.
5. In missing_link: if not supported, state in one sentence what would make the claim supported.
   If already supported, set missing_link to null.
"""


def _classify_with_semantic_candidates(
    claim: str,
    evidence_from_speech: Optional[str],
    candidates: list[SemanticChunkResult],
) -> tuple[str, str, Optional[str], Optional[str]]:
    """LLM classification over semantic chunk candidates.

    Returns (support_level, explanation, support_rationale, missing_link).
    """
    if not settings.openai_api_key:
        return EvidenceSupportLevel.UNVERIFIABLE, "OpenAI API key not configured.", None, None

    snippet_blocks = "\n\n---\n\n".join(
        f"Snippet {i + 1} (similarity {c.similarity:.2f}):\n{c.chunk_text[:_SNIPPET_CHARS]}"
        for i, c in enumerate(candidates)
    )

    user_msg = (
        f"Debater's claim: {claim}\n"
        f"Debater's cited evidence: {evidence_from_speech or '(none stated)'}\n\n"
        f"Evidence snippets from uploaded library:\n{snippet_blocks}"
    )

    try:
        client = openai.OpenAI(api_key=settings.openai_api_key)
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT_V2},
                {"role": "user", "content": user_msg},
            ],
            response_format=_SupportCheckOutputV2,
            max_tokens=300,
        )
        result = response.choices[0].message.parsed
        if result is None:
            return EvidenceSupportLevel.UNVERIFIABLE, "Could not classify support.", None, None

        level = result.support_level
        if level not in {
            EvidenceSupportLevel.SUPPORTED,
            EvidenceSupportLevel.PARTIALLY_SUPPORTED,
            EvidenceSupportLevel.UNSUPPORTED,
            EvidenceSupportLevel.UNVERIFIABLE,
        }:
            level = EvidenceSupportLevel.UNVERIFIABLE

        return level, result.explanation, result.support_rationale, result.missing_link

    except openai.AuthenticationError:
        return EvidenceSupportLevel.UNVERIFIABLE, "API authentication error.", None, None
    except Exception as exc:
        logger.warning("evidence_support_check: LLM v2 failed | %s", exc)
        return EvidenceSupportLevel.UNVERIFIABLE, "Could not complete support check.", None, None


# ── LLM classification — keyword fallback path ────────────────────────────────

class _SupportCheckOutputV1(BaseModel):
    support_level: str
    explanation: str


_SYSTEM_PROMPT_V1 = """\
You are a debate coach reviewing whether an uploaded evidence card supports a debater's claim.

RULES — follow exactly:
1. Base your judgment ONLY on the provided card text below. Do not use outside knowledge.
2. If none of the provided card texts support the claim, output support_level = "unverifiable".
3. Choose exactly one support_level from: supported, partially_supported, unsupported, unverifiable.
   - supported: the card clearly establishes the specific claim and mechanism
   - partially_supported: the card is relevant but does not prove the exact claim or magnitude
   - unsupported: the card contradicts the claim or is completely irrelevant
   - unverifiable: no provided card addresses the claim at all
4. In explanation, quote or closely paraphrase the card text you relied on. Do not invent evidence.
"""


def _classify_with_llm(
    claim: str,
    evidence_from_speech: Optional[str],
    candidates: list[EvidenceCardRow],
) -> tuple[str, str]:
    """Keyword-path LLM classification. Returns (level, explanation)."""
    if not settings.openai_api_key:
        return EvidenceSupportLevel.UNVERIFIABLE, "OpenAI API key not configured."

    card_blocks = "\n\n---\n\n".join(
        f"CARD {i + 1} (author: {c.author or 'unknown'}, year: {c.year or 'unknown'}):\n{c.card_text[:800]}"
        for i, c in enumerate(candidates)
    )

    user_msg = (
        f"Debater's claim: {claim}\n"
        f"Debater's cited evidence: {evidence_from_speech or '(none stated)'}\n\n"
        f"Uploaded evidence cards:\n{card_blocks}"
    )

    try:
        client = openai.OpenAI(api_key=settings.openai_api_key)
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT_V1},
                {"role": "user", "content": user_msg},
            ],
            response_format=_SupportCheckOutputV1,
            max_tokens=200,
        )
        result = response.choices[0].message.parsed
        if result is None:
            return EvidenceSupportLevel.UNVERIFIABLE, "Could not classify support."

        level = result.support_level
        if level not in {
            EvidenceSupportLevel.SUPPORTED,
            EvidenceSupportLevel.PARTIALLY_SUPPORTED,
            EvidenceSupportLevel.UNSUPPORTED,
            EvidenceSupportLevel.UNVERIFIABLE,
        }:
            level = EvidenceSupportLevel.UNVERIFIABLE

        return level, result.explanation

    except openai.AuthenticationError:
        return EvidenceSupportLevel.UNVERIFIABLE, "API authentication error."
    except Exception as exc:
        logger.warning("evidence_support_check: LLM v1 failed | %s", exc)
        return EvidenceSupportLevel.UNVERIFIABLE, "Could not complete support check."


# ── Public entry point ─────────────────────────────────────────────────────────

def check_claim_support(
    claim: str,
    evidence_from_speech: Optional[str],
    library_cards: list[EvidenceCardRow],
    user_id: Optional[str] = None,
) -> SupportCheckResult:
    """Check whether the user's uploaded evidence supports a speech claim.

    Args:
        claim: The debater's stated claim (from argument_map).
        evidence_from_speech: The evidence phrase the debater cited (may be None).
        library_cards: All evidence cards in the user's library (for keyword fallback).
        user_id: When provided, enables semantic retrieval via pgvector RPC.

    Semantic path (preferred):
        Embeds query → calls match_document_chunks → LLM classifies snippets.
    Keyword fallback:
        Used when user_id is absent, no chunks are embedded, or RPC fails.

    Always returns unverifiable when the library is empty.
    """
    if not library_cards:
        return SupportCheckResult(
            support_level=EvidenceSupportLevel.UNVERIFIABLE,
            explanation="No evidence has been uploaded to your library.",
            retrieval_mode=RetrievalMode.NONE,
        )

    # ── Semantic path ──────────────────────────────────────────────────────────
    if user_id:
        candidates = _retrieve_semantic_candidates(claim, evidence_from_speech, user_id)

        if candidates:
            level, explanation, rationale, missing_link = _classify_with_semantic_candidates(
                claim, evidence_from_speech, candidates
            )

            top_sim = candidates[0].similarity if candidates else None
            chunk_ids = [c.id for c in candidates]
            snippets = [
                {
                    "chunk_id": c.id,
                    "document_id": c.document_id,
                    "snippet": c.chunk_text[:_SNIPPET_CHARS],
                    "similarity": round(c.similarity, 4),
                    "heading": c.heading,
                }
                for c in candidates
            ]

            logger.info(
                "evidence_support_check: semantic | level=%s top_sim=%.3f chunks=%d",
                level,
                top_sim or 0.0,
                len(candidates),
            )

            return SupportCheckResult(
                support_level=level,
                explanation=explanation,
                matched_card=None,  # semantic path uses chunks, not card objects
                matched_chunk_ids=chunk_ids,
                top_similarity=top_sim,
                retrieved_snippets=snippets,
                support_rationale=rationale,
                missing_link=missing_link,
                retrieval_mode=RetrievalMode.SEMANTIC,
            )

        # Semantic returned nothing — fall through to keyword
        logger.info(
            "evidence_support_check: semantic returned no candidates, falling back to keyword"
        )

    # ── Keyword fallback ───────────────────────────────────────────────────────
    ranked = _rank_candidates(claim, evidence_from_speech, library_cards)

    if not ranked:
        return SupportCheckResult(
            support_level=EvidenceSupportLevel.UNVERIFIABLE,
            explanation=(
                "No uploaded evidence cards matched the keywords in your claim. "
                "Upload a case file that includes evidence for this argument."
            ),
            retrieval_mode=RetrievalMode.KEYWORD,
        )

    top_candidates = [card for _, card in ranked[:_MAX_CANDIDATES]]
    level, explanation = _classify_with_llm(claim, evidence_from_speech, top_candidates)

    best_card = top_candidates[0] if level != EvidenceSupportLevel.UNVERIFIABLE else None

    logger.info(
        "evidence_support_check: keyword | level=%s candidates=%d",
        level,
        len(top_candidates),
    )

    return SupportCheckResult(
        support_level=level,
        explanation=explanation,
        matched_card=best_card,
        retrieval_mode=RetrievalMode.KEYWORD,
    )
