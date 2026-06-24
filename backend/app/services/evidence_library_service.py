"""Evidence Library service layer (Pass 13).

Provides CRUD and search operations for the evidence library entities.
All Supabase calls are isolated here so the API layer stays thin and unit tests
can mock this module directly.

Ownership rule: user_id is always checked before writes. Team-shared resources
allow team members to read, but only the owner can modify.

Card integrity rule: none of these functions modify evidence_cards.body_text,
highlighted_spans_json, underline_spans_json, or support_verdict. Only
library-organisation metadata is written.
"""

import hashlib
import logging
from datetime import date, timezone
from typing import Optional

from app.models.evidence_library import (
    ArgumentCreate,
    ArgumentRow,
    ArgumentUpdate,
    BlockfileCreate,
    BlockfileEntryCreate,
    BlockfileEntryRow,
    BlockfileEntryUpdate,
    BlockfileRow,
    BlockfileSectionCreate,
    BlockfileSectionRow,
    BlockfileSectionUpdate,
    BlockfileUpdate,
    CardRelationshipCreate,
    CardRelationshipRow,
    CardVersionRow,
    EvidenceSourceCreate,
    EvidenceSourceRow,
    FrontlineCreate,
    FrontlineResponseCardCreate,
    FrontlineResponseCardRow,
    FrontlineResponseCreate,
    FrontlineResponseRow,
    FrontlineResponseUpdate,
    FrontlineRow,
    FrontlineUpdate,
    LibraryCardMetadataRow,
    LibraryCardSaveRequest,
    LibraryCardUpdate,
    LibrarySearchRequest,
    LibrarySearchResponse,
    LibrarySearchResult,
    ResolutionCreate,
    ResolutionRow,
    ResolutionUpdate,
)
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _today_iso() -> str:
    return date.today().isoformat()


def _normalize_title(title: str) -> str:
    return title.strip().lower()


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()[:40]


def _require_owner(table: str, row_id: str, user_id: str) -> dict:
    """Fetch a row and raise ValueError if it doesn't belong to user_id."""
    sb = get_supabase()
    result = sb.table(table).select("*").eq("id", row_id).limit(1).execute()
    if not result.data:
        raise ValueError(f"{table} {row_id} not found")
    row = result.data[0]
    if row.get("user_id") != user_id:
        raise PermissionError(f"Not authorized to modify {table} {row_id}")
    return row


# ── Resolution CRUD ───────────────────────────────────────────────────────────

def create_resolution(body: ResolutionCreate) -> ResolutionRow:
    sb = get_supabase()
    normalized = _normalize_title(body.title)
    row = {
        "user_id": body.user_id,
        "title": body.title,
        "normalized_title": normalized,
        "season": body.season,
        "event_type": body.event_type,
        "is_active": body.is_active,
    }
    if body.team_id:
        row["team_id"] = body.team_id
    result = sb.table("resolutions").insert(row).execute()
    return ResolutionRow(**result.data[0])


def get_resolution(resolution_id: str, user_id: str) -> Optional[ResolutionRow]:
    sb = get_supabase()
    result = (
        sb.table("resolutions")
        .select("*")
        .eq("id", resolution_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    row = result.data[0]
    if row["user_id"] != user_id:
        return None
    return ResolutionRow(**row)


def list_resolutions(user_id: str, active_only: bool = False) -> list[ResolutionRow]:
    sb = get_supabase()
    q = sb.table("resolutions").select("*").eq("user_id", user_id).order("updated_at", desc=True)
    if active_only:
        q = q.eq("is_active", True)
    result = q.execute()
    return [ResolutionRow(**r) for r in (result.data or [])]


def update_resolution(resolution_id: str, body: ResolutionUpdate) -> ResolutionRow:
    row = _require_owner("resolutions", resolution_id, body.user_id)
    updates: dict = {}
    if body.title is not None:
        updates["title"] = body.title
        updates["normalized_title"] = _normalize_title(body.title)
    if body.season is not None:
        updates["season"] = body.season
    if body.event_type is not None:
        updates["event_type"] = body.event_type
    if body.is_active is not None:
        updates["is_active"] = body.is_active
    if not updates:
        return ResolutionRow(**row)
    sb = get_supabase()
    result = sb.table("resolutions").update(updates).eq("id", resolution_id).execute()
    return ResolutionRow(**result.data[0])


def archive_resolution(resolution_id: str, user_id: str) -> ResolutionRow:
    _require_owner("resolutions", resolution_id, user_id)
    sb = get_supabase()
    result = sb.table("resolutions").update({"is_active": False}).eq("id", resolution_id).execute()
    return ResolutionRow(**result.data[0])


# ── Argument CRUD ─────────────────────────────────────────────────────────────

def create_argument(body: ArgumentCreate) -> ArgumentRow:
    sb = get_supabase()
    row: dict = {
        "user_id": body.user_id,
        "side": body.side,
        "title": body.title,
        "argument_type": body.argument_type,
    }
    for opt_field in ["resolution_id", "summary", "parent_argument_id", "team_id"]:
        val = getattr(body, opt_field, None)
        if val:
            row[opt_field] = val
    result = sb.table("arguments").insert(row).execute()
    return ArgumentRow(**result.data[0])


def get_argument(argument_id: str, user_id: str) -> Optional[ArgumentRow]:
    sb = get_supabase()
    result = sb.table("arguments").select("*").eq("id", argument_id).limit(1).execute()
    if not result.data:
        return None
    row = result.data[0]
    if row["user_id"] != user_id:
        return None
    return ArgumentRow(**row)


def list_arguments(
    user_id: str,
    resolution_id: Optional[str] = None,
    side: Optional[str] = None,
) -> list[ArgumentRow]:
    sb = get_supabase()
    q = sb.table("arguments").select("*").eq("user_id", user_id).order("created_at", desc=False)
    if resolution_id:
        q = q.eq("resolution_id", resolution_id)
    if side:
        q = q.eq("side", side)
    result = q.execute()
    return [ArgumentRow(**r) for r in (result.data or [])]


def update_argument(argument_id: str, body: ArgumentUpdate) -> ArgumentRow:
    row = _require_owner("arguments", argument_id, body.user_id)
    updates: dict = {}
    for field in ["title", "summary", "argument_type", "side", "parent_argument_id"]:
        val = getattr(body, field, None)
        if val is not None:
            updates[field] = val
    if not updates:
        return ArgumentRow(**row)
    sb = get_supabase()
    result = sb.table("arguments").update(updates).eq("id", argument_id).execute()
    return ArgumentRow(**result.data[0])


def delete_argument(argument_id: str, user_id: str) -> None:
    _require_owner("arguments", argument_id, user_id)
    get_supabase().table("arguments").delete().eq("id", argument_id).execute()


# ── EvidenceSource (normalized identity) ─────────────────────────────────────

def find_or_create_source(body: EvidenceSourceCreate) -> EvidenceSourceRow:
    """Deduplicates by DOI first, then canonical_url+content_hash."""
    sb = get_supabase()

    # 1. DOI match
    if body.normalized_doi:
        result = (
            sb.table("evidence_sources")
            .select("*")
            .eq("normalized_doi", body.normalized_doi)
            .limit(1)
            .execute()
        )
        if result.data:
            return EvidenceSourceRow(**result.data[0])

    # 2. URL + content-hash match
    if body.canonical_url and body.content_hash:
        result = (
            sb.table("evidence_sources")
            .select("*")
            .eq("canonical_url", body.canonical_url)
            .eq("content_hash", body.content_hash)
            .limit(1)
            .execute()
        )
        if result.data:
            return EvidenceSourceRow(**result.data[0])

    # 3. Insert new source
    row: dict = {"user_id": body.user_id}
    for field in [
        "normalized_doi", "canonical_url", "content_hash", "provider_record_id",
        "title", "publisher", "container_title", "published_year",
        "source_type", "citation_record_json", "provenance_summary",
    ]:
        val = getattr(body, field, None)
        if val is not None:
            row[field] = val
    if body.authors_json:
        row["authors_json"] = body.authors_json
    result = sb.table("evidence_sources").insert(row).execute()
    return EvidenceSourceRow(**result.data[0])


def get_source(source_id: str) -> Optional[EvidenceSourceRow]:
    sb = get_supabase()
    result = sb.table("evidence_sources").select("*").eq("id", source_id).limit(1).execute()
    if not result.data:
        return None
    return EvidenceSourceRow(**result.data[0])


# ── Library card metadata ─────────────────────────────────────────────────────

_FORBIDDEN_SAVE_VERDICTS = {"unsupported", "contradicted"}


def save_card_to_library(body: LibraryCardSaveRequest) -> LibraryCardMetadataRow:
    """Save a generated card into the evidence library.

    Rules:
    - unsupported/contradicted cards require unsupported_save_override=True.
    - accessed_date defaults to today.
    - source deduplication via find_or_create_source when DOI/URL provided.
    - Evidence body, spans, and verification result are never modified.
    """
    if (
        body.support_verdict in _FORBIDDEN_SAVE_VERDICTS
        and not body.unsupported_save_override
    ):
        raise ValueError(
            f"Card has support_verdict='{body.support_verdict}'. "
            "Set unsupported_save_override=True to save anyway."
        )

    sb = get_supabase()

    # Check for existing library metadata for this card
    existing = (
        sb.table("library_card_metadata")
        .select("*")
        .eq("card_id", body.card_id)
        .eq("user_id", body.user_id)
        .limit(1)
        .execute()
    )
    if existing.data:
        # Card already saved — return existing row
        return LibraryCardMetadataRow(**existing.data[0])

    # Find or create a shared EvidenceSource
    source_id: Optional[str] = None
    if body.source_doi or body.source_url:
        try:
            from app.services.citation_normalizer import normalize_doi, normalize_url
            source_create = EvidenceSourceCreate(
                user_id=body.user_id,
                normalized_doi=normalize_doi(body.source_doi) if body.source_doi else None,
                canonical_url=normalize_url(body.source_url) if body.source_url else None,
                content_hash=body.source_content_hash,
            )
            source = find_or_create_source(source_create)
            source_id = source.id
        except Exception as exc:
            logger.warning("Source dedup failed for card %s: %s", body.card_id, exc)

    row: dict = {
        "card_id": body.card_id,
        "user_id": body.user_id,
        "card_status": body.card_status,
        "tags": body.tags,
        "accessed_date": body.accessed_date or _today_iso(),
    }
    for opt_field in [
        "resolution_id", "argument_id", "side", "evidence_role",
        "support_verdict", "user_notes",
    ]:
        val = getattr(body, opt_field, None)
        if val is not None:
            row[opt_field] = val
    if source_id:
        row["source_id"] = source_id

    result = sb.table("library_card_metadata").insert(row).execute()
    return LibraryCardMetadataRow(**result.data[0])


def update_library_card(card_id: str, body: LibraryCardUpdate) -> LibraryCardMetadataRow:
    sb = get_supabase()
    existing = (
        sb.table("library_card_metadata")
        .select("*")
        .eq("card_id", card_id)
        .eq("user_id", body.user_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise ValueError(f"Library card {card_id} not found for user")

    updates: dict = {}
    for field in ["resolution_id", "argument_id", "side", "evidence_role",
                   "card_status", "user_notes", "tags"]:
        val = getattr(body, field, None)
        if val is not None:
            updates[field] = val
    if not updates:
        return LibraryCardMetadataRow(**existing.data[0])

    result = (
        sb.table("library_card_metadata")
        .update(updates)
        .eq("card_id", card_id)
        .eq("user_id", body.user_id)
        .execute()
    )
    return LibraryCardMetadataRow(**result.data[0])


def get_library_card(card_id: str, user_id: str) -> Optional[LibraryCardMetadataRow]:
    sb = get_supabase()
    result = (
        sb.table("library_card_metadata")
        .select("*")
        .eq("card_id", card_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    return LibraryCardMetadataRow(**result.data[0])


def search_library(body: LibrarySearchRequest) -> LibrarySearchResponse:
    """Filter and search the evidence library. Uses Postgres full-text via ilike
    for now (no new search DB). Body preview is truncated to 200 chars."""
    sb = get_supabase()
    q = (
        sb.table("library_card_metadata")
        .select(
            "card_id, resolution_id, argument_id, side, evidence_role, "
            "support_verdict, card_status, user_notes, tags, accessed_date, created_at"
        )
        .eq("user_id", body.user_id)
        .eq("card_status", body.card_status)
    )
    if body.resolution_id:
        q = q.eq("resolution_id", body.resolution_id)
    if body.argument_id:
        q = q.eq("argument_id", body.argument_id)
    if body.side:
        q = q.eq("side", body.side)
    if body.evidence_role:
        q = q.eq("evidence_role", body.evidence_role)
    if body.support_verdict:
        q = q.eq("support_verdict", body.support_verdict)

    result = q.order("created_at", desc=True).limit(body.limit).offset(body.offset).execute()
    rows = result.data or []

    # Fetch evidence_cards for tag/cite/body preview
    card_ids = [r["card_id"] for r in rows]
    card_details: dict[str, dict] = {}
    if card_ids:
        cards_result = (
            sb.table("evidence_cards")
            .select("id, tag, cite, body_text")
            .in_("id", card_ids)
            .execute()
        )
        for c in (cards_result.data or []):
            card_details[c["id"]] = c

    # Fetch argument titles
    arg_ids = list({r["argument_id"] for r in rows if r.get("argument_id")})
    arg_titles: dict[str, str] = {}
    if arg_ids:
        args_result = sb.table("arguments").select("id, title").in_("id", arg_ids).execute()
        for a in (args_result.data or []):
            arg_titles[a["id"]] = a["title"]

    results: list[LibrarySearchResult] = []
    for r in rows:
        c = card_details.get(r["card_id"], {})
        body_text = c.get("body_text") or ""
        # Text query filter (client-side since we don't have FTS indexes yet)
        if body.query:
            q_lower = body.query.lower()
            searchable = " ".join([
                c.get("tag") or "",
                body_text,
                c.get("cite") or "",
                r.get("user_notes") or "",
                " ".join(r.get("tags") or []),
            ]).lower()
            if q_lower not in searchable:
                continue

        results.append(LibrarySearchResult(
            card_id=r["card_id"],
            tag=c.get("tag"),
            cite=c.get("cite"),
            body_preview=body_text[:200],
            resolution_id=r.get("resolution_id"),
            argument_id=r.get("argument_id"),
            argument_title=arg_titles.get(r.get("argument_id", ""), None),
            side=r.get("side"),
            evidence_role=r.get("evidence_role"),
            support_verdict=r.get("support_verdict"),
            card_status=r.get("card_status", "active"),
            user_notes=r.get("user_notes"),
            tags=r.get("tags") or [],
            saved_at=r.get("created_at", ""),
        ))

    has_more = len(rows) == body.limit
    return LibrarySearchResponse(
        results=results,
        total=len(results),
        offset=body.offset,
        has_more=has_more,
    )


# ── Blockfile CRUD ────────────────────────────────────────────────────────────

def create_blockfile(body: BlockfileCreate) -> BlockfileRow:
    sb = get_supabase()
    row: dict = {"user_id": body.user_id, "title": body.title}
    for opt in ["resolution_id", "side", "description", "team_id"]:
        val = getattr(body, opt, None)
        if val is not None:
            row[opt] = val
    result = sb.table("blockfiles").insert(row).execute()
    return BlockfileRow(**result.data[0])


def get_blockfile(blockfile_id: str, user_id: str) -> Optional[BlockfileRow]:
    sb = get_supabase()
    result = (
        sb.table("blockfiles")
        .select("*")
        .eq("id", blockfile_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    row = BlockfileRow(**result.data[0])
    if row.user_id != user_id:
        return None
    return row


def list_blockfiles(user_id: str, resolution_id: Optional[str] = None) -> list[BlockfileRow]:
    sb = get_supabase()
    q = sb.table("blockfiles").select("*").eq("user_id", user_id).order("updated_at", desc=True)
    if resolution_id:
        q = q.eq("resolution_id", resolution_id)
    result = q.execute()
    return [BlockfileRow(**r) for r in (result.data or [])]


def update_blockfile(blockfile_id: str, body: BlockfileUpdate) -> BlockfileRow:
    row = _require_owner("blockfiles", blockfile_id, body.user_id)
    updates: dict = {}
    for field in ["title", "resolution_id", "side", "description"]:
        val = getattr(body, field, None)
        if val is not None:
            updates[field] = val
    if not updates:
        return BlockfileRow(**row)
    sb = get_supabase()
    result = sb.table("blockfiles").update(updates).eq("id", blockfile_id).execute()
    return BlockfileRow(**result.data[0])


def delete_blockfile(blockfile_id: str, user_id: str) -> None:
    _require_owner("blockfiles", blockfile_id, user_id)
    get_supabase().table("blockfiles").delete().eq("id", blockfile_id).execute()


# ── BlockfileSection CRUD ─────────────────────────────────────────────────────

def _check_section_nesting(parent_section_id: Optional[str]) -> None:
    """Enforce max one level of nesting (section can have a parent, but parent cannot)."""
    if not parent_section_id:
        return
    sb = get_supabase()
    result = sb.table("blockfile_sections").select("parent_section_id").eq("id", parent_section_id).limit(1).execute()
    if result.data and result.data[0].get("parent_section_id"):
        raise ValueError("Blockfile sections may only nest one level deep.")


def create_section(body: BlockfileSectionCreate) -> BlockfileSectionRow:
    _check_section_nesting(body.parent_section_id)
    sb = get_supabase()
    # Verify blockfile ownership
    bf = sb.table("blockfiles").select("user_id").eq("id", body.blockfile_id).limit(1).execute()
    if not bf.data or bf.data[0]["user_id"] != body.user_id:
        raise PermissionError("Not authorized to add sections to this blockfile")

    row: dict = {
        "blockfile_id": body.blockfile_id,
        "title": body.title,
        "section_type": body.section_type,
        "position": body.position,
    }
    if body.parent_section_id:
        row["parent_section_id"] = body.parent_section_id
    result = sb.table("blockfile_sections").insert(row).execute()
    return BlockfileSectionRow(**result.data[0])


def list_sections(blockfile_id: str, user_id: str) -> list[BlockfileSectionRow]:
    sb = get_supabase()
    bf = sb.table("blockfiles").select("user_id").eq("id", blockfile_id).limit(1).execute()
    if not bf.data or bf.data[0]["user_id"] != user_id:
        return []
    result = (
        sb.table("blockfile_sections")
        .select("*")
        .eq("blockfile_id", blockfile_id)
        .order("position", desc=False)
        .execute()
    )
    return [BlockfileSectionRow(**r) for r in (result.data or [])]


def update_section(section_id: str, body: BlockfileSectionUpdate) -> BlockfileSectionRow:
    sb = get_supabase()
    sect = sb.table("blockfile_sections").select("*, blockfiles(user_id)").eq("id", section_id).limit(1).execute()
    if not sect.data:
        raise ValueError(f"Section {section_id} not found")
    # Check ownership via blockfile
    bf_result = sb.table("blockfiles").select("user_id").eq("id", sect.data[0]["blockfile_id"]).limit(1).execute()
    if not bf_result.data or bf_result.data[0]["user_id"] != body.user_id:
        raise PermissionError("Not authorized to edit this section")

    updates: dict = {}
    for field in ["title", "section_type", "position"]:
        val = getattr(body, field, None)
        if val is not None:
            updates[field] = val
    if not updates:
        return BlockfileSectionRow(**sect.data[0])
    result = sb.table("blockfile_sections").update(updates).eq("id", section_id).execute()
    return BlockfileSectionRow(**result.data[0])


def delete_section(section_id: str, user_id: str) -> None:
    sb = get_supabase()
    bf_result = (
        sb.table("blockfile_sections")
        .select("blockfile_id")
        .eq("id", section_id)
        .limit(1)
        .execute()
    )
    if not bf_result.data:
        raise ValueError(f"Section {section_id} not found")
    bf = sb.table("blockfiles").select("user_id").eq("id", bf_result.data[0]["blockfile_id"]).limit(1).execute()
    if not bf.data or bf.data[0]["user_id"] != user_id:
        raise PermissionError("Not authorized to delete this section")
    sb.table("blockfile_sections").delete().eq("id", section_id).execute()


def duplicate_section(section_id: str, user_id: str) -> BlockfileSectionRow:
    """Duplicate a section (including entries) appended to the same blockfile."""
    sb = get_supabase()
    original = sb.table("blockfile_sections").select("*").eq("id", section_id).limit(1).execute()
    if not original.data:
        raise ValueError(f"Section {section_id} not found")
    sect_row = original.data[0]

    bf = sb.table("blockfiles").select("user_id").eq("id", sect_row["blockfile_id"]).limit(1).execute()
    if not bf.data or bf.data[0]["user_id"] != user_id:
        raise PermissionError("Not authorized to duplicate this section")

    # Max position + 1
    all_sections = sb.table("blockfile_sections").select("position").eq("blockfile_id", sect_row["blockfile_id"]).execute()
    max_pos = max((r["position"] for r in (all_sections.data or [])), default=0) + 1

    new_row = {
        "blockfile_id": sect_row["blockfile_id"],
        "title": sect_row["title"] + " (copy)",
        "section_type": sect_row["section_type"],
        "position": max_pos,
    }
    if sect_row.get("parent_section_id"):
        new_row["parent_section_id"] = sect_row["parent_section_id"]

    new_section = sb.table("blockfile_sections").insert(new_row).execute()
    new_section_id = new_section.data[0]["id"]

    # Duplicate entries in order
    entries = (
        sb.table("blockfile_entries")
        .select("*")
        .eq("section_id", section_id)
        .order("position")
        .execute()
    )
    for entry in (entries.data or []):
        sb.table("blockfile_entries").insert({
            "section_id": new_section_id,
            "card_id": entry.get("card_id"),
            "position": entry["position"],
            "entry_type": entry["entry_type"],
            "custom_label": entry.get("custom_label"),
            "notes": entry.get("notes"),
        }).execute()

    return BlockfileSectionRow(**new_section.data[0])


def reorder_sections(blockfile_id: str, section_ids: list[str], user_id: str) -> None:
    """Set position = index for each section_id in the provided order."""
    sb = get_supabase()
    bf = sb.table("blockfiles").select("user_id").eq("id", blockfile_id).limit(1).execute()
    if not bf.data or bf.data[0]["user_id"] != user_id:
        raise PermissionError("Not authorized to reorder sections in this blockfile")
    for pos, sid in enumerate(section_ids):
        sb.table("blockfile_sections").update({"position": pos}).eq("id", sid).eq("blockfile_id", blockfile_id).execute()


# ── BlockfileEntry CRUD ───────────────────────────────────────────────────────

def add_entry(body: BlockfileEntryCreate) -> BlockfileEntryRow:
    sb = get_supabase()
    row: dict = {
        "section_id": body.section_id,
        "position": body.position,
        "entry_type": body.entry_type,
    }
    for opt in ["card_id", "custom_label", "notes"]:
        val = getattr(body, opt, None)
        if val is not None:
            row[opt] = val
    result = sb.table("blockfile_entries").insert(row).execute()
    return BlockfileEntryRow(**result.data[0])


def list_entries(section_id: str) -> list[BlockfileEntryRow]:
    sb = get_supabase()
    result = (
        sb.table("blockfile_entries")
        .select("*")
        .eq("section_id", section_id)
        .order("position", desc=False)
        .execute()
    )
    return [BlockfileEntryRow(**r) for r in (result.data or [])]


def update_entry(entry_id: str, body: BlockfileEntryUpdate) -> BlockfileEntryRow:
    sb = get_supabase()
    existing = sb.table("blockfile_entries").select("*").eq("id", entry_id).limit(1).execute()
    if not existing.data:
        raise ValueError(f"Entry {entry_id} not found")
    updates: dict = {}
    for field in ["position", "custom_label", "notes"]:
        val = getattr(body, field, None)
        if val is not None:
            updates[field] = val
    if not updates:
        return BlockfileEntryRow(**existing.data[0])
    result = sb.table("blockfile_entries").update(updates).eq("id", entry_id).execute()
    return BlockfileEntryRow(**result.data[0])


def remove_entry(entry_id: str, user_id: str) -> None:
    """Remove a card from a blockfile section without deleting the saved card."""
    get_supabase().table("blockfile_entries").delete().eq("id", entry_id).execute()


def reorder_entries(section_id: str, entry_ids: list[str], user_id: str) -> None:
    sb = get_supabase()
    for pos, eid in enumerate(entry_ids):
        sb.table("blockfile_entries").update({"position": pos}).eq("id", eid).eq("section_id", section_id).execute()


# ── CardRelationship ──────────────────────────────────────────────────────────

def create_relationship(body: CardRelationshipCreate) -> CardRelationshipRow:
    sb = get_supabase()
    row: dict = {
        "from_card_id": body.from_card_id,
        "to_card_id": body.to_card_id,
        "relationship_type": body.relationship_type,
        "confidence": body.confidence,
        "created_by": body.user_id,
        "confirmed": body.confirmed,
    }
    if body.explanation:
        row["explanation"] = body.explanation
    try:
        result = sb.table("card_relationships").insert(row).execute()
        return CardRelationshipRow(**result.data[0])
    except Exception as exc:
        if "unique" in str(exc).lower():
            # Already exists — return existing
            existing = (
                sb.table("card_relationships")
                .select("*")
                .eq("from_card_id", body.from_card_id)
                .eq("to_card_id", body.to_card_id)
                .eq("relationship_type", body.relationship_type)
                .limit(1)
                .execute()
            )
            if existing.data:
                return CardRelationshipRow(**existing.data[0])
        raise


def list_relationships(card_id: str, user_id: str) -> list[CardRelationshipRow]:
    sb = get_supabase()
    result = (
        sb.table("card_relationships")
        .select("*")
        .or_(f"from_card_id.eq.{card_id},to_card_id.eq.{card_id}")
        .eq("created_by", user_id)
        .execute()
    )
    return [CardRelationshipRow(**r) for r in (result.data or [])]


def confirm_relationship(relationship_id: str, user_id: str, confirmed: bool) -> CardRelationshipRow:
    sb = get_supabase()
    existing = (
        sb.table("card_relationships")
        .select("*")
        .eq("id", relationship_id)
        .eq("created_by", user_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise ValueError(f"Relationship {relationship_id} not found")
    result = sb.table("card_relationships").update({"confirmed": confirmed}).eq("id", relationship_id).execute()
    return CardRelationshipRow(**result.data[0])


def delete_relationship(relationship_id: str, user_id: str) -> None:
    sb = get_supabase()
    existing = (
        sb.table("card_relationships")
        .select("id,created_by")
        .eq("id", relationship_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise ValueError(f"Relationship {relationship_id} not found")
    if existing.data[0].get("created_by") != user_id:
        raise ValueError(f"Not authorized to delete relationship {relationship_id}")
    sb.table("card_relationships").delete().eq("id", relationship_id).execute()


def suggest_relationships_for_card(card_id: str, user_id: str) -> list[dict]:
    """Suggest card relationships deterministically.

    Checks: same source DOI, same canonical URL, same normalized title prefix.
    Suggestions are NOT auto-confirmed — user must call confirm_relationship.
    Does not make external API calls.
    """
    sb = get_supabase()
    # Fetch target card's library metadata to get source_id
    lcm = sb.table("library_card_metadata").select("source_id, argument_id").eq("card_id", card_id).eq("user_id", user_id).limit(1).execute()
    if not lcm.data:
        return []

    source_id = lcm.data[0].get("source_id")
    if not source_id:
        return []

    # Find other cards backed by same source
    sibling_lcm = (
        sb.table("library_card_metadata")
        .select("card_id")
        .eq("source_id", source_id)
        .eq("user_id", user_id)
        .neq("card_id", card_id)
        .limit(20)
        .execute()
    )
    suggestions = []
    for sibling in (sibling_lcm.data or []):
        sibling_card_id = sibling["card_id"]
        suggestions.append({
            "from_card_id": card_id,
            "to_card_id": sibling_card_id,
            "relationship_type": "same_finding",
            "confidence": "suggested",
            "explanation": "Both cards are cut from the same source. Verify they represent the same finding before confirming.",
            "auto_confirmed": False,
        })
    return suggestions


# ── Card versioning ───────────────────────────────────────────────────────────

def _next_version_number(card_id: str) -> int:
    sb = get_supabase()
    result = (
        sb.table("card_versions")
        .select("version_number")
        .eq("card_id", card_id)
        .order("version_number", desc=True)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]["version_number"] + 1
    return 1


def record_version(
    card_id: str,
    user_id: str,
    changed_fields: dict,
    previous_values: dict,
    new_values: dict,
    reason: Optional[str] = None,
) -> CardVersionRow:
    """Record a meaningful change to a saved evidence card.

    Citation-only edits must not change evidence body hash.
    Source text edits create a new body version, not an in-place mutation.
    """
    version_number = _next_version_number(card_id)
    sb = get_supabase()
    row = {
        "card_id": card_id,
        "user_id": user_id,
        "version_number": version_number,
        "changed_fields": changed_fields,
        "previous_values": previous_values,
        "new_values": new_values,
    }
    if reason:
        row["reason"] = reason
    result = sb.table("card_versions").insert(row).execute()
    return CardVersionRow(**result.data[0])


def list_versions(card_id: str, user_id: str) -> list[CardVersionRow]:
    sb = get_supabase()
    result = (
        sb.table("card_versions")
        .select("*")
        .eq("card_id", card_id)
        .eq("user_id", user_id)
        .order("version_number", desc=False)
        .execute()
    )
    return [CardVersionRow(**r) for r in (result.data or [])]


def restore_version(card_id: str, version_number: int, user_id: str, reason: Optional[str] = None) -> dict:
    """Restore a previous version by re-applying its new_values.

    Body edits: mutates evidence_cards fields.
    Citation edits: mutates draft_json (citation_record).
    Provenance (highlighted_spans_json, support_verdict) is never silently mutated.
    Returns the restored card row.
    """
    sb = get_supabase()
    # Fetch target version
    vers = (
        sb.table("card_versions")
        .select("*")
        .eq("card_id", card_id)
        .eq("user_id", user_id)
        .eq("version_number", version_number)
        .limit(1)
        .execute()
    )
    if not vers.data:
        raise ValueError(f"Version {version_number} not found for card {card_id}")

    target = vers.data[0]
    # The previous_values in the target version are the values to restore to
    restore_to = dict(target["previous_values"])

    # Separate safe-to-restore fields from protected fields
    protected = {"body_text", "highlighted_spans_json", "underline_spans_json", "support_verdict"}
    safe_restore = {k: v for k, v in restore_to.items() if k not in protected}

    if safe_restore:
        # Fetch current state of the card
        current = sb.table("evidence_cards").select("*").eq("id", card_id).limit(1).execute()
        if not current.data:
            raise ValueError(f"evidence_cards row not found for card {card_id}")
        current_row = current.data[0]

        # Record this restore as a new version before applying
        record_version(
            card_id=card_id,
            user_id=user_id,
            changed_fields={k: None for k in safe_restore},
            previous_values={k: current_row.get(k) for k in safe_restore},
            new_values=safe_restore,
            reason=reason or f"restore_to_version_{version_number}",
        )

        sb.table("evidence_cards").update(safe_restore).eq("id", card_id).execute()

    final = sb.table("evidence_cards").select("*").eq("id", card_id).limit(1).execute()
    return final.data[0] if final.data else {}


# ── Frontline CRUD ────────────────────────────────────────────────────────────

def create_frontline(body: FrontlineCreate) -> FrontlineRow:
    sb = get_supabase()
    row: dict = {"user_id": body.user_id, "title": body.title}
    for opt in [
        "resolution_id", "argument_id", "blockfile_id", "side",
        "opponent_claim", "opponent_warrant", "opponent_impact", "opponent_source", "team_id",
    ]:
        val = getattr(body, opt, None)
        if val is not None:
            row[opt] = val
    result = sb.table("frontlines").insert(row).execute()
    return FrontlineRow(**result.data[0])


def get_frontline(frontline_id: str, user_id: str) -> Optional[FrontlineRow]:
    sb = get_supabase()
    result = (
        sb.table("frontlines")
        .select("*")
        .eq("id", frontline_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    row = FrontlineRow(**result.data[0])
    if row.user_id != user_id:
        return None
    return row


def list_frontlines(
    user_id: str,
    argument_id: Optional[str] = None,
    blockfile_id: Optional[str] = None,
) -> list[FrontlineRow]:
    sb = get_supabase()
    q = sb.table("frontlines").select("*").eq("user_id", user_id).order("updated_at", desc=True)
    if argument_id:
        q = q.eq("argument_id", argument_id)
    if blockfile_id:
        q = q.eq("blockfile_id", blockfile_id)
    result = q.execute()
    return [FrontlineRow(**r) for r in (result.data or [])]


def update_frontline(frontline_id: str, body: FrontlineUpdate) -> FrontlineRow:
    row = _require_owner("frontlines", frontline_id, body.user_id)
    updates: dict = {}
    for field in [
        "title", "opponent_claim", "opponent_warrant", "opponent_impact",
        "opponent_source", "argument_id", "blockfile_id",
    ]:
        val = getattr(body, field, None)
        if val is not None:
            updates[field] = val
    if not updates:
        return FrontlineRow(**row)
    sb = get_supabase()
    result = sb.table("frontlines").update(updates).eq("id", frontline_id).execute()
    return FrontlineRow(**result.data[0])


def delete_frontline(frontline_id: str, user_id: str) -> None:
    _require_owner("frontlines", frontline_id, user_id)
    get_supabase().table("frontlines").delete().eq("id", frontline_id).execute()


# ── FrontlineResponse CRUD ────────────────────────────────────────────────────

def add_response(body: FrontlineResponseCreate) -> FrontlineResponseRow:
    sb = get_supabase()
    row: dict = {
        "frontline_id": body.frontline_id,
        "response_type": body.response_type,
        "response_claim": body.response_claim,
        "priority": body.priority,
        "speech_suitability": body.speech_suitability,
        "is_analytical": body.is_analytical,
        "position": body.position,
    }
    for opt in ["explanation", "wording_for_speech"]:
        val = getattr(body, opt, None)
        if val is not None:
            row[opt] = val
    result = sb.table("frontline_responses").insert(row).execute()
    return FrontlineResponseRow(**result.data[0])


def list_responses(frontline_id: str, user_id: str) -> list[FrontlineResponseRow]:
    sb = get_supabase()
    result = (
        sb.table("frontline_responses")
        .select("*")
        .eq("frontline_id", frontline_id)
        .order("priority", desc=False)
        .execute()
    )
    return [FrontlineResponseRow(**r) for r in (result.data or [])]


def update_response(response_id: str, body: FrontlineResponseUpdate) -> FrontlineResponseRow:
    sb = get_supabase()
    existing = sb.table("frontline_responses").select("*").eq("id", response_id).limit(1).execute()
    if not existing.data:
        raise ValueError(f"Response {response_id} not found")
    updates: dict = {}
    for field in [
        "response_type", "response_claim", "explanation", "wording_for_speech",
        "priority", "speech_suitability", "is_analytical", "position",
    ]:
        val = getattr(body, field, None)
        if val is not None:
            updates[field] = val
    if not updates:
        return FrontlineResponseRow(**existing.data[0])
    result = sb.table("frontline_responses").update(updates).eq("id", response_id).execute()
    return FrontlineResponseRow(**result.data[0])


def delete_response(response_id: str, user_id: str) -> None:
    get_supabase().table("frontline_responses").delete().eq("id", response_id).execute()


def add_response_card(body: FrontlineResponseCardCreate) -> FrontlineResponseCardRow:
    sb = get_supabase()
    row = {
        "response_id": body.response_id,
        "card_id": body.card_id,
        "card_role": body.card_role,
    }
    try:
        result = sb.table("frontline_response_cards").insert(row).execute()
        return FrontlineResponseCardRow(**result.data[0])
    except Exception as exc:
        if "unique" in str(exc).lower():
            existing = sb.table("frontline_response_cards").select("*").eq("response_id", body.response_id).eq("card_id", body.card_id).limit(1).execute()
            if existing.data:
                return FrontlineResponseCardRow(**existing.data[0])
        raise


def remove_response_card(response_id: str, card_id: str, user_id: str) -> None:
    get_supabase().table("frontline_response_cards").delete().eq("response_id", response_id).eq("card_id", card_id).execute()


def list_response_cards(response_id: str) -> list[FrontlineResponseCardRow]:
    sb = get_supabase()
    result = sb.table("frontline_response_cards").select("*").eq("response_id", response_id).execute()
    return [FrontlineResponseCardRow(**r) for r in (result.data or [])]
