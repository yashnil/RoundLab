"""
Mastery engine — deterministic, no LLM, no database.

All functions are pure: given the same inputs they return the same outputs.
This makes them trivially testable and safe to call without side effects.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

# ── Evidence source type weights ───────────────────────────────────────────────
SOURCE_WEIGHTS: dict[str, float] = {
    "speech_analysis":            1.0,
    "drill_attempt":              0.7,
    "re_record":                  1.2,
    "coach_review":               1.5,
    "tournament_workout":         1.1,
    "judge_adaptation_exercise":  1.0,
    "full_round":                 1.1,
}

RECENCY_HALF_LIFE_DAYS: float = 14.0
MIN_EVIDENCE_FOR_MASTERY: int = 3
MASTERY_THRESHOLD: float = 75.0
PROFICIENT_THRESHOLD: float = 50.0
REFRESH_STALENESS_DAYS: float = 30.0
DECAY_PROTECTION: float = 0.5  # mastery score can't drop more than 50% in one update


# ── Core computation functions ─────────────────────────────────────────────────

def normalize_score(raw_score: float, source_type: str, input_scale: str = "0-100") -> float:
    """Normalize any raw score to 0-100."""
    if input_scale == "0-20":
        return min(100.0, max(0.0, raw_score * 5.0))
    return min(100.0, max(0.0, float(raw_score)))


def compute_recency_weight(recorded_at: datetime, now: datetime) -> float:
    """
    Exponential decay weighting: evidence loses half weight every
    RECENCY_HALF_LIFE_DAYS days.
    """
    delta = now - recorded_at
    days = max(0.0, delta.total_seconds() / 86400.0)
    return math.exp(-math.log(2) * days / RECENCY_HALF_LIFE_DAYS)


def compute_evidence_weight(source_type: str, recorded_at: datetime, now: datetime) -> float:
    """Combined weight: source importance × recency decay."""
    source_w = SOURCE_WEIGHTS.get(source_type, 0.8)
    recency_w = compute_recency_weight(recorded_at, now)
    return source_w * recency_w


def compute_confidence(evidence_items: list[dict]) -> float:
    """
    Confidence from 0-1 based on evidence count and source quality.
    Returns 0 if no evidence, approaches 1 for 5+ high-quality items.
    """
    if not evidence_items:
        return 0.0
    raw = min(1.0, len(evidence_items) / 5.0)
    avg_source_quality = (
        sum(SOURCE_WEIGHTS.get(e.get("source_type", ""), 0.8) for e in evidence_items)
        / len(evidence_items)
    )
    return min(1.0, raw * avg_source_quality)


def determine_mastery_state(
    mastery_score: float,
    confidence: float,
    evidence_count: int,
    last_demonstrated_at: Optional[datetime],
    now: datetime,
) -> str:
    """
    Deterministic state machine for mastery progression.

    States (in priority order):
      not_started  → no evidence recorded
      needs_refresh → was proficient/mastered but stale
      mastered     → score ≥ 75, confidence ≥ 0.7, ≥ 3 evidence items
      proficient   → score ≥ 50
      developing   → some evidence but score < 50, evidence_count > 2
      introduced   → first 1-2 evidence items
    """
    if evidence_count == 0:
        return "not_started"

    # Staleness check before level assessment
    if last_demonstrated_at is not None:
        days_since = (now - last_demonstrated_at).total_seconds() / 86400.0
        if days_since > REFRESH_STALENESS_DAYS and mastery_score >= PROFICIENT_THRESHOLD:
            return "needs_refresh"

    if (
        mastery_score >= MASTERY_THRESHOLD
        and confidence >= 0.7
        and evidence_count >= MIN_EVIDENCE_FOR_MASTERY
    ):
        return "mastered"

    if mastery_score >= PROFICIENT_THRESHOLD:
        return "proficient"

    if evidence_count <= 2:
        return "introduced"

    return "developing"


def aggregate_mastery(evidence_items: list[dict], now: datetime) -> dict:
    """
    Core aggregation: compute mastery from a list of evidence items.

    Each evidence item must have:
      - normalized_score : float 0-100
      - source_type      : str
      - recorded_at      : datetime (UTC) or ISO-format str

    Returns a dict with:
      mastery_score, confidence, evidence_count, last_demonstrated_at
    """
    if not evidence_items:
        return {
            "mastery_score": 0.0,
            "confidence": 0.0,
            "evidence_count": 0,
            "last_demonstrated_at": None,
        }

    total_weight = 0.0
    weighted_sum = 0.0
    last_at: Optional[datetime] = None

    for item in evidence_items:
        recorded_at = item["recorded_at"]
        if isinstance(recorded_at, str):
            recorded_at = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))

        # Ensure timezone-aware for subtraction
        if recorded_at.tzinfo is None:
            recorded_at = recorded_at.replace(tzinfo=timezone.utc)

        weight = compute_evidence_weight(item["source_type"], recorded_at, now)
        score = float(item["normalized_score"])

        weighted_sum += score * weight
        total_weight += weight

        if last_at is None or recorded_at > last_at:
            last_at = recorded_at

    if total_weight == 0:
        return {
            "mastery_score": 0.0,
            "confidence": 0.0,
            "evidence_count": len(evidence_items),
            "last_demonstrated_at": last_at,
        }

    raw_score = weighted_sum / total_weight
    confidence = compute_confidence(evidence_items)

    return {
        "mastery_score": round(raw_score, 2),
        "confidence": round(confidence, 3),
        "evidence_count": len(evidence_items),
        "last_demonstrated_at": last_at,
    }


def build_mastery_explanation(
    skill_id: str,
    old_score: float,
    new_score: float,
    new_evidence: list[dict],
) -> str:
    """Build a human-readable explanation of why mastery changed."""
    from app.event_packs.public_forum import get_skill  # deferred to avoid circular imports

    skill = get_skill(skill_id)
    skill_name = skill["name"] if skill else skill_id.replace("_", " ").title()

    if new_score > old_score:
        direction = "increased"
    elif new_score < old_score:
        direction = "decreased"
    else:
        direction = "unchanged"

    delta = abs(new_score - old_score)
    header = f"{skill_name} {direction} from {old_score:.0f} to {new_score:.0f} (+{delta:.0f} pts)" if direction == "increased" else f"{skill_name} {direction} from {old_score:.0f} to {new_score:.0f}"

    lines = [header, "because:"]
    for item in new_evidence[-3:]:
        source = item.get("source_type", "evidence").replace("_", " ")
        change = item.get("change_reason", "")
        if change:
            lines.append(f"- {source.capitalize()}: {change}")
        else:
            lines.append(f"- New {source}")

    return lines[0] + "\n" + "\n".join(lines[1:])


def compute_team_skill_gaps(student_masteries: list[dict]) -> dict:
    """
    Aggregate mastery scores across a team to find common gaps.

    student_masteries: list of dicts with keys:
      user_id, skill_id, mastery_score, mastery_state

    Returns: {skill_id: {avg_score, pct_proficient, pct_mastered, student_count}}
    """
    by_skill: dict[str, list[float]] = defaultdict(list)
    for m in student_masteries:
        by_skill[m["skill_id"]].append(float(m["mastery_score"]))

    result: dict[str, dict] = {}
    for skill_id, scores in by_skill.items():
        n = len(scores)
        avg = sum(scores) / n
        result[skill_id] = {
            "avg_score": round(avg, 1),
            "pct_proficient": round(sum(1 for s in scores if s >= PROFICIENT_THRESHOLD) / n * 100, 1),
            "pct_mastered": round(sum(1 for s in scores if s >= MASTERY_THRESHOLD) / n * 100, 1),
            "student_count": n,
        }
    return result
