"""Pass 17 — Coach round review service.

Coaches authorized to view a team round can:
- Add timestamped annotations to speeches/arguments
- Mark automated findings correct/incorrect
- Assign drills from round findings
- Export a concise round report

Coach feedback never alters historical speech, flow, or evidence records.
Ownership is enforced by the caller (via round ownership + team membership).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from app.services.supabase_client import get_supabase


# ── Data classes ──────────────────────────────────────────────────────────────


@dataclass
class CoachAnnotation:
    id: str
    round_id: str
    coach_id: str
    annotation_type: str  # "speech_note", "argument_note", "correction", "drill_assignment", "highlight"
    target_id: Optional[str]   # speech_id, argument_id, or drill_id
    target_type: Optional[str]  # "speech", "argument", "drill", "finding"
    content: str               # the note text
    is_correction: bool        # True if correcting an automated finding
    finding_id: Optional[str]  # if correcting a finding
    created_at: str


@dataclass
class AutomatedFindingRating:
    id: str
    round_id: str
    finding_id: str
    rater_id: str
    rating: str      # "correct", "partly_correct", "incorrect", "useful", "not_useful"
    note: Optional[str]
    created_at: str


# ── Constants ─────────────────────────────────────────────────────────────────

_VALID_ANNOTATION_TYPES = {
    "speech_note",
    "argument_note",
    "correction",
    "drill_assignment",
    "highlight",
}

_VALID_TARGET_TYPES = {
    "speech",
    "argument",
    "drill",
    "finding",
}

_VALID_RATINGS = {
    "correct",
    "partly_correct",
    "incorrect",
    "useful",
    "not_useful",
}

_ANNOTATION_TABLE = "round_coach_annotations"
_FINDING_RATING_TABLE = "round_finding_ratings"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_annotation(row: dict) -> CoachAnnotation:
    return CoachAnnotation(
        id=row["id"],
        round_id=row["round_id"],
        coach_id=row["coach_id"],
        annotation_type=row["annotation_type"],
        target_id=row.get("target_id"),
        target_type=row.get("target_type"),
        content=row["content"],
        is_correction=bool(row.get("is_correction", False)),
        finding_id=row.get("finding_id"),
        created_at=row["created_at"],
    )


def _row_to_finding_rating(row: dict) -> AutomatedFindingRating:
    return AutomatedFindingRating(
        id=row["id"],
        round_id=row["round_id"],
        finding_id=row["finding_id"],
        rater_id=row["rater_id"],
        rating=row["rating"],
        note=row.get("note"),
        created_at=row["created_at"],
    )


# ── Core annotation functions ─────────────────────────────────────────────────


def add_coach_annotation(
    round_id: str,
    coach_id: str,
    annotation_type: str,
    content: str,
    target_id: Optional[str] = None,
    target_type: Optional[str] = None,
    is_correction: bool = False,
    finding_id: Optional[str] = None,
) -> CoachAnnotation:
    """Create and persist a coach annotation. Never modifies historical records."""
    if annotation_type not in _VALID_ANNOTATION_TYPES:
        raise ValueError(
            f"Invalid annotation_type {annotation_type!r}. "
            f"Must be one of: {sorted(_VALID_ANNOTATION_TYPES)}"
        )
    if target_type is not None and target_type not in _VALID_TARGET_TYPES:
        raise ValueError(
            f"Invalid target_type {target_type!r}. "
            f"Must be one of: {sorted(_VALID_TARGET_TYPES)}"
        )
    if not content or not content.strip():
        raise ValueError("Annotation content must not be empty.")

    annotation_id = str(uuid.uuid4())
    created_at = _now_iso()

    row = {
        "id": annotation_id,
        "round_id": round_id,
        "coach_id": coach_id,
        "annotation_type": annotation_type,
        "target_id": target_id,
        "target_type": target_type,
        "content": content.strip(),
        "is_correction": is_correction,
        "finding_id": finding_id,
        "created_at": created_at,
    }

    supabase = get_supabase()
    supabase.table(_ANNOTATION_TABLE).insert(row).execute()

    return _row_to_annotation(row)


def list_coach_annotations(
    round_id: str,
    coach_id: Optional[str] = None,
) -> List[CoachAnnotation]:
    """List annotations for a round, optionally filtered by coach."""
    supabase = get_supabase()
    query = (
        supabase.table(_ANNOTATION_TABLE)
        .select("*")
        .eq("round_id", round_id)
        .order("created_at", desc=False)
    )
    if coach_id is not None:
        query = query.eq("coach_id", coach_id)

    result = query.execute()
    return [_row_to_annotation(r) for r in (result.data or [])]


def assign_drill_from_round(
    round_id: str,
    coach_id: str,
    student_id: str,
    drill_id: str,
    note: str = "",
) -> CoachAnnotation:
    """Assign a round drill to a student with a coach note."""
    content_parts = [f"Drill assigned to student {student_id}: drill_id={drill_id}"]
    if note.strip():
        content_parts.append(note.strip())
    content = " | ".join(content_parts)

    return add_coach_annotation(
        round_id=round_id,
        coach_id=coach_id,
        annotation_type="drill_assignment",
        content=content,
        target_id=drill_id,
        target_type="drill",
        is_correction=False,
        finding_id=None,
    )


# ── Report export ─────────────────────────────────────────────────────────────


def export_round_report(
    round_id: str,
    include_private_notes: bool = False,
) -> dict:
    """
    Export a concise round report dict suitable for display or PDF.

    Returns:
    {
      "round_id": str,
      "summary": str,
      "arguments": List[dict],  # label, side, status, response_count
      "evidence_issues": List[str],
      "legality_violations": List[str],
      "decision_summary": Optional[str],
      "drills": List[str],      # drill titles
      "coach_highlights": List[str],  # annotation contents (if include_private_notes)
    }

    ALWAYS excludes: raw speech transcripts, private coach-only notes
    (unless include_private_notes=True).
    """
    supabase = get_supabase()

    # ── Fetch round metadata ──────────────────────────────────────────────────
    round_result = (
        supabase.table("round_simulations")
        .select("id, resolution, student_side, judge_type, status, winner, created_at, completed_at")
        .eq("id", round_id)
        .single()
        .execute()
    )
    round_data = round_result.data or {}

    # ── Fetch arguments ───────────────────────────────────────────────────────
    args_result = (
        supabase.table("round_arguments")
        .select("label, side, status, response_count, is_offense")
        .eq("round_id", round_id)
        .order("created_at", desc=False)
        .execute()
    )
    raw_args = args_result.data or []
    arguments = [
        {
            "label": a.get("label", ""),
            "side": a.get("side", ""),
            "status": a.get("status", ""),
            "response_count": a.get("response_count", 0),
        }
        for a in raw_args
    ]

    # ── Fetch evidence issues (flagged uses) ──────────────────────────────────
    ev_result = (
        supabase.table("round_evidence_uses")
        .select("issue_flag, card_id")
        .eq("round_id", round_id)
        .not_.is_("issue_flag", "null")
        .execute()
    )
    evidence_issues: List[str] = [
        r["issue_flag"] for r in (ev_result.data or []) if r.get("issue_flag")
    ]

    # ── Fetch legality violations ─────────────────────────────────────────────
    leg_result = (
        supabase.table("round_legality_checks")
        .select("violation_description")
        .eq("round_id", round_id)
        .eq("is_violation", True)
        .execute()
    )
    legality_violations: List[str] = [
        r["violation_description"]
        for r in (leg_result.data or [])
        if r.get("violation_description")
    ]

    # ── Fetch decision ────────────────────────────────────────────────────────
    dec_result = (
        supabase.table("round_decisions")
        .select("decision_summary, winner")
        .eq("round_id", round_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    decision_summary: Optional[str] = None
    dec_rows = dec_result.data or []
    if dec_rows:
        decision_summary = dec_rows[0].get("decision_summary")

    # ── Fetch drills ──────────────────────────────────────────────────────────
    drills_result = (
        supabase.table("round_drills")
        .select("title")
        .eq("round_id", round_id)
        .execute()
    )
    drills: List[str] = [
        r["title"] for r in (drills_result.data or []) if r.get("title")
    ]

    # ── Fetch coach highlights ────────────────────────────────────────────────
    coach_highlights: List[str] = []
    if include_private_notes:
        annotations = list_coach_annotations(round_id=round_id)
        coach_highlights = [
            a.content
            for a in annotations
            if a.annotation_type in {"highlight", "speech_note", "argument_note"}
        ]

    # ── Build summary sentence ────────────────────────────────────────────────
    winner = round_data.get("winner") or "undecided"
    resolution = round_data.get("resolution", "")
    student_side = round_data.get("student_side", "")
    summary_parts = []
    if resolution:
        summary_parts.append(f"Resolution: {resolution}.")
    if student_side:
        summary_parts.append(f"Student debated {student_side.upper()}.")
    if winner and winner != "undecided":
        summary_parts.append(f"Winner: {winner}.")
    summary = " ".join(summary_parts) or "Round summary not available."

    return {
        "round_id": round_id,
        "summary": summary,
        "arguments": arguments,
        "evidence_issues": evidence_issues,
        "legality_violations": legality_violations,
        "decision_summary": decision_summary,
        "drills": drills,
        "coach_highlights": coach_highlights,
    }


# ── Finding rating ────────────────────────────────────────────────────────────


def rate_automated_finding(
    round_id: str,
    finding_id: str,
    rater_id: str,
    rating: str,
    note: Optional[str] = None,
) -> AutomatedFindingRating:
    """Rate an automated finding as correct/incorrect/useful/etc."""
    if rating not in _VALID_RATINGS:
        raise ValueError(
            f"Invalid rating {rating!r}. Must be one of: {sorted(_VALID_RATINGS)}"
        )

    rating_id = str(uuid.uuid4())
    created_at = _now_iso()

    row = {
        "id": rating_id,
        "round_id": round_id,
        "finding_id": finding_id,
        "rater_id": rater_id,
        "rating": rating,
        "note": note,
        "created_at": created_at,
    }

    supabase = get_supabase()
    supabase.table(_FINDING_RATING_TABLE).insert(row).execute()

    return _row_to_finding_rating(row)
