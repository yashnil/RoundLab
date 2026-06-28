"""Evidence Library API (Pass 13).

Endpoints follow the existing Dissio pattern: no auth middleware — user_id
is passed in request bodies and validated against table rows before writes.

Prefix: /library

Resolutions:  POST/GET /resolutions, GET/PATCH/DELETE /resolutions/{id}
Arguments:    POST/GET /arguments, GET/PATCH/DELETE /arguments/{id}
Sources:      POST /sources (find-or-create)
Cards:        POST /cards/save, GET/PATCH /cards/{card_id}
              GET /cards/{card_id}/versions, POST /cards/{card_id}/versions/{n}/restore
              GET /cards/{card_id}/relationships, POST /cards/{card_id}/relationships
              PATCH/DELETE /relationships/{id}
              GET /cards/{card_id}/suggest-relationships
Blockfiles:   POST/GET /blockfiles, GET/PATCH/DELETE /blockfiles/{id}
Sections:     POST /blockfiles/{id}/sections, GET /blockfiles/{id}/sections
              PATCH/DELETE /sections/{id}
              POST /sections/{id}/duplicate
              POST /sections/{id}/reorder-entries
              POST /blockfiles/{id}/reorder-sections
Entries:      POST /sections/{id}/entries, GET /sections/{id}/entries
              PATCH/DELETE /entries/{id}
Frontlines:   POST/GET /frontlines, GET/PATCH/DELETE /frontlines/{id}
Responses:    POST /frontlines/{id}/responses, PATCH/DELETE /responses/{id}
              POST /responses/{id}/cards, DELETE /responses/{id}/cards/{card_id}
Search:       POST /search
Export:       POST /export/blockfile, POST /export/frontline
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.models.evidence_library import (
    ArgumentCreate, ArgumentUpdate,
    BlockfileCreate, BlockfileEntryCreate, BlockfileEntryUpdate,
    BlockfileCreate, BlockfileSectionCreate, BlockfileSectionUpdate,
    BlockfileUpdate,
    CardRelationshipConfirm, CardRelationshipCreate,
    EvidenceSourceCreate,
    FrontlineCreate, FrontlineResponseCardCreate, FrontlineResponseCreate,
    FrontlineResponseUpdate, FrontlineUpdate,
    LibraryCardSaveRequest, LibraryCardUpdate,
    LibrarySearchRequest,
    ReorderEntriesRequest, ReorderSectionsRequest, DuplicateSectionRequest,
    ResolutionCreate, ResolutionUpdate,
    RestoreVersionRequest,
    BlockfileExportRequest, FrontlineExportRequest,
    RelatedEvidenceSearchRequest,
)
import app.services.evidence_library_service as svc

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/library", tags=["evidence_library"])


def _http(exc: Exception) -> HTTPException:
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=404, detail=str(exc))
    logger.error("Evidence library error: %s", exc)
    return HTTPException(status_code=500, detail="Evidence library error.")


# ─── Resolutions ──────────────────────────────────────────────────────────────

@router.post("/resolutions")
async def create_resolution(body: ResolutionCreate):
    try:
        return svc.create_resolution(body).model_dump()
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/resolutions")
async def list_resolutions(user_id: str = Query(...), active_only: bool = False):
    return [r.model_dump() for r in svc.list_resolutions(user_id, active_only)]


@router.get("/resolutions/{resolution_id}")
async def get_resolution(resolution_id: str, user_id: str = Query(...)):
    row = svc.get_resolution(resolution_id, user_id)
    if not row:
        raise HTTPException(status_code=404, detail="Resolution not found")
    return row.model_dump()


@router.patch("/resolutions/{resolution_id}")
async def update_resolution(resolution_id: str, body: ResolutionUpdate):
    try:
        return svc.update_resolution(resolution_id, body).model_dump()
    except Exception as exc:
        raise _http(exc) from exc


@router.delete("/resolutions/{resolution_id}")
async def archive_resolution(resolution_id: str, user_id: str = Query(...)):
    try:
        return svc.archive_resolution(resolution_id, user_id).model_dump()
    except Exception as exc:
        raise _http(exc) from exc


# ─── Arguments ────────────────────────────────────────────────────────────────

@router.post("/arguments")
async def create_argument(body: ArgumentCreate):
    try:
        return svc.create_argument(body).model_dump()
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/arguments")
async def list_arguments(
    user_id: str = Query(...),
    resolution_id: Optional[str] = Query(None),
    side: Optional[str] = Query(None),
):
    return [a.model_dump() for a in svc.list_arguments(user_id, resolution_id, side)]


@router.get("/arguments/{argument_id}")
async def get_argument(argument_id: str, user_id: str = Query(...)):
    row = svc.get_argument(argument_id, user_id)
    if not row:
        raise HTTPException(status_code=404, detail="Argument not found")
    return row.model_dump()


@router.patch("/arguments/{argument_id}")
async def update_argument(argument_id: str, body: ArgumentUpdate):
    try:
        return svc.update_argument(argument_id, body).model_dump()
    except Exception as exc:
        raise _http(exc) from exc


@router.delete("/arguments/{argument_id}")
async def delete_argument(argument_id: str, user_id: str = Query(...)):
    try:
        svc.delete_argument(argument_id, user_id)
        return {"ok": True}
    except Exception as exc:
        raise _http(exc) from exc


# ─── Evidence Sources ─────────────────────────────────────────────────────────

@router.post("/sources")
async def find_or_create_source(body: EvidenceSourceCreate):
    try:
        return svc.find_or_create_source(body).model_dump()
    except Exception as exc:
        raise _http(exc) from exc


# ─── Library Card Metadata ────────────────────────────────────────────────────

@router.post("/cards/save")
async def save_card(body: LibraryCardSaveRequest):
    try:
        return svc.save_card_to_library(body).model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/cards/{card_id}")
async def get_library_card(card_id: str, user_id: str = Query(...)):
    row = svc.get_library_card(card_id, user_id)
    if not row:
        raise HTTPException(status_code=404, detail="Card not in library")
    return row.model_dump()


@router.patch("/cards/{card_id}")
async def update_library_card(card_id: str, body: LibraryCardUpdate):
    try:
        return svc.update_library_card(card_id, body).model_dump()
    except Exception as exc:
        raise _http(exc) from exc


# ─── Card Versions ────────────────────────────────────────────────────────────

@router.get("/cards/{card_id}/versions")
async def list_card_versions(card_id: str, user_id: str = Query(...)):
    return [v.model_dump() for v in svc.list_versions(card_id, user_id)]


@router.post("/cards/{card_id}/versions/{version_number}/restore")
async def restore_card_version(card_id: str, version_number: int, body: RestoreVersionRequest):
    try:
        return svc.restore_version(card_id, version_number, body.user_id, body.reason)
    except Exception as exc:
        raise _http(exc) from exc


# ─── Card Relationships ───────────────────────────────────────────────────────

@router.get("/cards/{card_id}/relationships")
async def list_card_relationships(card_id: str, user_id: str = Query(...)):
    return [r.model_dump() for r in svc.list_relationships(card_id, user_id)]


@router.post("/cards/{card_id}/relationships")
async def create_relationship(card_id: str, body: CardRelationshipCreate):
    try:
        return svc.create_relationship(body).model_dump()
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/cards/{card_id}/suggest-relationships")
async def suggest_relationships(card_id: str, user_id: str = Query(...)):
    return svc.suggest_relationships_for_card(card_id, user_id)


@router.patch("/relationships/{relationship_id}")
async def confirm_relationship(relationship_id: str, body: CardRelationshipConfirm):
    try:
        return svc.confirm_relationship(relationship_id, body.user_id, body.confirmed).model_dump()
    except Exception as exc:
        raise _http(exc) from exc


@router.delete("/relationships/{relationship_id}")
async def delete_relationship(relationship_id: str, user_id: str = Query(...)):
    try:
        svc.delete_relationship(relationship_id, user_id)
        return {"ok": True}
    except Exception as exc:
        raise _http(exc) from exc


# ─── Blockfiles ───────────────────────────────────────────────────────────────

@router.post("/blockfiles")
async def create_blockfile(body: BlockfileCreate):
    try:
        return svc.create_blockfile(body).model_dump()
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/blockfiles")
async def list_blockfiles(
    user_id: str = Query(...),
    resolution_id: Optional[str] = Query(None),
):
    return [b.model_dump() for b in svc.list_blockfiles(user_id, resolution_id)]


@router.get("/blockfiles/{blockfile_id}")
async def get_blockfile(blockfile_id: str, user_id: str = Query(...)):
    row = svc.get_blockfile(blockfile_id, user_id)
    if not row:
        raise HTTPException(status_code=404, detail="Blockfile not found")
    return row.model_dump()


@router.patch("/blockfiles/{blockfile_id}")
async def update_blockfile(blockfile_id: str, body: BlockfileUpdate):
    try:
        return svc.update_blockfile(blockfile_id, body).model_dump()
    except Exception as exc:
        raise _http(exc) from exc


@router.delete("/blockfiles/{blockfile_id}")
async def delete_blockfile(blockfile_id: str, user_id: str = Query(...)):
    try:
        svc.delete_blockfile(blockfile_id, user_id)
        return {"ok": True}
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/blockfiles/{blockfile_id}/reorder-sections")
async def reorder_sections(blockfile_id: str, body: ReorderSectionsRequest):
    try:
        svc.reorder_sections(blockfile_id, body.section_ids, body.user_id)
        return {"ok": True}
    except Exception as exc:
        raise _http(exc) from exc


# ─── Blockfile Sections ───────────────────────────────────────────────────────

@router.post("/blockfiles/{blockfile_id}/sections")
async def create_section(blockfile_id: str, body: BlockfileSectionCreate):
    try:
        return svc.create_section(body).model_dump()
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/blockfiles/{blockfile_id}/sections")
async def list_sections(blockfile_id: str, user_id: str = Query(...)):
    return [s.model_dump() for s in svc.list_sections(blockfile_id, user_id)]


@router.patch("/sections/{section_id}")
async def update_section(section_id: str, body: BlockfileSectionUpdate):
    try:
        return svc.update_section(section_id, body).model_dump()
    except Exception as exc:
        raise _http(exc) from exc


@router.delete("/sections/{section_id}")
async def delete_section(section_id: str, user_id: str = Query(...)):
    try:
        svc.delete_section(section_id, user_id)
        return {"ok": True}
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/sections/{section_id}/duplicate")
async def duplicate_section(section_id: str, body: DuplicateSectionRequest):
    try:
        return svc.duplicate_section(section_id, body.user_id).model_dump()
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/sections/{section_id}/reorder-entries")
async def reorder_entries(section_id: str, body: ReorderEntriesRequest):
    try:
        svc.reorder_entries(section_id, body.entry_ids, body.user_id)
        return {"ok": True}
    except Exception as exc:
        raise _http(exc) from exc


# ─── Blockfile Entries ────────────────────────────────────────────────────────

@router.post("/sections/{section_id}/entries")
async def add_entry(section_id: str, body: BlockfileEntryCreate):
    try:
        return svc.add_entry(body).model_dump()
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/sections/{section_id}/entries")
async def list_entries(section_id: str):
    return [e.model_dump() for e in svc.list_entries(section_id)]


@router.patch("/entries/{entry_id}")
async def update_entry(entry_id: str, body: BlockfileEntryUpdate):
    try:
        return svc.update_entry(entry_id, body).model_dump()
    except Exception as exc:
        raise _http(exc) from exc


@router.delete("/entries/{entry_id}")
async def remove_entry(entry_id: str, user_id: str = Query(...)):
    try:
        svc.remove_entry(entry_id, user_id)
        return {"ok": True}
    except Exception as exc:
        raise _http(exc) from exc


# ─── Frontlines ───────────────────────────────────────────────────────────────

@router.post("/frontlines")
async def create_frontline(body: FrontlineCreate):
    try:
        return svc.create_frontline(body).model_dump()
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/frontlines")
async def list_frontlines(
    user_id: str = Query(...),
    argument_id: Optional[str] = Query(None),
    blockfile_id: Optional[str] = Query(None),
):
    return [f.model_dump() for f in svc.list_frontlines(user_id, argument_id, blockfile_id)]


@router.get("/frontlines/{frontline_id}")
async def get_frontline(frontline_id: str, user_id: str = Query(...)):
    row = svc.get_frontline(frontline_id, user_id)
    if not row:
        raise HTTPException(status_code=404, detail="Frontline not found")
    return row.model_dump()


@router.patch("/frontlines/{frontline_id}")
async def update_frontline(frontline_id: str, body: FrontlineUpdate):
    try:
        return svc.update_frontline(frontline_id, body).model_dump()
    except Exception as exc:
        raise _http(exc) from exc


@router.delete("/frontlines/{frontline_id}")
async def delete_frontline(frontline_id: str, user_id: str = Query(...)):
    try:
        svc.delete_frontline(frontline_id, user_id)
        return {"ok": True}
    except Exception as exc:
        raise _http(exc) from exc


# ─── Frontline Responses ──────────────────────────────────────────────────────

@router.post("/frontlines/{frontline_id}/responses")
async def add_response(frontline_id: str, body: FrontlineResponseCreate):
    try:
        return svc.add_response(body).model_dump()
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/frontlines/{frontline_id}/responses")
async def list_responses(frontline_id: str, user_id: str = Query(...)):
    return [r.model_dump() for r in svc.list_responses(frontline_id, user_id)]


@router.patch("/responses/{response_id}")
async def update_response(response_id: str, body: FrontlineResponseUpdate):
    try:
        return svc.update_response(response_id, body).model_dump()
    except Exception as exc:
        raise _http(exc) from exc


@router.delete("/responses/{response_id}")
async def delete_response(response_id: str, user_id: str = Query(...)):
    try:
        svc.delete_response(response_id, user_id)
        return {"ok": True}
    except Exception as exc:
        raise _http(exc) from exc


@router.post("/responses/{response_id}/cards")
async def add_response_card(response_id: str, body: FrontlineResponseCardCreate):
    try:
        return svc.add_response_card(body).model_dump()
    except Exception as exc:
        raise _http(exc) from exc


@router.delete("/responses/{response_id}/cards/{card_id}")
async def remove_response_card(response_id: str, card_id: str, user_id: str = Query(...)):
    try:
        svc.remove_response_card(response_id, card_id, user_id)
        return {"ok": True}
    except Exception as exc:
        raise _http(exc) from exc


@router.get("/responses/{response_id}/cards")
async def list_response_cards(response_id: str):
    return [c.model_dump() for c in svc.list_response_cards(response_id)]


# ─── Library Search ───────────────────────────────────────────────────────────

@router.post("/search")
async def search_library(body: LibrarySearchRequest):
    try:
        return svc.search_library(body).model_dump()
    except Exception as exc:
        raise _http(exc) from exc


# ─── Export ───────────────────────────────────────────────────────────────────

@router.post("/export/blockfile")
async def export_blockfile(body: BlockfileExportRequest):
    from app.services.library_export import (
        export_blockfile_json,
        export_blockfile_markdown,
        export_blockfile_docx,
    )
    from fastapi.responses import Response

    bf = svc.get_blockfile(body.blockfile_id, body.user_id)
    if not bf:
        raise HTTPException(status_code=404, detail="Blockfile not found")

    sections = svc.list_sections(body.blockfile_id, body.user_id)
    entries_by_section: dict[str, list] = {}
    for sect in sections:
        entries_by_section[sect.id] = svc.list_entries(sect.id)

    try:
        if body.format == "json":
            content = export_blockfile_json(bf, sections, entries_by_section)
            return Response(content=content, media_type="application/json",
                            headers={"Content-Disposition": f'attachment; filename="blockfile.json"'})
        elif body.format == "markdown":
            content = export_blockfile_markdown(bf, sections, entries_by_section)
            return Response(content=content, media_type="text/markdown",
                            headers={"Content-Disposition": f'attachment; filename="blockfile.md"'})
        elif body.format == "docx":
            content = export_blockfile_docx(bf, sections, entries_by_section)
            return Response(content=content,
                            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            headers={"Content-Disposition": f'attachment; filename="blockfile.docx"'})
    except Exception as exc:
        logger.error("Blockfile export failed: %s", exc)
        raise HTTPException(status_code=500, detail="Export failed.") from exc


@router.post("/export/frontline")
async def export_frontline(body: FrontlineExportRequest):
    from app.services.library_export import (
        export_frontline_json,
        export_frontline_markdown,
    )
    from fastapi.responses import Response

    fl = svc.get_frontline(body.frontline_id, body.user_id)
    if not fl:
        raise HTTPException(status_code=404, detail="Frontline not found")

    responses = svc.list_responses(body.frontline_id, body.user_id)
    response_cards = {r.id: svc.list_response_cards(r.id) for r in responses}

    try:
        if body.format == "json":
            content = export_frontline_json(fl, responses, response_cards)
            return Response(content=content, media_type="application/json",
                            headers={"Content-Disposition": f'attachment; filename="frontline.json"'})
        else:
            content = export_frontline_markdown(fl, responses, response_cards)
            return Response(content=content, media_type="text/markdown",
                            headers={"Content-Disposition": f'attachment; filename="frontline.md"'})
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Export failed.") from exc


# ─── Related Evidence Search ──────────────────────────────────────────────────

@router.post("/cards/{card_id}/find-related")
async def find_related_evidence(card_id: str, body: RelatedEvidenceSearchRequest):
    """Reuse existing query planner to find related evidence from a saved card.

    Passes card context (resolution, argument, claim, warrant) into claim_decomposition
    to generate targeted search queries. Does NOT replace the existing search flow.
    """
    from app.services.supabase_client import get_supabase
    from app.services.claim_decomposition import normalize_claim

    sb = get_supabase()

    # Fetch saved card text + metadata
    card_result = sb.table("evidence_cards").select("tag, cite, body_text").eq("id", card_id).limit(1).execute()
    if not card_result.data:
        raise HTTPException(status_code=404, detail="Card not found")
    card = card_result.data[0]

    # Fetch library context
    lcm = svc.get_library_card(card_id, body.user_id)
    context: dict = {
        "action": body.action,
        "card_tag": card.get("tag", ""),
        "card_cite": card.get("cite", ""),
        "resolution_id": lcm.resolution_id if lcm else None,
        "argument_id": lcm.argument_id if lcm else None,
        "side": lcm.side if lcm else None,
    }

    # Build search claim from action type
    action_map = {
        "find_stronger_source": f"Stronger source for: {card.get('tag', '')}",
        "find_newer_evidence": f"More recent evidence: {card.get('tag', '')}",
        "find_primary_source": f"Primary study for: {card.get('tag', '')}",
        "find_supporting": f"Additional support for: {card.get('tag', '')}",
        "find_counterevidence": f"Counter to: {card.get('tag', '')}",
        "find_impact": f"Impact evidence for: {card.get('tag', '')}",
        "find_warrant": f"Warrant for: {card.get('tag', '')}",
        "find_responses": f"Responses to: {card.get('tag', '')}",
    }
    search_claim = action_map.get(body.action, card.get("tag", ""))

    return {
        "search_claim": search_claim,
        "context": context,
        "instruction": (
            "Use POST /research/generate-cards with claim_to_support set to search_claim "
            "to find related evidence. Pass the context fields to improve relevance."
        ),
    }
