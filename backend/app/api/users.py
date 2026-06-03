import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.supabase_client import get_supabase

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

    # 6. Calculate gamification: XP, level, badges
    # New XP system: heavily reward drills and attempts, not just speech uploads
    xp = 0
    xp += speech_count * 5  # +5 XP per speech (reduced from 10)
    xp += feedback_ready_count * 10  # +10 XP per feedback (reduced from 20)
    xp += drills_assigned_count * 25  # +25 XP per drill generated (increased from 15)

    # Calculate first-time vs repeat attempts
    # First attempt on each drill = 50 XP, repeat attempts = 20 XP
    try:
        attempts_breakdown = (
            supabase.table("drill_attempts")
            .select("drill_id")
            .eq("user_id", user_id)
            .order("created_at")
            .execute()
        )

        seen_drills = set()
        first_attempts = 0
        repeat_attempts = 0
        for attempt in attempts_breakdown.data:
            drill_id = attempt["drill_id"]
            if drill_id not in seen_drills:
                first_attempts += 1
                seen_drills.add(drill_id)
            else:
                repeat_attempts += 1

        xp += first_attempts * 50  # +50 XP per first drill attempt
        xp += repeat_attempts * 20  # +20 XP per repeat attempt
    except Exception as exc:
        logger.error("get_user_progress: attempt breakdown failed | %s", type(exc).__name__)
        # Fallback: treat all attempts as first attempts
        xp += drill_attempts_count * 50

    # Calculate level from XP
    # New thresholds: Level 1: 0-99, Level 2: 100-249, Level 3: 250-499, Level 4: 500-899, Level 5: 900-1399, Level 6+: 1400+
    if xp < 100:
        level = 1
        xp_to_next_level = 100 - xp
    elif xp < 250:
        level = 2
        xp_to_next_level = 250 - xp
    elif xp < 500:
        level = 3
        xp_to_next_level = 500 - xp
    elif xp < 900:
        level = 4
        xp_to_next_level = 900 - xp
    elif xp < 1400:
        level = 5
        xp_to_next_level = 1400 - xp
    else:
        level = 6 + ((xp - 1400) // 300)  # Each additional level requires 300 XP
        xp_to_next_level = 300 - ((xp - 1400) % 300)

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

    if speech_count >= 1:
        badges.append(Badge(
            id="first_speech",
            name="First Speech",
            description="Created your first practice speech",
            icon="🎤",
            earned_at=speeches_res.data[0].get("created_at") if speeches_res.data else None
        ))

    if drills_assigned_count >= 1:
        badges.append(Badge(
            id="flow_builder",
            name="Flow Builder",
            description="Generated your first argument flow",
            icon="🗺️",
            earned_at=drills_res.data[0].get("created_at") if drills_res.data else None
        ))

    if feedback_ready_count >= 1:
        badges.append(Badge(
            id="judge_ready",
            name="Judge Ready",
            description="Received your first judge-style feedback",
            icon="⚖️",
            earned_at=None  # Would need to fetch feedback created_at
        ))

    if drill_attempts_count >= 1:
        badges.append(Badge(
            id="drill_starter",
            name="Drill Starter",
            description="Completed your first practice drill",
            icon="🎯",
            earned_at=None  # Would need to fetch attempt created_at
        ))

    if speech_count >= 3:
        badges.append(Badge(
            id="consistent_speaker",
            name="Consistent Speaker",
            description="Created 3 practice speeches",
            icon="🔥",
            earned_at=None
        ))

    if drill_attempts_count >= 3:
        badges.append(Badge(
            id="practice_streak",
            name="Practice Streak",
            description="Completed 3 drill attempts",
            icon="⚡",
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
