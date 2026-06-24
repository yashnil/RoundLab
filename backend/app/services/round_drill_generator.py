"""Pass 16 — Post-round drill generator.

Generates drills from actual round failures.
Links each drill to round ID, speech phase, argument, and card where relevant.
Reuses existing drill-attempt infrastructure.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models.round_simulation import (
    ArgumentFlowStatus,
    RoundArgument,
    RoundDecision,
    RoundDrill,
    RoundDrillSource,
    RoundEvidenceUse,
    RoundPhaseType,
    RoundSide,
    SpeechLegalityViolation,
)
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

_DRILL_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "dropped_response": {
        "skill_target": "drops",
        "title": "Dropped-Response Recovery Drill",
        "prompt": "Practice covering all opponent arguments in 90 seconds. Name each opponent argument and give a 2-sentence response.",
        "success_criteria": [
            "Every opponent argument is named and addressed.",
            "Responses are specific, not generic.",
            "No new arguments introduced.",
            "Delivered within time limit.",
        ],
        "time_limit_seconds": 90,
    },
    "rebuttal_coverage": {
        "skill_target": "clash",
        "title": "Rebuttal Coverage Sprint",
        "prompt": "Go through the flow line-by-line. Address each opponent argument in order with a clear response.",
        "success_criteria": [
            "Each argument is addressed in flow order.",
            "Direct clash on warrant, not just impact.",
            "At least one turn attempted.",
            "Completed within time.",
        ],
        "time_limit_seconds": 120,
    },
    "summary_extension": {
        "skill_target": "extensions",
        "title": "Summary Extension Drill",
        "prompt": "Practice extending your top argument through summary. Use: extend → warrant reminder → impact → weighing.",
        "success_criteria": [
            "Argument is clearly extended by name.",
            "Warrant is restated in 1-2 sentences.",
            "Impact is explained and compared.",
            "Weighing analysis is included.",
        ],
        "time_limit_seconds": 90,
    },
    "final_focus_consistency": {
        "skill_target": "extensions",
        "title": "Final Focus Consistency Drill",
        "prompt": "Practice final focus that mirrors your summary. Name your voter, explain why it was never answered, and give comparative weighing.",
        "success_criteria": [
            "Single clear voter named.",
            "Voter matches summary argument.",
            "Explain why opponent never answered it.",
            "Comparative weighing included.",
        ],
        "time_limit_seconds": 60,
    },
    "evidence_explanation": {
        "skill_target": "evidence",
        "title": "Evidence Explanation Sprint",
        "prompt": "After reading a card, immediately explain: what this means, why the warrant holds, and what the impact is.",
        "success_criteria": [
            "Card is cited (author, year).",
            "Warrant is explained in your own words.",
            "Impact is connected to the resolution.",
            "Delivered in under 45 seconds per card.",
        ],
        "time_limit_seconds": 90,
    },
    "evidence_indictment": {
        "skill_target": "evidence",
        "title": "Evidence Indictment Drill",
        "prompt": "Practice challenging opponent evidence. Identify the card's limitation, question the warrant logic, and turn the impact.",
        "success_criteria": [
            "Specific limitation named (stale, abstract, partial).",
            "Warrant gap exposed clearly.",
            "Turn or response offered.",
            "No fabricated counter-evidence.",
        ],
        "time_limit_seconds": 90,
    },
    "weighing": {
        "skill_target": "weighing",
        "title": "Impact Weighing Drill",
        "prompt": "Practice comparative weighing using magnitude, probability, timeframe, and reversibility. Compare your top impact to the opponent's top impact.",
        "success_criteria": [
            "At least two weighing dimensions used.",
            "Comparison is side-by-side, not one-sided.",
            "Clear conclusion about which impact is decisive.",
            "Delivered in under 45 seconds.",
        ],
        "time_limit_seconds": 90,
    },
    "crossfire_concession": {
        "skill_target": "clash",
        "title": "Crossfire Pressure Drill",
        "prompt": "Practice answering pointed crossfire questions without conceding unnecessary ground. Answer directly, then pivot back to your argument.",
        "success_criteria": [
            "Direct answer given without major concession.",
            "Pivot back to own argument attempted.",
            "No evasive non-answers.",
            "Contradiction avoided.",
        ],
        "time_limit_seconds": 60,
    },
    "judge_switch": {
        "skill_target": "judge_adaptation",
        "title": "Judge-Switch Adaptation Drill",
        "prompt": "Adapt your top argument for a different judge type. If you argued for a flow judge, now argue the same point for a lay judge.",
        "success_criteria": [
            "Technical jargon reduced or explained.",
            "Real-world framing added.",
            "Clarity of argument improved.",
            "Core argument preserved.",
        ],
        "time_limit_seconds": 90,
    },
    "time_allocation": {
        "skill_target": "pacing_control",
        "title": "Time Allocation Drill",
        "prompt": "Practice allocating your speech time intentionally. Assign a target time to each argument before you speak, then execute within limits.",
        "success_criteria": [
            "Time budget stated before speaking.",
            "Each argument finished within its budget.",
            "Total speech within time limit.",
            "Priority arguments get more time.",
        ],
        "time_limit_seconds": 120,
    },
}


def _choose_drill_types(
    all_args: List[RoundArgument],
    evidence_uses: List[RoundEvidenceUse],
    decision: Optional[RoundDecision],
    student_side: RoundSide,
    legality_violations: List[Dict[str, Any]],
) -> List[str]:
    """Determine which drill types are most relevant from round failures."""
    chosen: List[str] = []

    # Dropped arguments → dropped response drill
    opponent_side = RoundSide.CON if student_side == RoundSide.PRO else RoundSide.PRO
    student_dropped = [
        a for a in all_args
        if a.side == student_side and a.status == ArgumentFlowStatus.DROPPED
    ]
    opponent_live = [
        a for a in all_args
        if a.side == opponent_side and a.status in (
            ArgumentFlowStatus.LIVE, ArgumentFlowStatus.EXTENDED
        )
    ]
    if opponent_live:
        chosen.append("dropped_response")

    # Evidence violations → evidence explanation
    student_evidence_issues = [
        u for u in evidence_uses
        if u.speaker_side == student_side and u.flagged
    ]
    if student_evidence_issues:
        chosen.append("evidence_explanation")

    # Weighing missing → weighing drill
    # Check actual round data: did the student do any weighing?
    student_args = [a for a in all_args if a.side == student_side]
    student_did_weighing = any(a.weighing for a in student_args)
    if not student_did_weighing:
        chosen.append("weighing")

    # Summary extension issues
    legality_types = {v.get("type") for v in legality_violations}
    if "dropped_offense" in legality_types:
        chosen.append("summary_extension")

    # Crossfire concession drill — only add if student actually made a notable concession
    # or if they have DROPPED arguments (potentially lost in crossfire)
    student_dropped = [
        a for a in all_args
        if a.side == student_side and a.status == ArgumentFlowStatus.DROPPED
    ]
    conceded_args = [
        a for a in all_args
        if a.side == student_side and a.status == ArgumentFlowStatus.CONCEDED
    ]
    if (student_dropped or conceded_args) and "crossfire_concession" not in chosen:
        chosen.append("crossfire_concession")

    # Fill remaining with general drills
    all_types = list(_DRILL_TEMPLATES.keys())
    for t in all_types:
        if t not in chosen:
            chosen.append(t)
        if len(chosen) >= 5:
            break

    return chosen[:5]


def generate_post_round_drills(
    round_id: str,
    student_side: RoundSide,
    all_args: List[RoundArgument],
    evidence_uses: List[RoundEvidenceUse],
    decision: Optional[RoundDecision],
    legality_violations: Optional[List[Dict[str, Any]]] = None,
    max_drills: int = 5,
) -> List[RoundDrill]:
    """Generate post-round drills linked to actual round failures."""
    now = datetime.utcnow().isoformat()
    violations = legality_violations or []
    drill_types = _choose_drill_types(all_args, evidence_uses, decision, student_side, violations)

    drills: List[RoundDrill] = []
    for drill_type in drill_types[:max_drills]:
        template = _DRILL_TEMPLATES[drill_type]
        # Find the most relevant argument/card for this drill
        arg_label: Optional[str] = None
        card_id: Optional[str] = None
        weakness = f"Identified from round: {drill_type.replace('_', ' ')}."

        if drill_type in ("dropped_response", "rebuttal_coverage"):
            opponent_side = RoundSide.CON if student_side == RoundSide.PRO else RoundSide.PRO
            live = [a for a in all_args if a.side == opponent_side and a.status in (
                ArgumentFlowStatus.LIVE, ArgumentFlowStatus.EXTENDED
            )]
            if live:
                arg_label = live[0].label
                weakness = f"Opponent's {arg_label} argument was not adequately addressed."

        elif drill_type in ("evidence_explanation", "evidence_indictment"):
            flagged = [u for u in evidence_uses if u.speaker_side == student_side and u.flagged]
            if flagged:
                card_id = flagged[0].card_id
                weakness = f"Evidence use violations: {', '.join(flagged[0].violations[:2])}."

        elif drill_type == "summary_extension":
            student_args = [a for a in all_args if a.side == student_side]
            dropped = [a for a in student_args if a.status == ArgumentFlowStatus.DROPPED]
            if dropped:
                arg_label = dropped[0].label
                weakness = f"{arg_label} was not extended through summary."

        # Map drill type to the most relevant speech phase
        _DRILL_PHASE_MAP: Dict[str, str] = {
            "dropped_response": RoundPhaseType.FIRST_REBUTTAL.value,
            "rebuttal_coverage": RoundPhaseType.FIRST_REBUTTAL.value,
            "summary_extension": RoundPhaseType.FIRST_SUMMARY.value,
            "final_focus_consistency": RoundPhaseType.FIRST_FINAL_FOCUS.value,
            "evidence_explanation": RoundPhaseType.FIRST_CONSTRUCTIVE.value,
            "evidence_indictment": RoundPhaseType.FIRST_REBUTTAL.value,
            "weighing": RoundPhaseType.FIRST_SUMMARY.value,
            "crossfire_concession": RoundPhaseType.GRAND_CROSSFIRE.value,
            "judge_switch": RoundPhaseType.FIRST_SUMMARY.value,
            "time_allocation": RoundPhaseType.FIRST_CONSTRUCTIVE.value,
        }
        drill_phase = _DRILL_PHASE_MAP.get(drill_type, RoundPhaseType.FIRST_SUMMARY.value)

        source = RoundDrillSource(
            round_id=round_id,
            speech_phase=drill_phase,
            argument_label=arg_label,
            card_id=card_id,
            weakness_description=weakness,
        )

        drill = RoundDrill(
            id=str(uuid.uuid4()),
            round_id=round_id,
            drill_id=str(uuid.uuid4()),
            source=source,
            skill_target=template["skill_target"],
            title=template["title"],
            prompt=template["prompt"],
            success_criteria=template["success_criteria"],
            time_limit_seconds=template["time_limit_seconds"],
            created_at=now,
        )
        drills.append(drill)

    return drills


def save_round_drills(drills: List[RoundDrill]) -> None:
    """Persist round drills to the database."""
    if not drills:
        return
    supabase = get_supabase()
    try:
        rows = [d.model_dump() for d in drills]
        supabase.table("round_drills").insert(rows).execute()
    except Exception as exc:
        logger.error("Failed to save round drills: %s", exc)


def load_round_drills(round_id: str) -> List[RoundDrill]:
    """Load drills for a round."""
    supabase = get_supabase()
    try:
        resp = supabase.table("round_drills").select("*").eq("round_id", round_id).execute()
        return [RoundDrill.model_validate(r) for r in (resp.data or [])]
    except Exception as exc:
        logger.warning("Failed to load round drills: %s", exc)
        return []
