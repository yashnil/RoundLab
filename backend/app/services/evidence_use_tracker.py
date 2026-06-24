"""Pass 16 — Evidence-use tracking across a full round.

Records every card use, detects violations, and marks extension/challenge status.
Underlying card bodies are immutable. All checks are deterministic.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models.round_simulation import (
    EvidenceUseViolationType,
    RoundEvidenceUse,
    RoundPhaseType,
    RoundSide,
)
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

_CAUSAL_OVERCLAIM_PATTERNS = [
    r'\b(?:proves?|shows?|demonstrates?)\s+(?:that\s+)?(?:all|every)\b',
    r'\b100\s*%',
    r'\b(?:guarantees?|certainl[y])\b',
]

_CARD_DUMPING_THRESHOLD = 3  # More than this many cards in one speech without explanation


def _detect_unsupported_tag(
    card_tag: str,
    transcript_reference: str,
    support_verdict: str,
) -> bool:
    """Return True if a card is used in a way that exceeds its support verdict."""
    if support_verdict in ("fully_supported",):
        return False
    if support_verdict in ("not_supported", "contradicts"):
        return True
    if support_verdict == "partially_supported":
        # Flag if the transcript makes absolute claims using this card
        return any(re.search(p, transcript_reference, re.IGNORECASE) for p in _CAUSAL_OVERCLAIM_PATTERNS)
    return False


def _detect_causal_overclaim(text: str) -> bool:
    """Return True if the text contains a causal overclaim pattern."""
    return any(re.search(p, text, re.IGNORECASE) for p in _CAUSAL_OVERCLAIM_PATTERNS)


def _detect_missing_citation(transcript: str, cite: str) -> bool:
    """Return True if the cite string is not found near the card use in the transcript."""
    if not cite:
        return False
    # Check if the author name or year appears in the transcript
    parts = cite.split()
    if not parts:
        return True
    author = parts[0].rstrip(",")
    return not re.search(re.escape(author), transcript, re.IGNORECASE)


def _detect_warrant_explanation(transcript: str, card_body: str) -> bool:
    """Return True if the speaker seems to explain the warrant, not just read the card."""
    explain_cues = [
        r'\bthis means\b', r'\bwhat this shows\b', r'\bthe warrant(?:\s+here)? is\b',
        r'\bthe reason this matters\b', r'\bwhy this is important\b', r'\bthe link\b',
    ]
    return any(re.search(p, transcript, re.IGNORECASE) for p in explain_cues)


def create_evidence_use_record(
    round_id: str,
    speech_id: str,
    card_id: str,
    speaker_side: RoundSide,
    phase: RoundPhaseType,
    transcript: str,
    card_data: Dict[str, Any],
) -> RoundEvidenceUse:
    """
    Build an evidence-use record by analyzing how the card is used in the transcript.
    Does NOT mutate the underlying card.
    """
    intel = card_data.get("intelligence_json") or {}
    cut_result = card_data.get("card_cutting_result_json") or {}
    cite = card_data.get("cite") or ""
    tag = card_data.get("tag") or ""
    body_text = card_data.get("body_text") or ""
    support_verdict = intel.get("support_verdict") or cut_result.get("support_verdict") or "unknown"
    source_class = intel.get("source_classification")

    # Identify what the transcript says around this card
    context_window = transcript[:1500]

    citation_given = not _detect_missing_citation(transcript, cite)
    tag_matched_source = not _detect_unsupported_tag(tag, context_window, support_verdict)
    warrant_explained = _detect_warrant_explanation(context_window, body_text)

    violations: List[str] = []
    if not citation_given:
        violations.append(EvidenceUseViolationType.MISSING_CITATION.value)
    if not tag_matched_source:
        violations.append(EvidenceUseViolationType.UNSUPPORTED_TAG.value)
    if _detect_causal_overclaim(context_window):
        violations.append(EvidenceUseViolationType.CAUSAL_OVERCLAIM.value)
    if support_verdict == "not_supported":
        violations.append(EvidenceUseViolationType.EVIDENCE_MISMATCH.value)
    if intel.get("freshness_warning"):
        violations.append(EvidenceUseViolationType.STALE_EVIDENCE.value)
    if intel.get("source_type") == "abstract":
        violations.append(EvidenceUseViolationType.ABSTRACT_ONLY_LIMIT.value)

    return RoundEvidenceUse(
        id=str(uuid.uuid4()),
        round_id=round_id,
        speech_id=speech_id,
        card_id=card_id,
        speaker_side=speaker_side,
        phase=phase,
        citation_given=citation_given,
        tag_matched_source=tag_matched_source,
        warrant_explained=warrant_explained,
        violations=violations,
        support_verdict=support_verdict,
        source_classification=source_class,
        flagged=len(violations) > 0,
        created_at=datetime.utcnow().isoformat(),
    )


def detect_card_dumping(
    round_id: str,
    speech_id: str,
    card_ids: List[str],
    transcript: str,
) -> List[str]:
    """Return list of card IDs that appear to be dumped without explanation."""
    if len(card_ids) <= _CARD_DUMPING_THRESHOLD:
        return []
    explain_cues = r'(?:this means|explains?|shows?|the warrant|the link)'
    segments = re.split(r'(?<=\.) ', transcript)
    explained_count = sum(1 for s in segments if re.search(explain_cues, s, re.IGNORECASE))
    if explained_count < len(card_ids) // 2:
        return card_ids
    return []


def mark_card_extended(round_id: str, card_id: str, phase: RoundPhaseType) -> None:
    """Mark an evidence use as extended in a later speech."""
    supabase = get_supabase()
    try:
        supabase.table("round_evidence_uses").update(
            {"extended_later": True}
        ).eq("round_id", round_id).eq("card_id", card_id).execute()
    except Exception as exc:
        logger.warning("Failed to mark card extended: %s", exc)


def mark_card_challenged(round_id: str, card_id: str) -> None:
    """Mark an evidence use as challenged by opponent."""
    supabase = get_supabase()
    try:
        supabase.table("round_evidence_uses").update(
            {"challenged_by_opponent": True}
        ).eq("round_id", round_id).eq("card_id", card_id).execute()
    except Exception as exc:
        logger.warning("Failed to mark card challenged: %s", exc)


def save_evidence_use(use: RoundEvidenceUse) -> None:
    """Persist a new evidence-use record."""
    supabase = get_supabase()
    try:
        supabase.table("round_evidence_uses").insert(use.model_dump()).execute()
    except Exception as exc:
        logger.error("Failed to save evidence use: %s", exc)


def load_evidence_uses(round_id: str) -> List[RoundEvidenceUse]:
    """Load all evidence-use records for a round."""
    supabase = get_supabase()
    try:
        resp = (
            supabase.table("round_evidence_uses")
            .select("*")
            .eq("round_id", round_id)
            .execute()
        )
        return [RoundEvidenceUse.model_validate(r) for r in (resp.data or [])]
    except Exception as exc:
        logger.warning("Failed to load evidence uses: %s", exc)
        return []


def generate_evidence_report(uses: List[RoundEvidenceUse]) -> Dict[str, Any]:
    """Summarize evidence-use patterns for the round."""
    flagged = [u for u in uses if u.flagged]
    violations: Dict[str, int] = {}
    for u in flagged:
        for v in u.violations:
            violations[v] = violations.get(v, 0) + 1
    return {
        "total_uses": len(uses),
        "flagged_uses": len(flagged),
        "cards_with_citation": sum(1 for u in uses if u.citation_given),
        "cards_with_warrant": sum(1 for u in uses if u.warrant_explained),
        "cards_extended": sum(1 for u in uses if u.extended_later),
        "cards_challenged": sum(1 for u in uses if u.challenged_by_opponent),
        "violation_counts": violations,
    }
