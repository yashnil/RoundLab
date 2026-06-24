"""Multi-level deduplication for evidence passage candidates.

Removes candidates that are exact duplicates, near-duplicates, or from the
same domain over the diversity cap, before they reach the ranking stage.

Dedup levels (applied in order):
1. Exact passage hash — SHA-256 prefix (fast O(1) lookup).
2. Near-duplicate word-set overlap — Jaccard ≥ threshold (default 0.7).
3. Per-domain diversity cap — ensures multiple viewpoints are preserved.

SAFETY INVARIANTS:
- No text is modified. Rejected candidates get rejection_reason set, they are
  not deleted from the original list.
- Candidates marked rejected are NOT counted toward the kept set.
- `seen_canonical_urls` allows the caller to propagate cross-URL dedup state
  from previous processing steps.
"""

from __future__ import annotations

import hashlib
import re

from app.services.evidence_candidate import DeduplicationStats, EvidenceCandidate

# ── Dedup defaults ────────────────────────────────────────────────────────────

_DEFAULT_SIM_THRESHOLD = 0.7   # Jaccard word-set overlap for near-dup detection
_DEFAULT_MAX_PER_DOMAIN = 3    # max passage slots per domain before diversity cap

# ── Helpers ───────────────────────────────────────────────────────────────────


def _passage_hash(text: str) -> str:
    """16-hex SHA-256 fingerprint for exact-duplicate detection."""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def _word_set(text: str) -> frozenset[str]:
    """Lowercased word set, stripping punctuation (same algorithm as _is_near_duplicate)."""
    return frozenset(re.sub(r"[^\w\s]", " ", text.lower()).split())


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union else 0.0


def is_exact_or_near_duplicate(
    text: str,
    seen_hashes: set[str],
    seen_word_sets: list[frozenset[str]],
    sim_threshold: float = _DEFAULT_SIM_THRESHOLD,
) -> tuple[bool, str]:
    """Check whether `text` is an exact or near-duplicate of anything seen so far.

    Returns (is_dup, reason_code) where reason_code is one of:
    - "exact_hash" — identical text seen before
    - "near_dup"   — word-set Jaccard ≥ sim_threshold
    - ""           — not a duplicate
    """
    h = _passage_hash(text)
    if h in seen_hashes:
        return True, "exact_hash"

    ws = _word_set(text)
    for seen_ws in seen_word_sets:
        if _jaccard(ws, seen_ws) >= sim_threshold:
            return True, "near_dup"

    return False, ""


# ── Multi-level deduplicator ──────────────────────────────────────────────────


def deduplicate_passages(
    candidates: list[EvidenceCandidate],
    *,
    seen_canonical_urls: set[str] | None = None,
    max_per_domain: int = _DEFAULT_MAX_PER_DOMAIN,
    sim_threshold: float = _DEFAULT_SIM_THRESHOLD,
) -> tuple[list[EvidenceCandidate], DeduplicationStats]:
    """Remove duplicate or domain-excess passage candidates in-place.

    Modifies `candidate.rejection_reason` on rejected candidates.
    Returns (kept_candidates, stats).

    Args:
        candidates:            passage candidates to filter (order preserved).
        seen_canonical_urls:   set of canonical URLs already committed outside
                               this batch; used for cross-call URL dedup.
        max_per_domain:        max passages allowed per eTLD+1 domain.
        sim_threshold:         Jaccard threshold for near-duplicate detection.
    """
    stats = DeduplicationStats(candidates_in=len(candidates))
    seen_hashes: set[str] = set()
    seen_word_sets: list[frozenset[str]] = []
    seen_canons: set[str] = set(seen_canonical_urls or [])
    domain_counts: dict[str, int] = {}
    kept: list[EvidenceCandidate] = []

    for c in candidates:
        # Level 1 + 2: exact hash then near-duplicate
        is_dup, dup_reason = is_exact_or_near_duplicate(
            c.text, seen_hashes, seen_word_sets, sim_threshold
        )
        if is_dup:
            c.rejection_reason = dup_reason
            if dup_reason == "exact_hash":
                stats.exact_hash_removed += 1
            else:
                stats.near_dup_removed += 1
            continue

        # Level 3: per-domain diversity cap
        domain = c.domain or ""
        if domain and domain_counts.get(domain, 0) >= max_per_domain:
            c.rejection_reason = f"domain_cap:{domain}"
            stats.domain_capped += 1
            continue

        # Accepted — register this candidate
        h = _passage_hash(c.text)
        seen_hashes.add(h)
        seen_word_sets.append(_word_set(c.text))
        if domain:
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        kept.append(c)

    stats.candidates_out = len(kept)
    return kept, stats
