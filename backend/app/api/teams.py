import logging
import secrets
import string

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/teams", tags=["teams"])


# ── Models ────────────────────────────────────────────────────────────────────


class TeamCreateRequest(BaseModel):
    name: str
    created_by: str


class TeamJoinRequest(BaseModel):
    invite_code: str
    user_id: str


class TeamMember(BaseModel):
    id: str
    team_id: str
    user_id: str
    role: str
    created_at: str


class Team(BaseModel):
    id: str
    name: str
    invite_code: str
    created_by: str
    created_at: str


class UserTeam(BaseModel):
    team_id: str
    team_name: str
    role: str
    invite_code: str


class StudentProgress(BaseModel):
    user_id: str
    display_name: str | None
    speech_count: int
    feedback_ready_count: int
    drills_assigned_count: int
    drill_attempts_count: int
    latest_practice_at: str | None


class TeamDashboard(BaseModel):
    team_id: str
    team_name: str
    invite_code: str
    member_count: int
    students: list[StudentProgress]


# ── Helpers ───────────────────────────────────────────────────────────────────


def generate_invite_code(length: int = 8) -> str:
    """Generate a short random invite code (uppercase letters and digits)."""
    chars = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("", response_model=Team, status_code=201)
async def create_team(body: TeamCreateRequest) -> Team:
    """
    Create a new team and add the creator as a coach.
    Generates a unique invite code.
    """
    supabase = get_supabase()

    # Generate unique invite code
    max_attempts = 10
    invite_code = None
    for _ in range(max_attempts):
        candidate = generate_invite_code()
        try:
            # Check if code exists
            result = (
                supabase.table("teams")
                .select("id")
                .eq("invite_code", candidate)
                .execute()
            )
            if not result.data:
                invite_code = candidate
                break
        except Exception:
            pass

    if not invite_code:
        raise HTTPException(
            status_code=500, detail="Could not generate unique invite code"
        )

    # Create team
    try:
        team_result = (
            supabase.table("teams")
            .insert(
                {
                    "name": body.name,
                    "invite_code": invite_code,
                    "created_by": body.created_by,
                }
            )
            .execute()
        )
        team = team_result.data[0]
    except Exception as exc:
        logger.error("create_team: team insert failed | %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to create team") from exc

    # Add creator as coach
    try:
        supabase.table("team_members").insert(
            {
                "team_id": team["id"],
                "user_id": body.created_by,
                "role": "coach",
            }
        ).execute()
    except Exception as exc:
        logger.error("create_team: add coach failed | %s", type(exc).__name__)
        # Team was created but coach wasn't added - still return team
        # The creator can manually join as coach if needed

    logger.info("create_team: created team_id=%s | invite_code=%s", team["id"], invite_code)
    return Team(**team)


@router.post("/join", response_model=TeamMember, status_code=201)
async def join_team(body: TeamJoinRequest) -> TeamMember:
    """
    Join a team using an invite code.
    Adds the user as a student member.
    """
    supabase = get_supabase()

    # 1. Find team by invite code
    try:
        team_result = (
            supabase.table("teams")
            .select("id")
            .eq("invite_code", body.invite_code)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.error("join_team: team lookup failed | %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to lookup team") from exc

    if not team_result.data:
        raise HTTPException(status_code=404, detail="Invalid invite code")

    team_id = team_result.data[0]["id"]

    # 2. Check if already a member
    try:
        existing = (
            supabase.table("team_members")
            .select("id")
            .eq("team_id", team_id)
            .eq("user_id", body.user_id)
            .execute()
        )
        if existing.data:
            raise HTTPException(status_code=400, detail="Already a member of this team")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("join_team: membership check failed | %s", type(exc).__name__)

    # 3. Add as student
    try:
        member_result = (
            supabase.table("team_members")
            .insert(
                {
                    "team_id": team_id,
                    "user_id": body.user_id,
                    "role": "student",
                }
            )
            .execute()
        )
        logger.info("join_team: user_id=%s joined team_id=%s", body.user_id, team_id)
        return TeamMember(**member_result.data[0])
    except Exception as exc:
        logger.error("join_team: insert failed | %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to join team") from exc


@router.get("/users/{user_id}", response_model=list[UserTeam])
async def get_user_teams(user_id: str) -> list[UserTeam]:
    """
    Get all teams a user belongs to with their role.
    """
    supabase = get_supabase()

    try:
        result = (
            supabase.table("team_members")
            .select("team_id, role, teams(id, name, invite_code)")
            .eq("user_id", user_id)
            .execute()
        )

        teams = []
        for row in result.data:
            if row.get("teams"):
                teams.append(
                    UserTeam(
                        team_id=row["team_id"],
                        team_name=row["teams"]["name"],
                        role=row["role"],
                        invite_code=row["teams"]["invite_code"],
                    )
                )
        return teams
    except Exception as exc:
        logger.error("get_user_teams: fetch failed | %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to fetch teams") from exc


@router.get("/{team_id}/dashboard", response_model=TeamDashboard)
async def get_team_dashboard(team_id: str, user_id: str) -> TeamDashboard:
    """
    Get team dashboard with student progress.
    Only accessible to team members (coaches and students).
    """
    supabase = get_supabase()

    # 1. Verify user is a member
    try:
        membership = (
            supabase.table("team_members")
            .select("role")
            .eq("team_id", team_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if not membership.data:
            raise HTTPException(
                status_code=403, detail="You are not a member of this team"
            )
        user_role = membership.data[0]["role"]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_team_dashboard: membership check failed | %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to verify membership") from exc

    # 2. Get team info
    try:
        team_result = (
            supabase.table("teams")
            .select("id, name, invite_code")
            .eq("id", team_id)
            .limit(1)
            .execute()
        )
        if not team_result.data:
            raise HTTPException(status_code=404, detail="Team not found")
        team = team_result.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_team_dashboard: team fetch failed | %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to fetch team") from exc

    # 3. Get all team members
    try:
        members_result = (
            supabase.table("team_members")
            .select("user_id, role, profiles(display_name)")
            .eq("team_id", team_id)
            .execute()
        )
        all_members = members_result.data
    except Exception as exc:
        logger.error("get_team_dashboard: members fetch failed | %s", type(exc).__name__)
        all_members = []

    # 4. Get student progress
    students = []
    student_members = [m for m in all_members if m["role"] == "student"]

    for member in student_members:
        student_user_id = member["user_id"]
        display_name = member.get("profiles", {}).get("display_name") if member.get("profiles") else None

        # Get speech count
        try:
            speeches = (
                supabase.table("speeches")
                .select("id, status, created_at")
                .eq("user_id", student_user_id)
                .execute()
            )
            speech_count = len(speeches.data)
            feedback_ready_count = sum(1 for s in speeches.data if s["status"] == "done")

            # Latest practice
            latest_practice_at = None
            if speeches.data:
                sorted_speeches = sorted(
                    speeches.data, key=lambda s: s["created_at"], reverse=True
                )
                latest_practice_at = sorted_speeches[0]["created_at"]
        except Exception:
            speech_count = 0
            feedback_ready_count = 0
            latest_practice_at = None

        # Get drill stats
        try:
            drills = (
                supabase.table("drills")
                .select("id")
                .eq("user_id", student_user_id)
                .execute()
            )
            drills_assigned_count = len(drills.data)
        except Exception:
            drills_assigned_count = 0

        # Get drill attempts
        try:
            attempts = (
                supabase.table("drill_attempts")
                .select("id", count="exact")
                .eq("user_id", student_user_id)
                .execute()
            )
            drill_attempts_count = attempts.count or 0
        except Exception:
            drill_attempts_count = 0

        students.append(
            StudentProgress(
                user_id=student_user_id,
                display_name=display_name,
                speech_count=speech_count,
                feedback_ready_count=feedback_ready_count,
                drills_assigned_count=drills_assigned_count,
                drill_attempts_count=drill_attempts_count,
                latest_practice_at=latest_practice_at,
            )
        )

    return TeamDashboard(
        team_id=team["id"],
        team_name=team["name"],
        invite_code=team["invite_code"],
        member_count=len(all_members),
        students=students,
    )
