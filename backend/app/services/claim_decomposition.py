"""Claim decomposition: normalize typos, decompose into research sub-questions,
and generate multi-angle search queries for a debate claim.

Why claim decomposition exists: a single broad claim like "Section 230 reduces
accountability" can be supported by many narrow pieces of evidence — mechanism
cards (how the immunity works), example cards (specific court dismissals), impact
cards (harm to victims), and authority cards (scholars who agree). By decomposing
into these angles and running multiple targeted queries we dramatically increase
the chance of finding relevant evidence that a single-query search would miss.

SAFETY INVARIANTS:
- Returns a plain data object; no API calls are made unless _decompose_with_llm is called
- LLM path only called when openai is available and imported correctly
- Failures fall back to deterministic plan
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ── Entity corrections ────────────────────────────────────────────────────────
# Maps canonical form to list of common typos/variants that should be corrected.
_ENTITY_CORRECTIONS: dict[str, list[str]] = {
    "Section 230": ["ion 230", "tion 230", "sec 230", "sec. 230", "section230", "sec230"],
    "Fourth Amendment": ["4th amendment", "4th amend", "iv amendment"],
    "First Amendment": ["1st amendment", "1st amend", "i amendment"],
    "Second Amendment": ["2nd amendment", "2nd amend", "ii amendment"],
    "Title IX": ["title 9", "title ix"],
    "NATO": ["north atlantic treaty"],
    "GDPR": ["eu data protection", "european data privacy"],
}


def normalize_claim(topic: str, claim: str) -> tuple[str, list[str]]:
    """Normalize a claim by fixing known entity typos.

    If a canonical entity form appears in topic (case-insensitive) but a typo
    form appears in the claim, the typo is replaced with the canonical form.

    Returns:
        (normalized_claim, corrections_applied)
    """
    corrections_applied: list[str] = []
    normalized = claim

    topic_lower = topic.lower()
    claim_lower = claim.lower()

    for canonical, typos in _ENTITY_CORRECTIONS.items():
        canonical_lower = canonical.lower()
        # Only fix if the canonical form appears in the topic
        if canonical_lower not in topic_lower:
            continue
        # Fix any typo variants found in the claim
        for typo in typos:
            typo_lower = typo.lower()
            if typo_lower in claim_lower:
                # Skip if the canonical form is already correctly present —
                # some typos are substrings of the canonical (e.g. "tion 230"
                # is a suffix of "Section 230") which would produce garbled
                # output if we blindly replaced.
                if canonical_lower in claim_lower:
                    continue
                # Case-insensitive replace
                pattern = re.compile(re.escape(typo), re.IGNORECASE)
                new_normalized = pattern.sub(canonical, normalized)
                if new_normalized != normalized:
                    corrections_applied.append(f"{typo} → {canonical}")
                    normalized = new_normalized
                    # Update claim_lower for subsequent checks
                    claim_lower = normalized.lower()

    return normalized, corrections_applied


# ── Legal/policy domain-specific query contexts ───────────────────────────────
# Maps known legal/policy topic keywords to high-value search queries.
# These are injected into both deterministic and LLM decomposition paths so that
# topic-specific queries are always present regardless of which path runs.
_LEGAL_POLICY_CONTEXTS: dict[str, list[str]] = {
    "section 230": [
        "Section 230 liability shield third party content",
        "Section 230 platform immunity accountability gap",
        "Section 230 Backpage sex trafficking lawsuit dismissed",
        "Section 230 misinformation platform liability",
        "Section 230 algorithmic recommendation harmful content",
        "Section 230 court dismissed lawsuit platform",
        "Section 230 broad immunity law review reform",
        "platform immunity harmful user content lawsuit",
        "47 USC 230 publisher speaker third party content",
    ],
    "first amendment": [
        "First Amendment free speech government censorship court",
        "First Amendment overbreadth prior restraint case",
        "First Amendment content moderation social media",
    ],
    "fourth amendment": [
        "Fourth Amendment unreasonable search seizure court",
        "Fourth Amendment digital privacy expectation",
    ],
    "gdpr": [
        "GDPR data privacy enforcement fine court",
        "GDPR compliance cost small business",
    ],
    "nato": [
        "NATO collective defense Article 5 obligation",
        "NATO expansion membership eastern europe",
    ],
}


def _get_domain_specific_queries(normalized_claim: str, topic: str) -> list[str]:
    """Return domain-specific queries for any known legal/policy topic present
    in either the normalized claim or the topic string.

    Matching is case-insensitive substring match on the combined text.
    Returns an empty list if no known context is matched.
    """
    combined = (normalized_claim + " " + topic).lower()
    for key, queries in _LEGAL_POLICY_CONTEXTS.items():
        if key in combined:
            return list(queries)
    return []


# ── Pydantic models ────────────────────────────────────────────────────────────

class ClaimResearchPlan(BaseModel):
    original_claim: str
    normalized_claim: str
    corrections_applied: list[str] = []
    debate_position: str = "supporting"
    core_concepts: list[str] = []
    mechanism_hypotheses: list[str] = []
    example_hypotheses: list[str] = []
    impact_hypotheses: list[str] = []
    authority_targets: list[str] = []
    counter_evidence_targets: list[str] = []
    safe_narrower_claims: list[str] = []
    search_queries: list[str] = []


class _DecompositionLLMOutput(BaseModel):
    core_concepts: list[str]
    mechanism_hypotheses: list[str]
    example_hypotheses: list[str]
    impact_hypotheses: list[str]
    authority_targets: list[str]
    counter_evidence_targets: list[str]
    safe_narrower_claims: list[str]
    search_queries: list[str]


# ── LLM decomposition ─────────────────────────────────────────────────────────

def _decompose_with_llm(
    topic: str,
    normalized_claim: str,
    side: str,
) -> Optional[_DecompositionLLMOutput]:
    """Use GPT-4o-mini to generate a structured research plan for the claim.

    Returns None on any failure (caller falls back to deterministic).
    """
    try:
        from openai import OpenAI
        client = OpenAI()

        # Inject domain-specific queries into the prompt so the LLM knows
        # which high-value queries to include in its output.
        domain_queries = _get_domain_specific_queries(normalized_claim, topic)
        domain_hint = ""
        if domain_queries:
            domain_hint = (
                "\nAdditionally, these specific queries are known to be highly useful for this topic "
                "— include them in your search_queries list:\n"
                + "\n".join(f"  - {q}" for q in domain_queries[:6])
                + "\n"
            )

        system_prompt = (
            "You are an expert debate research assistant helping a student find evidence for a "
            "Public Forum debate claim. Your job is to decompose the claim into multiple research "
            "angles and generate specific web search queries. Think like a competitive debater who "
            "needs to find supporting evidence from multiple angles: mechanism (how it works), "
            "examples (specific cases), impacts (harms/effects), definitions, and authority sources. "
            "Be specific and varied. The queries should be real web searches, not vague prompts."
        )

        user_prompt = (
            f"Debate topic: {topic or '(not specified)'}\n"
            f"Claim to support: {normalized_claim}\n"
            f"Side: {side or 'supporting'}\n"
            f"{domain_hint}\n"
            "Generate a research plan with:\n"
            "- core_concepts: key terms to search for (max 6, single words or short phrases)\n"
            "- mechanism_hypotheses: how the mechanism works (2-4 items, short phrases describing "
            "what to look for about how the mechanism operates)\n"
            "- example_hypotheses: specific cases/examples to search for (2-4 items, e.g. specific "
            "court cases, events, or documented instances)\n"
            "- impact_hypotheses: harms/effects to search for (2-3 items)\n"
            "- authority_targets: types of authoritative sources (2-3 items, e.g. 'law review', "
            "'congressional report', 'academic study')\n"
            "- counter_evidence_targets: what counter-arguments look like (2-3 items, to find "
            "opposing evidence the debater should prepare for)\n"
            "- safe_narrower_claims: scoped claim versions a card can safely make (3-5 items, "
            "narrower statements that are easier to prove)\n"
            "- search_queries: 8-12 specific web search queries covering different angles. "
            "Include queries for: (a) the mechanism, (b) specific legal cases or examples, "
            "(c) impacts/harms, (d) academic/legal scholarship, (e) reform debates. "
            "For a claim about Section 230 immunity, for example, include queries like: "
            "'Section 230 liability shield third party content', "
            "'Section 230 Backpage sex trafficking lawsuit dismissed', "
            "'Section 230 algorithmic recommendation harmful content', "
            "'Section 230 platform immunity accountability gap'. "
            "Make each query specific and searchable."
        )

        result = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=_DecompositionLLMOutput,
            temperature=0.3,
            max_tokens=1200,
        )
        return result.choices[0].message.parsed
    except Exception as exc:
        logger.debug("LLM claim decomposition failed: %s", exc)
        return None


# ── Deterministic fallback ────────────────────────────────────────────────────

def _build_deterministic_plan(
    topic: str,
    normalized_claim: str,
    original_claim: str,
    side: str,
    corrections_applied: list[str],
) -> ClaimResearchPlan:
    """Build a research plan without LLM, using deterministic query variants.

    Prepends domain-specific queries for known legal/policy topics (Section 230,
    First Amendment, GDPR, etc.) before the generic variants so that the most
    targeted queries always appear first in the plan.
    """
    # Import here to avoid circular import at module level
    from app.services.research_search import build_research_query_variants

    base_queries = build_research_query_variants(topic or None, normalized_claim, side or None)

    # Prepend domain-specific queries if this is a known legal/policy topic
    domain_queries = _get_domain_specific_queries(normalized_claim, topic)

    # Generate angle-specific query variants
    topic_clean = (topic or "").strip()

    # Extract key noun phrases from claim (simple heuristic)
    claim_tokens = [
        w for w in re.sub(r"[^\w\s]", " ", normalized_claim).split()
        if len(w) > 3 and w.lower() not in {
            "that", "this", "with", "from", "have", "will", "been", "they",
            "their", "there", "when", "would", "could", "should", "about",
        }
    ][:6]
    key_phrase = " ".join(claim_tokens[:4]) if claim_tokens else normalized_claim[:60]

    legal_queries = [
        f"{key_phrase} liability court",
        f"{key_phrase} immunity legal ruling",
        f"{topic_clean} law reform".strip() if topic_clean else f"{key_phrase} law",
    ]

    example_queries = [
        f"{key_phrase} case example",
        f"{key_phrase} lawsuit dismissed",
        f"{topic_clean} real case study".strip() if topic_clean else f"{key_phrase} case study",
    ]

    impact_queries = [
        f"{key_phrase} harm damage victims",
        f"{key_phrase} harmful effects research",
    ]

    # Build deduplicated query list: domain-specific first, then generic
    all_queries: list[str] = []
    seen_lower: set[str] = set()

    for q in domain_queries + list(base_queries) + legal_queries + example_queries + impact_queries:
        q_clean = q.strip()
        if q_clean and q_clean.lower() not in seen_lower:
            seen_lower.add(q_clean.lower())
            all_queries.append(q_clean)

    return ClaimResearchPlan(
        original_claim=original_claim,
        normalized_claim=normalized_claim,
        corrections_applied=corrections_applied,
        debate_position=side or "supporting",
        core_concepts=[],
        mechanism_hypotheses=[],
        example_hypotheses=[],
        impact_hypotheses=[],
        authority_targets=[],
        counter_evidence_targets=[],
        safe_narrower_claims=[],
        search_queries=all_queries[:15],
    )


# ── Public API ────────────────────────────────────────────────────────────────

def decompose_claim(
    topic: str,
    claim: str,
    side: str = "",
) -> ClaimResearchPlan:
    """Decompose a debate claim into a structured research plan.

    1. Normalize the claim (fix typos based on topic entity matching).
    2. Attempt LLM decomposition.
    3. If LLM fails, fall back to deterministic plan.
    """
    normalized_claim, corrections_applied = normalize_claim(topic, claim)

    # Try LLM decomposition
    llm_output = _decompose_with_llm(topic, normalized_claim, side)

    if llm_output is not None:
        # Inject domain-specific queries into LLM output as well
        domain_queries = _get_domain_specific_queries(normalized_claim, topic)
        llm_queries = list(llm_output.search_queries)
        seen_lower = {q.lower() for q in llm_queries}
        for dq in domain_queries:
            if dq.lower() not in seen_lower:
                llm_queries.insert(0, dq)
                seen_lower.add(dq.lower())

        return ClaimResearchPlan(
            original_claim=claim,
            normalized_claim=normalized_claim,
            corrections_applied=corrections_applied,
            debate_position=side or "supporting",
            core_concepts=llm_output.core_concepts,
            mechanism_hypotheses=llm_output.mechanism_hypotheses,
            example_hypotheses=llm_output.example_hypotheses,
            impact_hypotheses=llm_output.impact_hypotheses,
            authority_targets=llm_output.authority_targets,
            counter_evidence_targets=llm_output.counter_evidence_targets,
            safe_narrower_claims=llm_output.safe_narrower_claims,
            search_queries=llm_queries[:15],
        )

    # Fallback to deterministic
    return _build_deterministic_plan(topic, normalized_claim, claim, side, corrections_applied)
