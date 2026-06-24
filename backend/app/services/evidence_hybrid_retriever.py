"""Hybrid evidence retrieval: BM25 + optional semantic, fused via RRF.

Improves over the heuristic reranker by combining two independent ranking
signals with Reciprocal Rank Fusion (RRF), making the ranking more robust
than either signal alone and more robust than a linear score combination.

Architecture:
- BM25 lexical signal uses the existing evidence_candidate_ranker.rank_candidate_windows().
- Semantic signal uses the existing _semantic_score() hook (only when enabled).
- RRF combines the two rankings (k=60 per Cormack et al., 2009).
- A small credibility bonus is applied after RRF to slightly prefer higher-quality sources.

SAFETY INVARIANTS:
- No text is modified. passage.text is the exact source passage.
- Semantic scoring failure degrades gracefully to BM25 only.
- Candidates are never fabricated or reordered beyond what the scores warrant.
- Scores on returned EvidenceCandidate objects are informational only; they
  never alter body_text.
"""

from __future__ import annotations

import logging

from app.services.evidence_candidate import EvidenceCandidate, RetrievalStats

logger = logging.getLogger(__name__)

# ── RRF ──────────────────────────────────────────────────────────────────────

_RRF_K_DEFAULT = 60  # Cormack et al. 2009 empirical default
_CREDIBILITY_WEIGHT = 0.02  # small bonus per normalized credibility unit


def _rrf_scores(
    n_items: int,
    rankings: list[list[int]],
    k: int = _RRF_K_DEFAULT,
    weights: list[float] | None = None,
) -> list[float]:
    """Reciprocal Rank Fusion across multiple ranked index lists.

    Args:
        n_items:  total number of items (indices 0..n_items-1).
        rankings: each inner list is a ranking of item indices, best-first.
                  Items missing from a ranking get score 0 from that source.
        k:        RRF constant (default 60).
        weights:  per-ranking weight multipliers (default 1.0 each).

    Returns list of RRF scores, one per item, higher = more relevant.
    """
    if weights is None:
        weights = [1.0] * len(rankings)
    scores = [0.0] * n_items
    for rank_list, w in zip(rankings, weights):
        for pos, idx in enumerate(rank_list):
            if 0 <= idx < n_items:
                scores[idx] += w / (k + pos)
    return scores


# ── Public API ────────────────────────────────────────────────────────────────


def hybrid_rank_passages(
    candidates: list[EvidenceCandidate],
    *,
    claim: str,
    topic: str = "",
    role: str = "direct_support",
    role_target: str = "",
    entities: list[str] | None = None,
    source_authority: float = 0.0,
    rrf_k: int = _RRF_K_DEFAULT,
    max_passages: int = 10,
) -> tuple[list[EvidenceCandidate], RetrievalStats]:
    """Rank passage candidates with hybrid BM25 + optional semantic RRF.

    Args:
        candidates:       passage candidates to rank (may be mutated to set scores).
        claim:            the claim the evidence should support.
        topic:            debate topic string (fed into BM25 query).
        role:             evidence role for role-signal scoring.
        role_target:      specific aspect of the claim (slot target).
        entities:         named entities from the claim for entity-overlap scoring.
        source_authority: normalized (0–1) credibility of the source.
        rrf_k:            RRF constant.
        max_passages:     return at most this many candidates.

    Returns (ranked_candidates, stats).
    The returned candidates are a (possibly shorter) subset of the input,
    sorted best-first, with lexical_score, semantic_score, and final_score set.
    """
    if not candidates:
        return [], RetrievalStats(backend="none")

    texts = [c.text for c in candidates]

    # ── BM25 lexical ranking ─────────────────────────────────────────────────
    from app.services.evidence_candidate_ranker import (
        rank_candidate_windows,
        _semantic_score,
        semantic_reranker_enabled,
    )

    bm25_windows = rank_candidate_windows(
        texts,
        topic=topic,
        claim=claim,
        role=role,
        role_target=role_target,
        source_authority=source_authority,
        entities=entities,
    )

    # Map passage text → its original index (handles the case where two
    # passages are identical text — uses first occurrence).
    text_to_orig: dict[str, int] = {}
    for i, t in enumerate(texts):
        if t not in text_to_orig:
            text_to_orig[t] = i

    # BM25 ranking: indices of candidates sorted by BM25 score (best-first).
    bm25_ranking: list[int] = []
    bm25_score_by_idx: dict[int, float] = {}
    bm25_sub_by_idx: dict[int, dict] = {}
    for w in bm25_windows:
        orig_idx = text_to_orig.get(w.text)
        if orig_idx is not None:
            bm25_ranking.append(orig_idx)
            bm25_score_by_idx[orig_idx] = w.score
            bm25_sub_by_idx[orig_idx] = w.subscores

    # Fill in any indices that didn't appear in bm25_windows (shouldn't happen,
    # but defensive).
    seen = set(bm25_ranking)
    for i in range(len(candidates)):
        if i not in seen:
            bm25_ranking.append(i)

    # ── Semantic ranking (optional) ──────────────────────────────────────────
    rankings: list[list[int]] = [bm25_ranking]
    weights: list[float] = [1.0]
    sem_backend = "none"
    sem_scores_list: list[float] | None = None

    if semantic_reranker_enabled():
        query_str = " ".join(p for p in [claim, topic, role_target] if p)
        try:
            sem_scores_list = _semantic_score(texts, query_str)
        except Exception as exc:  # pragma: no cover
            logger.debug("Semantic scorer failed in hybrid retriever: %s", exc)
            sem_scores_list = None

        if sem_scores_list is not None and len(sem_scores_list) == len(candidates):
            sem_order = sorted(range(len(texts)), key=lambda i: -sem_scores_list[i])  # type: ignore[index]
            rankings.append(sem_order)
            weights.append(0.5)  # lexical ranks 2× more than semantic
            sem_backend = "cross_encoder"

    # ── RRF fusion ───────────────────────────────────────────────────────────
    rrf = _rrf_scores(len(candidates), rankings, k=rrf_k, weights=weights)

    # Apply small credibility bonus on top of RRF
    final_scored: list[tuple[float, int]] = []
    for orig_idx, cand in enumerate(candidates):
        cred_bonus = cand.credibility_score * _CREDIBILITY_WEIGHT
        total = rrf[orig_idx] + cred_bonus
        final_scored.append((total, orig_idx))

    final_scored.sort(key=lambda x: (-x[0], x[1]))  # stable: score desc, then orig order

    # ── Build result list with updated scores ─────────────────────────────────
    result: list[EvidenceCandidate] = []
    for _, orig_idx in final_scored[:max_passages]:
        c = candidates[orig_idx]
        # BM25 subscores
        subs = bm25_sub_by_idx.get(orig_idx, {})
        c.lexical_score = round(subs.get("relevance", 0.0), 4)
        # Semantic score
        if sem_scores_list is not None and orig_idx < len(sem_scores_list):
            c.semantic_score = round(sem_scores_list[orig_idx], 4)
        c.final_score = round(rrf[orig_idx], 6)
        result.append(c)

    backend = "bm25+semantic" if sem_backend != "none" else "bm25"
    stats = RetrievalStats(
        backend=backend,
        total_in=len(candidates),
        total_out=len(result),
        rrf_k=rrf_k,
        semantic_available=sem_backend != "none",
    )
    return result, stats
