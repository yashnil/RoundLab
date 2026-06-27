"""
Event pack registry — single lookup point for all supported event formats.

Usage:
    from app.event_packs.registry import get_event_pack, list_event_packs

Only registered, complete event packs appear here.
Adding a new format requires adding it to REGISTRY below.
Requesting an unknown pack raises EventPackNotFoundError immediately
so callers get a clear error rather than silent wrong behavior.
"""

from __future__ import annotations

from app.event_packs.base import EventPackNotFoundError

# Registry of supported event packs — each entry is the module name
# of a complete event pack implementation.
# Only Public Forum is complete as of Pass 21.
REGISTRY: dict[str, str] = {
    "public_forum": "app.event_packs.public_forum",
}


def list_event_packs() -> list[dict]:
    """Return metadata for all registered event packs."""
    packs = []
    for pack_id, module_path in REGISTRY.items():
        import importlib
        mod = importlib.import_module(module_path)
        packs.append({
            "id": pack_id,
            "name": getattr(mod, "EVENT_PACK", {}).get("name", pack_id),
            "skill_count": len(getattr(mod, "SKILL_REGISTRY", {})),
            "lesson_count": len(getattr(mod, "NOVICE_PF_CURRICULUM", [])),
        })
    return packs


def get_event_pack(pack_id: str) -> object:
    """
    Return the event pack module for the given ID.

    Raises EventPackNotFoundError for unknown pack IDs.
    """
    if pack_id not in REGISTRY:
        supported = ", ".join(sorted(REGISTRY.keys()))
        raise EventPackNotFoundError(
            f"Unknown event pack '{pack_id}'. Supported: {supported}"
        )
    import importlib
    return importlib.import_module(REGISTRY[pack_id])
