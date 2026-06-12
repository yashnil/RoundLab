"""Deterministic source quality heuristics for Research-to-Card Evidence Builder.

Rates sources as high/medium/low/unknown based on domain, metadata, and content
signals. These are estimates — RoundLab does not make authoritative editorial
judgments about any source.
"""

import re
from urllib.parse import urlparse

from app.models.research import ArticleMetadata, SourceQualityResult

# ── Domain heuristics ────────────────────────────────────────────────────────

_HIGH_DOMAINS: frozenset[str] = frozenset({
    # Government / official
    "cdc.gov", "nih.gov", "cbo.gov", "gao.gov", "bls.gov", "census.gov",
    "fed.us", "whitehouse.gov", "state.gov", "defense.gov", "energy.gov",
    "epa.gov", "fda.gov", "justice.gov", "treasury.gov", "hhs.gov",
    "worldbank.org", "un.org", "who.int", "imf.org", "nato.int", "oecd.org",
    # Academic / journals
    "pubmed.ncbi.nlm.nih.gov", "scholar.google.com", "jstor.org",
    "nature.com", "science.org", "sciencemag.org", "cell.com",
    "lancet.com", "nejm.org", "bmj.com", "jamanetwork.com",
    "annals.org", "thelancet.com", "springer.com", "wiley.com",
    "tandfonline.com", "sagepub.com", "pnas.org", "plos.org",
    "frontiersin.org", "mdpi.com", "academic.oup.com", "cambridge.org",
    "arxiv.org", "ssrn.com", "nber.org", "bls.gov",
    # Major think tanks
    "rand.org", "brookings.edu", "pewresearch.org", "cfr.org",
    "csis.org", "iiss.org", "chathamhouse.org", "carnegieendowment.org",
    "wilsoncenter.org", "usip.org", "stimson.org",
    "cato.org", "heritage.org", "aei.org", "urban.org", "cbpp.org",
})

_HIGH_TLDS: frozenset[str] = frozenset({".gov", ".edu", ".mil"})

_MEDIUM_DOMAINS: frozenset[str] = frozenset({
    # Major media
    "nytimes.com", "washingtonpost.com", "wsj.com", "ft.com",
    "economist.com", "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk",
    "theguardian.com", "theatlantic.com", "foreignaffairs.com",
    "foreignpolicy.com", "politico.com", "thehill.com", "axios.com",
    "bloomberg.com", "businessinsider.com", "forbes.com",
    "time.com", "usatoday.com", "latimes.com", "chicagotribune.com",
    "npr.org", "pbs.org", "vox.com", "fivethirtyeight.com",
    "statista.com", "worldometers.info",
})

_LOW_SIGNALS: tuple[str, ...] = (
    "reddit.com", "quora.com", "wikipedia.org", "medium.com",
    "substack.com", "blogspot.com", "wordpress.com", "tumblr.com",
    "youtube.com", "twitter.com", "x.com", "facebook.com",
    "tiktok.com", "instagram.com", "linkedin.com",
)


# ── Quality rating ────────────────────────────────────────────────────────────

def rate_source_quality(
    url: str,
    metadata: ArticleMetadata,
    extracted_text: str = "",
) -> SourceQualityResult:
    """Estimate source quality based on domain, metadata completeness, and content.

    Returns a SourceQualityResult with quality, credibility_notes, and warnings.
    This is an estimate — not an authoritative editorial judgment.
    """
    warnings: list[str] = []
    notes_parts: list[str] = []

    try:
        hostname = urlparse(url).hostname or ""
    except Exception:
        hostname = ""

    domain = hostname.lower().removeprefix("www.")

    # ── Domain-based tier ────────────────────────────────────────────────
    tld = "." + domain.split(".")[-1] if "." in domain else ""

    if domain in _HIGH_DOMAINS or tld in _HIGH_TLDS:
        base_quality: str = "high"
        notes_parts.append("Recognized high-credibility domain or TLD.")
    elif domain in _MEDIUM_DOMAINS:
        base_quality = "medium"
        notes_parts.append("Recognized mainstream media or research outlet.")
    elif any(domain.endswith(low) or domain == low for low in _LOW_SIGNALS):
        base_quality = "low"
        notes_parts.append("User-generated content platform — verify sourcing carefully.")
    else:
        base_quality = "unknown"
        notes_parts.append("Domain not in RoundLab's quality database.")

    # ── Metadata bonus/malus ─────────────────────────────────────────────
    has_author = bool(metadata.author)
    has_date = bool(metadata.published_date)
    has_title = bool(metadata.title)

    if base_quality == "unknown":
        if has_author and has_date:
            base_quality = "medium"
            notes_parts.append("Has author and date — treated as medium quality.")
        elif not has_author and not has_date:
            base_quality = "low"
            warnings.append("No author or date found.")

    if not has_author:
        warnings.append("Author not found — attribution incomplete.")
    if not has_date:
        warnings.append("Publication date not found.")
    if not has_title:
        warnings.append("Page title not found.")

    # ── Content length signal ────────────────────────────────────────────
    text_len = len(extracted_text)
    if text_len < 300:
        warnings.append("Very short article — may not support a full card.")
        if base_quality not in ("high", "medium"):
            base_quality = "low"

    # ── Date recency ─────────────────────────────────────────────────────
    if metadata.published_date:
        year_match = re.search(r"(19|20)\d{2}", metadata.published_date)
        if year_match:
            year = int(year_match.group())
            if year < 2010:
                warnings.append(f"Article is from {year} — check if recency matters for this topic.")

    # ── Credibility note ────────────────────────────────────────────────
    notes_parts.append(
        "RoundLab source-quality estimate — not an authoritative editorial judgment. "
        "Users should verify sources independently."
    )

    final_quality: str = base_quality
    if final_quality not in ("high", "medium", "low", "unknown"):
        final_quality = "unknown"

    return SourceQualityResult(
        source_quality=final_quality,  # type: ignore[arg-type]
        credibility_notes=" ".join(notes_parts),
        warnings=warnings,
    )
