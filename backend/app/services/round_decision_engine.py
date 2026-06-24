"""Pass 16 — Round decision engine.

Explainable, stage-by-stage decision process. Winner is derived from the
completed flow and judge profile — not a free-form LLM narrative alone.

Decision trace stored separately from generated RFD.
No private chain-of-thought exposed.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import openai
from pydantic import BaseModel

from app.config import settings
from app.models.round_simulation import (
    ArgumentFlowStatus,
    DecisionTraceEntry,
    RoundArgument,
    RoundDecision,
    RoundDecisionTrace,
    RoundEvidenceUse,
    RoundPhaseType,
    RoundSide,
    SpeechLegalityViolation,
)
from app.services.judge_profiles import get_builtin_profile

logger = logging.getLogger(__name__)

# Statuses that mean the argument is effectively dead
_LOSING_STATUSES = {
    ArgumentFlowStatus.DROPPED,
    ArgumentFlowStatus.CONCEDED,
    ArgumentFlowStatus.TURNED,
    ArgumentFlowStatus.OUTWEIGHED,
}

# Statuses that represent live offense
_SURVIVING_STATUSES = {
    ArgumentFlowStatus.LIVE,
    ArgumentFlowStatus.EXTENDED,
    ArgumentFlowStatus.INTRODUCED,
    ArgumentFlowStatus.UNRESOLVED,
}

# Required: extended in FINAL_FOCUS or SECOND_SUMMARY to be a voter
_VOTER_PHASES = {
    RoundPhaseType.FIRST_FINAL_FOCUS,
    RoundPhaseType.SECOND_FINAL_FOCUS,
    RoundPhaseType.FIRST_SUMMARY,
    RoundPhaseType.SECOND_SUMMARY,
}


def _get_surviving_offense(
    args: List[RoundArgument],
    side: RoundSide,
    format_phases: Optional[List[str]] = None,
) -> List[RoundArgument]:
    """Return arguments that survived as offense for the given side."""
    return [
        a for a in args
        if a.side == side
        and a.status in _SURVIVING_STATUSES
        and a.is_offense
        and not a.is_framework
    ]


def _get_dropped_args(args: List[RoundArgument], side: RoundSide) -> List[RoundArgument]:
    return [a for a in args if a.side == side and a.status == ArgumentFlowStatus.DROPPED]


def _get_conceded_args(args: List[RoundArgument], side: RoundSide) -> List[RoundArgument]:
    return [a for a in args if a.side == side and a.status == ArgumentFlowStatus.CONCEDED]


def _apply_judge_profile_weights(
    pro_score: float,
    con_score: float,
    judge_type: str,
    evidence_uses: List[RoundEvidenceUse],
) -> Tuple[float, float, List[str]]:
    """
    Adjust scores based on judge profile preferences.
    Returns (pro_score, con_score, effects_list).
    """
    effects: List[str] = []
    try:
        profile = get_builtin_profile(judge_type)
        prefs = profile.preferences
    except Exception:
        return pro_score, con_score, effects

    # Evidence quality matters more for flow/technical judges
    if prefs.evidence_detail_preference >= 4:
        flagged_pro = sum(1 for u in evidence_uses if u.speaker_side == RoundSide.PRO and u.flagged)
        flagged_con = sum(1 for u in evidence_uses if u.speaker_side == RoundSide.CON and u.flagged)
        if flagged_pro > flagged_con:
            pro_score -= 0.5
            effects.append(f"Judge penalized Pro for {flagged_pro} evidence violation(s).")
        elif flagged_con > flagged_pro:
            con_score -= 0.5
            effects.append(f"Judge penalized Con for {flagged_con} evidence violation(s).")

    # Weighing emphasis for flow/technical judges
    if prefs.weighing_expectation >= 4:
        effects.append("Judge prioritizes comparative weighing as a deciding factor.")

    # Jargon tolerance adjustments for lay judges
    if prefs.jargon_tolerance <= 2:
        effects.append("Lay judge may discount technical PF jargon in favor of clarity.")

    return pro_score, con_score, effects


def _estimate_speaker_points(
    args: List[RoundArgument],
    side: RoundSide,
    evidence_uses: List[RoundEvidenceUse],
    legality_violations: List[Dict[str, Any]],
) -> float:
    """Estimate speaker points (25-30 scale)."""
    base = 27.0
    surviving = _get_surviving_offense(args, side)
    base += min(len(surviving) * 0.3, 1.0)
    clean_evidence = [u for u in evidence_uses if u.speaker_side == side and not u.flagged]
    base += min(len(clean_evidence) * 0.1, 0.5)
    errors = [v for v in legality_violations if v.get("severity") == "error"]
    base -= min(len(errors) * 0.5, 2.0)
    return round(max(25.0, min(30.0, base)), 1)


def run_decision_engine(
    round_id: str,
    judge_type: str,
    all_args: List[RoundArgument],
    evidence_uses: List[RoundEvidenceUse],
    legality_violations: List[Dict[str, Any]],
    speeches_summary: str = "",
) -> RoundDecision:
    """
    Deterministic decision engine.

    Steps:
    1. Identify surviving offense per side.
    2. Remove lost offense (dropped, conceded, turned, outweighed).
    3. Score surviving offense against evidence limits.
    4. Compare warrants and impacts.
    5. Apply weighing.
    6. Apply judge-profile adjustments.
    7. Determine winner.
    8. Generate RFD via LLM (structured, constrained to trace).
    """
    now = datetime.utcnow().isoformat()

    # Step 1 & 2: Identify surviving offense
    pro_offense = _get_surviving_offense(all_args, RoundSide.PRO)
    con_offense = _get_surviving_offense(all_args, RoundSide.CON)

    # Step 3: Score evidence limits
    def _evidence_penalty(side: RoundSide, args: List[RoundArgument]) -> float:
        penalty = 0.0
        for arg in args:
            if not arg.evidence_card_id:
                continue
            use = next(
                (u for u in evidence_uses if u.card_id == arg.evidence_card_id and u.speaker_side == side),
                None,
            )
            if use and use.flagged:
                penalty += 0.3
        return penalty

    pro_score = float(len(pro_offense)) - _evidence_penalty(RoundSide.PRO, pro_offense)
    con_score = float(len(con_offense)) - _evidence_penalty(RoundSide.CON, con_offense)

    # Step 4 & 5: Weighing (look for weighing in argument data)
    pro_weighing = any(a.weighing for a in pro_offense)
    con_weighing = any(a.weighing for a in con_offense)
    if pro_weighing and not con_weighing:
        pro_score += 0.5
    elif con_weighing and not pro_weighing:
        con_score += 0.5

    # Step 6: Judge profile
    pro_score, con_score, judge_effects = _apply_judge_profile_weights(
        pro_score, con_score, judge_type, evidence_uses
    )

    # Step 7: Winner
    if pro_score > con_score:
        winner = RoundSide.PRO
        confidence = "decisive" if pro_score - con_score > 1.0 else "contested"
    elif con_score > pro_score:
        winner = RoundSide.CON
        confidence = "decisive" if con_score - pro_score > 1.0 else "contested"
    else:
        # Tiebreak: compare dropped arguments; then weighing; then judge-type default
        pro_drops = _get_dropped_args(all_args, RoundSide.PRO)
        con_drops = _get_dropped_args(all_args, RoundSide.CON)
        if len(con_drops) > len(pro_drops):
            winner = RoundSide.PRO
        elif len(pro_drops) > len(con_drops):
            winner = RoundSide.CON
        elif con_weighing and not pro_weighing:
            # CON did comparative weighing; advantage CON
            winner = RoundSide.CON
        elif pro_weighing and not con_weighing:
            winner = RoundSide.PRO
        else:
            # Final tiebreak: flow/policy judges default to the status quo (CON),
            # lay/truth judges default to PRO (burden of proof on CON to disprove)
            winner = RoundSide.CON if judge_type in ("flow", "policy") else RoundSide.PRO
        confidence = "close"

    # Build trace (no private reasoning stored)
    trace_entries: List[DecisionTraceEntry] = []
    for arg in all_args:
        surviving = arg.status in _SURVIVING_STATUSES
        reason: Optional[str] = None
        if arg.status == ArgumentFlowStatus.DROPPED:
            reason = "dropped (not answered)"
        elif arg.status == ArgumentFlowStatus.CONCEDED:
            reason = "conceded"
        elif arg.status == ArgumentFlowStatus.TURNED:
            reason = "turned by opponent"
        elif arg.status == ArgumentFlowStatus.OUTWEIGHED:
            reason = "outweighed"
        trace_entries.append(DecisionTraceEntry(
            argument_id=arg.id,
            argument_label=arg.label,
            side=arg.side,
            included=surviving and arg.is_offense,
            reason=reason,
        ))

    surviving_voter_labels = [
        f"{e.argument_label} ({e.side.value})"
        for e in trace_entries
        if e.included
    ]

    dropped = [
        f"{a.label} ({a.side.value})"
        for a in all_args
        if a.status == ArgumentFlowStatus.DROPPED
    ]
    conceded = [
        f"{a.label} ({a.side.value})"
        for a in all_args
        if a.status == ArgumentFlowStatus.CONCEDED
    ]

    evidence_issues = [
        f"{u.phase.value}: {', '.join(u.violations)}"
        for u in evidence_uses
        if u.flagged
    ]

    legality_issue_texts = [
        v.get("description", "")
        for v in legality_violations
        if v.get("severity") == "error"
    ]

    trace = RoundDecisionTrace(
        arguments_considered=trace_entries,
        surviving_voters=surviving_voter_labels,
        weighing_comparison=_build_weighing_comparison(pro_offense, con_offense),
        judge_profile_effects=judge_effects,
        final_winner=winner,
        confidence=confidence,
    )

    # Step 8: Generate natural RFD
    rfd = _generate_rfd(
        winner=winner,
        judge_type=judge_type,
        surviving_voters=surviving_voter_labels,
        dropped=dropped,
        pro_score=pro_score,
        con_score=con_score,
        judge_effects=judge_effects,
        speeches_summary=speeches_summary,
    )

    voting_issues = surviving_voter_labels[:3] if surviving_voter_labels else ["No clear voter identified."]

    pro_pts = _estimate_speaker_points(all_args, RoundSide.PRO, evidence_uses, legality_violations)
    con_pts = _estimate_speaker_points(all_args, RoundSide.CON, evidence_uses, legality_violations)

    adaptation_successes, adaptation_failures = _compute_adaptation_feedback(
        judge_type=judge_type,
        pro_offense=pro_offense,
        con_offense=con_offense,
        evidence_uses=evidence_uses,
        judge_effects=judge_effects,
    )

    return RoundDecision(
        id=str(uuid.uuid4()),
        round_id=round_id,
        judge_type=judge_type,
        engine_version="v2",
        winner=winner,
        reason_for_decision=rfd,
        voting_issues=voting_issues,
        speaker_points={"pro": pro_pts, "con": con_pts},
        decisive_concessions=conceded,
        dropped_arguments=dropped,
        evidence_issues=evidence_issues,
        weighing_comparison=trace.weighing_comparison,
        legality_issues=legality_issue_texts,
        adaptation_successes=adaptation_successes,
        adaptation_failures=adaptation_failures,
        decision_trace=trace,
        created_at=now,
    )


def _build_weighing_comparison(
    pro_offense: List[RoundArgument],
    con_offense: List[RoundArgument],
) -> str:
    """Build a meaningful weighing comparison string from surviving offense."""
    pro_labels = [a.label for a in pro_offense]
    con_labels = [a.label for a in con_offense]

    if not pro_labels and not con_labels:
        return "Neither side has surviving offense — decision goes to the better defensive round."

    if not pro_labels:
        voters = ", ".join(con_labels[:2])
        return f"Con wins on {voters}. Pro has no surviving offense to weigh against."

    if not con_labels:
        voters = ", ".join(pro_labels[:2])
        return f"Pro wins on {voters}. Con has no surviving offense to weigh against."

    pro_has_weighing = any(a.weighing for a in pro_offense)
    con_has_weighing = any(a.weighing for a in con_offense)

    comparison = (
        f"Pro is winning on {', '.join(pro_labels[:2])}; "
        f"Con is winning on {', '.join(con_labels[:2])}."
    )
    if pro_has_weighing and not con_has_weighing:
        comparison += " Pro did comparative weighing; Con did not — Pro's impacts are prioritized."
    elif con_has_weighing and not pro_has_weighing:
        comparison += " Con did comparative weighing; Pro did not — Con's impacts are prioritized."
    elif not pro_has_weighing and not con_has_weighing:
        comparison += " Neither side did explicit weighing — decision by argument count and dropped arguments."

    return comparison


def _compute_adaptation_feedback(
    judge_type: str,
    pro_offense: List[RoundArgument],
    con_offense: List[RoundArgument],
    evidence_uses: List[RoundEvidenceUse],
    judge_effects: List[str],
) -> Tuple[List[str], List[str]]:
    """
    Derive adaptation successes and failures from judge profile and round data.

    Successes = student behavior that aligns with this judge's known preferences.
    Failures = behavior that likely hurt them given this judge type.
    """
    successes: List[str] = []
    failures: List[str] = []

    all_args = pro_offense + con_offense
    any_weighing = any(a.weighing for a in all_args)
    flagged_evidence = [u for u in evidence_uses if u.flagged]
    clean_evidence = [u for u in evidence_uses if not u.flagged]

    if judge_type == "flow":
        if any_weighing:
            successes.append("Did comparative weighing — flow judges reward this.")
        else:
            failures.append("No comparative weighing — flow judges expect explicit impact comparison.")
        if flagged_evidence:
            failures.append("Evidence quality violations flagged — flow judges track these closely.")
        if len(all_args) >= 3:
            successes.append("Multiple arguments developed — flow judges reward depth.")

    elif judge_type == "lay":
        if any_weighing:
            successes.append("Provided explicit impact comparison — helps lay judges follow.")
        if len(all_args) > 4:
            failures.append("Too many arguments for a lay judge to track — fewer, clearer arguments preferred.")
        if len(clean_evidence) >= 2:
            successes.append("Referenced evidence clearly — lay judges respond to concrete examples.")
        if flagged_evidence:
            failures.append("Evidence issues may have confused the lay judge.")

    elif judge_type == "truth":
        if any_weighing:
            successes.append("Comparative weighing provided — truth judges weigh substance.")
        if flagged_evidence:
            failures.append("Questionable evidence flagged — truth judges may reject claims not supported by evidence.")
        if clean_evidence:
            successes.append("Evidence grounded arguments in real-world facts — truth judges value this.")

    elif judge_type == "progressive":
        if any_weighing:
            successes.append("Framework-level weighing present — progressive judges look for this.")
        if not any_weighing:
            failures.append("No structural weighing — progressive judges often decide on framework.")

    # Judge profile effects as adaptation notes
    for effect in judge_effects[:2]:
        if "boost" in effect.lower() or "prefer" in effect.lower():
            successes.append(effect)
        elif "penalty" in effect.lower() or "against" in effect.lower():
            failures.append(effect)

    return successes, failures


def _generate_rfd(
    winner: RoundSide,
    judge_type: str,
    surviving_voters: List[str],
    dropped: List[str],
    pro_score: float,
    con_score: float,
    judge_effects: List[str],
    speeches_summary: str,
) -> str:
    """Generate a natural RFD constrained to the deterministic trace."""
    if not settings.openai_api_key:
        return _deterministic_rfd(winner, surviving_voters, dropped, judge_effects)

    voters_text = ", ".join(surviving_voters[:3]) or "no surviving voters"
    dropped_text = ", ".join(dropped[:3]) or "none"
    effects_text = " ".join(judge_effects[:2]) or "No judge-specific adjustments."

    system = (
        f"You are a {judge_type} PF judge delivering a reason for decision (RFD). "
        "Your decision is already determined by the flow and evidence below. "
        "Generate a 100-150 word explanation grounded only in the facts provided. "
        "Do not invent new arguments, evidence, or reasoning not present in the trace. "
        "Do not expose your internal scoring calculations."
    )
    user = (
        f"Winner: {winner.value}\n"
        f"Surviving voters: {voters_text}\n"
        f"Dropped arguments: {dropped_text}\n"
        f"Judge adjustments: {effects_text}\n"
        f"Round summary: {speeches_summary[:400] or '(not provided)'}\n\n"
        "Write the RFD now (100-150 words):"
    )

    try:
        client = openai.OpenAI(api_key=settings.openai_api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=300,
            temperature=0.3,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as exc:
        logger.warning("RFD generation failed: %s", exc)
        return _deterministic_rfd(winner, surviving_voters, dropped, judge_effects)


def _deterministic_rfd(
    winner: RoundSide,
    surviving_voters: List[str],
    dropped: List[str],
    judge_effects: List[str],
) -> str:
    voters = ", ".join(surviving_voters[:2]) or "surviving offense"
    drops = ", ".join(dropped[:2]) or "none"
    return (
        f"I vote for the {winner.value} side. "
        f"The key voter(s) in this round are: {voters}. "
        f"The losing side dropped: {drops}. "
        + (" ".join(judge_effects[:1]) if judge_effects else "")
    ).strip()


def rejudge_round(
    round_id: str,
    new_judge_type: str,
    all_args: List[RoundArgument],
    evidence_uses: List[RoundEvidenceUse],
    legality_violations: List[Dict[str, Any]],
    speeches_summary: str = "",
) -> RoundDecision:
    """
    Re-evaluate a completed round under a different judge profile.
    Does not alter the historical flow — only changes the scoring lens.
    """
    decision = run_decision_engine(
        round_id=round_id,
        judge_type=new_judge_type,
        all_args=all_args,
        evidence_uses=evidence_uses,
        legality_violations=legality_violations,
        speeches_summary=speeches_summary,
    )
    decision.id = str(uuid.uuid4())  # New record for the rejudged decision
    return decision
