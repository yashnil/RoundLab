"""Pass 17 — Round replay and turning point analysis.

Reconstructs a phase-by-phase replay timeline from append-only round records.
Identifies turning points: drops, concessions, failed extensions, etc.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.supabase_client import get_supabase


# ── Phase ordering ────────────────────────────────────────────────────────────

_PHASE_META: Dict[str, Dict[str, str]] = {
    "pro_constructive":       {"label": "Pro Constructive (AC)",      "speaker": "Pro"},
    "con_constructive":       {"label": "Con Constructive (NC)",      "speaker": "Con"},
    "crossfire_1":            {"label": "First Crossfire",            "speaker": "Both"},
    "pro_rebuttal":           {"label": "Pro Rebuttal",               "speaker": "Pro"},
    "con_rebuttal":           {"label": "Con Rebuttal",               "speaker": "Con"},
    "crossfire_2":            {"label": "Second Crossfire",           "speaker": "Both"},
    "pro_summary":            {"label": "Pro Summary",                "speaker": "Pro"},
    "con_summary":            {"label": "Con Summary",                "speaker": "Con"},
    "grand_crossfire":        {"label": "Grand Crossfire",            "speaker": "Both"},
    "pro_final_focus":        {"label": "Pro Final Focus",            "speaker": "Pro"},
    "con_final_focus":        {"label": "Con Final Focus",            "speaker": "Con"},
    "decision":               {"label": "Judge Decision",             "speaker": "Judge"},
}

_PHASE_ORDER = [
    "pro_constructive",
    "con_constructive",
    "crossfire_1",
    "pro_rebuttal",
    "con_rebuttal",
    "crossfire_2",
    "pro_summary",
    "con_summary",
    "grand_crossfire",
    "pro_final_focus",
    "con_final_focus",
    "decision",
]

_SUMMARY_PHASES = {"pro_summary", "con_summary"}
_FINAL_FOCUS_PHASES = {"pro_final_focus", "con_final_focus"}
_CONSTRUCTIVE_PHASES = {"pro_constructive", "con_constructive"}
_CROSSFIRE_PHASES = {"crossfire_1", "crossfire_2", "grand_crossfire"}

_MAX_TURNING_POINTS = 8


# ── Data classes ──────────────────────────────────────────────────────────────


@dataclass
class ReplayPhase:
    phase: str
    phase_label: str
    speaker_label: str
    transcript_preview: str = ""   # first 200 chars of transcript
    flow_events: List[dict] = field(default_factory=list)
    arguments_changed: List[dict] = field(default_factory=list)
    evidence_used: List[str] = field(default_factory=list)
    legality_violations: List[str] = field(default_factory=list)
    turning_points: List[dict] = field(default_factory=list)


@dataclass
class TurningPoint:
    phase: str
    type: str  # "major_drop", "decisive_concession", "failed_extension",
               # "strongest_weighing", "evidence_challenge_unanswered",
               # "final_focus_mismatch", "key_turn"
    description: str
    argument_label: Optional[str] = None
    severity: str = "notable"  # "critical", "significant", "notable"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _severity_rank(severity: str) -> int:
    return {"critical": 0, "significant": 1, "notable": 2}.get(severity, 3)


def _args_by_phase(all_args: List[dict]) -> Dict[str, List[dict]]:
    """Group arguments by the phase they were introduced (introduced_in_phase)."""
    result: Dict[str, List[dict]] = {}
    for arg in all_args:
        phase = arg.get("introduced_in_phase") or arg.get("phase", "")
        result.setdefault(phase, []).append(arg)
    return result


def _evidence_by_phase(evidence_uses: List[dict]) -> Dict[str, List[str]]:
    """Map phase → list of card_ids used in that phase."""
    result: Dict[str, List[str]] = {}
    for eu in evidence_uses:
        phase = eu.get("phase", "")
        card_id = eu.get("card_id", "")
        if phase and card_id:
            result.setdefault(phase, []).append(card_id)
    return result


def _violations_by_phase(speeches: List[dict]) -> Dict[str, List[str]]:
    """Extract legality violations per phase from speech records."""
    result: Dict[str, List[str]] = {}
    for sp in speeches:
        phase = sp.get("phase", "")
        violations = sp.get("legality_violations") or []
        if phase and violations:
            result[phase] = [str(v) for v in violations]
    return result


def _transcript_preview(speeches: List[dict], phase: str) -> str:
    """Return first 200 chars of transcript for a phase (raw text, no PII trimming needed)."""
    for sp in speeches:
        if sp.get("phase") == phase:
            transcript = sp.get("transcript") or ""
            return transcript[:200]
    return ""


def _crossfire_by_phase(crossfire_exchanges: List[dict]) -> Dict[str, List[dict]]:
    result: Dict[str, List[dict]] = {}
    for cx in crossfire_exchanges:
        phase = cx.get("phase", "")
        result.setdefault(phase, []).append(cx)
    return result


# ── Core builder ──────────────────────────────────────────────────────────────


def build_replay_timeline(
    round_id: str,
    all_args: List[dict],
    speeches: List[dict],
    crossfire_exchanges: List[dict],
    evidence_uses: List[dict],
    decision: Optional[dict],
) -> List[ReplayPhase]:
    """Build a replay timeline from all round data."""
    args_by_phase = _args_by_phase(all_args)
    ev_by_phase = _evidence_by_phase(evidence_uses)
    viol_by_phase = _violations_by_phase(speeches)
    cx_by_phase = _crossfire_by_phase(crossfire_exchanges)

    # Build per-phase argument status history to detect changes
    # We track the "current" known status per argument label across phases.
    arg_status_history: Dict[str, str] = {}

    # Pre-compute turning points so they can be attached to phases
    all_turning_points = identify_turning_points(
        all_args=all_args,
        speeches=speeches,
        crossfire_exchanges=crossfire_exchanges,
        evidence_uses=evidence_uses,
        decision=decision,
    )
    tp_by_phase: Dict[str, List[dict]] = {}
    for tp in all_turning_points:
        tp_dict = {
            "type": tp.type,
            "description": tp.description,
            "argument_label": tp.argument_label,
            "severity": tp.severity,
        }
        tp_by_phase.setdefault(tp.phase, []).append(tp_dict)

    phases: List[ReplayPhase] = []
    active_phases = _PHASE_ORDER if not decision else _PHASE_ORDER
    if not decision:
        active_phases = [p for p in _PHASE_ORDER if p != "decision"]

    for phase in active_phases:
        meta = _PHASE_META.get(phase, {"label": phase, "speaker": "Unknown"})

        # Detect argument status changes introduced or updated this phase
        arguments_changed: List[dict] = []
        phase_args = args_by_phase.get(phase, [])
        for arg in phase_args:
            label = arg.get("label", "")
            new_status = arg.get("status", "")
            old_status = arg_status_history.get(label)
            if old_status is None:
                # Newly introduced
                arguments_changed.append({"label": label, "old_status": None, "new_status": new_status})
            elif old_status != new_status:
                arguments_changed.append({"label": label, "old_status": old_status, "new_status": new_status})
            if label:
                arg_status_history[label] = new_status

        # Build flow events for this phase
        flow_events: List[dict] = []
        for arg in phase_args:
            label = arg.get("label", "")
            status = arg.get("status", "")
            if label:
                flow_events.append({"event": "argument_update", "label": label, "status": status})
        for cx in cx_by_phase.get(phase, []):
            q = cx.get("question", "")
            concession = cx.get("is_concession", False)
            if q:
                evt: dict = {"event": "crossfire_exchange", "question_preview": q[:100]}
                if concession:
                    evt["concession"] = True
                flow_events.append(evt)

        replay_phase = ReplayPhase(
            phase=phase,
            phase_label=meta["label"],
            speaker_label=meta["speaker"],
            transcript_preview=_transcript_preview(speeches, phase),
            flow_events=flow_events,
            arguments_changed=arguments_changed,
            evidence_used=ev_by_phase.get(phase, []),
            legality_violations=viol_by_phase.get(phase, []),
            turning_points=tp_by_phase.get(phase, []),
        )
        phases.append(replay_phase)

    return phases


# ── Turning point detection ───────────────────────────────────────────────────


def identify_turning_points(
    all_args: List[dict],
    speeches: List[dict],
    crossfire_exchanges: List[dict],
    evidence_uses: List[dict],
    decision: Optional[dict],
) -> List[TurningPoint]:
    """
    Identify turning points deterministically.

    Rules:
    - major_drop: an argument with is_offense=True goes to DROPPED status → severity=critical
    - decisive_concession: a crossfire concession with strategic_significance="high" → severity=critical
    - failed_extension: an argument not in summary that was in constructive → severity=significant
    - strongest_weighing: a weighing comparison that references both magnitude and timeframe → severity=notable
    - evidence_challenge_unanswered: challenged evidence (flagged use) left unaddressed → severity=significant
    - final_focus_mismatch: final focus voter not in summary → severity=critical
    - key_turn: an argument status changed to TURNED → severity=critical

    Does NOT list every minor warning. Max 8 turning points.
    Priority: critical > significant > notable
    """
    candidates: List[TurningPoint] = []

    # ── Build argument lookup by label ────────────────────────────────────────
    arg_by_label: Dict[str, dict] = {}
    for arg in all_args:
        label = arg.get("label", "")
        if label:
            arg_by_label[label] = arg

    # Determine which phase each argument was first introduced in
    constructive_labels: set[str] = set()
    for arg in all_args:
        phase = arg.get("introduced_in_phase") or arg.get("phase", "")
        if phase in _CONSTRUCTIVE_PHASES:
            constructive_labels.add(arg.get("label", ""))

    summary_labels: set[str] = set()
    for arg in all_args:
        phase = arg.get("introduced_in_phase") or arg.get("phase", "")
        if phase in _SUMMARY_PHASES:
            summary_labels.add(arg.get("label", ""))
        # Also check if the argument appears in summary speeches by speech references
    # Additionally scan speeches for labels mentioned in summary
    for sp in speeches:
        if sp.get("phase") in _SUMMARY_PHASES:
            for label in constructive_labels:
                if label and label.lower() in (sp.get("transcript") or "").lower():
                    summary_labels.add(label)

    final_focus_labels: set[str] = set()
    for sp in speeches:
        if sp.get("phase") in _FINAL_FOCUS_PHASES:
            for label in constructive_labels:
                if label and label.lower() in (sp.get("transcript") or "").lower():
                    final_focus_labels.add(label)
    # Also from arguments directly
    for arg in all_args:
        phase = arg.get("introduced_in_phase") or arg.get("phase", "")
        if phase in _FINAL_FOCUS_PHASES:
            final_focus_labels.add(arg.get("label", ""))

    # ── Rule 1: major_drop ────────────────────────────────────────────────────
    for arg in all_args:
        if arg.get("is_offense") and arg.get("status", "").upper() == "DROPPED":
            label = arg.get("label", "")
            phase = arg.get("dropped_in_phase") or arg.get("phase") or "unknown"
            candidates.append(
                TurningPoint(
                    phase=phase,
                    type="major_drop",
                    description=(
                        f"Offensive argument '{label}' was dropped — "
                        "no response was offered."
                    ),
                    argument_label=label,
                    severity="critical",
                )
            )

    # ── Rule 2: decisive_concession ───────────────────────────────────────────
    for cx in crossfire_exchanges:
        if cx.get("is_concession") and cx.get("strategic_significance") == "high":
            phase = cx.get("phase", "unknown")
            question = (cx.get("question") or "")[:80]
            candidates.append(
                TurningPoint(
                    phase=phase,
                    type="decisive_concession",
                    description=(
                        f"High-significance concession made in crossfire: \"{question}...\""
                    ),
                    argument_label=None,
                    severity="critical",
                )
            )

    # ── Rule 3: failed_extension ──────────────────────────────────────────────
    for label in constructive_labels:
        if label and label not in summary_labels:
            arg = arg_by_label.get(label, {})
            status = arg.get("status", "")
            # Only flag if the argument wasn't already cleanly resolved
            if status.upper() not in {"DROPPED", "TURNED"}:
                # Find the phase it was introduced
                intro_phase = arg.get("introduced_in_phase") or arg.get("phase", "unknown")
                candidates.append(
                    TurningPoint(
                        phase=intro_phase,
                        type="failed_extension",
                        description=(
                            f"Argument '{label}' from constructive was not extended "
                            "into the summary speech."
                        ),
                        argument_label=label,
                        severity="significant",
                    )
                )

    # ── Rule 4: strongest_weighing ────────────────────────────────────────────
    for sp in speeches:
        transcript = (sp.get("transcript") or "").lower()
        phase = sp.get("phase", "unknown")
        has_magnitude = any(kw in transcript for kw in [
            "magnitude", "scale", "scope", "millions", "thousands", "large-scale",
            "outweighs", "more important",
        ])
        has_timeframe = any(kw in transcript for kw in [
            "timeframe", "time frame", "short-term", "long-term", "immediate",
            "decades", "years", "quickly", "urgently", "now",
        ])
        if has_magnitude and has_timeframe and phase in _SUMMARY_PHASES | _FINAL_FOCUS_PHASES:
            candidates.append(
                TurningPoint(
                    phase=phase,
                    type="strongest_weighing",
                    description=(
                        "Weighing comparison invoked both magnitude and timeframe — "
                        "potential impact on the judge's decision calculus."
                    ),
                    argument_label=None,
                    severity="notable",
                )
            )
            # Only note this once per round
            break

    # ── Rule 5: evidence_challenge_unanswered ─────────────────────────────────
    flagged_card_ids: set[str] = set()
    for eu in evidence_uses:
        if eu.get("issue_flag"):
            flagged_card_ids.add(eu.get("card_id", ""))

    # Check if flagged cards were "addressed" by appearing in a subsequent speech
    for eu in evidence_uses:
        card_id = eu.get("card_id", "")
        if card_id not in flagged_card_ids:
            continue
        phase = eu.get("phase", "unknown")
        # Determine if any later speech addresses the challenge (naive: mentions card_id)
        addressed = False
        for sp in speeches:
            sp_phase = sp.get("phase", "")
            if sp_phase in _SUMMARY_PHASES | _FINAL_FOCUS_PHASES:
                if card_id in (sp.get("transcript") or ""):
                    addressed = True
                    break
        if not addressed:
            candidates.append(
                TurningPoint(
                    phase=phase,
                    type="evidence_challenge_unanswered",
                    description=(
                        f"Evidence card {card_id[:12]}... was challenged but "
                        "the challenge went unanswered in summary/final focus."
                    ),
                    argument_label=None,
                    severity="significant",
                )
            )
            # Cap at one per round to avoid noise
            break

    # ── Rule 6: final_focus_mismatch ─────────────────────────────────────────
    if final_focus_labels and summary_labels:
        mismatch_labels = final_focus_labels - summary_labels
        for label in mismatch_labels:
            if label:
                candidates.append(
                    TurningPoint(
                        phase="pro_final_focus",
                        type="final_focus_mismatch",
                        description=(
                            f"Final focus voter '{label}' was not extended in the summary — "
                            "judge may be skeptical of this voter."
                        ),
                        argument_label=label,
                        severity="critical",
                    )
                )
                break  # One is enough to flag

    # ── Rule 7: key_turn ──────────────────────────────────────────────────────
    for arg in all_args:
        if arg.get("status", "").upper() == "TURNED":
            label = arg.get("label", "")
            phase = arg.get("turned_in_phase") or arg.get("phase") or "unknown"
            candidates.append(
                TurningPoint(
                    phase=phase,
                    type="key_turn",
                    description=(
                        f"Argument '{label}' was turned — the offense now runs against "
                        "the team that originally read it."
                    ),
                    argument_label=label,
                    severity="critical",
                )
            )

    # ── Deduplicate, sort, cap ────────────────────────────────────────────────
    # Dedup by (type, argument_label) to avoid repeating the same event
    seen: set[tuple] = set()
    deduped: List[TurningPoint] = []
    for tp in candidates:
        key = (tp.type, tp.argument_label or "")
        if key not in seen:
            seen.add(key)
            deduped.append(tp)

    deduped.sort(key=lambda tp: _severity_rank(tp.severity))
    return deduped[:_MAX_TURNING_POINTS]


# ── DB-backed entry point ─────────────────────────────────────────────────────


def get_replay_timeline(round_id: str) -> List[dict]:
    """DB-backed version: fetch all round data and build timeline."""
    supabase = get_supabase()

    # Fetch arguments
    args_result = (
        supabase.table("round_arguments")
        .select("*")
        .eq("round_id", round_id)
        .order("created_at", desc=False)
        .execute()
    )
    all_args: List[dict] = args_result.data or []

    # Fetch speeches
    speeches_result = (
        supabase.table("round_speeches")
        .select("*")
        .eq("round_id", round_id)
        .order("created_at", desc=False)
        .execute()
    )
    speeches: List[dict] = speeches_result.data or []

    # Fetch crossfire exchanges
    cx_result = (
        supabase.table("round_crossfire_exchanges")
        .select("*")
        .eq("round_id", round_id)
        .order("created_at", desc=False)
        .execute()
    )
    crossfire_exchanges: List[dict] = cx_result.data or []

    # Fetch evidence uses
    ev_result = (
        supabase.table("round_evidence_uses")
        .select("*")
        .eq("round_id", round_id)
        .order("created_at", desc=False)
        .execute()
    )
    evidence_uses: List[dict] = ev_result.data or []

    # Fetch decision
    dec_result = (
        supabase.table("round_decisions")
        .select("*")
        .eq("round_id", round_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    decision: Optional[dict] = None
    dec_rows = dec_result.data or []
    if dec_rows:
        decision = dec_rows[0]

    phases = build_replay_timeline(
        round_id=round_id,
        all_args=all_args,
        speeches=speeches,
        crossfire_exchanges=crossfire_exchanges,
        evidence_uses=evidence_uses,
        decision=decision,
    )

    return [
        {
            "phase": p.phase,
            "phase_label": p.phase_label,
            "speaker_label": p.speaker_label,
            "transcript_preview": p.transcript_preview,
            "flow_events": p.flow_events,
            "arguments_changed": p.arguments_changed,
            "evidence_used": p.evidence_used,
            "legality_violations": p.legality_violations,
            "turning_points": p.turning_points,
        }
        for p in phases
    ]
