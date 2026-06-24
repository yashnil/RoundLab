import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.supabase_client import get_supabase
from app.services.xp_ledger import get_user_total_xp, calculate_level

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


class IncompleteDrill(BaseModel):
    id: str
    speech_id: str
    title: str
    skill_target: str
    difficulty: str
    status: str
    speech_title: str


class SkillAverage(BaseModel):
    clash: float
    weighing: float
    extensions: float
    drops: float
    judge_adaptation: float


class Badge(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    earned_at: str | None


class ProgressSummary(BaseModel):
    speech_count: int
    feedback_ready_count: int
    drills_assigned_count: int
    drill_attempts_count: int
    drills_completed_count: int
    drill_completion_rate: float | None
    incomplete_drills: list[IncompleteDrill]
    skill_averages: SkillAverage | None
    # Gamification
    xp: int
    level: int
    xp_to_next_level: int
    badges: list[Badge]


@router.get("/{user_id}/progress", response_model=ProgressSummary)
async def get_user_progress(user_id: str) -> ProgressSummary:
    """
    Get aggregated progress metrics for a user.

    Returns:
    - Total speeches created
    - Speeches with feedback ready
    - Total drills assigned
    - Total drill attempts
    - Drill completion rate
    - List of incomplete drills (for "Recommended Next Practice")
    - Average scores across all feedback reports
    """
    supabase = get_supabase()

    # 1. Count speeches
    try:
        speeches_res = (
            supabase.table("speeches")
            .select("id, status")
            .eq("user_id", user_id)
            .execute()
        )
        speech_count = len(speeches_res.data)
        feedback_ready_count = sum(1 for s in speeches_res.data if s["status"] == "done")
    except Exception as exc:
        logger.error("get_user_progress: speeches fetch failed | %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to fetch speech data") from exc

    # 2. Count drills
    try:
        drills_res = (
            supabase.table("drills")
            .select("id, status")
            .eq("user_id", user_id)
            .execute()
        )
        drills_assigned_count = len(drills_res.data)
        drills_completed_count = sum(1 for d in drills_res.data if d["status"] == "completed")
        drill_completion_rate = (
            drills_completed_count / drills_assigned_count if drills_assigned_count > 0 else None
        )
    except Exception as exc:
        logger.error("get_user_progress: drills fetch failed | %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to fetch drill data") from exc

    # 3. Count drill attempts
    try:
        attempts_res = (
            supabase.table("drill_attempts")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        drill_attempts_count = attempts_res.count or 0
    except Exception as exc:
        logger.error("get_user_progress: drill attempts fetch failed | %s", type(exc).__name__)
        drill_attempts_count = 0

    # 4. Fetch incomplete drills (for "Recommended Next Practice")
    # Get the most recent drills that are not completed
    try:
        incomplete_res = (
            supabase.table("drills")
            .select("id, speech_id, title, skill_target, difficulty, status, speeches(title)")
            .eq("user_id", user_id)
            .neq("status", "completed")
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )
        incomplete_drills = [
            IncompleteDrill(
                id=d["id"],
                speech_id=d["speech_id"],
                title=d["title"],
                skill_target=d["skill_target"],
                difficulty=d["difficulty"],
                status=d["status"],
                speech_title=d["speeches"]["title"] if d.get("speeches") else "Unknown Speech",
            )
            for d in incomplete_res.data
        ]
    except Exception as exc:
        logger.error("get_user_progress: incomplete drills fetch failed | %s", type(exc).__name__)
        incomplete_drills = []

    # 5. Calculate average feedback scores
    try:
        feedback_res = (
            supabase.table("feedback_reports")
            .select("scores, speeches!inner(user_id)")
            .eq("speeches.user_id", user_id)
            .execute()
        )

        if feedback_res.data:
            # Average each dimension
            clash_scores = []
            weighing_scores = []
            extensions_scores = []
            drops_scores = []
            judge_adaptation_scores = []

            for fb in feedback_res.data:
                scores = fb.get("scores", {})
                if isinstance(scores, dict):
                    if "clash" in scores: clash_scores.append(scores["clash"])
                    if "weighing" in scores: weighing_scores.append(scores["weighing"])
                    if "extensions" in scores: extensions_scores.append(scores["extensions"])
                    if "drops" in scores: drops_scores.append(scores["drops"])
                    if "judge_adaptation" in scores: judge_adaptation_scores.append(scores["judge_adaptation"])

            skill_averages = SkillAverage(
                clash=sum(clash_scores) / len(clash_scores) if clash_scores else 0,
                weighing=sum(weighing_scores) / len(weighing_scores) if weighing_scores else 0,
                extensions=sum(extensions_scores) / len(extensions_scores) if extensions_scores else 0,
                drops=sum(drops_scores) / len(drops_scores) if drops_scores else 0,
                judge_adaptation=sum(judge_adaptation_scores) / len(judge_adaptation_scores) if judge_adaptation_scores else 0,
            )
        else:
            skill_averages = None
    except Exception as exc:
        logger.error("get_user_progress: feedback averages failed | %s", type(exc).__name__)
        skill_averages = None

    # 6. Calculate gamification: XP, level, badges (from append-only ledger)
    # XP represents earned learning progress, not current database rows.
    # Deleting speeches/drills does not remove earned XP.
    try:
        xp = get_user_total_xp(user_id)
    except Exception as exc:
        logger.error("get_user_progress: XP fetch failed | %s", type(exc).__name__)
        xp = 0

    # Calculate level from XP using ledger function
    level, xp_to_next_level = calculate_level(xp)

    # Calculate badges based on achievements
    badges = []

    # Check if user joined a team
    try:
        team_res = (
            supabase.table("team_members")
            .select("created_at")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        has_team = len(team_res.data) > 0
        team_joined_at = team_res.data[0]["created_at"] if has_team else None
    except Exception:
        has_team = False
        team_joined_at = None

    # Practice-focused badges: reward effort and improvement loops
    if feedback_ready_count >= 1:
        badges.append(Badge(
            id="first_feedback",
            name="First Feedback",
            description="Received your first judge-style feedback",
            icon="⚖️",
            earned_at=None
        ))

    if drill_attempts_count >= 1:
        badges.append(Badge(
            id="first_drill_attempt",
            name="First Drill Attempt",
            description="Completed your first practice drill",
            icon="🎯",
            earned_at=None
        ))

    if drill_attempts_count >= 3:
        badges.append(Badge(
            id="three_drill_attempts",
            name="Practice Habit",
            description="Completed 3 drill attempts",
            icon="⚡",
            earned_at=None
        ))

    # Full practice loop: at least one drill attempt exists
    if drill_attempts_count >= 1:
        badges.append(Badge(
            id="full_practice_loop",
            name="Full Practice Loop",
            description="Completed feedback → drill → attempt for one speech",
            icon="🔄",
            earned_at=None
        ))

    if feedback_ready_count >= 3:
        badges.append(Badge(
            id="three_feedback_reports",
            name="Feedback Analyst",
            description="Received 3 feedback reports",
            icon="📊",
            earned_at=None
        ))

    if has_team:
        badges.append(Badge(
            id="team_player",
            name="Team Player",
            description="Joined a debate team",
            icon="👥",
            earned_at=team_joined_at
        ))

    return ProgressSummary(
        speech_count=speech_count,
        feedback_ready_count=feedback_ready_count,
        drills_assigned_count=drills_assigned_count,
        drill_attempts_count=drill_attempts_count,
        drills_completed_count=drills_completed_count,
        drill_completion_rate=drill_completion_rate,
        incomplete_drills=incomplete_drills,
        skill_averages=skill_averages,
        xp=xp,
        level=level,
        xp_to_next_level=xp_to_next_level,
        badges=badges,
    )


# ── Pass 18: Account deletion (GDPR / pilot cleanup) ─────────────────────────

@router.delete("/{user_id}", status_code=200)
async def delete_user_account(user_id: str) -> dict:
    """
    Delete a user account and cascade all user-owned data.

    Removes in this order:
    1. Round simulations (coach annotations, findings, replay markers)
    2. Card drafts and saved evidence cards
    3. Speeches (cascades transcripts, feedback, drills)
    4. Product events (analytics history)
    5. Profile row

    Audio files in Storage are deleted best-effort; DB deletion
    proceeds even if storage cleanup partially fails.

    WARNING: Irreversible. Caller must verify identity before calling.
    """
    supabase = get_supabase()
    errors: list[str] = []

    # 1. Round simulations (cascade tables)
    for cascade_table in (
        "round_coach_annotations",
        "round_finding_ratings",
        "round_strategic_memory",
        "round_replay_markers",
        "round_quality_reports",
    ):
        try:
            supabase.table(cascade_table).delete().eq("round_id", user_id).execute()
        except Exception:
            pass  # cascade table may not have user_id — skip

    try:
        # Get round IDs first so we can cascade
        round_res = (
            supabase.table("round_simulations")
            .select("id")
            .eq("user_id", user_id)
            .execute()
        )
        round_ids = [r["id"] for r in (round_res.data or [])]
        if round_ids:
            for cascade_table in (
                "round_coach_annotations",
                "round_finding_ratings",
                "round_strategic_memory",
                "round_replay_markers",
                "round_quality_reports",
                "round_arguments",
                "round_speeches",
                "round_crossfire_exchanges",
                "round_evidence_uses",
                "round_decisions",
            ):
                try:
                    supabase.table(cascade_table).delete().in_("round_id", round_ids).execute()
                except Exception:
                    pass
        supabase.table("round_simulations").delete().eq("user_id", user_id).execute()
    except Exception as exc:
        errors.append(f"rounds: {type(exc).__name__}")

    # 2. Evidence cards + drafts
    for evidence_table in ("evidence_cards", "card_drafts", "research_documents"):
        try:
            supabase.table(evidence_table).delete().eq("user_id", user_id).execute()
        except Exception as exc:
            errors.append(f"{evidence_table}: {type(exc).__name__}")

    # 3. Speeches (cascade: transcripts, feedback_reports, argument_maps, drills)
    try:
        speech_res = (
            supabase.table("speeches").select("id").eq("user_id", user_id).execute()
        )
        speech_ids = [s["id"] for s in (speech_res.data or [])]
        if speech_ids:
            for cascade_table in (
                "transcripts",
                "feedback_reports",
                "argument_maps",
                "drills",
                "drill_attempts",
                "analysis_jobs",
                "delivery_metrics",
            ):
                try:
                    supabase.table(cascade_table).delete().in_("speech_id", speech_ids).execute()
                except Exception:
                    pass
            # Best-effort audio file deletion
            for speech_id in speech_ids:
                try:
                    supabase.storage.from_("speeches").remove([f"{user_id}/{speech_id}.webm"])
                except Exception:
                    pass
        supabase.table("speeches").delete().eq("user_id", user_id).execute()
    except Exception as exc:
        errors.append(f"speeches: {type(exc).__name__}")

    # 4. Product events (analytics)
    try:
        supabase.table("product_events").delete().eq("user_id", user_id).execute()
    except Exception as exc:
        errors.append(f"product_events: {type(exc).__name__}")

    # 5. Team membership
    try:
        supabase.table("team_members").delete().eq("user_id", user_id).execute()
    except Exception as exc:
        errors.append(f"team_members: {type(exc).__name__}")

    # 6. Profile row (last — identity anchor)
    try:
        supabase.table("profiles").delete().eq("id", user_id).execute()
    except Exception as exc:
        errors.append(f"profile: {type(exc).__name__}")
        raise HTTPException(status_code=500, detail="Failed to delete profile row.") from exc

    logger.info("delete_user_account: completed | user=%s | errors=%s", user_id[:8], errors)
    return {
        "deleted": True,
        "user_id": user_id,
        "partial_errors": errors if errors else None,
    }


@router.get("/{user_id}/cost-summary")
async def get_user_cost_summary(user_id: str) -> dict:
    """Developer/admin view: today's estimated cost for a user."""
    from app.services.cost_tracker import get_daily_cost_summary
    return get_daily_cost_summary(user_id)
