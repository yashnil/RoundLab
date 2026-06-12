"""
Blockfile and Frontline Trainer API.

Endpoints:
  POST /documents/{document_id}/extract-blocks
  GET  /block-entries
  PATCH /block-entries/{entry_id}
  DELETE /block-entries/{entry_id}
  POST /speeches/{speech_id}/block-coverage
  GET  /speeches/{speech_id}/block-coverage
"""

from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.supabase_client import get_supabase
from app.models.blockfile import (
    BlockEntryRow,
    BlockCoverageCheck,
    BlockCoverageResponse,
    ExtractBlocksRequest,
    ExtractBlocksResponse,
    BlockCoverageRequest,
    PatchBlockEntryRequest,
)
from app.services.blockfile_extraction import extract_block_entries, build_embedding_text
from app.models.document import DocumentChunkRow

logger = logging.getLogger(__name__)

router = APIRouter(tags=["blockfiles"])

EMBEDDING_MODEL = "text-embedding-3-small"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _assert_owns(row: dict, user_id: str, entity: str = "resource") -> None:
    if row.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail=f"Not authorised to access this {entity}.")


def _get_doc_or_404(doc_id: str, user_id: str) -> dict:
    result = (
        get_supabase()
        .table("documents")
        .select("*")
        .eq("id", doc_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Document not found.")
    return result.data[0]


def _fetch_doc_chunks(document_id: str) -> list[dict]:
    result = (
        get_supabase()
        .table("document_chunks")
        .select("*")
        .eq("document_id", document_id)
        .order("chunk_index")
        .execute()
    )
    return result.data or []


def _entry_dict_to_row(row: dict) -> BlockEntryRow:
    return BlockEntryRow(
        id=row["id"],
        user_id=row["user_id"],
        document_id=row.get("document_id"),
        source_chunk_id=row.get("source_chunk_id"),
        entry_type=row.get("entry_type", "unknown"),
        side=row.get("side"),
        tag=row.get("tag"),
        opponent_claim=row.get("opponent_claim"),
        response_text=row.get("response_text", ""),
        warrant_text=row.get("warrant_text"),
        evidence_text=row.get("evidence_text"),
        impact_text=row.get("impact_text"),
        weighing_text=row.get("weighing_text"),
        author=row.get("author"),
        source=row.get("source"),
        date=row.get("date"),
        topic=row.get("topic"),
        metadata_json=row.get("metadata_json") or {},
        embedding_model=row.get("embedding_model"),
        embedded_at=_parse_ts(row.get("embedded_at")),
        created_at=_parse_ts(row.get("created_at")) or datetime.now(timezone.utc),
        updated_at=_parse_ts(row.get("updated_at")) or datetime.now(timezone.utc),
    )


def _coverage_dict_to_row(row: dict) -> BlockCoverageCheck:
    return BlockCoverageCheck(
        id=row["id"],
        user_id=row["user_id"],
        speech_id=row["speech_id"],
        argument_id=row.get("argument_id"),
        claim_text=row.get("claim_text", ""),
        check_type=row.get("check_type", "block"),
        status=row.get("status", "no_available_block"),
        matched_block_entry_ids=row.get("matched_block_entry_ids") or [],
        top_similarity=row.get("top_similarity"),
        rationale=row.get("rationale"),
        missing_piece=row.get("missing_piece"),
        suggested_drill_json=row.get("suggested_drill_json"),
        created_at=_parse_ts(row.get("created_at")) or datetime.now(timezone.utc),
        updated_at=_parse_ts(row.get("updated_at")) or datetime.now(timezone.utc),
    )


def _parse_ts(val: Any) -> Optional[datetime]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
    except Exception:
        return None


# ── POST /documents/{document_id}/extract-blocks ──────────────────────────────

@router.post("/documents/{document_id}/extract-blocks", response_model=ExtractBlocksResponse)
def extract_blocks(document_id: str, body: ExtractBlocksRequest) -> ExtractBlocksResponse:
    sb = get_supabase()
    doc = _get_doc_or_404(document_id, body.user_id)

    # Optionally update document role/side/topic
    doc_update: dict[str, Any] = {}
    if body.document_role:
        doc_update["document_role"] = body.document_role
    if body.side:
        doc_update["debate_side"] = body.side
    if body.topic:
        doc_update["topic"] = body.topic
    if doc_update:
        sb.table("documents").update(doc_update).eq("id", document_id).execute()

    # Delete existing entries if force_regenerate
    if body.force_regenerate:
        sb.table("block_entries").delete().eq("document_id", document_id).execute()

    # Fetch chunks
    raw_chunks = _fetch_doc_chunks(document_id)
    if not raw_chunks:
        raise HTTPException(status_code=400, detail="Document has no parsed chunks. Parse it first.")

    chunks = [DocumentChunkRow(**c) for c in raw_chunks]
    full_text = "\n".join(c.chunk_text for c in chunks)

    # Infer role
    doc_role = body.document_role or doc.get("document_role") or doc.get("doc_type") or "mixed"

    # Extract entries
    entries = extract_block_entries(
        chunks=chunks,
        full_text=full_text,
        user_id=body.user_id,
        document_id=document_id,
        document_role=doc_role,
        topic=body.topic or doc.get("topic"),
        side=body.side or doc.get("debate_side"),
    )

    if not entries:
        return ExtractBlocksResponse(
            document_id=document_id,
            entries_extracted=0,
            entries_embedded=0,
            entries=[],
        )

    # Embed each entry
    from app.services.embeddings import EMBEDDING_MODEL as EMBD_MODEL, embed_text, vector_to_pg_str

    now_iso = datetime.now(timezone.utc).isoformat()
    inserted_rows: list[BlockEntryRow] = []
    embedded_count = 0

    for entry in entries:
        # Build embedding text
        emb_text = build_embedding_text(entry)
        embedding_val: Optional[str] = None
        emb_model: Optional[str] = None
        emb_at: Optional[str] = None

        try:
            vec = embed_text(emb_text)
            embedding_val = vector_to_pg_str(vec)
            emb_model = EMBD_MODEL
            emb_at = now_iso
            embedded_count += 1
        except Exception as exc:
            logger.warning("block_entry_embed: failed (non-fatal) | %s", exc)

        row_data: dict[str, Any] = {
            "user_id": entry.user_id,
            "document_id": entry.document_id,
            "source_chunk_id": entry.source_chunk_id,
            "entry_type": entry.entry_type,
            "side": entry.side,
            "tag": entry.tag,
            "opponent_claim": entry.opponent_claim,
            "response_text": entry.response_text,
            "warrant_text": entry.warrant_text,
            "evidence_text": entry.evidence_text,
            "impact_text": entry.impact_text,
            "weighing_text": entry.weighing_text,
            "author": entry.author,
            "source": entry.source,
            "date": entry.date,
            "topic": entry.topic,
            "metadata_json": entry.metadata_json,
            "embedding_model": emb_model,
            "embedded_at": emb_at,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        if embedding_val:
            row_data["embedding"] = embedding_val

        insert_result = sb.table("block_entries").insert(row_data).execute()
        if insert_result.data:
            inserted_rows.append(_entry_dict_to_row(insert_result.data[0]))

    return ExtractBlocksResponse(
        document_id=document_id,
        entries_extracted=len(inserted_rows),
        entries_embedded=embedded_count,
        entries=inserted_rows,
    )


# ── GET /block-entries ────────────────────────────────────────────────────────

@router.get("/block-entries", response_model=list[BlockEntryRow])
def list_block_entries(
    user_id: str = Query(...),
    q: Optional[str] = Query(None),
    mode: str = Query("keyword"),
    entry_type: Optional[str] = Query(None),
    side: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
) -> list[BlockEntryRow]:
    sb = get_supabase()

    if q and mode in ("semantic", "hybrid"):
        # Semantic search via match_block_entries RPC
        try:
            from app.services.embeddings import embed_text, vector_to_pg_str
            vec = embed_text(q[:2000])
            pg_vec = "[" + ",".join(str(f) for f in vec) + "]"
            params: dict[str, Any] = {
                "query_embedding": pg_vec,
                "match_user_id": user_id,
                "match_count": limit,
                "similarity_threshold": 0.20,
            }
            if entry_type:
                params["entry_type_filter"] = entry_type
            if side:
                params["side_filter"] = side

            rpc_result = sb.rpc("match_block_entries", params).execute()
            ids_ordered = [r["id"] for r in (rpc_result.data or [])]

            if ids_ordered:
                full_result = (
                    sb.table("block_entries")
                    .select("*")
                    .eq("user_id", user_id)
                    .in_("id", ids_ordered)
                    .execute()
                )
                id_to_row = {r["id"]: r for r in (full_result.data or [])}
                rows = [id_to_row[i] for i in ids_ordered if i in id_to_row]
                return [_entry_dict_to_row(r) for r in rows]
        except Exception as exc:
            logger.warning("block_entries_semantic: failed, falling back to keyword | %s", exc)

    # Keyword / default path
    query = (
        sb.table("block_entries")
        .select("*")
        .eq("user_id", user_id)
    )
    if entry_type:
        query = query.eq("entry_type", entry_type)
    if side:
        query = query.eq("side", side)
    if topic:
        query = query.eq("topic", topic)
    if q and mode == "keyword":
        query = query.ilike("response_text", f"%{q}%")

    result = query.order("created_at", desc=True).limit(limit).execute()
    return [_entry_dict_to_row(r) for r in (result.data or [])]


# ── PATCH /block-entries/{entry_id} ──────────────────────────────────────────

@router.patch("/block-entries/{entry_id}", response_model=BlockEntryRow)
def update_block_entry(entry_id: str, body: PatchBlockEntryRequest) -> BlockEntryRow:
    sb = get_supabase()

    existing = (
        sb.table("block_entries")
        .select("*")
        .eq("id", entry_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Block entry not found.")
    _assert_owns(existing.data[0], body.user_id, "block entry")

    updates: dict[str, Any] = {"updated_at": datetime.now(timezone.utc).isoformat()}
    for field in ("entry_type", "side", "tag", "opponent_claim", "response_text",
                  "warrant_text", "evidence_text", "impact_text", "weighing_text", "topic"):
        val = getattr(body, field, None)
        if val is not None:
            updates[field] = val

    updated = sb.table("block_entries").update(updates).eq("id", entry_id).execute()
    if not updated.data:
        raise HTTPException(status_code=500, detail="Update failed.")
    return _entry_dict_to_row(updated.data[0])


# ── DELETE /block-entries/{entry_id} ─────────────────────────────────────────

@router.delete("/block-entries/{entry_id}", status_code=204)
def delete_block_entry(entry_id: str, user_id: str = Query(...)) -> None:
    sb = get_supabase()

    existing = (
        sb.table("block_entries")
        .select("id, user_id")
        .eq("id", entry_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Block entry not found.")
    _assert_owns(existing.data[0], user_id, "block entry")

    sb.table("block_entries").delete().eq("id", entry_id).execute()


# ── POST /speeches/{speech_id}/block-coverage ─────────────────────────────────

@router.post("/speeches/{speech_id}/block-coverage", response_model=BlockCoverageResponse)
def run_block_coverage(speech_id: str, body: BlockCoverageRequest) -> BlockCoverageResponse:
    sb = get_supabase()

    # Verify speech ownership and status
    speech_result = (
        sb.table("speeches")
        .select("id, user_id, speech_type, status")
        .eq("id", speech_id)
        .eq("user_id", body.user_id)
        .limit(1)
        .execute()
    )
    if not speech_result.data:
        raise HTTPException(status_code=404, detail="Speech not found.")
    speech = speech_result.data[0]
    if speech.get("status") != "done":
        raise HTTPException(status_code=400, detail="Speech analysis must be complete before checking block coverage.")

    # Delete existing checks if force_rerun
    if body.force_rerun:
        sb.table("block_coverage_checks").delete().eq("speech_id", speech_id).execute()

    # Fetch argument map
    arg_map_result = (
        sb.table("argument_maps")
        .select("*")
        .eq("speech_id", speech_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not arg_map_result.data:
        raise HTTPException(status_code=400, detail="No argument map found for this speech.")

    arg_map = arg_map_result.data[0]
    arguments_raw = arg_map.get("arguments") or []
    if isinstance(arguments_raw, str):
        try:
            arguments_raw = json.loads(arguments_raw)
        except Exception:
            arguments_raw = []

    # Check if user has any block entries
    count_result = (
        sb.table("block_entries")
        .select("id", count="exact")
        .eq("user_id", body.user_id)
        .limit(1)
        .execute()
    )
    total_block_entries: int = count_result.count or 0

    # Run coverage classification
    from app.services.block_coverage import classify_block_coverage
    results = classify_block_coverage(
        arguments=arguments_raw,
        speech_type=speech.get("speech_type", ""),
        user_id=body.user_id,
        speech_id=speech_id,
        supabase_client=sb,
        user_has_blocks=total_block_entries > 0,
    )

    now_iso = datetime.now(timezone.utc).isoformat()
    saved_checks: list[BlockCoverageCheck] = []

    for result in results:
        row_data = {
            "user_id": body.user_id,
            "speech_id": speech_id,
            "argument_id": result.argument_id,
            "claim_text": result.claim_text,
            "check_type": result.check_type,
            "status": result.status,
            "matched_block_entry_ids": [e.id for e in result.matched_entries],
            "top_similarity": float(result.top_similarity) if result.top_similarity is not None else None,
            "rationale": result.rationale,
            "missing_piece": result.missing_piece,
            "suggested_drill_json": result.suggested_drill_json,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        insert_result = sb.table("block_coverage_checks").insert(row_data).execute()
        if insert_result.data:
            saved_checks.append(_coverage_dict_to_row(insert_result.data[0]))

    # Generate drills for missing/partial coverage (up to 2)
    drills_to_create = [r for r in results if r.suggested_drill_json and r.status in ("missing", "partially_covered")]
    if drills_to_create:
        # Count existing drills to get proper order
        existing_drills = (
            sb.table("drills")
            .select("id")
            .eq("speech_id", speech_id)
            .execute()
        )
        base_order = len(existing_drills.data or [])

        for i, result in enumerate(drills_to_create[:2]):
            drill_data = result.suggested_drill_json
            if not drill_data:
                continue

            success_criteria = drill_data.get("success_criteria") or []
            if isinstance(success_criteria, str):
                success_criteria = [success_criteria]

            sb.table("drills").insert({
                "speech_id": speech_id,
                "user_id": body.user_id,
                "title": drill_data.get("title", "Block application drill"),
                "description": drill_data.get("description"),
                "skill_target": drill_data.get("skill_target", "block_application"),
                "prompt": drill_data.get("prompt", ""),
                "order": base_order + i,
                "instructions": drill_data.get("instructions"),
                "success_criteria": success_criteria,
                "source_weakness": result.claim_text[:200],
                "difficulty": drill_data.get("difficulty", "beginner"),
                "status": "assigned",
                "time_limit_seconds": drill_data.get("time_limit_seconds", 90),
                "created_at": now_iso,
            }).execute()

    # Tally results
    status_counts: dict[str, int] = {
        "covered": 0,
        "partially_covered": 0,
        "missing": 0,
        "no_available_block": 0,
    }
    for r in results:
        key = r.status if r.status in status_counts else "no_available_block"
        status_counts[key] += 1

    return BlockCoverageResponse(
        speech_id=speech_id,
        checks=saved_checks,
        covered_count=status_counts["covered"],
        partially_covered_count=status_counts["partially_covered"],
        missing_count=status_counts["missing"],
        no_available_block_count=status_counts["no_available_block"],
        total_block_entries=total_block_entries,
    )


# ── GET /speeches/{speech_id}/block-coverage ──────────────────────────────────

@router.get("/speeches/{speech_id}/block-coverage", response_model=BlockCoverageResponse)
def get_block_coverage(
    speech_id: str,
    user_id: str = Query(...),
) -> BlockCoverageResponse:
    sb = get_supabase()

    # Verify ownership
    speech_result = (
        sb.table("speeches")
        .select("id, user_id")
        .eq("id", speech_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not speech_result.data:
        raise HTTPException(status_code=404, detail="Speech not found.")

    checks_result = (
        sb.table("block_coverage_checks")
        .select("*")
        .eq("speech_id", speech_id)
        .eq("user_id", user_id)
        .order("created_at")
        .execute()
    )
    rows = checks_result.data or []
    checks = [_coverage_dict_to_row(r) for r in rows]

    # Tally
    status_counts: dict[str, int] = {
        "covered": 0, "partially_covered": 0,
        "missing": 0, "no_available_block": 0,
    }
    for c in checks:
        key = c.status if c.status in status_counts else "no_available_block"
        status_counts[key] += 1

    total_blocks = (
        sb.table("block_entries")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    ).count or 0

    return BlockCoverageResponse(
        speech_id=speech_id,
        checks=checks,
        covered_count=status_counts["covered"],
        partially_covered_count=status_counts["partially_covered"],
        missing_count=status_counts["missing"],
        no_available_block_count=status_counts["no_available_block"],
        total_block_entries=total_blocks,
    )
