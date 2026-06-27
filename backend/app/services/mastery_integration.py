"""
Mastery integration — emit mastery evidence from existing event sources.

All functions are idempotent: calling twice with the same composite key is safe.
The composite unique index on mastery_evidence(user_id, source_type, source_id,
skill_id) prevents duplicate inserts; callers catch the constraint error and
return False instead of raising.

Score normalization contract:
  - Rubric scores come in on 0-20 scale → normalised to 0-100
  - Drill score_delta (percentage points, 0-100) → used directly
  - Delivery score (0-100) → used directly
  - Judge adaptation (0-100) → used directly
  - Tournament workout (0-100) → used directly

Coach action taxonomy (Pass 21.3):
  - emit_from_coach_performance_review  — coach observed real student performance
    (tied to an artifact: speech, drill, assignment).  Creates mastery_evidence.
  - emit_mastery_override               — coach explicitly sets authoritative score
    WITHOUT requiring performance evidence.  Creates coach_mastery_audit only;
    does NOT create mastery_evidence rows (avoids inflating the evidence pool).
  - Priority override (changing what to practice) does NOT call either function.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Canonical skill routing for existing event types
# ---------------------------------------------------------------------------

_RUBRIC_DIM_TO_SKILL: dict[str, str] = {
    "warranting":       "warranting",
    "weighing":         "weighing",
    "extensions":       "extensions",
    "drops":            "responses",      # canonical rename
    "clash":            "clash",
    "judge_adaptation": "judge_adaptation",
    "evidence_use":     "evidence_use",
    "organization":     "organization",
    "delivery":         "clarity",        # canonical rename
    "delivery_score":   "clarity",
}

# Legacy mission skill names → canonical
_MISSION_SKILL_TO_CANONICAL: dict[str, str] = {
    "warranting":       "warranting",
    "weighing":         "weighing",
    "extensions":       "extensions",
    "drops":            "responses",
    "evidence_use":     "evidence_use",
    "clash":            "clash",
    "judge_adaptation": "judge_adaptation",
    "delivery":         "clarity",
    "organization":     "organization",
}

# Minimum confidence thresholds before emitting evidence
_MIN_SPEECH_OVERALL_SCORE = 4     # out of 20 — reject garbage transcripts
_MIN_DRILL_SCORE = 0.0            # accept all drill scores (even 0)


def _to_canonical_skill(raw_skill: str) -> Optional[str]:
    """Map any legacy or canonical skill name to the canonical taxonomy ID."""
    from app.event_packs.public_forum import resolve_legacy_skill, SKILL_REGISTRY
    resolved = resolve_legacy_skill(raw_skill)
    if resolved in SKILL_REGISTRY:
        return resolved
    # Try rubric dim map
    mapped = _RUBRIC_DIM_TO_SKILL.get(raw_skill)
    if mapped and mapped in SKILL_REGISTRY:
        return mapped
    return None


def _rubric_score_to_0_100(score_0_20: float) -> float:
    """Normalise a 0-20 rubric score to 0-100."""
    return min(100.0, max(0.0, score_0_20 * 5.0))


def _emit_evidence(
    supabase,
    user_id: str,
    skill_id: str,
    raw_score: float,
    normalized_score: float,
    source_type: str,
    source_id: str,
    change_reason: str,
) -> bool:
    """
    Insert one mastery_evidence row and upsert mastery_scores.

    Returns True if a new row was inserted (not a duplicate).
    Idempotent: duplicate source_id silently ignored via ON CONFLICT DO NOTHING.
    """
    from app.services.mastery_engine import (
        aggregate_mastery, determine_mastery_state,
    )

    now = datetime.now(timezone.utc)

    # Insert evidence — idempotent via unique constraint on source_id
    try:
        result = supabase.table("mastery_evidence").insert(
            {
                "user_id": user_id,
                "skill_id": skill_id,
                "raw_score": raw_score,
                "normalized_score": normalized_score,
                "source_type": source_type,
                "source_id": source_id,
                "change_reason": change_reason,
                "recorded_at": now.isoformat(),
            },
            # Supabase-py uses on_conflict for upsert; for insert we pass returning
        ).execute()
        inserted = bool(result.data)
    except Exception as exc:
        msg = str(exc)
        if "duplicate" in msg.lower() or "unique" in msg.lower():
            return False  # Already recorded, not an error
        logger.warning("mastery_evidence insert failed | skill=%s | exc=%s", skill_id, exc)
        return False

    if not inserted:
        return False

    # Recompute mastery for this user+skill
    try:
        rows = (
            supabase.table("mastery_evidence")
            .select("normalized_score,source_type,recorded_at")
            .eq("user_id", user_id)
            .eq("skill_id", skill_id)
            .order("recorded_at", desc=False)
            .execute()
            .data
            or []
        )
        evidence_items = []
        for row in rows:
            rat = row.get("recorded_at")
            if isinstance(rat, str):
                rat = datetime.fromisoformat(rat.replace("Z", "+00:00"))
            evidence_items.append({
                "normalized_score": float(row["normalized_score"]),
                "source_type": row["source_type"],
                "recorded_at": rat,
            })

        agg = aggregate_mastery(evidence_items, now)
        new_state = determine_mastery_state(
            agg["mastery_score"], agg["confidence"],
            agg["evidence_count"], agg["last_demonstrated_at"], now,
        )
        last_at = agg["last_demonstrated_at"]
        supabase.table("mastery_scores").upsert(
            {
                "user_id": user_id,
                "skill_id": skill_id,
                "mastery_score": agg["mastery_score"],
                "confidence": agg["confidence"],
                "evidence_count": agg["evidence_count"],
                "mastery_state": new_state,
                "last_demonstrated_at": last_at.isoformat() if last_at else None,
                "updated_at": now.isoformat(),
            },
            on_conflict="user_id,skill_id",
        ).execute()
    except Exception as exc:
        logger.warning("mastery_scores recompute failed | skill=%s | exc=%s", skill_id, exc)

    return True


# ---------------------------------------------------------------------------
# Public integration entry points — called from existing API handlers
# ---------------------------------------------------------------------------

def emit_from_speech_analysis(
    supabase,
    user_id: str,
    speech_id: str,
    scores: dict,          # feedback_report.scores — rubric dims keyed, 0-20
    overall_score: int,    # 0-20 overall
) -> list[str]:
    """
    Emit mastery evidence from a completed speech analysis.

    Called at the end of run_speech_analysis_pipeline when feedback is saved.
    Returns list of skill_ids for which evidence was emitted.

    Low-confidence check: skip if overall_score < 4 (likely bad transcript).
    """
    if overall_score < _MIN_SPEECH_OVERALL_SCORE:
        logger.info(
            "emit_from_speech_analysis: skipping low-confidence report | "
            "score=%d speech_id=%s", overall_score, speech_id,
        )
        return []

    emitted: list[str] = []
    for dim, raw_score in scores.items():
        if raw_score is None:
            continue
        skill_id = _to_canonical_skill(dim)
        if not skill_id:
            continue
        norm = _rubric_score_to_0_100(float(raw_score))
        source_id = f"speech_analysis:{speech_id}:{skill_id}"
        ok = _emit_evidence(
            supabase, user_id, skill_id,
            raw_score=float(raw_score),
            normalized_score=norm,
            source_type="speech_analysis",
            source_id=source_id,
            change_reason=f"Speech analysis — {dim} scored {raw_score}/20",
        )
        if ok:
            emitted.append(skill_id)
    return emitted


def emit_from_drill_attempt(
    supabase,
    user_id: str,
    drill_id: str,
    skill_target: str,
    score_pct: float,      # 0-100 normalised score
    source_label: str = "Drill completed",
) -> bool:
    """
    Emit mastery evidence from a completed drill.
    `score_pct` must already be 0-100.
    """
    skill_id = _to_canonical_skill(skill_target)
    if not skill_id:
        logger.info("emit_from_drill_attempt: unknown skill '%s'", skill_target)
        return False
    source_id = f"drill_attempt:{drill_id}:{skill_id}"
    return _emit_evidence(
        supabase, user_id, skill_id,
        raw_score=score_pct,
        normalized_score=min(100.0, max(0.0, score_pct)),
        source_type="drill_attempt",
        source_id=source_id,
        change_reason=source_label,
    )


def emit_from_mission_completion(
    supabase,
    user_id: str,
    mission_id: str,
    skill: str,
    score_delta_pct: float,     # percentage-point delta from score_delta field
    after_score_raw: float,     # rubric 0-20 after score for the primary dim
) -> bool:
    """
    Emit mastery evidence when a Next Mission is completed.

    Uses after_score as the skill's performance score (normalized to 0-100),
    not the delta, because the delta can be negative when recovering from a
    bad speech.
    """
    skill_id = _to_canonical_skill(skill)
    if not skill_id:
        return False
    norm = _rubric_score_to_0_100(after_score_raw)
    source_id = f"mission_complete:{mission_id}:{skill_id}"
    return _emit_evidence(
        supabase, user_id, skill_id,
        raw_score=after_score_raw,
        normalized_score=norm,
        source_type="drill_attempt",   # mission completion is drill evidence
        source_id=source_id,
        change_reason=f"Mission completed — {skill.replace('_', ' ')} demonstrated at {norm:.0f}/100",
    )


def emit_from_rerecord(
    supabase,
    user_id: str,
    new_speech_id: str,
    parent_speech_id: str,
    skill_target: Optional[str],
    new_overall_score: int,       # 0-20
    new_skill_score: Optional[float],  # 0-20 for the specific skill dim
) -> list[str]:
    """
    Emit mastery evidence from a successful re-record (before/after comparison).

    Re-records receive source_type='re_record' which has 1.2× weight in the
    mastery engine.
    """
    emitted: list[str] = []

    # Overall score as evidence for the primary drill skill
    if skill_target and new_skill_score is not None:
        skill_id = _to_canonical_skill(skill_target)
        if skill_id:
            norm = _rubric_score_to_0_100(new_skill_score)
            source_id = f"re_record:{new_speech_id}:{skill_id}"
            ok = _emit_evidence(
                supabase, user_id, skill_id,
                raw_score=new_skill_score,
                normalized_score=norm,
                source_type="re_record",
                source_id=source_id,
                change_reason=f"Re-record — {skill_target.replace('_', ' ')} at {norm:.0f}/100",
            )
            if ok:
                emitted.append(skill_id)

    # Overall score as general evidence
    overall_norm = _rubric_score_to_0_100(new_overall_score)
    source_id = f"re_record_overall:{new_speech_id}"
    ok = _emit_evidence(
        supabase, user_id, "organization",
        raw_score=float(new_overall_score),
        normalized_score=overall_norm,
        source_type="re_record",
        source_id=source_id,
        change_reason=f"Re-record overall score {new_overall_score}/20",
    )
    if ok:
        emitted.append("organization")

    return emitted


def emit_from_coach_performance_review(
    supabase,
    coach_id: str,
    student_id: str,
    review_id: str,
    skill: str,
    score_pct: float,     # 0-100
    artifact_id: str,     # speech_id / drill_id / assignment_id backing this review
    note: str = "",
) -> bool:
    """
    Emit mastery evidence when a coach observed actual student performance.

    Requires an artifact_id (speech, drill, assignment) proving the coach
    reviewed a real performance event.  Creates both mastery_evidence and a
    coach_mastery_audit record.

    Use emit_mastery_override for explicit score-setting without evidence.
    """
    skill_id = _to_canonical_skill(skill)
    if not skill_id:
        return False
    if not artifact_id:
        logger.warning(
            "emit_from_coach_performance_review: artifact_id required | "
            "review_id=%s skill=%s", review_id, skill,
        )
        return False

    source_id = f"coach_review:{review_id}:{skill_id}"
    ok = _emit_evidence(
        supabase, student_id, skill_id,
        raw_score=score_pct,
        normalized_score=min(100.0, max(0.0, score_pct)),
        source_type="coach_review",
        source_id=source_id,
        change_reason=note or f"Coach reviewed {skill.replace('_', ' ')}",
    )
    if ok:
        # Audit record — best-effort, non-fatal
        try:
            supabase.table("coach_mastery_audit").insert({
                "coach_id": coach_id,
                "student_id": student_id,
                "skill_id": skill_id,
                "override_score": round(score_pct, 2),
                "override_type": "coach_performance_review",
                "reason": note or f"Coach observed {skill.replace('_', ' ')}",
                "artifact_id": artifact_id,
            }).execute()
        except Exception as exc:
            logger.warning("coach_mastery_audit insert failed | %s", exc)
    return ok


def emit_mastery_override(
    supabase,
    coach_id: str,
    student_id: str,
    skill: str,
    override_score: float,   # 0-100 authoritative score
    reason: str,             # required non-empty justification
    artifact_id: Optional[str] = None,
) -> bool:
    """
    Record an explicit coach mastery override.

    This does NOT create mastery_evidence rows — it is an administrative act,
    not a performance observation.  The override_score is stored in
    mastery_scores.coach_override_score by the API endpoint; this function only
    writes the audit trail.

    Returns True if the audit record was created, False on error.
    """
    skill_id = _to_canonical_skill(skill)
    if not skill_id:
        logger.warning("emit_mastery_override: unknown skill '%s'", skill)
        return False
    if not reason or not reason.strip():
        logger.warning("emit_mastery_override: reason is required")
        return False
    try:
        supabase.table("coach_mastery_audit").insert({
            "coach_id": coach_id,
            "student_id": student_id,
            "skill_id": skill_id,
            "override_score": round(override_score, 2),
            "override_type": "mastery_override",
            "reason": reason.strip(),
            "artifact_id": artifact_id,
        }).execute()
        return True
    except Exception as exc:
        logger.warning("emit_mastery_override audit insert failed | %s", exc)
        return False


# Backward-compat shim: callers that use the old name still work.
# New code should call emit_from_coach_performance_review with artifact_id.
def emit_from_coach_review(
    supabase,
    user_id: str,
    review_id: str,
    skill: str,
    score_pct: float,
    note: str = "",
) -> bool:
    """Deprecated shim — use emit_from_coach_performance_review with artifact_id."""
    logger.warning(
        "emit_from_coach_review is deprecated; call "
        "emit_from_coach_performance_review with an artifact_id",
    )
    skill_id = _to_canonical_skill(skill)
    if not skill_id:
        return False
    source_id = f"coach_review:{review_id}:{skill_id}"
    return _emit_evidence(
        supabase, user_id, skill_id,
        raw_score=score_pct,
        normalized_score=min(100.0, max(0.0, score_pct)),
        source_type="coach_review",
        source_id=source_id,
        change_reason=note or f"Coach reviewed {skill.replace('_', ' ')}",
    )


def emit_from_workout(
    supabase,
    user_id: str,
    workout_id: str,
    skill_scores: dict[str, float],  # {skill_name: score_0_100}
) -> list[str]:
    """Emit mastery evidence from a Tournament Prep workout completion."""
    emitted: list[str] = []
    for skill, score in skill_scores.items():
        skill_id = _to_canonical_skill(skill)
        if not skill_id:
            continue
        source_id = f"tournament_workout:{workout_id}:{skill_id}"
        ok = _emit_evidence(
            supabase, user_id, skill_id,
            raw_score=score,
            normalized_score=min(100.0, max(0.0, score)),
            source_type="tournament_workout",
            source_id=source_id,
            change_reason=f"Tournament prep workout — {skill.replace('_', ' ')}",
        )
        if ok:
            emitted.append(skill_id)
    return emitted


def emit_from_judge_adaptation(
    supabase,
    user_id: str,
    exercise_id: str,
    adaptation_score: float,   # 0-100
    judge_type: str = "",
) -> bool:
    """Emit mastery evidence from a Judge Adaptation exercise."""
    source_id = f"judge_adaptation_exercise:{exercise_id}"
    return _emit_evidence(
        supabase, user_id, "judge_adaptation",
        raw_score=adaptation_score,
        normalized_score=min(100.0, max(0.0, adaptation_score)),
        source_type="judge_adaptation_exercise",
        source_id=source_id,
        change_reason=f"Judge adaptation exercise ({judge_type})" if judge_type else "Judge adaptation exercise",
    )


def emit_from_full_round(
    supabase,
    user_id: str,
    round_id: str,
    skill_scores: dict[str, float],  # {skill_name: score_0_100}
) -> list[str]:
    """Emit mastery evidence from a Full Round Simulation."""
    emitted: list[str] = []
    for skill, score in skill_scores.items():
        skill_id = _to_canonical_skill(skill)
        if not skill_id:
            continue
        source_id = f"full_round:{round_id}:{skill_id}"
        ok = _emit_evidence(
            supabase, user_id, skill_id,
            raw_score=score,
            normalized_score=min(100.0, max(0.0, score)),
            source_type="full_round",
            source_id=source_id,
            change_reason=f"Full round simulation — {skill.replace('_', ' ')}",
        )
        if ok:
            emitted.append(skill_id)
    return emitted
