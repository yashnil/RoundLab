"""Evidence query planner — role-aware, deduplicated search query generation.

Decomposes a debate claim into evidence roles and produces targeted queries
ordered from most specific to most general. The plan supports progressive
escalation: direct-outcome queries run first; mechanism, impact, and
credible-source queries are escalated to only when needed.

DESIGN NOTES
- Purely deterministic: no LLM calls here.
- All queries preserve the original claim text; none rewrites it.
- Near-duplicate query pairs (>= SIMILARITY_THRESHOLD word overlap) are dropped.
- Total query count is bounded at max_queries (default 8) matching the
  existing _search_exa cap and build_research_query_variants cap.
- The four roles mirror the evidence roles used in research_search.py
  so downstream classifiers can align role intent with role classification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

SIMILARITY_THRESHOLD = 0.65

_STOPWORDS = frozenset({
    "that", "this", "with", "from", "have", "will", "been", "they",
    "their", "there", "when", "would", "could", "should", "about",
    "than", "more", "into", "over", "such", "each", "also", "very",
    "just", "some", "what", "which", "where", "while", "these", "those",
    "then", "were", "does", "because", "through", "and", "the",
    "for", "are", "but", "not", "lack", "leads", "lead",
})

_MECHANISM_WORDS = frozenset({
    "leads", "lead", "causes", "cause", "results", "enables", "allows",
    "permits", "facilitates", "fosters", "produces", "generates", "creates",
    "prevents", "blocks", "stops", "reduces", "increases", "shields",
    "protects", "exposes", "caused", "resulted", "enabled", "allowed",
    "lack", "absence",
})

_IMPACT_WORDS = frozenset({
    "harm", "damage", "effect", "consequence", "impact", "outcome",
    "risk", "danger", "threat", "crisis", "hurt", "loss", "injur",
    "victim", "abuse", "exploit", "harassment", "violence",
})


@dataclass
class RoleQueryGroup:
    """Queries targeting one evidence role, in priority order."""
    role: str          # "direct_outcome" | "causal_mechanism" | "impact" | "credible_source"
    label: str         # human-readable role name for trace display
    queries: list[str] = field(default_factory=list)
    priority: int = 0  # lower = run first


@dataclass
class EvidenceResearchPlan:
    """A role-aware evidence search plan for one claim."""
    original_claim: str
    role_groups: list[RoleQueryGroup] = field(default_factory=list)
    # Flat deduplicated query list ordered by priority (first group first).
    all_queries_deduped: list[str] = field(default_factory=list)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _tokenize(text: str, max_tokens: int = 12) -> list[str]:
    """Extract meaningful tokens, skipping stopwords and short words."""
    raw = re.sub(r"[^\w\s]", " ", text.lower()).split()
    return [t for t in raw if len(t) > 2 and t not in _STOPWORDS][:max_tokens]


def _clean(parts: list[str], suffix: str = "") -> str:
    """Join parts into a clean query string."""
    q = " ".join(parts)
    if suffix:
        q = q + " " + suffix
    return re.sub(r"\s+", " ", q).strip()


def _build_direct_queries(claim: str, topic: str) -> list[str]:
    """Close-wording and synonym-broader queries for the full claim."""
    claim_tokens = _tokenize(claim)
    topic_tokens = _tokenize(topic) if topic else []
    prefix = topic_tokens[:2] if topic and topic.lower() not in claim.lower() else []

    q1 = _clean(prefix + claim_tokens[:8], "evidence report")
    q2 = _clean(prefix + claim_tokens[:5], "study research findings")
    return [q for q in [q1, q2] if len(q) > 10]


def _build_mechanism_queries(claim: str, topic: str) -> list[str]:
    """Mechanism/warrant-focused queries — how or why the claim is true."""
    claim_tokens = _tokenize(claim)
    topic_tokens = _tokenize(topic) if topic else []
    prefix = topic_tokens[:2] if topic and topic.lower() not in claim.lower() else []

    # Separate mechanism words from content words
    mech_tokens = [t for t in claim_tokens if t in _MECHANISM_WORDS]
    content_tokens = [t for t in claim_tokens if t not in _MECHANISM_WORDS][:5]

    # Q1: content context + mechanism signal + "mechanism"
    parts1 = prefix + content_tokens[:3]
    if mech_tokens:
        parts1 += mech_tokens[:1]
    q1 = _clean(parts1 + ["mechanism"], "evidence")

    # Q2: broader "how / why" framing
    parts2 = prefix + content_tokens[:4]
    q2 = _clean(parts2 + ["how", "why"], "research")

    return [q for q in [q1, q2] if len(q) > 10]


def _build_impact_queries(claim: str, topic: str) -> list[str]:
    """Impact/consequence-focused queries — what the effect/harm is."""
    claim_tokens = _tokenize(claim)
    topic_tokens = _tokenize(topic) if topic else []
    prefix = topic_tokens[:2] if topic and topic.lower() not in claim.lower() else []

    # Subject tokens (non-mechanism)
    subject_tokens = [t for t in claim_tokens if t not in _MECHANISM_WORDS][:5]

    q1 = _clean(prefix + subject_tokens[:4] + ["harm", "impact"], "study")
    q2 = _clean(subject_tokens[:4] + ["consequences", "outcomes"], "research")
    return [q for q in [q1, q2] if len(q) > 10]


def _build_credible_source_queries(claim: str, topic: str) -> list[str]:
    """Queries framed to surface credible academic/legal/policy sources."""
    claim_tokens = _tokenize(claim)
    topic_tokens = _tokenize(topic) if topic else []
    prefix = topic_tokens[:2] if topic and topic.lower() not in claim.lower() else []
    base = prefix + claim_tokens[:4]

    q1 = _clean(base, "study report")
    q2 = _clean(base, "law review analysis")
    return [q for q in [q1, q2] if len(q) > 10]


def _deduplicate_queries(queries: list[str]) -> list[str]:
    """Remove near-duplicate queries based on word-set overlap."""
    result: list[str] = []
    seen_wordsets: list[frozenset] = []
    for q in queries:
        words = frozenset(q.lower().split())
        duplicate = False
        for sw in seen_wordsets:
            if not words or not sw:
                continue
            overlap = len(words & sw) / max(len(words), len(sw))
            if overlap >= SIMILARITY_THRESHOLD:
                duplicate = True
                break
        if not duplicate and q.strip():
            result.append(q)
            seen_wordsets.append(words)
    return result


# ── Public API ────────────────────────────────────────────────────────────────

def plan_evidence_research(
    claim: str,
    topic: str = "",
    side: str = "",
    max_queries: int = 8,
) -> EvidenceResearchPlan:
    """Generate a role-aware, deduplicated evidence research plan.

    Roles and their priorities:
      direct_outcome (0)  — closest to the claim; run first
      causal_mechanism (1) — how/why the claim is true; run second
      impact (2)           — harm/consequence evidence; run third
      credible_source (3)  — framed for academic/legal sources; run last

    Returns an EvidenceResearchPlan with all queries deduplicated and
    ordered by priority so callers can escalate through the list.
    """
    claim = claim.strip()
    topic = topic.strip()

    role_groups: list[RoleQueryGroup] = [
        RoleQueryGroup(
            role="direct_outcome",
            label="Direct claim support",
            queries=_build_direct_queries(claim, topic),
            priority=0,
        ),
        RoleQueryGroup(
            role="causal_mechanism",
            label="Mechanism/warrant",
            queries=_build_mechanism_queries(claim, topic),
            priority=1,
        ),
        RoleQueryGroup(
            role="impact",
            label="Impact/consequence",
            queries=_build_impact_queries(claim, topic),
            priority=2,
        ),
        RoleQueryGroup(
            role="credible_source",
            label="Study/report framing",
            queries=_build_credible_source_queries(claim, topic),
            priority=3,
        ),
    ]

    # Flatten in priority order, then deduplicate
    ordered: list[str] = []
    for group in sorted(role_groups, key=lambda g: g.priority):
        ordered.extend(group.queries)

    deduped = _deduplicate_queries(ordered)[:max_queries]

    return EvidenceResearchPlan(
        original_claim=claim,
        role_groups=role_groups,
        all_queries_deduped=deduped,
    )
