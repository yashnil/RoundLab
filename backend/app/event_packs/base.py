"""
Event pack base — defines the interface all event packs must satisfy.

An event pack encapsulates everything that is debate-format-specific:
  - canonical skill graph
  - curriculum lessons
  - speech roles and timing
  - rubric dimensions
  - drill templates
  - judge profiles

Generic systems (mastery engine, training planner, diagnostic engine)
operate on the abstract interface, not on PF-specific constants.
Unknown event packs raise EventPackNotFoundError immediately.
"""

from __future__ import annotations

from typing import Optional


class EventPackNotFoundError(ValueError):
    """Raised when an unknown event pack ID is requested."""
    pass


class EventPackBase:
    """
    Abstract base for event packs.

    Concrete event packs do not inherit from this — they just expose these
    module-level names via the registry. This class documents the contract.
    """

    #: Unique string ID for this event pack (e.g., "public_forum")
    id: str

    #: Human-readable name
    name: str

    #: dict[skill_id, skill_dict] — canonical skill taxonomy
    SKILL_REGISTRY: dict

    #: dict[str, str] — legacy name → canonical skill_id
    LEGACY_SKILL_MAP: dict

    #: dict[skill_id, list[str]] — prerequisite skill graph
    SKILL_PREREQUISITES: dict

    #: list[dict] — ordered curriculum lessons
    CURRICULUM: list

    #: list[dict] — speech role definitions [{id, label, minutes, description}]
    SPEECH_ROLES: list

    def get_skill(self, skill_id: str) -> Optional[dict]:
        raise NotImplementedError

    def get_lesson(self, lesson_id: str) -> Optional[dict]:
        raise NotImplementedError

    def resolve_legacy_skill(self, name: str) -> str:
        raise NotImplementedError
