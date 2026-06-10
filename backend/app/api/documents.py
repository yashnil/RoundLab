"""Evidence-Aware Coach document endpoints — Evidence RAG v1.

POST /documents                           — register an uploaded document and trigger parse
GET  /documents?user_id=...               — list user documents
GET  /documents/{id}?user_id=...          — get document with chunks and cards
DELETE /documents/{id}?user_id=...        — delete document and cascade
POST /documents/{id}/embed?user_id=...    — (re)embed chunks for a document

POST /documents/search                    — keyword / semantic / hybrid search

POST /speeches/{speech_id}/evidence-check  — run claim→chunk semantic support check
GET  /speeches/{speech_id}/evidence-checks — list all checks for a speech
POST /speeches/{speech_id}/evidence-drills — generate evidence-specific drills (deterministic)

All endpoints are additive — they do not touch any existing speech/drill/feedback routes.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app.models.document import (
    ClaimEvidenceCheckRow,
    DocumentCreateRequest,
    DocumentRow,
    DocumentSearchRequest,
    DocumentWithCards,
    EmbedDocumentResponse,
    EvidenceCardRow,
    EvidenceCheckRequest,
    EvidenceCheckResult,
    RetrievalMode,
    SearchResultItem,
)
from app.services.document_parsing import DocumentParseError, parse_document
from app.services.evidence_drill_generation import generate_evidence_drills
from app.services.evidence_extraction import ExtractedCard, extract_evidence_cards
from app.services.evidence_support_check import SupportCheckResult, check_claim_support
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(tags=["evidence"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _assert_owns_document(doc_row: dict, user_id: str) -> None:
    if doc_row.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not authorised.")


def _get_document_or_404(doc_id: str, user_id: str) -> dict:
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


def _fetch_cards(document_id: str) -> list[dict]:
    result = (
        get_supabase()
        .table("evidence_cards")
        .select("*")
        .eq("document_id", document_id)
        .order("created_at")
        .execute()
    )
    return result.data or []


def _fetch_chunks(document_id: str) -> list[dict]:
    result = (
        get_supabase()
        .table("document_chunks")
        .select("*")
        .eq("document_id", document_id)
        .order("chunk_index")
        .execute()
    )
    return result.data or []


def _trigger_parse(doc_id: str, user_id: str, storage_path: str, filename: str) -> None:
    """Download, parse, extract cards, and update document status.

    Called synchronously after insert. For a production system this would be
    offloaded to a background task / queue; for MVP it runs inline.
    """
    sb = get_supabase()

    try:
        parsed = parse_document(storage_path, filename)
    except DocumentParseError as exc:
        sb.table("documents").update({
            "status": "failed",
            "error_message": str(exc),
        }).eq("id", doc_id).execute()
        logger.warning("document_parsing: failed | doc_id=%s | %s", doc_id, exc)
        return
    except Exception as exc:
        sb.table("documents").update({
            "status": "failed",
            "error_message": "Unexpected error during parsing.",
        }).eq("id", doc_id).execute()
        logger.error("document_parsing: unexpected | doc_id=%s | %s", doc_id, exc)
        return

    # Insert chunks
    chunk_id_map: dict[int, str] = {}
    if parsed.chunks:
        chunk_rows = [
            {
                "document_id": doc_id,
                "user_id": user_id,
                "chunk_text": c.chunk_text,
                "chunk_index": c.chunk_index,
                "heading": c.heading,
                "page_number": c.page_number,
                "metadata_json": c.metadata or {},
            }
            for c in parsed.chunks
        ]
        chunk_result = sb.table("document_chunks").insert(chunk_rows).execute()
        for row in (chunk_result.data or []):
            chunk_id_map[row["chunk_index"]] = row["id"]

    # Embed chunks — non-fatal; if this fails, keyword search still works
    if chunk_id_map:
        _embed_chunks_by_id(
            sb,
            chunk_id_list=list(chunk_id_map.values()),
            chunk_texts=[c.chunk_text for c in parsed.chunks],
            doc_id=doc_id,
        )

    # Extract and insert evidence cards (summaries generated per card)
    cards: list[ExtractedCard] = extract_evidence_cards(
        parsed.chunks,
        generate_summaries=True,
    )
    if cards:
        card_rows = [
            {
                "document_id": doc_id,
                "user_id": user_id,
                "chunk_id": chunk_id_map.get(c.chunk_index),
                "tag": c.tag,
                "author": c.author,
                "source": c.source,
                "year": c.year,
                "card_text": c.card_text,
                "claim_summary": c.claim_summary,
                "attribution_complete": c.attribution_complete,
                "metadata_json": {},
            }
            for c in cards
        ]
        sb.table("evidence_cards").insert(card_rows).execute()

    # Update document status and page count
    sb.table("documents").update({
        "status": "parsed",
        "page_count": parsed.page_count,
    }).eq("id", doc_id).execute()

    logger.info(
        "document_parsing: stored | doc_id=%s chunks=%d cards=%d",
        doc_id,
        len(parsed.chunks),
        len(cards),
    )


def _embed_chunks_by_id(
    sb,
    chunk_id_list: list[str],
    chunk_texts: list[str],
    doc_id: str,
) -> tuple[int, int]:
    """Embed a list of chunks and write embeddings to document_chunks.

    Returns (embedded_count, failed_count).
    This function is non-fatal: any exception is caught and logged.
    """
    from app.services.embeddings import EMBEDDING_MODEL, embed_texts, vector_to_pg_str

    if not chunk_id_list or not chunk_texts:
        return 0, 0

    try:
        embeddings = embed_texts(chunk_texts)
    except Exception as exc:
        logger.warning(
            "document_embed: embed_texts failed (non-fatal) | doc_id=%s | %s", doc_id, exc
        )
        return 0, len(chunk_id_list)

    now = datetime.now(timezone.utc).isoformat()
    embedded_count = 0
    failed_count = 0

    for chunk_id, emb in zip(chunk_id_list, embeddings):
        try:
            sb.table("document_chunks").update({
                "embedding": vector_to_pg_str(emb),
                "embedding_model": EMBEDDING_MODEL,
                "embedded_at": now,
            }).eq("id", chunk_id).execute()
            embedded_count += 1
        except Exception as exc:
            logger.warning(
                "document_embed: update failed for chunk %s | %s", chunk_id, exc
            )
            failed_count += 1

    logger.info(
        "document_embed: done | doc_id=%s embedded=%d failed=%d",
        doc_id,
        embedded_count,
        failed_count,
    )
    return embedded_count, failed_count


# ── Documents CRUD ─────────────────────────────────────────────────────────────

@router.post("/documents", response_model=DocumentRow, status_code=201)
async def create_document(body: DocumentCreateRequest) -> DocumentRow:
    """Register an uploaded document and trigger synchronous parsing."""
    sb = get_supabase()
    try:
        row = {
            "user_id": body.user_id,
            "filename": body.filename,
            "storage_path": body.storage_path,
            "doc_type": body.doc_type,
            "status": "uploaded",
            "file_size_bytes": body.file_size_bytes,
        }
        if body.team_id:
            row["team_id"] = body.team_id

        result = sb.table("documents").insert(row).execute()
        doc = result.data[0]
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to create document record.") from exc

    # Trigger parsing inline (synchronous for MVP)
    _trigger_parse(doc["id"], body.user_id, body.storage_path, body.filename)

    # Re-fetch to get updated status after parse
    updated = sb.table("documents").select("*").eq("id", doc["id"]).limit(1).execute()
    return updated.data[0]


@router.get("/documents", response_model=list[DocumentRow])
async def list_documents(user_id: str = Query(...)) -> list[DocumentRow]:
    try:
        result = (
            get_supabase()
            .table("documents")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch documents.") from exc


@router.get("/documents/{doc_id}", response_model=DocumentWithCards)
async def get_document(doc_id: str, user_id: str = Query(...)) -> DocumentWithCards:
    doc = _get_document_or_404(doc_id, user_id)
    chunks = _fetch_chunks(doc_id)
    cards = _fetch_cards(doc_id)
    return {"document": doc, "chunks": chunks, "cards": cards}


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, user_id: str = Query(...)) -> dict:
    doc = _get_document_or_404(doc_id, user_id)
    try:
        # Delete storage object (best-effort — don't fail if already gone)
        try:
            get_supabase().storage.from_("documents").remove([doc["storage_path"]])
        except Exception:
            pass
        get_supabase().table("documents").delete().eq("id", doc_id).execute()
        return {"deleted": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to delete document.") from exc


@router.post("/documents/{doc_id}/embed", response_model=EmbedDocumentResponse)
async def embed_document_chunks(
    doc_id: str,
    user_id: str = Query(...),
) -> EmbedDocumentResponse:
    """(Re-)embed all chunks for a document that have no embedding yet.

    Safe to call multiple times — only processes chunks where embedding IS NULL.
    Useful for backfilling documents uploaded before pgvector was enabled.
    """
    doc = _get_document_or_404(doc_id, user_id)
    sb = get_supabase()

    # Fetch only un-embedded chunks for this document
    try:
        result = (
            sb.table("document_chunks")
            .select("id, chunk_text, chunk_index")
            .eq("document_id", doc_id)
            .eq("user_id", user_id)
            .is_("embedding", "null")
            .order("chunk_index")
            .execute()
        )
        rows = result.data or []
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch chunks.") from exc

    if not rows:
        return EmbedDocumentResponse(
            document_id=doc_id,
            chunks_embedded=0,
            chunks_failed=0,
            message="All chunks are already embedded.",
        )

    chunk_ids = [r["id"] for r in rows]
    chunk_texts = [r["chunk_text"] for r in rows]

    embedded, failed = _embed_chunks_by_id(sb, chunk_ids, chunk_texts, doc_id)

    return EmbedDocumentResponse(
        document_id=doc_id,
        chunks_embedded=embedded,
        chunks_failed=failed,
        message=f"Embedded {embedded} chunks. {failed} failed.",
    )


# ── Search ─────────────────────────────────────────────────────────────────────

def _keyword_search(
    sb,
    user_id: str,
    query: str,
    limit: int,
    document_id: str | None = None,
) -> list[dict]:
    """FTS search with ilike fallback. Returns raw chunk rows."""
    base = sb.table("document_chunks").select("*").eq("user_id", user_id)
    if document_id:
        base = base.eq("document_id", document_id)

    try:
        fts_result = base.text_search(
            "fts", query, config="english", type="websearch"
        ).limit(limit).execute()
        rows = fts_result.data or []
    except Exception:
        rows = []

    if not rows:
        try:
            fallback_base = (
                sb.table("document_chunks")
                .select("*")
                .eq("user_id", user_id)
                .ilike("chunk_text", f"%{query}%")
            )
            if document_id:
                fallback_base = fallback_base.eq("document_id", document_id)
            rows = (fallback_base.limit(limit).execute().data or [])
        except Exception:
            rows = []

    return rows


def _semantic_search(
    sb,
    user_id: str,
    query: str,
    limit: int,
    similarity_threshold: float,
    document_id: str | None = None,
) -> list[dict]:
    """Semantic search via match_document_chunks RPC. Returns rows with 'similarity' field."""
    try:
        from app.services.embeddings import embed_text, vector_to_pg_str
        embedding_str = vector_to_pg_str(embed_text(query))
    except Exception as exc:
        logger.warning("documents/search: semantic embed failed | %s", exc)
        return []

    try:
        result = sb.rpc(
            "match_document_chunks",
            {
                "query_embedding": embedding_str,
                "match_user_id": user_id,
                "match_count": limit,
                "similarity_threshold": similarity_threshold,
            },
        ).execute()
        rows = result.data or []
        if document_id:
            rows = [r for r in rows if r.get("document_id") == document_id]
        return rows
    except Exception as exc:
        logger.warning("documents/search: RPC failed | %s", exc)
        return []


def _build_search_items(
    sb,
    chunk_rows: list[dict],
    similarity_map: dict[str, float] | None,
    retrieval_mode: str,
) -> list[SearchResultItem]:
    """Attach document filenames and linked evidence cards to chunk rows."""
    if not chunk_rows:
        return []

    doc_ids = list({row["document_id"] for row in chunk_rows})
    doc_result = (
        sb.table("documents").select("id, filename").in_("id", doc_ids).execute()
    )
    doc_map = {r["id"]: r["filename"] for r in (doc_result.data or [])}

    chunk_ids = [row["id"] for row in chunk_rows]
    card_result = (
        sb.table("evidence_cards").select("*").in_("chunk_id", chunk_ids).execute()
    )
    chunk_card_map: dict[str, list[dict]] = {}
    for card in (card_result.data or []):
        cid = card.get("chunk_id")
        if cid:
            chunk_card_map.setdefault(cid, []).append(card)

    items: list[SearchResultItem] = []
    for row in chunk_rows:
        items.append(
            SearchResultItem(
                chunk=row,
                document_filename=doc_map.get(row["document_id"], ""),
                cards=chunk_card_map.get(row["id"], []),
                similarity=similarity_map.get(row["id"]) if similarity_map else None,
                retrieval_mode=retrieval_mode,
            )
        )
    return items


@router.post("/documents/search", response_model=list[SearchResultItem])
async def search_evidence(body: DocumentSearchRequest) -> list[SearchResultItem]:
    """Search the user's evidence library.

    mode = "keyword"  — PostgreSQL FTS + ilike fallback
    mode = "semantic" — pgvector cosine similarity via match_document_chunks RPC
    mode = "hybrid"   — semantic first; merges keyword results for any gaps;
                        deduplicates by chunk id; prefers higher similarity
    """
    if not body.query.strip():
        raise HTTPException(status_code=422, detail="Query must not be empty.")

    sb = get_supabase()
    limit = max(1, min(body.limit, 25))
    mode = body.mode if body.mode in ("keyword", "semantic", "hybrid") else "keyword"

    similarity_map: dict[str, float] = {}
    merged_rows: list[dict] = []
    seen_ids: set[str] = set()

    # ── Semantic pass ──────────────────────────────────────────────────────────
    if mode in ("semantic", "hybrid"):
        semantic_rows = _semantic_search(
            sb,
            user_id=body.user_id,
            query=body.query,
            limit=limit,
            similarity_threshold=body.similarity_threshold,
            document_id=body.document_id,
        )
        for row in semantic_rows:
            rid = row["id"]
            if rid not in seen_ids:
                seen_ids.add(rid)
                similarity_map[rid] = round(float(row.get("similarity", 0)), 4)
                merged_rows.append(row)

    # ── Keyword pass (always run for keyword mode; fill gaps for hybrid) ───────
    if mode in ("keyword", "hybrid"):
        keyword_rows = _keyword_search(
            sb,
            user_id=body.user_id,
            query=body.query,
            limit=limit,
            document_id=body.document_id,
        )
        for row in keyword_rows:
            rid = row["id"]
            if rid not in seen_ids:
                seen_ids.add(rid)
                merged_rows.append(row)

    if not merged_rows:
        return []

    # Trim to requested limit
    merged_rows = merged_rows[:limit]

    actual_mode = (
        "semantic" if mode == "semantic"
        else "keyword" if mode == "keyword"
        else ("hybrid" if len(similarity_map) > 0 else "keyword")
    )

    return _build_search_items(sb, merged_rows, similarity_map or None, actual_mode)


# ── Evidence support check ─────────────────────────────────────────────────────

@router.post(
    "/speeches/{speech_id}/evidence-check",
    response_model=EvidenceCheckResult,
)
async def evidence_check_for_argument(
    speech_id: str,
    body: EvidenceCheckRequest,
) -> EvidenceCheckResult:
    """Run evidence support check for a single speech argument.

    Searches the user's evidence library for cards matching the claim,
    then uses the LLM to classify support level.
    """
    sb = get_supabase()

    # Verify speech ownership
    speech_result = (
        sb.table("speeches")
        .select("id, user_id")
        .eq("id", speech_id)
        .eq("user_id", body.user_id)
        .limit(1)
        .execute()
    )
    if not speech_result.data:
        raise HTTPException(status_code=404, detail="Speech not found.")

    # Load user's evidence library
    library_result = (
        sb.table("evidence_cards")
        .select("*")
        .eq("user_id", body.user_id)
        .execute()
    )
    library_cards: list[EvidenceCardRow] = [
        EvidenceCardRow(**row) for row in (library_result.data or [])
    ]

    # Pass user_id to enable semantic retrieval
    result: SupportCheckResult = check_claim_support(
        claim=body.claim_text,
        evidence_from_speech=body.evidence_text_from_speech,
        library_cards=library_cards,
        user_id=body.user_id,
    )

    # Persist the check result including RAG audit fields
    try:
        check_row = {
            "speech_id": speech_id,
            "user_id": body.user_id,
            "argument_label": body.argument_label,
            "claim_text": body.claim_text,
            "evidence_text_from_speech": body.evidence_text_from_speech,
            "matched_card_id": result.matched_card.id if result.matched_card else None,
            "support_level": result.support_level,
            "explanation": result.explanation,
            "matched_chunk_ids": result.matched_chunk_ids,
            "top_similarity": float(result.top_similarity) if result.top_similarity is not None else None,
            "retrieved_snippets_json": result.retrieved_snippets,
            "support_rationale": result.support_rationale,
            "missing_link": result.missing_link,
            "retrieval_mode": result.retrieval_mode,
        }
        sb.table("claim_evidence_checks").insert(check_row).execute()
    except Exception as exc:
        logger.warning("evidence_check: failed to persist | %s", exc)

    return EvidenceCheckResult(
        argument_label=body.argument_label,
        claim_text=body.claim_text,
        evidence_text_from_speech=body.evidence_text_from_speech,
        matched_card=result.matched_card,
        support_level=result.support_level,
        explanation=result.explanation,
        matched_chunk_ids=result.matched_chunk_ids,
        top_similarity=result.top_similarity,
        retrieved_snippets=result.retrieved_snippets,
        support_rationale=result.support_rationale,
        missing_link=result.missing_link,
        retrieval_mode=result.retrieval_mode,
    )


@router.get(
    "/speeches/{speech_id}/evidence-checks",
    response_model=list[ClaimEvidenceCheckRow],
)
async def get_evidence_checks(
    speech_id: str,
    user_id: str = Query(...),
) -> list[ClaimEvidenceCheckRow]:
    """Retrieve all saved evidence checks for a speech."""
    try:
        result = (
            get_supabase()
            .table("claim_evidence_checks")
            .select("*")
            .eq("speech_id", speech_id)
            .eq("user_id", user_id)
            .order("created_at")
            .execute()
        )
        return result.data or []
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch evidence checks.") from exc


# ── Evidence drills ────────────────────────────────────────────────────────────

@router.post(
    "/speeches/{speech_id}/evidence-drills",
    response_model=list[dict],
    status_code=201,
)
async def generate_evidence_drills_endpoint(
    speech_id: str,
    user_id: str = Query(...),
) -> list[dict]:
    """Generate 1–3 evidence-specific drills from saved evidence checks.

    Uses deterministic templates — no LLM call required.
    Does NOT delete existing standard drills. Deduplicates via source_weakness.
    Returns the newly inserted drill rows.
    """
    sb = get_supabase()

    # Verify speech ownership
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

    # Fetch existing evidence checks
    checks_result = (
        sb.table("claim_evidence_checks")
        .select("*")
        .eq("speech_id", speech_id)
        .eq("user_id", user_id)
        .execute()
    )
    checks_data = checks_result.data or []
    if not checks_data:
        raise HTTPException(
            status_code=422,
            detail="No evidence checks found for this speech. Run evidence check first.",
        )
    checks = [ClaimEvidenceCheckRow(**row) for row in checks_data]

    # One query: fetch source_weakness + order for dedup and offset computation.
    # Avoids a second round-trip and eliminates edge cases from two separate queries.
    existing_drills_result = (
        sb.table("drills")
        .select("source_weakness, order")
        .eq("speech_id", speech_id)
        .eq("user_id", user_id)
        .execute()
    )
    existing_rows = existing_drills_result.data or []

    existing_sw: set[str] = {
        row["source_weakness"]
        for row in existing_rows
        if row.get("source_weakness")
    }

    # Compute next_order robustly:
    # - collect only integer order values (guards against None, str, or negative rows)
    # - default to 0 if none found
    # - enforce floor of 1 so the CHECK (order >= 1) constraint is never violated
    valid_orders = [
        row["order"]
        for row in existing_rows
        if isinstance(row.get("order"), int) and row["order"] >= 1
    ]
    max_order = max(valid_orders) if valid_orders else 0
    next_order = max(1, max_order + 1)

    logger.info(
        "evidence_drills: existing_drills=%d max_order=%d next_order=%d | speech_id=%s",
        len(existing_rows),
        max_order,
        next_order,
        speech_id,
    )

    # Generate drills
    drill_templates = generate_evidence_drills(checks, existing_source_weaknesses=existing_sw)
    if not drill_templates:
        return []

    rows = []
    for i, tmpl in enumerate(drill_templates):
        rows.append({
            "speech_id": speech_id,
            "user_id": user_id,
            "title": tmpl["title"],
            "description": tmpl["description"],
            "skill_target": tmpl["skill_target"],
            "prompt": tmpl["prompt"],
            "order": next_order + i,
            "instructions": tmpl["instructions"],
            "success_criteria": tmpl["success_criteria"],
            "source_weakness": tmpl["source_weakness"],
            "difficulty": tmpl["difficulty"],
            "status": "assigned",
            "time_limit_seconds": tmpl["time_limit_seconds"],
        })

    logger.info(
        "evidence_drills: inserting %d rows | speech_id=%s | orders=%s | skill_targets=%s",
        len(rows),
        speech_id,
        [r["order"] for r in rows],
        [r["skill_target"] for r in rows],
    )

    try:
        result = sb.table("drills").insert(rows).execute()
        logger.info(
            "evidence_drills: inserted %d drills | speech_id=%s", len(rows), speech_id
        )
        return result.data or rows
    except Exception as exc:
        exc_str = str(exc)
        logger.error(
            "evidence_drills: insert failed | exc_type=%s | exc=%s | speech_id=%s | sample_order=%s",
            type(exc).__name__,
            exc_str,
            speech_id,
            rows[0].get("order") if rows else None,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save evidence drills: {exc_str}",
        ) from exc
