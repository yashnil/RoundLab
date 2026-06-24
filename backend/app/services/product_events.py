"""
Internal product analytics: best-effort event tracking for pilot readiness.

Failures here MUST NEVER break user flows.
All public functions swallow exceptions and log server-side only.

Pilot funnel events:
  onboarding_completed        — user finished onboarding flow
  first_speech_completed      — first speech analysis done
  evidence_card_saved         — user saved an evidence card
  first_evidence_card_saved   — specifically the first card ever
  drill_completed             — drill attempt marked complete
  round_started               — round simulation created
  round_completed             — round simulation reached ballot stage
  coach_review_completed      — coach finished annotating a round
  return_visit                — user active on a subsequent day
  feedback_marked_useful      — user rated feedback as useful
  workflow_stage_failed       — a stage failed (funnel drop detection)

Do NOT log: raw speech text, audio, evidence body text, private notes.
"""

import logging
from typing import Any, Optional

from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)


class PilotEvent:
    ONBOARDING_COMPLETED = "onboarding_completed"
    ONBOARDING_STEP = "onboarding_step_completed"
    FIRST_SPEECH_COMPLETED = "first_speech_completed"
    EVIDENCE_CARD_SAVED = "evidence_card_saved"
    FIRST_EVIDENCE_CARD_SAVED = "first_evidence_card_saved"
    DRILL_COMPLETED = "drill_completed"
    ROUND_STARTED = "round_started"
    ROUND_COMPLETED = "round_completed"
    COACH_REVIEW_COMPLETED = "coach_review_completed"
    RETURN_VISIT = "return_visit"
    FEEDBACK_MARKED_USEFUL = "feedback_marked_useful"
    WORKFLOW_STAGE_FAILED = "workflow_stage_failed"
    # Backward-compatible existing events
    SPEECH_CREATED = "speech_created"
    SPEECH_ANALYZED = "speech_analyzed"
    DRILL_RATED = "drill_rated"
    RERECORD_STARTED = "rerecord_started"
    # Cost monitoring
    LLM_COST_INCURRED = "llm_cost_incurred"
    PROVIDER_COST_INCURRED = "provider_cost_incurred"


def track_product_event(
    user_id: str,
    event_name: str,
    speech_id: Optional[str] = None,
    drill_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """
    Insert a product analytics event. Best-effort — never raises.

    Args:
        user_id:    UUID of the acting user.
        event_name: Slug identifier (e.g. "round_completed").
        speech_id:  Optional FK to speeches table.
        drill_id:   Optional FK to drills table.
        metadata:   Optional payload (no PII, no speech text, no secrets).
    """
    try:
        supabase = get_supabase()
        row: dict[str, Any] = {
            "user_id": user_id,
            "event_name": event_name,
            "metadata_json": metadata or {},
        }
        if speech_id:
            row["speech_id"] = speech_id
        if drill_id:
            row["drill_id"] = drill_id

        supabase.table("product_events").insert(row).execute()
        logger.debug(
            "track_product_event: %s | user=%s speech=%s drill=%s",
            event_name, user_id, speech_id, drill_id,
        )
    except Exception as exc:
        logger.error(
            "track_product_event: failed silently | event=%s user=%s | exc_type=%s",
            event_name, user_id, type(exc).__name__,
        )


def track_evidence_saved(
    user_id: str,
    card_id: str,
    is_first_card: bool = False,
) -> None:
    """Track evidence card save (and first-card milestone separately)."""
    track_product_event(
        user_id=user_id,
        event_name=PilotEvent.EVIDENCE_CARD_SAVED,
        metadata={"card_id": card_id},
    )
    if is_first_card:
        track_product_event(
            user_id=user_id,
            event_name=PilotEvent.FIRST_EVIDENCE_CARD_SAVED,
            metadata={"card_id": card_id},
        )


def track_round_event(
    user_id: str,
    event_name: str,
    round_id: str,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """Track a round lifecycle event (started, completed)."""
    payload: dict[str, Any] = {"round_id": round_id, **(metadata or {})}
    track_product_event(user_id=user_id, event_name=event_name, metadata=payload)


def track_workflow_failure(
    user_id: str,
    stage: str,
    error_code: str,
    speech_id: Optional[str] = None,
) -> None:
    """Track a workflow failure for funnel drop detection."""
    track_product_event(
        user_id=user_id,
        event_name=PilotEvent.WORKFLOW_STAGE_FAILED,
        speech_id=speech_id,
        metadata={"stage": stage, "error_code": error_code},
    )
