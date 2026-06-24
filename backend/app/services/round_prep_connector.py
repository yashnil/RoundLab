"""Pass 16 / 16.5 — Tournament Prep connector for round simulation.

Pre-round: surface readiness gaps and warn about unsafe cards.
Post-round: record discovered gaps with fingerprint deduplication;
  increment occurrence_count on existing open gaps rather than inserting duplicates.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

from app.models.round_simulation import (
    RoundArgument,
    RoundDecision,
    RoundEvidenceUse,
    RoundPhaseType,
    RoundSide,
    RoundSimulationConfig,
)
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)


def get_pre_round_readiness_warnings(
    config: RoundSimulationConfig,
    user_id: str,
) -> List[Dict[str, Any]]:
    """
    Surface readiness gaps before the round starts.
    Returns a list of warnings the student should see.
    Does NOT block the round — student can proceed anyway.
    """
    warnings: List[Dict[str, Any]] = []
    if not config.prep_workspace_id:
        return warnings

    supabase = get_supabase()

    # Load latest readiness report for this workspace
    try:
        resp = (
            supabase.table("prep_readiness_reports")
            .select("*")
            .eq("workspace_id", config.prep_workspace_id)
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        reports = resp.data or []
        if not reports:
            warnings.append({
                "type": "no_readiness_report",
                "severity": "info",
                "message": "No readiness report found. Run Tournament Prep before the round for best results.",
            })
            return warnings

        report = reports[0]
        score = report.get("readiness_score", 100)
        if score < 50:
            warnings.append({
                "type": "low_readiness",
                "severity": "warning",
                "message": f"Readiness score is {score}/100. Consider reviewing key evidence gaps before simulating.",
            })
    except Exception as exc:
        logger.warning("Failed to load readiness report: %s", exc)

    # Check for stale cards in approved list
    if config.approved_card_ids:
        try:
            resp = (
                supabase.table("evidence_cards")
                .select("id,intelligence_json")
                .in_("id", config.approved_card_ids)
                .execute()
            )
            for card in resp.data or []:
                intel = card.get("intelligence_json") or {}
                if intel.get("freshness_warning"):
                    warnings.append({
                        "type": "stale_card",
                        "severity": "warning",
                        "card_id": card["id"],
                        "message": f"Card {card['id'][:8]}... may be stale. Consider finding newer evidence.",
                    })
        except Exception as exc:
            logger.warning("Failed to check card freshness: %s", exc)

    return warnings


def _gap_fingerprint(user_id: str, workspace_id: str, category: str, title: str) -> str:
    """Stable fingerprint for deduplication. Independent of round_id."""
    key = json.dumps([user_id, workspace_id, category, title], sort_keys=True)
    return hashlib.sha256(key.encode()).hexdigest()[:32]


def _upsert_gap(
    supabase: Any,
    gap: Dict[str, Any],
    round_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Insert a new gap OR increment occurrence_count on an existing open gap
    with the same fingerprint. Never duplicates a resolved gap.
    Returns the gap row (new or updated), or None on failure.
    """
    fp = gap.get("fingerprint") or _gap_fingerprint(
        gap.get("user_id", ""),
        gap.get("workspace_id", ""),
        gap.get("category", ""),
        gap.get("title", ""),
    )
    gap["fingerprint"] = fp

    try:
        # Find existing open gap with same fingerprint
        existing_resp = (
            supabase.table("prep_gaps")
            .select("id,occurrence_count,first_seen_at,status")
            .eq("fingerprint", fp)
            .neq("status", "resolved")
            .neq("status", "completed")
            .limit(1)
            .execute()
        )
        existing = (existing_resp.data or [None])[0]
        if existing:
            # Update: increment count, record last seen
            new_count = (existing.get("occurrence_count") or 1) + 1
            supabase.table("prep_gaps").update({
                "occurrence_count": new_count,
                "last_seen_at": gap.get("last_seen_at"),
                "last_round_id": round_id,
                "round_simulation_id": round_id,
            }).eq("id", existing["id"]).execute()
            return existing
        else:
            # New gap
            gap["last_round_id"] = round_id
            supabase.table("prep_gaps").insert(gap).execute()
            return gap
    except Exception as exc:
        logger.warning("Failed to upsert gap: %s", exc)
        return None


def record_post_round_gaps(
    round_id: str,
    user_id: str,
    workspace_id: Optional[str],
    all_args: List[RoundArgument],
    evidence_uses: List[RoundEvidenceUse],
    student_side: RoundSide,
    decision: Optional[RoundDecision],
) -> List[Dict[str, Any]]:
    """
    Record gaps discovered during the round. Deduplicates via fingerprint:
    if an identical open gap already exists, increment its occurrence_count
    rather than inserting a duplicate.
    Does NOT falsely close existing gaps.
    Returns list of gaps upserted.
    """
    if not workspace_id:
        return []

    supabase = get_supabase()
    gaps_recorded: List[Dict[str, Any]] = []
    opponent_side = RoundSide.CON if student_side == RoundSide.PRO else RoundSide.PRO
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    from app.models.round_simulation import ArgumentFlowStatus

    # Gap: opponent arguments the student failed to answer (LIVE or EXTENDED = still standing)
    # DROPPED opponent args mean the student already beat them — exclude those.
    unanswered_opponent_args = [
        a for a in all_args
        if a.side == opponent_side
        and a.status in (ArgumentFlowStatus.LIVE, ArgumentFlowStatus.EXTENDED)
    ]
    for arg in unanswered_opponent_args[:3]:
        severity = "high" if arg.status == ArgumentFlowStatus.EXTENDED else "medium"
        title = f"No response to opponent's {arg.label}"
        gap = {
            "workspace_id": workspace_id,
            "user_id": user_id,
            "round_simulation_id": round_id,
            "category": "missing_response",
            "severity": severity,
            "title": title,
            "description": f"Opponent's argument '{arg.claim}' was not adequately answered during the simulation.",
            "suggested_action": f"Find frontline responses to '{arg.label}' and practice rebuttal coverage.",
            "auto_resolved": False,
            "status": "open",
            "occurrence_count": 1,
            "first_seen_at": now,
            "last_seen_at": now,
        }
        result = _upsert_gap(supabase, gap, round_id)
        if result:
            gaps_recorded.append(result)

    # Gap: student's own arguments not extended through summary
    student_args = [a for a in all_args if a.side == student_side]
    student_unextended = [
        a for a in student_args
        if a.status in (ArgumentFlowStatus.LIVE, ArgumentFlowStatus.INTRODUCED)
        and a.is_offense
    ]
    if student_unextended:
        title = "Offense not extended through summary"
        gap = {
            "workspace_id": workspace_id,
            "user_id": user_id,
            "round_simulation_id": round_id,
            "category": "extension_gap",
            "severity": "high",
            "title": title,
            "description": (
                f"Arguments {', '.join(a.label for a in student_unextended[:3])} "
                "were not extended through summary — they cannot count as voters."
            ),
            "suggested_action": "Practice summary extension: extend → warrant reminder → impact → weighing.",
            "auto_resolved": False,
            "status": "open",
            "occurrence_count": 1,
            "first_seen_at": now,
            "last_seen_at": now,
        }
        result = _upsert_gap(supabase, gap, round_id)
        if result:
            gaps_recorded.append(result)

    # Gap: no weighing analysis found
    student_did_weighing = any(a.weighing for a in student_args)
    if not student_did_weighing and student_args:
        title = "Missing comparative weighing"
        gap = {
            "workspace_id": workspace_id,
            "user_id": user_id,
            "round_simulation_id": round_id,
            "category": "weighing_gap",
            "severity": "medium",
            "title": title,
            "description": "No comparative weighing was detected in the student's speeches.",
            "suggested_action": "Practice weighing using magnitude, probability, timeframe, and reversibility.",
            "auto_resolved": False,
            "status": "open",
            "occurrence_count": 1,
            "first_seen_at": now,
            "last_seen_at": now,
        }
        result = _upsert_gap(supabase, gap, round_id)
        if result:
            gaps_recorded.append(result)

    # Gap: evidence cards that were flagged
    flagged_uses = [u for u in evidence_uses if u.flagged and u.speaker_side == student_side]
    if flagged_uses:
        title = "Evidence quality violations in simulation"
        gap = {
            "workspace_id": workspace_id,
            "user_id": user_id,
            "round_simulation_id": round_id,
            "category": "evidence_quality",
            "severity": "medium",
            "title": title,
            "description": "Evidence was used without proper citation, warrant explanation, or matching support verdict.",
            "suggested_action": "Review evidence explanation drills and practice reading cards with citation.",
            "auto_resolved": False,
            "status": "open",
            "occurrence_count": 1,
            "first_seen_at": now,
            "last_seen_at": now,
        }
        result = _upsert_gap(supabase, gap, round_id)
        if result:
            gaps_recorded.append(result)

    # Gap: rebuttal coverage weak (many opponent args surviving)
    if len(unanswered_opponent_args) >= 3:
        title = "Weak rebuttal coverage"
        gap = {
            "workspace_id": workspace_id,
            "user_id": user_id,
            "round_simulation_id": round_id,
            "category": "rebuttal_coverage",
            "severity": "high",
            "title": title,
            "description": (
                f"{len(unanswered_opponent_args)} opponent arguments survived without a response. "
                "Strong rebuttal coverage is essential in PF."
            ),
            "suggested_action": "Practice the Rebuttal Coverage Sprint drill — address each argument in flow order.",
            "auto_resolved": False,
            "status": "open",
            "occurrence_count": 1,
            "first_seen_at": now,
            "last_seen_at": now,
        }
        result = _upsert_gap(supabase, gap, round_id)
        if result:
            gaps_recorded.append(result)

    return gaps_recorded


def record_frontline_performance(
    round_id: str,
    user_id: str,
    workspace_id: Optional[str],
    frontline_id: str,
    was_effective: bool,
    response_context: str,
) -> None:
    """Record whether a frontline was effective in the round."""
    if not workspace_id:
        return
    supabase = get_supabase()
    try:
        supabase.table("frontline_performance_log").insert({
            "round_simulation_id": round_id,
            "user_id": user_id,
            "workspace_id": workspace_id,
            "frontline_id": frontline_id,
            "was_effective": was_effective,
            "response_context": response_context[:500],
        }).execute()
    except Exception as exc:
        logger.warning("Failed to record frontline performance: %s", exc)
