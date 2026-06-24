"""Pass 14 — Evidence Freshness Assessment.

Assesses whether a saved evidence card is still current relative to the claim
it supports. Does NOT automatically mark cards stale purely by age.

Public interface:
    assess_freshness(card, *, today=None) -> EvidenceFreshnessAssessment

Freshness states:
    current               — well within accepted window for claim type
    aging                 — approaching staleness; worth monitoring
    stale                 — clearly outside the accepted window
    superseded            — a newer related source was found (must be explicit)
    older_but_still_relevant — date is old but claim type tolerates it
    freshness_unknown     — no publication date and cannot be inferred
    not_time_sensitive    — claim type is inherently non-temporal

Clock dependency:
    Pass `today` (a datetime.date) for deterministic tests.
    Defaults to date.today() in production.

Design invariants:
    - Never raises; returns freshness_unknown on unexpected errors.
    - Does not call any LLM or network service.
    - Does not modify the card.
    - Does not treat old evidence as false solely because of age.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Optional

from app.models.tournament_prep import EvidenceFreshnessAssessment, FreshnessState

logger = logging.getLogger(__name__)

# ── Claim-type classifiers ────────────────────────────────────────────────────
# These patterns look for keywords in the card tag/body that indicate the
# temporal sensitivity of the claim.

_STAT_PATTERNS = re.compile(
    r"\b(percent|%|rate|ratio|growth|gdp|unemployment|inflation|poll|approval|"
    r"survey|index|price|cost|market share|revenue|users|subscribers|daily active)\b",
    re.IGNORECASE,
)
_POLICY_PATTERNS = re.compile(
    r"\b(policy|regulation|rule|executive order|statute|bill|act |mandate|"
    r"ban|tax|tariff|law |legislation|directive)\b",
    re.IGNORECASE,
)
_LAW_PATTERNS = re.compile(
    r"\b(court|ruling|decision|held|plaintiff|defendant|circuit|supreme court|"
    r"case |v\.|upheld|overturned|precedent|enjoined)\b",
    re.IGNORECASE,
)
_SCIENCE_PATTERNS = re.compile(
    r"\b(study|research|researchers|findings|journal|peer.reviewed|meta.analysis|"
    r"randomized|clinical trial|published in|nature|science|lancet|jama)\b",
    re.IGNORECASE,
)
_HISTORICAL_PATTERNS = re.compile(
    r"\b(in \d{3,4}|century|war|revolution|founding|historical|dated back|"
    r"ancient|during the|in the \d{4}s)\b",
    re.IGNORECASE,
)
_TECH_PATTERNS = re.compile(
    r"\b(ai|artificial intelligence|algorithm|platform|social media|internet|"
    r"software|app |cloud|model |llm|gpt|neural|chip|semiconductor)\b",
    re.IGNORECASE,
)

# ── Freshness windows by claim type (in days) ─────────────────────────────────

_FRESHNESS_WINDOWS: dict[str, dict[str, int]] = {
    "statistics": {
        "current": 365,        # <1 year → current
        "aging": 730,          # 1-2 years → aging
        "stale": 730,          # >2 years → stale
    },
    "market_conditions": {
        "current": 180,
        "aging": 365,
        "stale": 365,
    },
    "technology": {
        "current": 365,
        "aging": 730,
        "stale": 730,
    },
    "policy": {
        "current": 730,        # policies can persist 2+ years
        "aging": 1460,
        "stale": 1460,
    },
    "law": {
        "current": 1460,       # laws may persist; flag if very old
        "aging": 2920,
        "stale": 2920,
    },
    "scientific": {
        "current": 1825,       # foundational research doesn't auto-expire
        "aging": 3650,
        "stale": 3650,
    },
    "historical": {
        "current": 999999,     # never stale; historical facts don't expire
        "aging": 999999,
        "stale": 999999,
    },
    "general": {
        "current": 1095,       # default: 3 years
        "aging": 1825,
        "stale": 1825,
    },
}

_CLAIM_TYPE_LABELS: dict[str, str] = {
    "statistics": "current statistics / public opinion",
    "market_conditions": "market conditions / prices",
    "technology": "AI / platform / technology behavior",
    "policy": "active policy effects",
    "law": "law or court ruling",
    "scientific": "scientific research",
    "historical": "historical fact",
    "general": "general claim",
}


def _classify_claim_type(tag: Optional[str], body: Optional[str]) -> str:
    """Infer the temporal sensitivity of the claim from text signals."""
    text = f"{tag or ''} {body or ''}".lower()
    if _HISTORICAL_PATTERNS.search(text):
        return "historical"
    if _LAW_PATTERNS.search(text):
        return "law"
    if _STAT_PATTERNS.search(text):
        return "statistics"
    if _TECH_PATTERNS.search(text):
        return "technology"
    if _POLICY_PATTERNS.search(text):
        return "policy"
    if _SCIENCE_PATTERNS.search(text):
        return "scientific"
    return "general"


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """Try to parse an ISO or partial date string. Returns None on failure."""
    if not date_str:
        return None
    # Try YYYY-MM-DD
    try:
        return date.fromisoformat(date_str[:10])
    except ValueError:
        pass
    # Try YYYY alone
    m = re.match(r"^(\d{4})$", date_str.strip())
    if m:
        try:
            return date(int(m.group(1)), 1, 1)
        except ValueError:
            pass
    return None


def _compute_freshness(
    days_old: int,
    claim_type: str,
    has_newer_corroboration: bool,
) -> tuple[FreshnessState, str, str]:
    """Return (state, rule_name, explanation)."""
    windows = _FRESHNESS_WINDOWS.get(claim_type, _FRESHNESS_WINDOWS["general"])
    type_label = _CLAIM_TYPE_LABELS.get(claim_type, claim_type)

    # Historical facts are never stale
    if claim_type == "historical":
        return (
            "not_time_sensitive",
            "historical_fact_rule",
            f"Historical facts do not expire. This card describes {type_label} "
            f"and is {days_old} days old, which is acceptable.",
        )

    if days_old <= windows["current"]:
        return (
            "current",
            f"{claim_type}_current_rule",
            f"Evidence is {days_old} days old, within the {windows['current']}-day "
            f"freshness window for {type_label}.",
        )

    if days_old <= windows["aging"]:
        if has_newer_corroboration:
            return (
                "older_but_still_relevant",
                f"{claim_type}_corroborated_rule",
                f"Evidence is {days_old} days old for {type_label}. A newer related "
                "source corroborates this finding, so it remains strategically usable.",
            )
        return (
            "aging",
            f"{claim_type}_aging_rule",
            f"Evidence is {days_old} days old for {type_label}. Consider checking "
            "for updated data, but it is not yet stale.",
        )

    # Beyond aging window
    if has_newer_corroboration:
        return (
            "older_but_still_relevant",
            f"{claim_type}_old_corroborated_rule",
            f"Evidence is {days_old} days old for {type_label}, which exceeds the "
            "normal freshness window. However, a newer source corroborates this finding.",
        )
    return (
        "stale",
        f"{claim_type}_stale_rule",
        f"Evidence is {days_old} days old for {type_label} "
        f"(threshold: {windows['stale']} days). Prioritize finding an updated source.",
    )


def assess_freshness(
    card: dict,
    *,
    today: Optional[date] = None,
    has_newer_corroboration: bool = False,
) -> EvidenceFreshnessAssessment:
    """
    Assess freshness for a single card dict.

    Args:
        card: Dict with at minimum: id, tag, body_text, published_date.
        today: Override for deterministic testing; defaults to date.today().
        has_newer_corroboration: True if a newer related card already exists in library.
    """
    if today is None:
        today = date.today()

    card_id: str = card.get("id", "")
    tag: Optional[str] = card.get("tag") or card.get("generated_tag_text")
    body: Optional[str] = card.get("body_text")
    pub_date_str: Optional[str] = card.get("published_date")

    try:
        claim_type = _classify_claim_type(tag, body)
        pub_date = _parse_date(pub_date_str)
        assessed_at = datetime.utcnow().isoformat()

        if pub_date is None:
            return EvidenceFreshnessAssessment(
                card_id=card_id,
                card_tag=tag,
                published_date=None,
                freshness_state="freshness_unknown",
                claim_type=claim_type,
                rule_applied="missing_date_rule",
                explanation=(
                    "No publication date is available for this card. "
                    "Freshness cannot be assessed without a date. "
                    "Verify the source and add a date if possible."
                ),
                days_old=None,
                has_newer_corroboration=has_newer_corroboration,
                assessed_at=assessed_at,
            )

        days_old = (today - pub_date).days
        # Negative days_old means the pub date is in the future; treat as current
        days_old = max(0, days_old)

        state, rule, explanation = _compute_freshness(
            days_old, claim_type, has_newer_corroboration
        )

        return EvidenceFreshnessAssessment(
            card_id=card_id,
            card_tag=tag,
            published_date=pub_date_str,
            freshness_state=state,
            claim_type=claim_type,
            rule_applied=rule,
            explanation=explanation,
            days_old=days_old,
            has_newer_corroboration=has_newer_corroboration,
            assessed_at=assessed_at,
        )

    except Exception as exc:
        logger.warning("assess_freshness: unexpected error for card %s: %s", card_id, exc)
        return EvidenceFreshnessAssessment(
            card_id=card_id,
            card_tag=tag,
            published_date=pub_date_str,
            freshness_state="freshness_unknown",
            claim_type="general",
            rule_applied="error_fallback",
            explanation=f"Freshness could not be assessed due to an internal error: {exc}",
            days_old=None,
            has_newer_corroboration=False,
            assessed_at=datetime.utcnow().isoformat(),
        )


def assess_freshness_batch(
    cards: list[dict],
    *,
    today: Optional[date] = None,
    newer_card_ids: Optional[set[str]] = None,
) -> list[EvidenceFreshnessAssessment]:
    """Assess freshness for multiple cards. newer_card_ids marks cards that have newer siblings."""
    newer_card_ids = newer_card_ids or set()
    return [
        assess_freshness(
            c,
            today=today,
            has_newer_corroboration=c.get("id", "") in newer_card_ids,
        )
        for c in cards
    ]


def freshness_needs_attention(assessment: EvidenceFreshnessAssessment) -> bool:
    """True if the card should surface in a prep gap or warning."""
    return assessment.freshness_state in ("stale", "freshness_unknown", "aging")


def freshness_is_safe(assessment: EvidenceFreshnessAssessment) -> bool:
    """True if the card is clearly fresh or non-temporal."""
    return assessment.freshness_state in (
        "current", "not_time_sensitive", "older_but_still_relevant"
    )
