"""
XP Ledger Service: Append-only XP tracking.

XP represents earned learning progress, not current database rows.
Deleting speeches/drills does not remove earned XP.
"""

import logging
from typing import Optional

from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)


# XP Award Rules (research-inspired learning motivation)
XP_RULES = {
    # No XP for just uploading - reward practice, not content creation
    "speech_upload": 0,
    "transcript_generated": 0,

    # Minimal XP for generating reports
    "feedback_generated": 5,
    "flow_generated": 5,

    # Meaningful XP for drill practice
    "drill_attempt_first": 50,  # First attempt at a drill
    "drill_attempt_repeat": 20,  # Additional attempts
    "drill_completed": 30,  # Mark drill as completed

    # Bonus XP for improvement
    "skill_improved_minor": 20,  # Improve dimension by 3+ points
    "skill_improved_major": 40,  # Improve dimension by 6+ points

    # Consistency bonuses
    "daily_practice": 10,  # Practice on a new day
    "streak_3_days": 25,
    "streak_7_days": 75,
    "streak_14_days": 150,

    # Quality milestones
    "first_75_plus_score": 50,
    "balanced_case": 30,  # All constructive dimensions >= 12

    # Team contribution (if team features enabled)
    "team_practice": 10,
}


def award_xp(
    user_id: str,
    event_type: str,
    event_key: str,
    xp_amount: Optional[int] = None,
    metadata: Optional[dict] = None,
) -> bool:
    """
    Award XP to a user for a specific event.

    Returns True if XP was awarded, False if event_key already exists (duplicate).

    Args:
        user_id: User UUID
        event_type: Category of event (e.g., "drill_attempt", "skill_improvement")
        event_key: Unique identifier for this event (e.g., "drill_attempt:{attempt_id}")
        xp_amount: XP to award. If None, looks up in XP_RULES.
        metadata: Optional additional data about the event
    """
    supabase = get_supabase()

    if xp_amount is None:
        xp_amount = XP_RULES.get(event_type, 0)

    if xp_amount == 0:
        logger.debug("award_xp: skipping zero-XP event | user_id=%s event_type=%s", user_id, event_type)
        return False

    try:
        # Try to insert XP event - unique constraint prevents duplicates
        result = supabase.table("user_xp_events").insert({
            "user_id": user_id,
            "event_type": event_type,
            "event_key": event_key,
            "xp_amount": xp_amount,
            "metadata": metadata or {},
        }).execute()

        if result.data:
            logger.info(
                "award_xp: success | user_id=%s event_type=%s xp=%d event_key=%s",
                user_id,
                event_type,
                xp_amount,
                event_key,
            )
            return True

    except Exception as exc:
        # Unique constraint violation means event already awarded
        if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
            logger.debug(
                "award_xp: duplicate event ignored | user_id=%s event_key=%s",
                user_id,
                event_key,
            )
            return False

        # Check if table doesn't exist
        exc_str = str(exc).lower()
        if "user_xp_events" in exc_str and ("does not exist" in exc_str or "relation" in exc_str):
            logger.warning(
                "award_xp: user_xp_events table missing | Apply migration 20260604000000_add_xp_ledger.sql | user_id=%s event_type=%s",
                user_id,
                event_type,
            )
        else:
            logger.error(
                "award_xp: failed | user_id=%s event_type=%s | exc_type=%s | exc=%s",
                user_id,
                event_type,
                type(exc).__name__,
                str(exc),
            )

    return False


def get_user_total_xp(user_id: str) -> int:
    """Get total XP earned by user from ledger."""
    supabase = get_supabase()

    try:
        result = (
            supabase.table("user_xp_events")
            .select("xp_amount")
            .eq("user_id", user_id)
            .execute()
        )

        if result.data:
            total = sum(event.get("xp_amount", 0) for event in result.data)
            return total
    except Exception as exc:
        logger.error("get_user_total_xp: failed | user_id=%s | exc_type=%s", user_id, type(exc).__name__)

    return 0


def calculate_level(xp: int) -> tuple[int, int]:
    """
    Calculate level and XP to next level.

    Returns (level, xp_to_next_level)

    Level curve: 100 XP for level 2, then +50 per level
    Level 1: 0-99 XP
    Level 2: 100-199 XP
    Level 3: 200-299 XP
    etc.
    """
    if xp < 100:
        return (1, 100 - xp)

    # After 100, each level needs 100 more XP
    level = 1 + (xp // 100)
    xp_in_current_level = xp % 100
    xp_to_next = 100 - xp_in_current_level

    return (level, xp_to_next)


def check_and_award_streak_bonus(user_id: str, current_date: str) -> None:
    """
    Check if user has a practice streak and award bonus XP.

    current_date: ISO date string (YYYY-MM-DD)
    """
    supabase = get_supabase()

    try:
        # Get recent practice days
        result = (
            supabase.table("user_xp_events")
            .select("created_at")
            .eq("user_id", user_id)
            .gte("created_at", f"{current_date}T00:00:00Z")  # Events today or later
            .limit(1)
            .execute()
        )

        if not result.data:
            # Award daily practice bonus
            award_xp(
                user_id=user_id,
                event_type="daily_practice",
                event_key=f"daily_practice:{current_date}",
            )

        # TODO: Calculate streak length and award streak bonuses
        # This requires counting consecutive days with practice events
        # Implement if needed based on product priority

    except Exception as exc:
        logger.error("check_and_award_streak_bonus: failed | exc_type=%s", type(exc).__name__)


def check_and_award_skill_improvement(
    user_id: str,
    speech_id: str,
    dimension: str,
    old_score: int,
    new_score: int,
) -> None:
    """
    Check if a skill improved and award bonus XP.

    Awards XP for significant score improvements in specific dimensions.
    """
    improvement = new_score - old_score

    if improvement >= 6:
        # Major improvement
        award_xp(
            user_id=user_id,
            event_type="skill_improved_major",
            event_key=f"skill_improved:{speech_id}:{dimension}",
            metadata={"dimension": dimension, "improvement": improvement},
        )
    elif improvement >= 3:
        # Minor improvement
        award_xp(
            user_id=user_id,
            event_type="skill_improved_minor",
            event_key=f"skill_improved:{speech_id}:{dimension}",
            metadata={"dimension": dimension, "improvement": improvement},
        )
