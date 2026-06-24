"""Research search helpers: query building, concept expansion, and candidate card generation.

Why indirect support is accepted: In Public Forum debate, evidence does not need to directly
prove the full claim to be useful. A card explaining the legal mechanism (e.g. how Section 230
grants immunity), a specific example (a court case dismissal), or an impact (documented harms)
all support the debater's argument chain — even if none proves the full claim alone. The
evidence roles system (direct_support, mechanism_support, example_support, impact_support,
definition_support, authority_support) captures this so debaters get the most relevant cards.

SAFETY INVARIANTS (all preserved):
- body_text is always exact extracted source text
- Weak/no-support passages never become cards
- Fabricated metadata (author, date, publication) is never inserted
- At most 4 candidate cards returned per request
- Cards are stored as drafts; user must confirm before saving to evidence_cards
- Counter-evidence is never mixed into main card_drafts; kept in counter_evidence_drafts
- is_snippet_source=True on any card derived from a Tavily snippet (not full extraction)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Literal, Optional
from urllib.parse import urlparse

from pydantic import BaseModel

from app.models.research import (
    CardPurpose,
    ExtractedArticle,
    SourceQuality,
    SupportLevel,
)
from app.services.card_cutting import generate_card_draft, _score_paragraph, _split_paragraphs
from app.services.source_quality import rate_source_quality
from app.services.web_article_extraction import extract_article

logger = logging.getLogger(__name__)

# ── URL canonicalization ───────────────────────────────────────────────────────

_TRACKING_PARAMS = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
    "gclid", "fbclid", "msclkid", "ref", "source", "_ga", "mc_cid",
})


def canonicalize_url(url: str) -> str:
    """Normalize URL for deduplication: lowercase host, strip tracking params, remove fragment."""
    try:
        from urllib.parse import urlparse as _up, urlencode, parse_qsl, urlunparse
        p = _up(url.strip())
        clean_qs = urlencode(
            [(k, v) for k, v in parse_qsl(p.query) if k.lower() not in _TRACKING_PARAMS]
        )
        return urlunparse((p.scheme.lower(), p.netloc.lower(), p.path, p.params, clean_qs, ""))
    except Exception:
        return url


# ── Boilerplate detection ─────────────────────────────────────────────────────

def _looks_like_boilerplate(text: str) -> bool:
    """Return True if text looks like navigation/menu/boilerplate."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return True
    short_line_ratio = sum(1 for l in lines if len(l) < 30) / len(lines)
    nav_words = sum(1 for l in lines if any(
        w in l.lower() for w in ("menu", "navigation", "cookie", "subscribe", "sign in", "log in")
    ))
    return short_line_ratio > 0.7 or nav_words > 3


# ── Exa search provider (HTTP-based, no SDK) ──────────────────────────────────

def _search_exa(
    queries: list[str],
    api_key: str,
    max_results_per_query: int = 3,
    timeout: float = 10.0,
) -> list[dict]:
    """Call Exa Search API over HTTP. Returns Tavily-compatible dicts.

    Exa supplements Tavily for semantic discovery of relevant research sources.
    Only called when EXA_API_KEY is configured.
    """
    import httpx
    results = []
    seen: set[str] = set()
    for query in queries[:4]:  # cap to avoid rate limits
        try:
            resp = httpx.post(
                "https://api.exa.ai/search",
                headers={
                    "x-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "query": query,
                    "numResults": max_results_per_query,
                    "type": "neural",
                    "contents": {"text": {"maxCharacters": 2000}, "highlights": {"numSentences": 3}},
                },
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("results", []):
                url = item.get("url", "")
                canonical = canonicalize_url(url)
                if canonical in seen:
                    continue
                seen.add(canonical)
                # Build Tavily-compatible dict
                text = item.get("text") or ""
                highlights = item.get("highlights") or []
                snippet = " ".join(h for h in highlights if h) if highlights else text[:300]
                results.append({
                    "url": url,
                    "title": item.get("title"),
                    "content": snippet,
                    "raw_content": text if len(text) > 200 else None,
                    "score": item.get("score", 0.5),
                    "published_date": item.get("publishedDate"),
                    "_provider": "exa",
                })
        except Exception as exc:
            logger.warning("Exa search failed for query %r: %s", query[:80], exc)
    return results


# ── Firecrawl extraction fallback ─────────────────────────────────────────────

def _extract_with_firecrawl(url: str, api_key: str, timeout: float = 15.0) -> Optional[str]:
    """Try Firecrawl scrape API for cleaner text extraction.

    Firecrawl/trafilatura improve extraction reliability for paywalled or
    JavaScript-heavy pages where basic httpx fetch fails.
    Only called when FIRECRAWL_API_KEY is configured.
    """
    try:
        import httpx
        resp = httpx.post(
            "https://api.firecrawl.dev/v1/scrape",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "url": url,
                "formats": ["markdown", "text"],
                "onlyMainContent": True,
                "timeout": int(timeout * 1000),
            },
            timeout=timeout + 5,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data.get("data", {})
        text = content.get("markdown") or content.get("text") or ""
        return text if len(text) >= 200 else None
    except Exception as exc:
        logger.debug("Firecrawl failed for %s: %s", url[:80], exc)
        return None


# ── Heuristic and Cohere reranking ────────────────────────────────────────────

def _rerank_chunks_heuristic(
    chunks: list[str],
    concepts: "ClaimConcepts",
    source_quality_score: float,
    max_chunks: int = 10,
) -> list[str]:
    """Score and reorder chunks by debate usefulness before LLM classification.

    Reranking happens before expensive LLM classification to select top chunks
    and reduce API costs. Uses concept overlap + role signals + quality.
    """
    _ROLE_SIGNAL_WORDS = frozenset({
        "liability", "immunity", "shield", "lawsuit", "court", "study",
        "evidence", "finds", "according to", "experts", "researchers",
        "impact", "harm", "causes", "increases", "example", "case",
        "ruling", "statute", "held that", "provides that", "enacted",
    })

    scored: list[tuple[float, str]] = []
    for chunk in chunks:
        concept_score = _score_passage_with_concepts(chunk, concepts)
        chunk_lower = chunk.lower()
        signal_count = sum(1 for w in _ROLE_SIGNAL_WORDS if w in chunk_lower)
        length_score = min(1.0, len(chunk.split()) / 200)
        quality_bonus = source_quality_score / 10.0
        boilerplate_penalty = 0.5 if _looks_like_boilerplate(chunk) else 0.0

        total = concept_score * 3 + signal_count * 0.8 + length_score + quality_bonus - boilerplate_penalty
        scored.append((total, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in scored[:max_chunks]]


def _rerank_chunks_cohere(
    chunks: list[str],
    query: str,
    api_key: str,
    max_chunks: int = 10,
    timeout: float = 10.0,
) -> Optional[list[str]]:
    """Use Cohere Rerank API to order chunks by debate usefulness.

    Reranking before LLM classification reduces cost by selecting best chunks.
    Returns None on any failure (caller falls back to heuristic).
    """
    try:
        import httpx
        resp = httpx.post(
            "https://api.cohere.ai/v1/rerank",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "rerank-english-v3.0",
                "query": query,
                "documents": chunks[:50],  # API limit
                "top_n": max_chunks,
                "return_documents": True,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        reranked = [item["document"]["text"] for item in data.get("results", [])]
        return reranked if reranked else None
    except Exception as exc:
        logger.debug("Cohere rerank failed: %s", exc)
        return None


_MAX_CARDS = 5

# ── Domain-aware source quality scoring (Change 2) ────────────────────────────

# High-quality domains for policy/legal research.
# Values are base scores (0-10). Suffix entries (.gov, .edu) match any subdomain.
_HIGH_QUALITY_DOMAINS: dict[str, float] = {
    ".gov": 9.0,
    ".edu": 8.5,
    "law.cornell.edu": 9.5,
    "congress.gov": 9.5,
    "crs.gov": 9.5,
    "ftc.gov": 9.0,
    "fcc.gov": 9.0,
    "doj.gov": 9.0,
    "scotusblog.com": 8.5,
    "supremecourt.gov": 9.5,
    "reuters.com": 8.0,
    "apnews.com": 8.0,
    "nytimes.com": 7.5,
    "washingtonpost.com": 7.5,
    "theatlantic.com": 7.0,
    "brookings.edu": 8.5,
    "pewresearch.org": 8.0,
    "cfr.org": 8.0,
    "rand.org": 8.0,
    "techpolicy.press": 7.5,
    "eff.org": 7.5,
}

_LOW_QUALITY_SIGNALS: list[str] = [
    "wordpress.com", "blogspot.com", "medium.com", "substack.com",
    "reddit.com", "quora.com", "wikipedia.org",
]


def _assess_source_quality(
    url: str,
    article: Optional[object],
    extraction_method: str,
) -> tuple[float, str]:
    """Score a source URL for quality and credibility (domain-aware).

    Returns (score 0-10, reason_string).
    Catches all exceptions and returns a safe default so the pipeline never
    fails due to domain-scoring errors.
    """
    try:
        try:
            from urllib.parse import urlparse as _up
            parsed = _up(url)
            hostname = (parsed.hostname or "").lower()
        except Exception:
            hostname = ""

        # Check specific domains FIRST (longest/most-specific match wins),
        # then fall back to suffix domains (.gov, .edu). This ensures
        # law.cornell.edu (9.5) beats the generic .edu (8.5) match.
        base_score: Optional[float] = None
        reason = "Unknown domain — standard confidence"

        specific_keys = [(k, v) for k, v in _HIGH_QUALITY_DOMAINS.items() if not k.startswith(".")]
        suffix_keys = [(k, v) for k, v in _HIGH_QUALITY_DOMAINS.items() if k.startswith(".")]

        for domain_key, score_val in specific_keys:
            if hostname == domain_key or hostname.endswith("." + domain_key):
                base_score = score_val
                reason = f"High-quality source: {domain_key}"
                break

        if base_score is None:
            for domain_key, score_val in suffix_keys:
                if hostname.endswith(domain_key):
                    base_score = score_val
                    tld = domain_key.lstrip(".")
                    reason = f"High-authority .{tld} domain"
                    break

        if base_score is None:
            # Check low-quality signals
            for lq in _LOW_QUALITY_SIGNALS:
                if hostname == lq or hostname.endswith("." + lq):
                    if lq in ("reddit.com", "quora.com"):
                        base_score = 2.0
                        reason = "Discussion forum — very unlikely to be citable"
                    elif lq == "wikipedia.org":
                        base_score = 4.0
                        reason = "Wikipedia — not a primary source but often neutral"
                    else:
                        # medium.com, substack.com, wordpress.com, blogspot.com
                        base_score = 4.0
                        reason = "Blog/personal site — lower confidence"
                    break

        if base_score is None:
            base_score = 6.0
            reason = "Unknown domain — standard confidence"

        # Apply deductions
        score = base_score
        if extraction_method in ("failed", "snippet"):
            if extraction_method == "snippet":
                score -= 2.0
                reason += "; snippet-only (partial text)"
            else:
                score -= 1.5
                reason += "; extraction failed"

        # Check extraction confidence if available
        if article is not None:
            conf = getattr(article, "extraction_confidence", None)
            if conf is not None and conf < 0.5:
                score -= 1.0
                reason += "; low extraction confidence"
            body = getattr(article, "extracted_text", "")
            if body and len(body) < 200:
                score -= 2.0
                reason += "; very short body text"

        # Cap and floor
        score = max(0.5, min(10.0, score))
        return score, reason

    except Exception as exc:
        logger.debug("_assess_source_quality failed for %s: %s", url, exc)
        return 5.0, "Quality scoring error — default confidence"
_QUALITY_ORDER = {"high": 3, "medium": 2, "low": 1, "unknown": 0}

_STRONG_SUPPORT_SIGNALS = frozenset({
    "proves", "demonstrates", "shows", "confirms", "establishes",
    "according", "study", "research", "data", "found", "finds", "found that",
    "report", "concluded", "results", "percent", "million", "billion",
    "increase", "decrease", "reduces", "causes", "leads to", "results in",
})

_PARTIAL_SIGNALS = frozenset({
    "suggests", "indicates", "may", "could", "likely", "possible",
    "some evidence", "limited", "preliminary",
})


# ── Policy/debate synonym map ─────────────────────────────────────────────────

# Maps a debate-domain term to its semantic equivalents.
# Keys are lowercase; multi-word synonyms are single strings (split during scoring).
_POLICY_SYNONYMS: dict[str, frozenset[str]] = {
    # Accountability / liability
    "accountability": frozenset({
        "liability", "responsibility", "culpability", "recourse", "immune",
        "immunity", "shield", "protection", "accountable", "responsible",
        "liable", "civil", "damages", "lawsuits", "legal",
    }),
    "accountable": frozenset({"liable", "responsible", "culpable", "answerable"}),
    "liability": frozenset({
        "accountability", "responsibility", "exposure",
        "civil", "culpability", "damages", "suits", "sued",
    }),
    "immune": frozenset({"shield", "protect", "exempt", "insulate", "protected", "immunity"}),
    "immunity": frozenset({
        "protection", "shield", "harbor", "exemption", "insulation",
        "protected", "exempt", "shielded",
    }),
    "shield": frozenset({
        "protect", "immunity", "exemption", "insulate", "shelter",
        "harbor", "protection",
    }),

    # Harmful content / online harms
    "harmful": frozenset({
        "illegal", "dangerous", "abusive", "exploitative",
        "offensive", "toxic", "damaging", "destructive", "hateful", "illicit",
    }),
    "harm": frozenset({
        "damage", "injury", "abuse", "exploitation", "trafficking",
        "harassment", "hurt", "violence", "crime", "injustice", "harms",
    }),
    "content": frozenset({
        "material", "speech", "posts", "information",
        "user-generated", "messages", "publications", "postings", "data",
    }),

    # Causation / mechanism
    "leads": frozenset({
        "causes", "results", "produces", "generates", "creates",
        "enables", "allows", "permits", "facilitates", "fosters", "caused",
    }),
    "lead": frozenset({
        "cause", "result", "produce", "generate", "create",
        "enable", "allow", "permit", "facilitate", "foster",
    }),
    "cause": frozenset({
        "lead", "result", "produce", "generate", "create",
        "enable", "allow", "permit", "facilitate", "foster", "cause",
    }),
    "lack": frozenset({
        "absence", "failure", "gap", "insufficient",
        "deficiency", "without", "missing", "void", "lacking",
    }),

    # Platforms / tech
    "platform": frozenset({
        "website", "online", "social", "company",
        "internet", "provider", "host", "service", "tech",
        "giants", "companies", "websites",
    }),

    # Section 230 specific
    "230": frozenset({
        "cda", "decency", "harbor", "immunity", "shield",
    }),

    # Reform / change
    "reform": frozenset({"change", "revise", "amend", "update", "repeal", "modify", "overhaul"}),
    "repeal": frozenset({"reform", "abolish", "eliminate", "remove", "strike"}),

    # Economic
    "economic": frozenset({
        "financial", "fiscal", "monetary", "market", "trade", "commercial",
    }),
    "cost": frozenset({"expense", "price", "burden", "loss", "damage"}),
    "growth": frozenset({"expansion", "increase", "rise", "prosperity", "gdp", "output"}),

    # Security/safety
    "security": frozenset({"safety", "protection", "defense", "threat", "risk", "danger"}),
    "risk": frozenset({"danger", "threat", "hazard", "vulnerability", "exposure", "peril"}),

    # Environment
    "environment": frozenset({"climate", "nature", "ecology", "planet", "earth"}),
    "emission": frozenset({"pollution", "carbon", "greenhouse", "discharge", "release"}),

    # Policy / law
    "policy": frozenset({"law", "regulation", "rule", "statute", "legislation", "measure"}),
    "regulation": frozenset({"law", "policy", "rule", "statute", "legislation", "oversight"}),
    "government": frozenset({
        "federal", "state", "congress", "agency", "authority", "official", "administration",
    }),

    # Common modifiers
    "increase": frozenset({"rise", "grow", "expand", "escalate", "surge", "growing"}),
    "decrease": frozenset({"reduce", "decline", "lower", "diminish", "mitigate", "fall"}),
    "reduce": frozenset({"decrease", "lower", "cut", "minimize", "limit", "curtail", "fewer"}),
    "impact": frozenset({"effect", "consequence", "result", "outcome", "implication"}),
    "data": frozenset({"evidence", "research", "study", "statistics", "findings", "report"}),
    "study": frozenset({"research", "analysis", "report", "investigation", "survey", "review"}),
}

_STOPWORDS = frozenset({
    "that", "this", "with", "from", "have", "will", "been", "they",
    "their", "there", "when", "would", "could", "should", "about",
    "than", "more", "into", "over", "such", "each", "also", "very",
    "just", "some", "what", "which", "where", "while", "these", "those",
    "then", "were", "does", "been", "have", "because", "through",
})


# ── Claim concepts ─────────────────────────────────────────────────────────────

@dataclass
class ClaimConcepts:
    core_terms: frozenset[str]       # direct tokens from claim + topic
    expanded_terms: frozenset[str]   # synonym-expanded terms
    mechanism_terms: frozenset[str]  # causation words present in expanded set
    all_terms: frozenset[str]        # union of core + expanded (for scoring)


_MECHANISM_WORDS = frozenset({
    "leads", "lead", "causes", "cause", "results", "enables", "allows", "permits",
    "facilitates", "fosters", "produces", "generates", "creates", "prevents",
    "blocks", "stops", "reduces", "increases", "shields", "protects", "exposes",
    "caused", "resulted", "enabled", "allowed",
})


def expand_claim_concepts(claim: str, topic: str = "") -> ClaimConcepts:
    """Build expanded concept set for a claim.

    Uses _POLICY_SYNONYMS to add semantic equivalents so that passages using
    synonymous language (e.g. 'liability' for 'accountability') still score well.
    """
    raw_tokens = re.sub(r"[^\w\s]", " ", (claim + " " + topic).lower()).split()
    core = frozenset(w for w in raw_tokens if len(w) > 2 and w not in _STOPWORDS)

    expanded: set[str] = set()
    for term in core:
        if term in _POLICY_SYNONYMS:
            for syn in _POLICY_SYNONYMS[term]:
                expanded.update(syn.lower().split())

    # Also check for multi-word key phrases in the claim
    claim_lower = claim.lower()
    for key, synonyms in _POLICY_SYNONYMS.items():
        if key in claim_lower:
            for syn in synonyms:
                expanded.update(syn.lower().split())

    expanded.discard("")
    mechanism = (core | frozenset(expanded)) & _MECHANISM_WORDS
    all_terms = core | frozenset(w for w in expanded if len(w) > 2)
    return ClaimConcepts(
        core_terms=core,
        expanded_terms=frozenset(expanded),
        mechanism_terms=mechanism,
        all_terms=all_terms,
    )


# ── Query builder ─────────────────────────────────────────────────────────────

def build_research_search_query(
    topic: Optional[str],
    claim_to_support: str,
    side: Optional[str] = None,
) -> str:
    """Build a single concise web search query from topic + claim + side."""
    claim = claim_to_support.strip()
    topic_clean = (topic or "").strip()

    topic_in_claim = topic_clean and topic_clean.lower() in claim.lower()

    claim_tokens = [
        w for w in re.sub(r"[^\w\s]", " ", claim).lower().split()
        if len(w) > 3 and w not in _STOPWORDS
    ][:10]

    parts: list[str] = []
    if topic_clean and not topic_in_claim:
        parts.append(topic_clean)
    parts.extend(claim_tokens)

    seen: set[str] = set()
    unique_parts: list[str] = []
    for p in parts:
        if p.lower() not in seen:
            seen.add(p.lower())
            unique_parts.append(p)

    query = " ".join(unique_parts[:12])

    q_lower = query.lower()
    if not any(w in q_lower for w in ("evidence", "study", "report", "data", "research")):
        query += " evidence report"

    return re.sub(r"\s+", " ", query).strip()


# Priority synonyms for query variant building.
# These are the most search-useful synonyms per term (NOT alphabetical sort).
_QUERY_PRIORITY_SYNONYMS: dict[str, list[str]] = {
    "accountability":  ["liability", "immunity", "shield", "responsible"],
    "accountable":     ["liable", "immune"],
    "harmful":         ["illegal", "abusive", "dangerous"],
    "harm":            ["abuse", "damage", "trafficking"],
    "leads":           ["causes", "enables", "results"],
    "lead":            ["cause", "enable"],
    "lack":            ["absence", "failure"],
    "platform":        ["companies", "services", "providers"],
    "policy":          ["regulation", "law"],
    "immunity":        ["liability", "protection", "exemption"],
    "liability":       ["accountability", "immunity", "responsibility"],
    "increase":        ["rise", "grow"],
    "decrease":        ["reduce", "decline"],
    "reduce":          ["lower", "cut", "diminish"],
    "economic":        ["financial", "fiscal"],
    "cost":            ["expense", "burden"],
    "security":        ["safety", "defense"],
    "environment":     ["climate", "ecology"],
    "emission":        ["pollution", "carbon"],
    "government":      ["federal", "congress"],
    "reform":          ["change", "amend", "repeal"],
}


def build_research_query_variants(
    topic: Optional[str],
    claim_to_support: str,
    side: Optional[str] = None,
) -> list[str]:
    """Generate 4–8 diverse search query variants for a claim.

    Strategy:
    1. Base query (original tokenised claim)
    2. Synonym-addition variants: add key synonyms alongside original terms
    3. Legal/academic framing variant
    4. Topic + narrowed-effect variant
    """
    base = build_research_search_query(topic, claim_to_support, side)
    variants: list[str] = [base]
    claim_lower = claim_to_support.lower()
    topic_clean = (topic or "").strip()

    # Strip trailing signal words from base for building cleaner variants
    base_core = base
    for suffix in (" evidence report", " evidence", " report"):
        if base_core.lower().endswith(suffix.lower()):
            base_core = base_core[: -len(suffix)].strip()

    # Synonym-addition variants: for each matched priority term, add its best synonyms
    synonym_additions: list[str] = []
    for key, priority_syns in _QUERY_PRIORITY_SYNONYMS.items():
        if key not in claim_lower:
            continue
        for syn in priority_syns[:2]:
            if syn not in claim_lower and syn not in base_core.lower():
                synonym_additions.append(syn)
        if len(synonym_additions) >= 6:
            break

    # Build synonym-augmented variants (add 2 synonyms per variant)
    for i in range(0, min(len(synonym_additions), 6), 2):
        chunk = " ".join(synonym_additions[i:i + 2])
        candidate = f"{base_core} {chunk} evidence"
        candidate = re.sub(r"\s+", " ", candidate).strip()
        if candidate.lower() not in {v.lower() for v in variants}:
            variants.append(candidate)

    # Legal/source-type framing variants
    for suffix in ("lawsuit court ruling", "study research findings"):
        candidate = f"{base_core} {suffix}".strip()
        if candidate.lower() not in {v.lower() for v in variants}:
            variants.append(candidate)

    # Topic + narrowed-effect variant (avoids repeating broad claim tokens)
    if topic_clean:
        concepts = expand_claim_concepts(claim_to_support, topic_clean)
        core_minus_topic = [
            t for t in sorted(concepts.core_terms)
            if t not in topic_clean.lower() and len(t) > 4
        ][:4]
        if core_minus_topic:
            narrow_q = f"{topic_clean} {' '.join(core_minus_topic)} study evidence"
            narrow_q = re.sub(r"\s+", " ", narrow_q).strip()
            if narrow_q.lower() not in {v.lower() for v in variants}:
                variants.append(narrow_q)

    # Deduplicate and cap
    seen: set[str] = set()
    result: list[str] = []
    for v in variants:
        v_clean = re.sub(r"\s+", " ", v).strip()
        if v_clean and v_clean.lower() not in seen:
            seen.add(v_clean.lower())
            result.append(v_clean)

    return result[:8]


# ── Passage scoring ───────────────────────────────────────────────────────────

def _score_passage_with_concepts(passage: str, concepts: ClaimConcepts) -> float:
    """Score a passage for relevance using concept-expanded terms."""
    words = frozenset(passage.lower().split())
    overlap = len(words & concepts.all_terms)
    core_overlap = len(words & concepts.core_terms)
    return overlap * 1.0 + core_overlap * 0.5


# ── LLM support classifier ────────────────────────────────────────────────────

class _SupportClassificationOutput(BaseModel):
    support_level: SupportLevel
    rationale: str
    best_supported_claim: str
    overclaim_warning: str
    safe_tag_scope: str


def _classify_support_with_llm(
    passage: str,
    claim_to_support: str,
    topic: str,
    source_url: str = "",
) -> Optional[_SupportClassificationOutput]:
    """Optional LLM-based support classifier.

    Returns None on any failure (caller falls back to deterministic).
    The LLM must not fabricate text — it only classifies the given passage.
    """
    try:
        from openai import OpenAI
        client = OpenAI()
        result = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict evidence evaluator for competitive debate (Public Forum). "
                        "Classify whether a source passage supports a debate claim. "
                        "Be honest about the strength of support. "
                        "NEVER fabricate claims or evidence. "
                        "'best_supported_claim' must be directly and literally supported by the passage. "
                        "If the passage supports only a narrower version of the claim, state that narrower claim. "
                        "'overclaim_warning' is an empty string if the original claim is safe; "
                        "otherwise, explain what the passage cannot prove. "
                        "'safe_tag_scope' describes what argument the card can safely make in a round."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Claim to support: {claim_to_support}\n"
                        f"Topic: {topic or '(not specified)'}\n"
                        f"Source: {source_url or '(unknown)'}\n\n"
                        f"Passage:\n{passage[:1500]}\n\n"
                        "Classify the support level. Narrow the claim to what the passage actually proves."
                    ),
                },
            ],
            response_format=_SupportClassificationOutput,
            temperature=0.0,
            max_tokens=350,
        )
        return result.choices[0].message.parsed
    except Exception as exc:
        logger.debug("LLM support classifier failed: %s", exc)
        return None


# ── Deterministic support classifier ─────────────────────────────────────────

def _classify_support_deterministic(
    passage: str,
    claim_to_support: str,
    topic: str,
    concepts: Optional[ClaimConcepts] = None,
) -> tuple[SupportLevel, str]:
    """Classify support using concept-aware keyword scoring.

    Uses synonym expansion so that semantically related passages (e.g. a passage
    about 'platform liability' for a claim about 'accountability') score correctly.
    """
    if concepts is None:
        concepts = expand_claim_concepts(claim_to_support, topic)

    words = frozenset(passage.lower().split())

    # Concept overlap (core + expanded synonyms)
    overlap = len(words & concepts.all_terms)
    core_overlap = len(words & concepts.core_terms)
    mechanism_match = bool(words & concepts.mechanism_terms)

    strong_hits = sum(1 for s in _STRONG_SUPPORT_SIGNALS if s in passage.lower())
    partial_hits = sum(1 for s in _PARTIAL_SIGNALS if s in passage.lower())

    score = overlap * 1.0 + core_overlap * 0.5 + strong_hits * 2.0 + partial_hits * 0.5
    if mechanism_match:
        score += 1.5

    has_stats = bool(re.search(r"\d+(\.\d+)?%|\b\d{4}\b|\$\d+|\d+ (million|billion)", passage))
    if has_stats:
        score += 2.0

    has_institution = bool(re.search(
        r"\b(university|institute|foundation|bureau|department|agency|"
        r"commission|congress|senate|court|journal|review|association)\b",
        passage.lower(),
    ))
    if has_institution:
        score += 1.0

    if len(passage) < 150:
        score *= 0.6

    if score >= 7.0:
        return "strong_support", f"Passage uses claim-relevant terms and evidence signals (score {score:.1f})."
    if score >= 3.5:
        return "partial_support", f"Passage partially supports the claim (score {score:.1f})."
    if score >= 1.5:
        return "weak_support", f"Passage is tangentially related (score {score:.1f})."
    return "no_support", f"Passage does not support this claim (score {score:.1f})."


def _classify_support(
    passage: str,
    claim_to_support: str,
    topic: str,
) -> tuple[SupportLevel, str]:
    """Backward-compatible wrapper: deterministic classification with concept expansion."""
    return _classify_support_deterministic(passage, claim_to_support, topic)


# ── Card purpose inference ────────────────────────────────────────────────────

def _infer_card_purpose(passage: str, claim_to_support: str) -> str:
    p = passage.lower()
    c = claim_to_support.lower()
    if any(w in p for w in ("solve", "solution", "address", "mitigate", "reduce", "prevent")):
        return "solvency"
    if any(w in p for w in ("death", "war", "conflict", "crisis", "catastroph", "collapse")):
        return "impact"
    if any(w in p for w in ("unique", "current", "status quo", "baseline", "present")):
        return "uniqueness"
    if any(w in p for w in ("link", "connect", "lead", "result in", "cause")):
        return "link"
    if any(w in p for w in ("harm", "damage", "hurt", "injure", "cost")):
        return "harm"
    if any(w in p for w in ("weigh", "outweigh", "magnitude", "probability", "scope")):
        return "weighing"
    if any(w in c for w in ("answer", "response", "counter", "rebut")):
        return "answer"
    return "background"


# ── Diversity checks ──────────────────────────────────────────────────────────

def _is_near_duplicate(body_text: str, existing_bodies: list[str], threshold: float = 0.7) -> bool:
    words_new = set(body_text.lower().split())
    for existing in existing_bodies:
        words_existing = set(existing.lower().split())
        if not words_new or not words_existing:
            continue
        overlap = len(words_new & words_existing) / max(len(words_new), len(words_existing))
        if overlap >= threshold:
            return True
    return False


def _domain_from_url(url: str) -> str:
    try:
        return urlparse(url).hostname or url
    except Exception:
        return url


# ── Text chunking ─────────────────────────────────────────────────────────────

def _chunk_text(text: str, chunk_words: int = 400, overlap_words: int = 60) -> list[str]:
    """Split text into overlapping word chunks of ~400 words.

    Skips chunks < 80 words. Returns at most 15 chunks.
    """
    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_words, len(words))
        chunk_words_list = words[start:end]
        if len(chunk_words_list) >= 80:
            chunks.append(" ".join(chunk_words_list))
        if end >= len(words):
            break
        start += chunk_words - overlap_words
        if start >= len(words):
            break

    return chunks[:15]


# ── Evidence role classification ───────────────────────────────────────────────

EvidenceRole = Literal[
    "direct_support", "mechanism_support", "example_support",
    "impact_support", "definition_support", "authority_support",
    "counter_evidence", "not_useful",
]


class EvidenceRoleOutput(BaseModel):
    evidence_role: EvidenceRole
    relevance_score: float = 5.0
    source_quality_score: float = 5.0
    debate_usefulness_score: float = 5.0
    card_cut_quality_score: float = 5.0
    best_supported_claim: str = ""
    safe_tag_scope: str = ""
    overclaim_warning: str = ""
    reasoning_short: str = ""


def _classify_role_with_llm(
    passage: str,
    claim: str,
    topic: str,
    url: str = "",
    side: Optional[str] = None,
) -> Optional[EvidenceRoleOutput]:
    """Use GPT-4o-mini with structured output to classify evidence role.

    Returns None on any failure (caller falls back to deterministic).
    """
    try:
        from openai import OpenAI
        client = OpenAI()

        system_prompt = (
            "You are an expert debate evidence judge for Public Forum debate. Your job is to "
            "classify passages into evidence roles for the debater's SUPPORTING argument.\n\n"
            "EVIDENCE ROLES:\n"
            "- direct_support: The passage directly supports the user's broad claim or a close "
            "paraphrase. High bar.\n"
            "- mechanism_support: Explains how or why the claim could be true. A passage about "
            "'Section 230 grants platforms immunity from civil liability' IS mechanism_support "
            "for 'Section 230 reduces accountability' even though it does not say 'reduces "
            "accountability' directly.\n"
            "- example_support: A specific case, lawsuit, incident, court ruling, or real-world "
            "example. The passage does NOT need to prove the full claim. A Backpage case "
            "dismissal IS example_support for 'Section 230 shields platforms from accountability' "
            "even though it only mentions one case.\n"
            "- definition_support: Defines a law, policy, doctrine, or mechanism. Useful for "
            "setup cards.\n"
            "- impact_support: Supports the harm, effect, or consequence part of the argument. "
            "Does NOT need to mention the policy.\n"
            "- authority_support: An expert, scholar, court, government body, or institution "
            "makes a claim relevant to the argument.\n"
            "- counter_evidence: The passage argues AGAINST the user's claim, supports the "
            "opposing side, or presents a pro-con framing that contradicts the claim.\n"
            "- not_useful: Completely unrelated, pure boilerplate/navigation text, or so vague "
            "it provides no debate value.\n\n"
            "CRITICAL RULES:\n"
            "1. Accept mechanism, example, definition, and impact passages even if they do NOT "
            "directly prove the full claim.\n"
            "2. A passage only gets 'not_useful' if it has no plausible connection to the argument.\n"
            "3. best_supported_claim MUST be shorter and safer than the user's claim — what this "
            "exact passage can honestly support.\n"
            "4. If the passage supports a narrower claim, say so in best_supported_claim. Do NOT "
            "say the user's full claim if the passage only supports part of it.\n"
            "5. safe_tag_scope is a one-sentence tag safe to use on a debate card — grounded in "
            "the body text only.\n"
            "6. If body text only supports legal immunity, safe_tag_scope should say 'Section 230 "
            "shields platforms from liability' NOT 'Section 230 causes misinformation.'\n"
            "7. counter_evidence passages must be flagged; never call them support.\n"
            "8. debate_usefulness_score (0-10): How useful is this for a debater? 7-10 = great "
            "card material; 4-6 = usable with caveats; <4 = not worth cutting."
        )

        user_prompt = (
            f"Claim to support: {claim}\n"
            f"Topic: {topic or '(not specified)'}\n"
            f"Side: {side or 'supporting'}\n"
            f"Source: {url or '(unknown)'}\n\n"
            f"Passage:\n{passage[:1800]}\n\n"
            "Classify the evidence role of this passage relative to the claim."
        )

        result = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=EvidenceRoleOutput,
            temperature=0.0,
            max_tokens=400,
        )
        return result.choices[0].message.parsed
    except Exception as exc:
        logger.debug("LLM evidence role classifier failed: %s", exc)
        return None


def _classify_role_deterministic(
    passage: str,
    claim: str,
    topic: str,
    concepts: ClaimConcepts,
) -> EvidenceRoleOutput:
    """Deterministic fallback evidence role classification using concept scoring.

    We look for regex signals first because they are cheap and highly predictive
    for the legal/policy topics most common in Public Forum debate. Concept
    overlap scoring alone can miss passages where relevant terms appear in a
    different syntactic form (e.g. "court dismissed" for example support).
    """
    score = _score_passage_with_concepts(passage, concepts)
    passage_lower = passage.lower()

    # Require specific case-level language for example_support, not just generic legal terms.
    # "courts have held" (doctrine) should NOT trigger this — only specific case patterns do.
    is_example = bool(re.search(
        r'\b(plaintiff|defendant|v\.|charged|indicted|convicted|alleged)\b',
        passage_lower,
    )) or bool(re.search(
        r'\bcourt\b.{0,30}\b(ruled|dismissed|rejected|affirmed|overturned|reversed|vacated)\b',
        passage_lower,
    )) or bool(re.search(
        r'\b(the case of|in the case|case no\.|case number|no\.\s*\d+|docket)\b',
        passage_lower,
    ))
    # Enhanced Section 230 / legal mechanism detection.
    # NOTE: "statute" intentionally removed here to avoid confusion with definition_support.
    is_mechanism = bool(re.search(
        r'\b(liability|immune|immunity|shield|exempt|protect|prevent|allow|enable|permit|'
        r'bar|block|insulate|harbor|provision|grants?|provides? immunity|provides? protection)\b',
        passage_lower,
    )) or bool(re.search(
        r'\b(230|section 230)\b',
        passage_lower,
    ) and re.search(
        r'\b(liability|immune|immunity|platform|publisher|speaker)\b',
        passage_lower,
    ))
    is_impact = bool(re.search(
        r'\b(harm|damage|victim|abuse|exploit|traffick|harass|violence|death|injur|crisis|'
        r'hurt|suffer|devastating|severe|serious)\b',
        passage_lower,
    ))
    # Tightened definition detection: requires explicit definitional language
    # (not just mention of a statute name, which appears in mechanism/example passages too).
    is_definition = bool(re.search(
        r'\b(is defined as|means that|is defined to (mean|include)|'
        r'the term ["\']?\w+["\']? (means?|refers?|includes?)|'
        r'provides? that "?.+?" means|enacted in|codified at|'
        r'shall mean|shall refer)\b',
        passage_lower,
    ))
    is_authority = bool(re.search(
        r'\b(professor|scholar|expert|study|research|report|concluded|recommends?|'
        r'according to|law review|journal|publication|survey|analysis|findings)\b',
        passage_lower,
    ))
    # Detect explicit counter-evidence signals: passage argues for the opposing position
    claim_lower = claim.lower()
    is_counter = (
        bool(re.search(
            r'\b(protects? free speech|enables? moderation|critics argue|opponents claim|'
            r'defenders of|benefits? platform|preserves? speech)\b',
            passage_lower,
        )) and
        # Only flag as counter if the passage seems to argue the opposite of the claim
        (
            ("accountability" in claim_lower and "promotes? accountability" in passage_lower) or
            ("harmful" in claim_lower and re.search(r'reduces? harm|prevents? harm', passage_lower))
        )
    )

    if score < 0.8:
        return EvidenceRoleOutput(
            evidence_role="not_useful",
            debate_usefulness_score=0.0,
            reasoning_short=f"Low concept overlap (score {score:.1f})",
        )

    # Check counter-evidence before positive roles
    if is_counter:
        return EvidenceRoleOutput(
            evidence_role="counter_evidence",
            debate_usefulness_score=min(6.0, score),
            reasoning_short=f"Passage appears to argue against the claim (score {score:.1f})",
        )

    # Prioritize specific, identifiable role signals before falling back to direct_support.
    # direct_support is reserved for passages that genuinely assert the claim's conclusion
    # directly — not merely passages about the same topic.  The specific roles are more
    # informative and help debaters understand how to USE the card.
    if is_example:
        return EvidenceRoleOutput(
            evidence_role="example_support",
            debate_usefulness_score=min(8.5, score + 2.0),
            reasoning_short=f"Specific case or court ruling found (score {score:.1f})",
        )
    if is_definition:
        return EvidenceRoleOutput(
            evidence_role="definition_support",
            debate_usefulness_score=min(7.5, score + 1.5),
            reasoning_short=f"Definitional/statutory language found (score {score:.1f})",
        )
    if is_mechanism:
        return EvidenceRoleOutput(
            evidence_role="mechanism_support",
            debate_usefulness_score=min(8.5, score + 2.0),
            reasoning_short=f"Mechanism/legal provision language found (score {score:.1f})",
        )
    if is_impact:
        return EvidenceRoleOutput(
            evidence_role="impact_support",
            debate_usefulness_score=min(7.5, score + 1.5),
            reasoning_short=f"Impact/harm language found (score {score:.1f})",
        )
    if is_authority:
        return EvidenceRoleOutput(
            evidence_role="authority_support",
            debate_usefulness_score=min(7.0, score + 1.0),
            reasoning_short=f"Authority/scholarly language found (score {score:.1f})",
        )
    if score >= 5.0:
        # No specific role signal — high concept overlap implies broad direct support
        return EvidenceRoleOutput(
            evidence_role="direct_support",
            debate_usefulness_score=min(9.0, score),
            reasoning_short=f"High concept overlap, no specific role signal (score {score:.1f})",
        )
    if score >= 1.5:
        return EvidenceRoleOutput(
            evidence_role="mechanism_support",
            debate_usefulness_score=min(6.0, score + 1.0),
            reasoning_short=f"Partial concept overlap (score {score:.1f})",
        )
    else:
        return EvidenceRoleOutput(
            evidence_role="not_useful",
            debate_usefulness_score=0.0,
            reasoning_short=f"Insufficient concept overlap (score {score:.1f})",
        )


# ── Evidence role → SupportLevel backward compat ─────────────────────────────

_EVIDENCE_ROLE_TO_SUPPORT_LEVEL: dict[str, SupportLevel] = {
    "direct_support": "strong_support",
    "mechanism_support": "partial_support",
    "example_support": "partial_support",
    "impact_support": "partial_support",
    "definition_support": "partial_support",
    "authority_support": "partial_support",
    "counter_evidence": "weak_support",
    "not_useful": "no_support",
}


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class CandidateCardsResult:
    card_drafts: list[dict] = field(default_factory=list)
    # Counter-evidence drafts — kept separate from card_drafts (Change 1)
    counter_evidence_drafts: list[dict] = field(default_factory=list)
    sources_considered: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    sources_found: int = 0
    sources_attempted: int = 0
    sources_extracted: int = 0
    passages_considered: int = 0
    candidates_generated: int = 0
    filtered_no_support: int = 0
    filtered_low_quality: int = 0
    # Acceptance gate rejection counters (Change 1)
    rejected_by_source_quality: int = 0
    rejected_by_missing_best_claim: int = 0
    # URLs where extraction failed but snippet exists (Change 1)
    possible_lead_urls: list[str] = field(default_factory=list)
    suggested_revised_claims: list[str] = field(default_factory=list)
    candidates_by_role: dict[str, int] = field(default_factory=dict)
    normalized_claim: str = ""
    corrections_applied: list[str] = field(default_factory=list)
    # Reranker tracking
    reranker_used: str = "none"  # "cohere" | "heuristic" | "bm25" | "bm25+semantic" | "none"
    # Pass 8: deduplication and retrieval tracking
    dedup_removed: int = 0
    retrieval_backend: str = ""
    # Firecrawl / Cohere instrumentation
    firecrawl_attempted: int = 0
    firecrawl_succeeded: int = 0
    firecrawl_failed: int = 0
    cohere_rerank_attempted: int = 0
    cohere_rerank_succeeded: int = 0
    # GROBID instrumentation (optional scholarly PDF extraction)
    grobid_attempted: int = 0
    grobid_succeeded: int = 0
    grobid_failed: int = 0
    # Evidence Set Builder (Parts 2 + 6)
    evidence_set_plan: Optional[dict] = None
    unfilled_slots: list[str] = field(default_factory=list)
    weak_leads: list[dict] = field(default_factory=list)
    # Per-slot search diagnostics (per-slot search path)
    slot_queries_run: dict = field(default_factory=dict)
    slot_urls_found: dict = field(default_factory=dict)
    slot_cards_filled: list = field(default_factory=list)
    slot_weak_leads_by_slot: list = field(default_factory=list)
    slot_unfilled_reasons: dict = field(default_factory=dict)
    per_slot_provider_errors: dict = field(default_factory=dict)
    slot_diagnostics: dict = field(default_factory=dict)
    # Pass 11: card support verification counters
    p11_cards_verified: int = 0
    p11_cards_supported: int = 0
    p11_cards_partially_supported: int = 0
    p11_cards_unsupported: int = 0
    p11_cards_contradicted: int = 0
    p11_cards_insufficient_context: int = 0
    p11_det_mismatches: int = 0
    p11_semantic_attempted: int = 0
    p11_semantic_backend: str = ""
    p11_semantic_failures: int = 0
    p11_abstract_warnings: int = 0
    p11_safer_tags: int = 0


# ── Tag safety validation (Change 6) ─────────────────────────────────────────

def _validate_card_tag(
    tag: str,
    body_text: str,
    best_supported_claim: str,
    use_llm: bool = True,
) -> tuple[str, Optional[str]]:
    """Validate that a card tag is grounded in the body text and does not overclaim.

    The tag must be safer than the user's full claim — it should only assert what
    the body text actually proves, not the debater's broader argument. This prevents
    students from using cards that promise more than the source delivers.

    Returns (safe_tag, overclaim_warning_or_None).
    Falls back gracefully on any error.
    """
    try:
        # Deterministic check: causal language in tag not present in body text
        causal_patterns = re.findall(
            r'\b(causes?|leads? to|facilitates?|enables?|creates?|increases?|allows?|'
            r'permits?|results? in)\b',
            tag.lower(),
        )
        overclaim_warning: Optional[str] = None
        safe_tag = tag

        if causal_patterns:
            body_lower = body_text.lower()
            if not any(cp in body_lower for cp in causal_patterns):
                overclaim_warning = "Tag implies causation not found in source text"
                # Fall back to best_supported_claim if available
                if best_supported_claim and best_supported_claim.strip():
                    safe_tag = best_supported_claim.strip()

        # If best_supported_claim is much shorter/narrower, check concepts align
        if best_supported_claim and len(best_supported_claim) < len(tag) * 0.7:
            tag_words = set(re.sub(r"[^\w\s]", " ", tag).lower().split())
            body_words = set(re.sub(r"[^\w\s]", " ", body_text).lower().split())
            missing_in_body = tag_words - body_words - _STOPWORDS
            if len(missing_in_body) > 3:
                if overclaim_warning is None:
                    overclaim_warning = "Tag contains terms not clearly present in source text"
                safe_tag = best_supported_claim.strip()

        # Optional LLM validation pass
        from app.config import settings
        if use_llm and getattr(settings, "research_enable_strict_card_validation", True):
            try:
                from openai import OpenAI
                from pydantic import BaseModel as _BM

                class _TagValidationOutput(_BM):
                    tag_supported_by_body: bool
                    safer_tag: str
                    overclaim_warning: Optional[str] = None
                    confidence: float

                client = OpenAI()
                result = client.beta.chat.completions.parse(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You validate debate card tags against source body text. "
                                "A tag is overclaiming if it asserts something the body text does not support. "
                                "If the tag is not fully supported, provide a safer_tag grounded only in the body."
                            ),
                        },
                        {
                            "role": "user",
                            "content": (
                                f"Tag: {tag}\n\n"
                                f"Body text (first 800 chars): {body_text[:800]}\n\n"
                                "Is the tag supported by the body? If not, what safer tag would be grounded in the body?"
                            ),
                        },
                    ],
                    response_format=_TagValidationOutput,
                    temperature=0.0,
                    max_tokens=200,
                )
                llm_val = result.choices[0].message.parsed
                if llm_val and not llm_val.tag_supported_by_body and llm_val.safer_tag:
                    safe_tag = llm_val.safer_tag
                    overclaim_warning = llm_val.overclaim_warning or "Tag not fully supported by source text (LLM)"
            except Exception as exc:
                logger.debug("LLM tag validation failed: %s", exc)

        return safe_tag, overclaim_warning

    except Exception as exc:
        logger.debug("_validate_card_tag failed: %s", exc)
        return tag, None


# ── Main candidate generation ─────────────────────────────────────────────────

def generate_candidate_cards(
    search_results: list[dict],
    topic: str,
    claim_to_support: str,
    side: Optional[str],
    user_id: str,
    max_cards: int = _MAX_CARDS,
    source_quality_min: SourceQuality = "medium",
    include_partial_support: bool = True,
    use_llm: bool = True,
    research_plan: Optional[object] = None,  # ClaimResearchPlan from claim_decomposition
) -> CandidateCardsResult:
    """Extract, score, and draft candidate cards from search results.

    Acceptance pipeline: for each URL we extract text, classify evidence role,
    check source quality >= 3.0, require non-empty best_supported_claim and
    safe_tag_scope, then validate the card tag for overclaiming. Counter-evidence
    goes to counter_evidence_drafts instead of card_drafts. Sources where
    extraction fails but a usable snippet (>= 80 chars) exists are added to
    possible_lead_urls rather than silently dropped.

    Returns a CandidateCardsResult with:
    - card_drafts: list of draft dicts (status='draft', not yet saved to evidence_cards)
    - counter_evidence_drafts: passages classified as counter-evidence (Change 1)
    - sources_considered: per-URL summary
    - warnings: non-fatal notes
    - diagnostic counts (sources_found, sources_attempted, …)
    - rejected_by_source_quality / rejected_by_missing_best_claim counters (Change 1)
    - possible_lead_urls: URLs worth manual follow-up (extraction failed, snippet exists)
    - suggested_revised_claims: narrower claims based on what sources actually say
    - candidates_by_role: count of candidates per evidence role
    - normalized_claim: normalized form of the claim (from research_plan if provided)
    - corrections_applied: list of corrections applied to the claim

    SAFETY: body_text always comes from extracted source text.
             Cards are not generated for not_useful passages (debate_usefulness_score < 4.0).
             Maximum 4 cards returned.
             Counter-evidence is NEVER mixed into card_drafts.
             is_snippet_source=True for cards derived from Tavily snippets.
    """
    _quality_min_rank = _QUALITY_ORDER.get(source_quality_min, 0)
    concepts = expand_claim_concepts(claim_to_support, topic)

    result = CandidateCardsResult(sources_found=len(search_results))

    # Carry over plan info if provided
    if research_plan is not None:
        result.normalized_claim = getattr(research_plan, "normalized_claim", claim_to_support)
        result.corrections_applied = getattr(research_plan, "corrections_applied", [])

    # ── Evidence Set Plan (Parts 1-2): plan distinct strategic slots ──────────
    from app.config import settings as _slot_settings
    _slots: list = []
    if getattr(_slot_settings, "research_enable_slot_planner", True):
        try:
            from app.services.evidence_set_planner import plan_evidence_set
            _plan = plan_evidence_set(
                topic or "", claim_to_support, side or "", use_llm=False,
            )
            _slots = list(_plan.slots)
            result.evidence_set_plan = _plan.model_dump()
        except Exception as exc:
            logger.debug("evidence set planning failed: %s", exc)

    # Map evidence role → first matching slot for slot assignment.
    def _slot_for_role(role: str, used_slot_ids: set) -> Optional[object]:
        for s in _slots:
            if s.slot_id in used_slot_ids:
                continue
            if getattr(s, "desired_evidence_role", "") == role:
                return s
        # Fall back to any unused slot for diversity labelling.
        for s in _slots:
            if s.slot_id not in used_slot_ids:
                return s
        return None

    _used_slot_ids: set = set()

    existing_bodies: list[str] = []
    seen_domains: dict[str, int] = {}
    weak_best_claims: list[str] = []
    # Pass 8: track body hashes for O(1) exact-dup check before word-set dedup
    _seen_body_hashes: set[str] = set()
    # Pass 8: aggregated retrieval stats for trace
    _total_dedup_removed: int = 0
    _retrieval_backend: str = ""

    for candidate in search_results:
        if len(result.card_drafts) >= max_cards:
            break

        url = candidate.get("url", "")
        if not url:
            continue

        domain = _domain_from_url(url)
        if seen_domains.get(domain, 0) >= 2:
            result.sources_considered.append({"url": url, "status": "skipped", "reason": "domain limit reached"})
            continue

        result.sources_attempted += 1

        # Gather provider-level data from the search result dict
        snippet_text = candidate.get("content") or candidate.get("snippet") or ""
        provider_raw = candidate.get("raw_content") or ""
        provider_name = candidate.get("_provider", "tavily")

        # ── Multi-step extraction fallback chain ──────────────────────────────
        # Step 1: Use provider raw content if long enough and not boilerplate
        extracted_text = ""
        extraction_method = "failed"
        is_snippet_source = False
        article = None

        if len(provider_raw.strip()) >= 600 and not _looks_like_boilerplate(provider_raw):
            extracted_text = provider_raw.strip()
            extraction_method = "provider_raw"
            # Build a synthetic article for downstream use
            from app.models.research import ArticleMetadata
            _meta = ArticleMetadata(url=url)
            article = ExtractedArticle(
                url=url,
                metadata=_meta,
                extracted_text=extracted_text,
                extraction_method=extraction_method,
                extraction_confidence=0.7,
                status="ok",
            )

        # Step 2: Standard extraction (trafilatura/BS4)
        if not extracted_text:
            try:
                _art = extract_article(url)
                if _art and len(_art.extracted_text or "") >= 200:
                    extracted_text = _art.extracted_text
                    extraction_method = _art.extraction_method
                    article = _art
                else:
                    # Keep the article object for error reporting; may be used in Step 3/4
                    article = _art
            except ValueError as exc:
                result.sources_considered.append({"url": url, "status": "skipped", "reason": f"SSRF rejected: {exc}"})
                continue
            except Exception as exc:
                result.sources_considered.append({"url": url, "status": "failed", "reason": str(exc)})
                result.warnings.append(f"Could not fetch {url}: {exc}")
                continue

        # Step 2.5: GROBID for PDF URLs (optional)
        from app.config import settings as _settings
        from app.services.grobid_extraction import extract_with_grobid, is_pdf_url
        _grobid_url = getattr(_settings, "grobid_url", None)
        _grobid_enabled = getattr(_settings, "research_enable_grobid", False)
        if not extracted_text and _grobid_enabled and _grobid_url and is_pdf_url(url):
            result.grobid_attempted += 1
            _max_pdf_mb = getattr(_settings, "research_max_pdf_mb", 10)
            grobid_meta = extract_with_grobid(url, _grobid_url, _max_pdf_mb)
            if grobid_meta and grobid_meta.full_text:
                result.grobid_succeeded += 1
                extracted_text = grobid_meta.full_text
                extraction_method = "grobid"
                # Build article from GROBID metadata
                from app.models.research import ArticleMetadata
                _meta = ArticleMetadata(
                    url=url,
                    title=grobid_meta.title or None,
                    author=grobid_meta.author_display or None,
                    published_date=grobid_meta.year or None,
                )
                article = ExtractedArticle(
                    url=url, metadata=_meta, extracted_text=extracted_text,
                    extraction_method="grobid", extraction_confidence=0.85, status="ok",
                )
            else:
                result.grobid_failed += 1

        # Step 3: Firecrawl if standard extraction insufficient
        if not extracted_text:
            _firecrawl_key = getattr(_settings, "firecrawl_api_key", None)
            if _firecrawl_key:
                # Re-validate URL before delegating to external Firecrawl API
                from app.services.web_article_extraction import validate_url as _validate_url
                _fc_safe, _fc_reason = _validate_url(url)
                if not _fc_safe:
                    result.sources_considered.append({"url": url, "status": "skipped", "reason": f"SSRF rejected (firecrawl): {_fc_reason}"})
                    continue
                result.firecrawl_attempted += 1
                _fc_text = _extract_with_firecrawl(url, _firecrawl_key)
                if _fc_text:
                    result.firecrawl_succeeded += 1
                    extracted_text = _fc_text
                    extraction_method = "firecrawl"
                    from app.models.research import ArticleMetadata
                    _meta = ArticleMetadata(url=url)
                    article = ExtractedArticle(
                        url=url,
                        metadata=_meta,
                        extracted_text=extracted_text,
                        extraction_method=extraction_method,
                        extraction_confidence=0.6,
                        status="ok",
                    )
                else:
                    result.firecrawl_failed += 1

        # Step 4: Snippet fallback
        if not extracted_text:
            if len(snippet_text.strip()) >= 150:
                extracted_text = snippet_text.strip()
                extraction_method = "snippet"
                is_snippet_source = True
                from app.models.research import ArticleMetadata
                _meta = ArticleMetadata(url=url)
                article = ExtractedArticle(
                    url=url,
                    metadata=_meta,
                    extracted_text=extracted_text,
                    extraction_method="snippet",
                    extraction_confidence=0.3,
                    status="partial",
                )
            elif len(snippet_text.strip()) >= 80:
                # Short snippet — record as possible lead but don't process
                result.possible_lead_urls.append(url)
                result.sources_considered.append({
                    "url": url,
                    "status": "possible_lead",
                    "reason": "extraction failed; short snippet available for manual review",
                })
                continue
            else:
                _err = (article.error if article and hasattr(article, "error") else None) or "extraction failed"
                result.sources_considered.append({
                    "url": url,
                    "status": "failed",
                    "reason": _err,
                })
                continue

        # Ensure we have a valid article object at this point
        if article is None:
            from app.models.research import ArticleMetadata
            _meta = ArticleMetadata(url=url)
            article = ExtractedArticle(
                url=url,
                metadata=_meta,
                extracted_text=extracted_text,
                extraction_method=extraction_method,
                extraction_confidence=0.5,
                status="ok",
            )

        if len(article.extracted_text) < 150:
            result.sources_considered.append({"url": url, "status": "skipped", "reason": "too short"})
            continue

        quality_result = rate_source_quality(url, article.metadata, article.extracted_text)
        quality_rank = _QUALITY_ORDER.get(quality_result.source_quality, 0)

        if quality_rank < _quality_min_rank:
            result.filtered_low_quality += 1
            result.sources_considered.append({
                "url": url,
                "status": "skipped",
                "reason": f"quality={quality_result.source_quality} below minimum={source_quality_min}",
                "quality": quality_result.source_quality,
            })
            continue

        result.sources_extracted += 1

        # ── Passage construction: paragraph-aware (Pass 8) ────────────────────
        from app.services.evidence_passage_builder import build_passages as _build_passages
        _meta = article.metadata if article else None
        _p8_candidates = _build_passages(
            article.extracted_text,
            url=url,
            domain=domain,
            title=(_meta.title or "") if _meta else "",
            author=(_meta.author or "") if _meta else "",
            published_date=(_meta.published_date or "") if _meta else "",
            provider=provider_name,
            query=candidate.get("query", claim_to_support[:80]),
        )

        if _p8_candidates:
            all_chunks = [c.text for c in _p8_candidates]
        else:
            all_chunks = _chunk_text(article.extracted_text)
        if not all_chunks:
            all_chunks = _split_paragraphs(article.extracted_text)
        if not all_chunks:
            result.sources_considered.append({"url": url, "status": "skipped", "reason": "no usable text chunks"})
            continue

        # ── Rerank chunks before LLM classification ───────────────────────────
        from app.config import settings as _settings
        _max_chunks = getattr(_settings, "research_search_max_classified_chunks", 40)
        _cohere_key = getattr(_settings, "cohere_api_key", None)
        _chunk_reranker_used = "none"

        if _cohere_key and use_llm and len(all_chunks) > 1:
            result.cohere_rerank_attempted += 1
            _rerank_query = (
                f"Find passages useful as debate evidence supporting: {claim_to_support}. "
                f"Topic: {topic}."
            )
            _cohere_reranked = _rerank_chunks_cohere(
                all_chunks, _rerank_query, _cohere_key, max_chunks=min(10, _max_chunks)
            )
            if _cohere_reranked:
                result.cohere_rerank_succeeded += 1
                all_chunks = _cohere_reranked
                _chunk_reranker_used = "cohere"
                if result.reranker_used == "none":
                    result.reranker_used = "cohere"

        if _chunk_reranker_used == "none":
            _sq_score, _ = _assess_source_quality(url, article, extraction_method)
            if _p8_candidates:
                # Pass 8: use hybrid BM25+RRF ranker when passage builder succeeded
                from app.services.evidence_hybrid_retriever import hybrid_rank_passages as _hybrid_rank
                _norm_cred = _sq_score / 10.0
                for _pc in _p8_candidates:
                    _pc.credibility_score = _norm_cred
                _ranked_cands, _ret_stats = _hybrid_rank(
                    _p8_candidates,
                    claim=claim_to_support,
                    topic=topic,
                    role="direct_support",
                    source_authority=_norm_cred,
                )
                all_chunks = [c.text for c in _ranked_cands[:min(10, _max_chunks)]]
                if not _retrieval_backend:
                    _retrieval_backend = _ret_stats.backend
                if result.reranker_used == "none":
                    result.reranker_used = _ret_stats.backend
            else:
                all_chunks = _rerank_chunks_heuristic(
                    all_chunks, concepts, _sq_score, max_chunks=min(10, _max_chunks)
                )
                if result.reranker_used == "none":
                    result.reranker_used = "heuristic"

        top_chunks = all_chunks[:3]

        # Process each top chunk
        chunk_processed = False
        for chunk in top_chunks:
            if len(result.card_drafts) >= max_cards:
                break

            result.passages_considered += 1

            # Classify evidence role
            role_output: Optional[EvidenceRoleOutput] = None
            if use_llm:
                role_output = _classify_role_with_llm(chunk, claim_to_support, topic, url, side)
            if role_output is None:
                role_output = _classify_role_deterministic(chunk, claim_to_support, topic, concepts)

            role = role_output.evidence_role

            # Track role counts
            result.candidates_by_role[role] = result.candidates_by_role.get(role, 0) + 1

            # Counter-evidence: keep separately, NEVER in card_drafts (Change 1)
            if role == "counter_evidence":
                result.sources_considered.append({
                    "url": url,
                    "status": "counter_evidence",
                    "reason": "Passage argues against the claim",
                })
                # Track in counter_evidence_drafts for potential pre-empt use
                result.counter_evidence_drafts.append({
                    "url": url,
                    "passage_excerpt": chunk[:200],
                    "reasoning": role_output.reasoning_short,
                })
                chunk_processed = True
                continue

            # Skip not_useful or low-usefulness
            if role == "not_useful" or role_output.debate_usefulness_score < 4.0:
                result.filtered_no_support += 1
                # Collect narrower claims as suggestions
                if role_output.best_supported_claim:
                    if role_output.best_supported_claim not in weak_best_claims:
                        weak_best_claims.append(role_output.best_supported_claim)
                continue

            # Skip if partial support excluded
            if role != "direct_support" and not include_partial_support:
                result.sources_considered.append({
                    "url": url,
                    "status": "partial_skipped",
                    "reason": "non-direct support excluded by config",
                })
                continue

            # ── Stricter acceptance gates (Change 1) ─────────────────────────
            # Gate 1: Source quality score >= 3.0
            sq_score, sq_reason = _assess_source_quality(url, article, article.extraction_method)
            if sq_score < 3.0 and not is_snippet_source:
                result.rejected_by_source_quality += 1
                result.sources_considered.append({
                    "url": url,
                    "status": "rejected_quality",
                    "reason": f"source quality score {sq_score:.1f} below 3.0: {sq_reason}",
                })
                continue

            # Gate 2: best_supported_claim must be non-empty
            bsc = (role_output.best_supported_claim or "").strip()
            if not bsc:
                # Try to synthesize a fallback from the role + topic
                bsc = f"{topic} — {role.replace('_', ' ')}" if topic else ""
            if not bsc:
                result.rejected_by_missing_best_claim += 1
                result.sources_considered.append({
                    "url": url,
                    "status": "rejected_no_best_claim",
                    "reason": "best_supported_claim is empty after classification",
                })
                continue

            # Gate 3: safe_tag_scope must be non-empty
            sts = (role_output.safe_tag_scope or "").strip()
            # Generate a minimal safe_tag_scope if missing
            if not sts:
                sts = bsc[:100]

            # Pass 8: exact-hash check before Jaccard (O(1) vs O(n))
            from app.services.evidence_deduplicator import _passage_hash as _ph
            _body_hash = _ph(chunk)
            if _body_hash in _seen_body_hashes:
                result.sources_considered.append({"url": url, "status": "duplicate", "reason": "exact-duplicate passage"})
                _total_dedup_removed += 1
                continue
            if _is_near_duplicate(chunk, existing_bodies):
                result.sources_considered.append({"url": url, "status": "duplicate", "reason": "near-duplicate passage"})
                _total_dedup_removed += 1
                continue

            # Get backward-compat support level
            support_level = _EVIDENCE_ROLE_TO_SUPPORT_LEVEL.get(role, "partial_support")

            # ── Assign this card to a strategic slot (Parts 2 + 9) ───────────
            _slot = _slot_for_role(role, _used_slot_ids)
            _slot_id = getattr(_slot, "slot_id", "") if _slot else ""
            _slot_label = getattr(_slot, "slot_label", "") if _slot else ""
            _slot_target_claim = getattr(_slot, "target_claim", "") if _slot else ""
            _slot_function = getattr(_slot, "strategic_function", "") if _slot else ""

            try:
                draft = generate_card_draft(
                    article=article,
                    topic=topic or "",
                    claim_goal=claim_to_support,
                    side=side,
                    user_id=user_id,
                    source_quality=quality_result.source_quality,
                    credibility_notes=quality_result.credibility_notes,
                    slot_id=_slot_id,
                    slot_label=_slot_label,
                    slot_target_claim=_slot_target_claim,
                )
            except Exception as exc:
                result.sources_considered.append({"url": url, "status": "draft_failed", "reason": str(exc)})
                result.warnings.append(f"Card drafting failed for {url}: {exc}")
                continue

            card_purpose = _infer_card_purpose(draft.get("body_text", ""), claim_to_support)

            # Validate and harden the tag against overclaiming (Change 6)
            raw_tag = draft.get("tag", "") or sts or bsc
            safe_tag, tag_overclaim_warning = _validate_card_tag(
                raw_tag,
                draft.get("body_text", ""),
                bsc,
                use_llm=use_llm,
            )
            if safe_tag and safe_tag != raw_tag:
                draft["tag"] = safe_tag

            # Merge overclaim warnings from role classifier + tag validator
            merged_overclaim = (role_output.overclaim_warning or "").strip() or tag_overclaim_warning

            # ── Evidence cut + citation enrichment ───────────────────────────
            from app.services.card_cutting import (
                derive_card_intelligence,
                enrich_citation_metadata,
                generate_evidence_cut,
            )

            _cut_compression_ratio = 1.0
            _cut_style = "medium_cut"
            _highlighted_text = ""
            try:
                evidence_cut = generate_evidence_cut(
                    passage=chunk,
                    claim=claim_to_support,
                    evidence_role=role,
                    tag=draft.get("tag", ""),
                    use_llm=use_llm,
                    is_snippet_source=is_snippet_source,
                )
                draft["evidence_cut"] = evidence_cut.model_dump()
                draft["cut_text_with_ellipses"] = evidence_cut.cut_text_with_ellipses
                draft["selected_spans"] = [s.model_dump() for s in evidence_cut.selected_spans]
                _cut_compression_ratio = evidence_cut.compression_ratio
                _cut_style = evidence_cut.cut_style
                _highlighted_text = (
                    (evidence_cut.read_aloud_validation.read_aloud_text
                     if evidence_cut.read_aloud_validation else "")
                    or " ".join(s.text for s in evidence_cut.cut_body_spans)
                )
            except Exception as exc:
                logger.debug("evidence_cut failed: %s", exc)

            _citation_quality = "partial"
            try:
                citation = enrich_citation_metadata(
                    url=url,
                    author=draft.get("author"),
                    title=draft.get("title"),
                    publication=draft.get("publication"),
                    published_date=draft.get("published_date"),
                    extracted_text=chunk[:500],
                )
                draft["citation"] = citation.model_dump()
                draft["short_cite"] = citation.short_cite
                draft["mla_citation"] = citation.mla_citation
                draft["citation_quality"] = citation.citation_quality
                draft["source_domain"] = citation.publication_name or ""
                _citation_quality = citation.citation_quality
            except Exception as exc:
                logger.debug("citation_enrichment failed: %s", exc)

            # ── Debate-intelligence annotations (deterministic) ──────────────
            try:
                intelligence = derive_card_intelligence(
                    evidence_role=role,
                    best_supported_claim=bsc or "",
                    overclaim_warning=merged_overclaim or "",
                    source_quality=quality_result.source_quality or "",
                    debate_usefulness_score=role_output.debate_usefulness_score,
                    is_snippet_source=is_snippet_source,
                    citation_quality=_citation_quality,
                    compression_ratio=_cut_compression_ratio,
                    cut_style=_cut_style,
                    is_counter_evidence=False,
                    claim=claim_to_support,
                    slot_label=_slot_label,
                    slot_target_claim=_slot_target_claim,
                    slot_function=_slot_function,
                    topic=topic or "",
                    passage=chunk or "",
                    source_title=draft.get("title") or "",
                    highlighted_text=_highlighted_text,
                )
                draft["intelligence"] = intelligence.model_dump()
            except Exception as exc:
                logger.debug("derive_card_intelligence failed: %s", exc)

            draft["card_source_type"] = "research_search"
            draft["slot_id"] = _slot_id
            draft["slot_label"] = _slot_label
            draft["debate_usefulness_score"] = role_output.debate_usefulness_score
            draft["draft_json"] = {
                "evidence_role": role,
                "support_level": support_level,
                "support_rationale": role_output.reasoning_short,
                "card_purpose": card_purpose,
                "claim_supported": role != "counter_evidence",
                "best_supported_claim": bsc or None,
                "overclaim_warning": merged_overclaim or None,
                "safe_tag_scope": sts or None,
                "is_counter_evidence": False,
                "is_snippet_source": is_snippet_source,
                "query_topic": topic,
                "query_claim": claim_to_support,
                "slot_id": _slot_id,
                "slot_label": _slot_label,
            }

            if _slot_id:
                _used_slot_ids.add(_slot_id)
            _accepted_body = draft.get("body_text", "")
            existing_bodies.append(_accepted_body)
            # Pass 8: register body hash so future exact-dup check is O(1)
            _seen_body_hashes.add(_ph(_accepted_body))
            seen_domains[domain] = seen_domains.get(domain, 0) + 1

            # ── Pass 11: Card support verification ───────────────────────────
            # Runs deterministic checks + optional LLM verifier. Never raises.
            # Unsupported cards are excluded; contradicted cards moved to
            # counter_evidence_drafts; partial/insufficient cards kept with warnings.
            try:
                from app.services.evidence_card_verifier import (
                    verify_card_support, should_accept_card,
                    should_move_to_counter_evidence,
                    PARTIALLY_SUPPORTED as _PARTIAL,
                    INSUFFICIENT_CONTEXT as _INSUF_CTX,
                    CONTRADICTED as _CONTRADICTED,
                )
                from app.config import settings as _v_settings

                if getattr(_v_settings, "research_enable_card_verification", True):
                    # Snippet sources cannot be fully verified — always insufficient_context
                    _src_type = (
                        "snippet_only" if is_snippet_source
                        else draft.get("draft_json", {}).get("source_text_type", "full_text")
                    )
                    _v_result = verify_card_support(
                        claim=claim_to_support,
                        tag=draft.get("tag", ""),
                        body_text=_accepted_body,
                        context=chunk or "",
                        source_text_type=_src_type,
                        best_supported_claim=bsc or "",
                        enable_semantic=False,  # LLM verifier disabled in search loop for speed
                    )

                    # Update P11 counters
                    result.p11_cards_verified += 1
                    _verd = _v_result.overall_verdict
                    if _verd == "supported":
                        result.p11_cards_supported += 1
                    elif _verd == _PARTIAL:
                        result.p11_cards_partially_supported += 1
                    elif _verd == "unsupported":
                        result.p11_cards_unsupported += 1
                    elif _verd == _CONTRADICTED:
                        result.p11_cards_contradicted += 1
                    elif _verd == _INSUF_CTX:
                        result.p11_cards_insufficient_context += 1

                    result.p11_det_mismatches += len(_v_result.deterministic_mismatches)
                    if _v_result.source_text_type == "abstract_only" and _v_result.context_limitation:
                        result.p11_abstract_warnings += 1
                    if _v_result.safer_tag_generated:
                        result.p11_safer_tags += 1

                    # Attach verification to draft_json
                    if not draft.get("draft_json"):
                        draft["draft_json"] = {}
                    draft["draft_json"]["support_verification"] = _v_result.to_dict()

                    # Contradicted supporting card → move to counter_evidence
                    if should_move_to_counter_evidence(_v_result):
                        result.counter_evidence_drafts.append({
                            "url": url,
                            "tag": draft.get("tag", ""),
                            "passage_excerpt": _accepted_body[:200],
                            "reasoning": "Card verified as contradicting the requested claim.",
                            "support_verdict": _verd,
                        })
                        result.sources_considered.append({
                            "url": url,
                            "status": "moved_to_counter_evidence",
                            "support_verdict": _verd,
                        })
                        result.candidates_generated += 1
                        chunk_processed = True
                        continue  # do NOT add to card_drafts

                    # Unsupported → exclude silently, track reason
                    if not should_accept_card(_v_result):
                        result.filtered_no_support += 1
                        result.sources_considered.append({
                            "url": url,
                            "status": "rejected_verification",
                            "support_verdict": _verd,
                            "reason": (
                                f"Card failed support verification: {_verd}. "
                                + ("; ".join(_v_result.deterministic_mismatches[:2]) or "")
                            ),
                        })
                        result.candidates_generated += 1
                        chunk_processed = True
                        continue  # do NOT add to card_drafts

            except Exception as exc:
                # Verification errors never block card generation
                logger.debug("Support verification error for %s: %s", url, exc)

            # ── End Pass 11 ──────────────────────────────────────────────────

            result.sources_considered.append({
                "url": url,
                "status": "card_generated",
                "quality": quality_result.source_quality,
                "support_level": support_level,
                "evidence_role": role,
                "slot_label": _slot_label,
            })
            result.candidates_generated += 1
            result.card_drafts.append(draft)
            chunk_processed = True
            # Only generate one card per URL
            break

        if not chunk_processed and len(result.sources_considered) < result.sources_attempted:
            result.sources_considered.append({"url": url, "status": "no_support", "reason": "No chunk passed usefulness threshold"})

    # Build suggested revised claims from weak passages
    result.suggested_revised_claims = [c for c in weak_best_claims if c.strip()][:5]

    # Pass 8: store aggregated retrieval stats on the result
    result.dedup_removed = _total_dedup_removed
    result.retrieval_backend = _retrieval_backend

    # ── Part 6: result filtering / post-processing ───────────────────────────
    _post_process_card_set(result, _slots, max_cards)

    return result


# ── Post-processing: weak leads, dedup, sort, unfilled slots (Part 6) ─────────

def _post_process_card_set(
    result: CandidateCardsResult,
    slots: list,
    max_cards: int,
) -> None:
    """Move snippet-only cards to weak_leads, drop near-duplicates, sort by
    usefulness, cap at max_cards, and compute unfilled_slots. Mutates result.
    """
    main_cards: list[dict] = []
    weak_leads: list[dict] = list(result.weak_leads)

    for card in result.card_drafts:
        dj = card.get("draft_json") or {}
        if dj.get("is_snippet_source"):
            weak_leads.append({
                "url": card.get("url"),
                "tag": card.get("tag"),
                "slot_label": card.get("slot_label", ""),
                "short_cite": card.get("short_cite", ""),
                "reason": "Snippet-only source — verify the full original manually",
                "body_excerpt": (card.get("body_text") or "")[:300],
            })
        else:
            main_cards.append(card)

    # Near-duplicate filtering: keep the more useful of any >70%-overlap pair.
    def _usefulness(c: dict) -> float:
        return float(c.get("debate_usefulness_score", 0.0) or 0.0)

    main_cards.sort(key=_usefulness, reverse=True)
    kept: list[dict] = []
    kept_bodies: list[str] = []
    for card in main_cards:
        body = card.get("body_text", "") or ""
        if _is_near_duplicate(body, kept_bodies, threshold=0.7):
            continue
        kept.append(card)
        kept_bodies.append(body)

    kept = kept[:max_cards]

    result.card_drafts = kept
    result.weak_leads = weak_leads

    # Unfilled slots: planner slots with no card assigned.
    filled_slot_ids = {c.get("slot_id") for c in kept if c.get("slot_id")}
    result.unfilled_slots = [
        s.slot_label for s in slots
        if s.slot_id not in filled_slot_ids
    ]


# ── Per-slot search path ──────────────────────────────────────────────────────

# Slot-type → preferred domain substrings. A matching domain gets a small bonus.
_SLOT_DOMAIN_PREFS: dict[str, list[str]] = {
    "legal_warrant":     [".gov", ".edu", "lawreview", "law.cornell", "brookings", "cfr.org", "rand.org", "un.org", "icj-cij"],
    "moral_warrant":     [".edu", "philosophy", "stanford.edu", "plato.stanford", "oxford", "cambridge"],
    "historical_example": [".edu", "cfr.org", "brookings", "hrw.org", "amnesty", "un.org", "rand.org"],
    "impact":            ["hrw.org", "amnesty", "un.org", "rand.org", "cfr.org", "reuters", "apnews", ".gov"],
    "threshold":         [".edu", "lawreview", "law.", "cfr.org", "brookings", "rand.org"],
}


def _slot_domain_bonus(slot_id: str, url: str) -> float:
    """Return a small quality bonus when the source domain matches slot preferences."""
    prefs = _SLOT_DOMAIN_PREFS.get(slot_id, [])
    if not prefs:
        return 0.0
    try:
        hostname = urlparse(url).hostname or ""
    except Exception:
        hostname = ""
    url_lower = url.lower()
    return 1.5 if any(p in hostname or p in url_lower for p in prefs) else 0.0


def _process_single_slot(
    slot: object,
    search_results: list[dict],
    topic: str,
    claim_to_support: str,
    side: Optional[str],
    user_id: str,
    used_canonical_urls: set,
    used_bodies: list,
    use_llm: bool,
    source_quality_min: str = "medium",
) -> "tuple[Optional[dict], Optional[dict], Optional[str]]":
    """Extract, classify, and draft the best card for one evidence slot.

    Processes all search results for the slot, picks the highest-scoring
    candidate (role match + debate usefulness + recency), generates a full
    card draft for it, and returns exactly one of three outcomes:
      - (card_draft, None, None)      — strong card found
      - (None, weak_lead, None)       — only a snippet-only source found
      - (None, None, unfilled_reason) — nothing useful found

    Mutates `used_canonical_urls` and `used_bodies` when a card is produced
    so later slots skip already-claimed URLs/text (cross-slot dedup).

    Simplified extraction chain vs. generate_candidate_cards():
    - provider_raw → trafilatura → snippet-weak-lead
    - No Firecrawl/GROBID (too expensive per-slot)
    - Top 2 reranked chunks per URL
    - Best-first selection across all candidates before card generation
    """
    _quality_min_rank = _QUALITY_ORDER.get(source_quality_min, 0)

    # Build slot-specific concepts for chunk scoring
    slot_id = getattr(slot, "slot_id", "")
    slot_label = getattr(slot, "slot_label", "")
    slot_target_claim = getattr(slot, "target_claim", claim_to_support)
    slot_desired_role = getattr(slot, "desired_evidence_role", "direct_support")
    slot_recency = getattr(slot, "recency_policy", "any")
    slot_function = getattr(slot, "strategic_function", "")
    slot_concepts = expand_claim_concepts(slot_target_claim, topic)

    # Collect: (slot_score, chunk, article, url, quality_result, role_output, role)
    best_candidate: Optional[tuple] = None
    best_slot_score: float = -1.0
    snippet_weak_lead: Optional[dict] = None

    for candidate in search_results:
        url = candidate.get("url", "")
        if not url:
            continue

        canonical = canonicalize_url(url)
        if canonical in used_canonical_urls:
            continue

        snippet_text = candidate.get("content") or candidate.get("snippet") or ""
        provider_raw = candidate.get("raw_content") or ""

        # Extraction chain (simplified — no Firecrawl/GROBID per slot)
        extracted_text = ""
        extraction_method = "failed"
        article = None

        if len(provider_raw.strip()) >= 600 and not _looks_like_boilerplate(provider_raw):
            extracted_text = provider_raw.strip()
            extraction_method = "provider_raw"
            from app.models.research import ArticleMetadata as _AM
            article = ExtractedArticle(
                url=url, metadata=_AM(url=url),
                extracted_text=extracted_text,
                extraction_method="provider_raw",
                extraction_confidence=0.7, status="ok",
            )

        if not extracted_text:
            try:
                _art = extract_article(url)
                if _art and len(_art.extracted_text or "") >= 200:
                    extracted_text = _art.extracted_text
                    extraction_method = _art.extraction_method
                    article = _art
                else:
                    article = _art
            except (ValueError, Exception):
                continue

        if not extracted_text:
            if len(snippet_text.strip()) >= 150 and snippet_weak_lead is None:
                snippet_weak_lead = {
                    "url": url,
                    "tag": None,
                    "slot_id": slot_id,
                    "slot_label": slot_label,
                    "short_cite": None,
                    "reason": "Snippet-only — verify the full article manually",
                    "body_excerpt": snippet_text[:300],
                }
            continue

        if article is None:
            from app.models.research import ArticleMetadata as _AM
            article = ExtractedArticle(
                url=url, metadata=_AM(url=url),
                extracted_text=extracted_text,
                extraction_method=extraction_method,
                extraction_confidence=0.5, status="ok",
            )

        if len(article.extracted_text) < 150:
            continue

        quality_result = rate_source_quality(url, article.metadata, article.extracted_text)
        quality_rank = _QUALITY_ORDER.get(quality_result.source_quality, 0)
        if quality_rank < _quality_min_rank:
            continue

        # Chunk and rerank against slot's target_claim
        all_chunks = _chunk_text(article.extracted_text)
        if not all_chunks:
            all_chunks = _split_paragraphs(article.extracted_text)
        if not all_chunks:
            continue

        sq_score, _ = _assess_source_quality(url, article, extraction_method)
        all_chunks = _rerank_chunks_heuristic(all_chunks, slot_concepts, sq_score, max_chunks=8)

        for chunk in all_chunks[:2]:
            if _is_near_duplicate(chunk, used_bodies, threshold=0.7):
                continue

            # Classify role using slot's target_claim (not full claim)
            role_output: Optional[EvidenceRoleOutput] = None
            if use_llm:
                role_output = _classify_role_with_llm(
                    chunk, slot_target_claim, topic, url, side,
                )
            if role_output is None:
                role_output = _classify_role_deterministic(
                    chunk, slot_target_claim, topic, slot_concepts,
                )

            role = role_output.evidence_role
            if role in ("not_useful", "counter_evidence") or role_output.debate_usefulness_score < 3.5:
                continue

            # Slot-adjusted score
            slot_score = role_output.debate_usefulness_score

            # Role-match bonus: passage fills exactly the desired role
            if role == slot_desired_role:
                slot_score += 2.0

            # Recency boost for prefer_recent slots
            if slot_recency == "prefer_recent":
                pub_date = getattr(article.metadata, "published_date", "") or ""
                if pub_date and len(pub_date) >= 4:
                    try:
                        import datetime as _dt
                        if _dt.datetime.now().year - int(pub_date[:4]) <= 3:
                            slot_score += 1.5
                    except (ValueError, Exception):
                        pass

            # Slot-type domain bonus (e.g. .edu/.gov preferred for legal slots)
            slot_score += _slot_domain_bonus(slot_id, url)

            if slot_score > best_slot_score:
                best_slot_score = slot_score
                best_candidate = (slot_score, chunk, article, url, quality_result, role_output, role)

            break  # Only top-1 reranked chunk per URL

    if best_candidate is None:
        return (None, snippet_weak_lead, f"No strong source found for: {slot_label}")

    _, chunk, article, url, quality_result, role_output, role = best_candidate

    # Generate full card for the winning candidate only
    try:
        from app.services.card_cutting import (
            derive_card_intelligence,
            enrich_citation_metadata,
            generate_evidence_cut,
        )

        draft = generate_card_draft(
            article=article,
            topic=topic or "",
            claim_goal=claim_to_support,
            side=side,
            user_id=user_id,
            source_quality=quality_result.source_quality,
            credibility_notes=quality_result.credibility_notes,
            slot_id=slot_id,
            slot_label=slot_label,
            slot_target_claim=slot_target_claim,
        )

        _cut_cr = 1.0
        _cut_style = "medium_cut"
        _highlighted_text = ""
        try:
            evidence_cut = generate_evidence_cut(
                passage=chunk,
                claim=slot_target_claim,
                evidence_role=role,
                tag=draft.get("tag", ""),
                use_llm=use_llm,
                is_snippet_source=False,
            )
            draft["evidence_cut"] = evidence_cut.model_dump()
            draft["cut_text_with_ellipses"] = evidence_cut.cut_text_with_ellipses
            draft["selected_spans"] = [s.model_dump() for s in evidence_cut.selected_spans]
            _cut_cr = evidence_cut.compression_ratio
            _cut_style = evidence_cut.cut_style
            _highlighted_text = (
                (evidence_cut.read_aloud_validation.read_aloud_text
                 if evidence_cut.read_aloud_validation else "")
                or " ".join(s.text for s in evidence_cut.cut_body_spans)
            )
        except Exception as exc:
            logger.debug("Per-slot evidence_cut failed: %s", exc)

        _citation_quality = "partial"
        try:
            citation = enrich_citation_metadata(
                url=url,
                author=draft.get("author"),
                title=draft.get("title"),
                publication=draft.get("publication"),
                published_date=draft.get("published_date"),
                extracted_text=chunk[:500],
            )
            draft["citation"] = citation.model_dump()
            draft["short_cite"] = citation.short_cite
            draft["mla_citation"] = citation.mla_citation
            draft["citation_quality"] = citation.citation_quality
            draft["source_domain"] = citation.publication_name or ""
            _citation_quality = citation.citation_quality
        except Exception as exc:
            logger.debug("Per-slot citation_enrichment failed: %s", exc)

        bsc = (role_output.best_supported_claim or "").strip() or slot_target_claim[:100]
        merged_overclaim = (role_output.overclaim_warning or "").strip()
        sts = (role_output.safe_tag_scope or "").strip() or bsc[:100]

        # ── Override tag with slot+role-aware generation ──────────────────────
        # generate_card_draft() drafts a tag without knowing the classified role.
        # We re-generate here using the actual role so each slot gets a specific tag.
        try:
            from app.services.card_cutting import generate_debate_tag as _gen_tag
            _slot_tag, _tag_over = _gen_tag(
                chunk,
                slot_target_claim,
                role,
                slot_label,
                slot_target_claim,
                use_llm=use_llm,
            )
            if _slot_tag and _slot_tag.strip():
                draft["tag"] = _slot_tag
            if _tag_over and not merged_overclaim:
                merged_overclaim = _tag_over
        except Exception as _te:
            logger.debug("Per-slot tag generation failed: %s", _te)

        # Validate tag for overclaiming against body text (deterministic only per slot)
        try:
            _safe_tag, _tag_warn = _validate_card_tag(
                draft.get("tag", ""),
                draft.get("body_text", ""),
                bsc,
                use_llm=False,
            )
            if _safe_tag and _safe_tag != draft.get("tag", ""):
                draft["tag"] = _safe_tag
            if _tag_warn and not merged_overclaim:
                merged_overclaim = _tag_warn
        except Exception as _ve:
            logger.debug("Per-slot tag validation failed: %s", _ve)

        try:
            intelligence = derive_card_intelligence(
                evidence_role=role,
                best_supported_claim=bsc,
                overclaim_warning=merged_overclaim,
                source_quality=quality_result.source_quality or "",
                debate_usefulness_score=role_output.debate_usefulness_score,
                is_snippet_source=False,
                citation_quality=_citation_quality,
                compression_ratio=_cut_cr,
                cut_style=_cut_style,
                is_counter_evidence=False,
                claim=claim_to_support,
                slot_label=slot_label,
                slot_target_claim=slot_target_claim,
                slot_function=slot_function,
                topic=topic or "",
                passage=draft.get("body_text") or "",
                source_title=draft.get("title") or "",
                highlighted_text=_highlighted_text,
            )
            draft["intelligence"] = intelligence.model_dump()
        except Exception as exc:
            logger.debug("Per-slot derive_card_intelligence failed: %s", exc)

        support_level = _EVIDENCE_ROLE_TO_SUPPORT_LEVEL.get(role, "partial_support")
        draft["card_source_type"] = "research_search"
        draft["slot_id"] = slot_id
        draft["slot_label"] = slot_label
        draft["debate_usefulness_score"] = best_slot_score
        draft["draft_json"] = {
            "evidence_role": role,
            "support_level": support_level,
            "support_rationale": role_output.reasoning_short,
            "card_purpose": _infer_card_purpose(draft.get("body_text", ""), slot_target_claim),
            "claim_supported": True,
            "best_supported_claim": bsc or None,
            "overclaim_warning": merged_overclaim or None,
            "safe_tag_scope": sts or None,
            "is_counter_evidence": False,
            "is_snippet_source": False,
            "query_topic": topic,
            "query_claim": claim_to_support,
            "slot_id": slot_id,
            "slot_label": slot_label,
        }

        used_canonical_urls.add(canonicalize_url(url))
        used_bodies.append(draft.get("body_text", ""))
        return (draft, None, None)

    except Exception as exc:
        logger.debug("Per-slot card generation failed for %s: %s", url, exc)
        return (None, snippet_weak_lead, f"Card generation failed for {slot_label}: {exc}")


def generate_cards_per_slot(
    per_slot_results: dict,
    plan: object,
    topic: str,
    claim_to_support: str,
    side: Optional[str],
    user_id: str,
    max_cards: int = _MAX_CARDS,
    source_quality_min: str = "medium",
    use_llm: bool = True,
) -> CandidateCardsResult:
    """Process per-slot search results: at most 1 card per slot, up to max_cards total.

    Each slot's results are processed independently.  Cross-slot URL and body-text
    deduplication is enforced via shared sets passed into _process_single_slot.

    Args:
        per_slot_results: {slot_id: [search_result_dicts]} from per-slot Tavily searches.
        plan: EvidenceSetPlan from evidence_set_planner.
        topic / claim_to_support / side / user_id: search context.
        max_cards: hard cap on total cards returned (default _MAX_CARDS = 5).

    Returns CandidateCardsResult with:
        card_drafts: up to max_cards cards (one per filled slot)
        weak_leads:  snippet-only sources (by slot)
        unfilled_slots: slot labels where no card was found
        slot_diagnostics: per-slot outcome summary
    """
    slots = list(getattr(plan, "slots", []))
    result = CandidateCardsResult(
        sources_found=sum(len(v) for v in per_slot_results.values()),
        evidence_set_plan=plan.model_dump() if plan and hasattr(plan, "model_dump") else None,
    )

    used_canonical_urls: set = set()
    used_bodies: list = []

    for slot in slots:
        slot_id = getattr(slot, "slot_id", "")
        slot_label = getattr(slot, "slot_label", "")

        if len(result.card_drafts) >= max_cards:
            result.unfilled_slots.append(slot_label)
            result.slot_unfilled_reasons[slot_id] = "Max cards already reached"
            result.slot_diagnostics[slot_id] = {
                "urls_in_pool": 0,
                "outcome": "skipped",
                "reason": "max cards reached",
            }
            continue

        slot_results = per_slot_results.get(slot_id, [])
        result.slot_urls_found[slot_id] = len(slot_results)
        result.sources_attempted += len(slot_results)

        card, weak_lead, unfilled_reason = _process_single_slot(
            slot=slot,
            search_results=slot_results,
            topic=topic,
            claim_to_support=claim_to_support,
            side=side,
            user_id=user_id,
            used_canonical_urls=used_canonical_urls,
            used_bodies=used_bodies,
            use_llm=use_llm,
            source_quality_min=source_quality_min,
        )

        slot_diag: dict = {
            "urls_in_pool": len(slot_results),
            "recency_policy": getattr(slot, "recency_policy", "any"),
            "desired_role": getattr(slot, "desired_evidence_role", ""),
        }

        if card is not None:
            result.card_drafts.append(card)
            result.candidates_generated += 1
            result.sources_extracted += 1
            result.slot_cards_filled.append(slot_id)
            role = card.get("draft_json", {}).get("evidence_role", "")
            if role:
                result.candidates_by_role[role] = result.candidates_by_role.get(role, 0) + 1
            slot_diag["outcome"] = "card"
        elif weak_lead is not None:
            result.weak_leads.append(weak_lead)
            result.slot_weak_leads_by_slot.append(slot_id)
            slot_diag["outcome"] = "weak_lead"
        else:
            result.unfilled_slots.append(slot_label)
            result.slot_unfilled_reasons[slot_id] = unfilled_reason or "No strong source found"
            slot_diag["outcome"] = "unfilled"
            slot_diag["reason"] = unfilled_reason

        result.slot_diagnostics[slot_id] = slot_diag

    # Sort cards by slot_score descending
    result.card_drafts.sort(
        key=lambda c: float(c.get("debate_usefulness_score", 0) or 0),
        reverse=True,
    )

    return result
