"""Evidence candidate ranking for the card cutter.

Ranks article paragraph/sentence "windows" for how strong a debate card they
would make against a claim/topic/role — a real scoring layer instead of fragile
string heuristics.

Scoring is a hybrid of:
  - BM25 lexical relevance (rank_bm25, lightweight pure-python) against a query
    built from topic + claim + the slot's target,
  - entity overlap (named cases/laws/places carry debate weight),
  - role-specific signal (causal/legal/moral/impact language for the slot),
  - read-aloud coherence (complete sentences with a finite verb beat fragments).

Design notes / tool decision:
  - rank_bm25 chosen as the semantic-lexical backbone: tiny (numpy-only), no
    model download, deterministic — safe for local dev and CI.
  - A cross-encoder / sentence-transformers reranker would add true semantic
    scoring but pulls in torch (hundreds of MB); deferred. An optional hook
    (`_semantic_score`) is left so it can be enabled later without refactoring.
  - Everything degrades gracefully: if rank_bm25 is unavailable the ranker falls
    back to pure lexical overlap, so callers never crash.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_STOPWORDS = frozenset({
    "the", "a", "an", "of", "to", "in", "on", "for", "with", "at", "by", "from",
    "as", "and", "or", "but", "is", "are", "was", "were", "be", "been", "that",
    "this", "these", "those", "it", "its", "their", "they", "which", "who", "has",
    "have", "had", "not", "will", "would", "can", "could", "should", "may", "might",
})

_CAUSAL = frozenset({
    "because", "therefore", "thus", "hence", "result", "results", "cause", "causes",
    "leads", "enables", "prevents", "requires", "shows", "demonstrates", "proves",
    "found", "held", "ruled", "argues", "establishes",
})
_LEGAL = frozenset({
    "court", "law", "legal", "statute", "ruling", "doctrine", "immunity",
    "liability", "treaty", "convention", "sovereignty", "jurisdiction", "r2p",
    "resolution", "charter", "legitimacy",
})
_MORAL = frozenset({
    "moral", "ethical", "obligation", "duty", "rights", "justice", "genocide",
    "atrocity", "atrocities", "suffering", "humanitarian", "dignity",
})
_IMPACT = frozenset({
    "million", "billion", "percent", "thousand", "deaths", "killed", "displaced",
    "casualties", "crisis", "threat", "war", "economy", "economic", "stability",
})

_ROLE_SIGNALS: dict[str, frozenset] = {
    "direct_support": _CAUSAL,
    "mechanism_support": _CAUSAL | _LEGAL,
    "example_support": _IMPACT | _MORAL,
    "impact_support": _IMPACT,
    "definition_support": _LEGAL,
    "authority_support": _LEGAL | _CAUSAL,
}


@dataclass
class CandidateWindow:
    text: str
    start: int = 0          # char offset in the source (optional)
    end: int = 0
    score: float = 0.0
    subscores: dict = field(default_factory=dict)


def _tokenize(text: str) -> list[str]:
    return [w for w in re.sub(r"[^\w\s]", " ", (text or "").lower()).split() if w not in _STOPWORDS]


def _has_finite_verb(text: str) -> bool:
    return bool(re.search(
        r"\b(?:is|are|was|were|be|been|has|have|had|do|does|did|will|would|can|"
        r"could|should|may|might|must|argue[sd]?|show[sn]?|found|held|rule[sd]?|"
        r"state[sd]?|grant[sd]?|provide[sd]?|enable[sd]?|prevent[sd]?|require[sd]?|"
        r"cause[sd]?|lead[s]?|demonstrate[sd]?|justif(?:y|ies|ied)|prove[sd]?|"
        r"engage[sd]?|protect[sd]?|emerge[sd]?|allow[sed]*)\b",
        (text or ""), re.IGNORECASE,
    ))


def _build_query(topic: str, claim: str, role_target: str) -> list[str]:
    return _tokenize(" ".join(p for p in (topic, claim, role_target) if p))


def _bm25_scores(candidates: list[str], query_tokens: list[str]) -> list[float] | None:
    """BM25 relevance per candidate, or None if rank_bm25 is unavailable."""
    if not query_tokens:
        return None
    try:
        from rank_bm25 import BM25Okapi
        corpus = [_tokenize(c) or ["_"] for c in candidates]
        bm = BM25Okapi(corpus)
        raw = list(bm.get_scores(query_tokens))
        hi = max(raw) if raw else 0.0
        return [float(s) / hi if hi > 0 else 0.0 for s in raw]  # normalize 0-1
    except Exception as exc:  # pragma: no cover - import/env dependent
        logger.debug("rank_bm25 unavailable, using lexical overlap: %s", exc)
        return None


def _lexical_overlap(cand_tokens: set[str], query_tokens: set[str]) -> float:
    if not query_tokens:
        return 0.0
    return len(cand_tokens & query_tokens) / len(query_tokens)


# A pluggable semantic scorer. Tests (and deployments) can install one with
# set_semantic_scorer(fn); fn(candidates, query) -> list[float] in [0,1] (any
# length-matching, order-preserving relevance scores). Kept out of the default
# path so local dev never pulls a model.
_SEMANTIC_SCORER = None


def set_semantic_scorer(fn) -> None:
    """Register (or clear, with None) the semantic scoring backend."""
    global _SEMANTIC_SCORER
    _SEMANTIC_SCORER = fn


def semantic_reranker_enabled() -> bool:
    """True when semantic reranking is switched on AND a scorer is available."""
    try:
        from app.config import settings
        flag = bool(getattr(settings, "use_semantic_reranker", False))
    except Exception:  # pragma: no cover
        flag = False
    return flag and _SEMANTIC_SCORER is not None


def _try_load_sentence_transformer_scorer():
    """Best-effort loader for a local CrossEncoder if the package + flag exist.

    Never imports torch unless explicitly enabled; returns a callable or None.
    This is the seam where a real reranker plugs in without touching callers.
    """
    try:
        from app.config import settings
        if not getattr(settings, "use_semantic_reranker", False):
            return None
        from sentence_transformers import CrossEncoder  # type: ignore
        model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

        def _score(cands: list[str], query: str) -> list[float]:
            pairs = [(query, c) for c in cands]
            raw = list(model.predict(pairs))
            hi = max(raw) if raw else 0.0
            lo = min(raw) if raw else 0.0
            rng = (hi - lo) or 1.0
            return [float((s - lo) / rng) for s in raw]

        return _score
    except Exception as exc:  # pragma: no cover - optional/heavy
        logger.debug("sentence-transformers reranker unavailable: %s", exc)
        return None


def _semantic_score(candidates: list[str], query: str) -> list[float] | None:
    """Optional semantic relevance per candidate, or None when not configured.

    Resolution order: an explicitly-registered scorer (tests/deployments) →
    a lazily-loaded local CrossEncoder when USE_SEMANTIC_RERANKER is on. Returns
    None (BM25 + heuristics only) whenever nothing is available.
    """
    global _SEMANTIC_SCORER
    if _SEMANTIC_SCORER is None:
        loaded = _try_load_sentence_transformer_scorer()
        if loaded is not None:
            _SEMANTIC_SCORER = loaded
    if not semantic_reranker_enabled():
        return None
    try:
        scores = _SEMANTIC_SCORER(candidates, query)  # type: ignore[misc]
        if scores and len(scores) == len(candidates):
            return [float(s) for s in scores]
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("semantic scorer failed, using BM25 only: %s", exc)
    return None


def rank_candidate_windows(
    candidates: list[str],
    topic: str = "",
    claim: str = "",
    role: str = "",
    role_target: str = "",
    source_authority: float = 0.0,
    entities: list[str] | None = None,
) -> list[CandidateWindow]:
    """Score and rank candidate passages for debate-card worthiness.

    Returns CandidateWindow objects sorted best-first. Deterministic. Combines
    BM25 (or lexical fallback) relevance with entity/role/coherence signals.
    """
    if not candidates:
        return []

    query_tokens = _build_query(topic, claim, role_target)
    query_set = set(query_tokens)
    entities = entities or []
    entity_low = [e.lower() for e in entities]
    role_signal = _ROLE_SIGNALS.get(role, _CAUSAL)

    bm25 = _bm25_scores(candidates, query_tokens)
    semantic = _semantic_score(candidates, " ".join([topic, claim, role_target]))

    windows: list[CandidateWindow] = []
    for i, text in enumerate(candidates):
        toks = _tokenize(text)
        tok_set = set(toks)
        low = text.lower()
        n_words = len(text.split())

        rel = bm25[i] if bm25 is not None else _lexical_overlap(tok_set, query_set)
        sem = semantic[i] if semantic is not None else 0.0
        entity = sum(1 for e in entity_low if e and e in low) * 0.6
        role_sc = min(1.2, len(tok_set & role_signal) * 0.3)
        # Read-aloud coherence: reward complete, verb-bearing, reasonably-sized lines.
        coherence = 0.0
        if _has_finite_verb(text):
            coherence += 0.8
        if text[:1].isupper():
            coherence += 0.3
        if 8 <= n_words <= 45:
            coherence += 0.4
        elif n_words < 5:
            coherence -= 0.6  # fragment penalty
        if re.search(r"\d", text):
            coherence += 0.2
        # Penalize lines that read like titles / metadata (no verb, Title Case).
        if not _has_finite_verb(text) and sum(1 for w in text.split() if w[:1].isupper()) > n_words * 0.6:
            coherence -= 0.8

        score = (
            rel * 3.0
            + sem * 2.0
            + entity
            + role_sc
            + coherence
            + source_authority * 0.5
        )
        windows.append(CandidateWindow(
            text=text, score=round(score, 4),
            subscores={
                "relevance": round(rel, 3), "semantic": round(sem, 3),
                "entity": round(entity, 3), "role": round(role_sc, 3),
                "coherence": round(coherence, 3),
            },
        ))

    # Stable sort: score desc, then original order for determinism.
    windows.sort(key=lambda w: (-w.score, candidates.index(w.text)))
    return windows


def reranker_backend() -> str:
    """Report which relevance backend is active (for diagnostics/tests)."""
    try:
        import rank_bm25  # noqa: F401
        return "bm25"
    except Exception:  # pragma: no cover
        return "lexical"
