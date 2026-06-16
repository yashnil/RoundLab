"""Research-to-Card Evidence Builder API.

POST /research/extract-url               — fetch + extract article, save research_source
POST /research/search-sources            — search web for relevant sources (Tavily or fallback)
POST /research/card-draft                — generate card draft from source/URL/paste
PATCH /research/card-drafts/{id}         — edit draft fields (user edits tag, cite, body)
POST  /research/card-drafts/{id}/save    — confirm review + save to evidence_cards
GET   /research/card-drafts              — list user's drafts
DELETE /research/card-drafts/{id}        — discard a draft
GET   /research/config                   — safe config status (no secrets)
POST  /research/generate-cards           — search + extract + draft 0-4 candidate cards

Safety rules enforced here:
- body_text comes from extraction only — never LLM-written
- Save requires confirmed=True (user must actively confirm)
- All URLs validated (SSRF prevention in web_article_extraction)
- Research Library document is created per-user on first save (storage_path='_research')
- Tavily key read via settings (pydantic-settings loads .env), never exposed to frontend
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.config import get_tavily_api_key, settings
from app.models.research import (
    CardDraftRequest,
    EvidenceCutResult,
    ExtractUrlRequest,
    ExtractUrlResponse,
    GenerateCardsRequest,
    GenerateCardsResponse,
    PatchCardDraftRequest,
    ResearchConfigResponse,
    SaveDraftRequest,
    SaveDraftResponse,
    SearchDiagnostics,
    SearchSourcesRequest,
    SearchSourcesResponse,
    SearchSourceCandidate,
)
from app.services.card_cutting import generate_card_draft, generate_evidence_cut
from app.services.claim_decomposition import decompose_claim
from app.services.research_search import (
    build_research_query_variants,
    build_research_search_query,
    canonicalize_url,
    generate_candidate_cards,
)
from app.services.source_quality import rate_source_quality
from app.services.supabase_client import get_supabase
from app.services.web_article_extraction import (
    extract_article,
    extract_article_from_paste,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/research", tags=["research"])

_RESEARCH_DOC_STORAGE_PATH = "_research"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_draft_or_404(draft_id: str, user_id: str) -> dict:
    sb = get_supabase()
    result = (
        sb.table("card_drafts")
        .select("*")
        .eq("id", draft_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Card draft not found.")
    return result.data[0]


def _ensure_user_profile(user_id: str, sb) -> None:
    """Ensure a profile row exists for the user. Service-role safe.

    The profiles table is auto-populated by the auth trigger handle_new_user(),
    but during local dev or if the trigger failed the row may be absent.
    This function creates the minimal required row (just the PK) if missing.
    """
    try:
        res = sb.table("profiles").select("id").eq("id", user_id).limit(1).execute()
        if not res.data:
            sb.table("profiles").insert({"id": user_id}).execute()
            logger.info("Created missing profile row for user %s", user_id[:8])
    except Exception as exc:
        logger.warning("Could not ensure profile for user %s: %s", user_id[:8], exc)


def _get_or_create_research_doc(user_id: str) -> str:
    """Return the id of the per-user Research Library document, creating it if absent.

    First ensures the user has a profile row (required by the documents FK).
    Uses upsert-style logic: check → insert → retry-check to handle race conditions.
    """
    sb = get_supabase()

    # Guarantee profiles row so FK insert succeeds
    _ensure_user_profile(user_id, sb)

    def _select() -> Optional[str]:
        res = (
            sb.table("documents")
            .select("id")
            .eq("user_id", user_id)
            .eq("storage_path", _RESEARCH_DOC_STORAGE_PATH)
            .limit(1)
            .execute()
        )
        return res.data[0]["id"] if res.data else None

    existing = _select()
    if existing:
        return existing

    try:
        insert_result = (
            sb.table("documents")
            .insert({
                "user_id": user_id,
                "filename": "Research Library",
                "storage_path": _RESEARCH_DOC_STORAGE_PATH,
                "doc_type": "evidence",
                "status": "parsed",
                "document_role": "evidence",
            })
            .execute()
        )
        if insert_result.data:
            return insert_result.data[0]["id"]
    except Exception as exc:
        logger.warning("Research Library document insert failed (%s) — retrying select", exc)

    # Second-chance select (concurrent create or insert returned empty data)
    existing2 = _select()
    if existing2:
        return existing2

    raise RuntimeError(
        f"Could not create or find Research Library document for user {user_id[:8]}. "
        "Check that the Supabase profiles + documents tables are migrated correctly."
    )


def _embed_text_safe(text: str) -> Optional[list[float]]:
    """Embed text; return None on any failure (embedding is best-effort)."""
    try:
        from app.services.embeddings import embed_text
        return embed_text(text)
    except Exception as exc:
        logger.warning("embed_text failed for research card: %s", exc)
        return None


def _build_card_cutting_metadata(draft: dict, draft_id: str) -> dict:
    """Build the card_cutting_metadata_json stored on a saved evidence_card.

    Includes any user markup (highlight/underline/bold/italic) captured in the
    draft's draft_json so user formatting survives the draft → card save. Pure
    function for unit testing.
    """
    draft_json = draft.get("draft_json") or {}
    metadata = {
        "draft_id": draft_id,
        "research_source_id": draft.get("research_source_id"),
        "warrant_summary": draft.get("warrant_summary"),
        "impact_summary": draft.get("impact_summary"),
    }
    user_markup = draft_json.get("user_markup")
    if user_markup:
        metadata["user_markup"] = user_markup
    return metadata


def _save_draft_to_db(draft_dict: dict, sb) -> dict:
    """Insert a card draft dict into card_drafts table and return the row."""
    # Strip fields not in the DB schema (extra fields go to draft_json)
    db_fields = {
        "user_id", "research_source_id", "url", "topic", "claim_goal", "side",
        "tag", "cite", "body_text", "highlighted_spans_json", "underline_spans_json",
        "author", "publication", "title", "published_date", "author_credentials",
        "warrant_summary", "impact_summary", "source_quality", "credibility_notes",
        "extraction_confidence", "generated_tag", "missing_metadata_json",
        "draft_json", "card_source_type", "status",
    }
    row = {k: v for k, v in draft_dict.items() if k in db_fields}
    result = sb.table("card_drafts").insert(row).execute()
    return result.data[0]


# ── 0. Config status (safe — no secrets) ─────────────────────────────────────

@router.get("/config", response_model=ResearchConfigResponse)
async def research_config() -> ResearchConfigResponse:
    """Return configuration status. Never returns secret values."""
    return ResearchConfigResponse(
        search_provider="tavily",
        search_configured=get_tavily_api_key() is not None,
        url_extraction_available=True,
        card_builder_available=True,
    )


# ── 0b. Regenerate evidence cut (no auth — passage in body) ──────────────────

class RegenerateCutRequest(BaseModel):
    original_passage: str
    claim: str
    evidence_role: str = "direct_support"
    tag: str = ""
    cut_style: str = "medium"  # "medium" (default) | "high"
    use_llm: bool = True


class RegenerateCutResponse(BaseModel):
    cut: EvidenceCutResult
    cut_style_applied: str


@router.post("/regenerate-cut", response_model=RegenerateCutResponse)
async def regenerate_cut(body: RegenerateCutRequest) -> RegenerateCutResponse:
    """Re-cut a passage at a requested cut style.

    No auth needed — the passage is sent in the request body, not fetched from DB.
    body_text is never modified: the cut is built from exact substrings of the passage.
    """
    if not body.original_passage or not body.original_passage.strip():
        raise HTTPException(status_code=422, detail="original_passage is required.")

    cut = generate_evidence_cut(
        passage=body.original_passage,
        claim=body.claim,
        evidence_role=body.evidence_role,
        tag=body.tag,
        use_llm=body.use_llm,
        preferred_cut_style=body.cut_style,
    )
    return RegenerateCutResponse(cut=cut, cut_style_applied=body.cut_style)


# ── 1. Extract URL ─────────────────────────────────────────────────────────────

@router.post("/extract-url", response_model=ExtractUrlResponse)
async def extract_url(body: ExtractUrlRequest) -> ExtractUrlResponse:
    """Fetch and extract an article from a URL.

    SSRF validation is performed inside extract_article(). The article text is
    never modified — it is stored verbatim in research_sources.
    """
    try:
        article = extract_article(body.url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Extraction failed.") from exc

    quality = rate_source_quality(body.url, article.metadata, article.extracted_text)

    sb = get_supabase()
    try:
        row = {
            "user_id": body.user_id,
            "query": body.topic or body.claim_goal or "",
            "url": body.url,
            "title": article.metadata.title,
            "publication": article.metadata.publication,
            "author": article.metadata.author,
            "published_date": article.metadata.published_date,
            "extracted_text": article.extracted_text,
            "extraction_metadata_json": {
                "method": article.extraction_method,
                "confidence": article.extraction_confidence,
                "warnings": article.metadata.warnings,
            },
            "source_quality": quality.source_quality,
            "status": "fetched" if article.status != "failed" else "failed",
            "error_message": article.error,
        }
        insert_result = sb.table("research_sources").insert(row).execute()
        research_source_id = insert_result.data[0]["id"]
    except Exception as exc:
        logger.error("Failed to save research_source: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to save extraction result.") from exc

    return ExtractUrlResponse(
        research_source_id=research_source_id,
        article=article,
        quality=quality,
    )


# ── 2. Search sources (simple list, for URL mode discovery) ───────────────────

@router.post("/search-sources", response_model=SearchSourcesResponse)
async def search_sources(body: SearchSourcesRequest) -> SearchSourcesResponse:
    """Search for relevant sources via Tavily (if configured) or return fallback."""
    tavily_key = get_tavily_api_key()
    if not tavily_key:
        return SearchSourcesResponse(
            results=[],
            fallback=(
                "Web search is not configured. Add TAVILY_API_KEY to the backend "
                "environment and restart the backend. You can still cut cards using "
                "URL mode or Paste Text mode."
            ),
        )

    try:
        from tavily import TavilyClient  # type: ignore
        client = TavilyClient(api_key=tavily_key)
        response = client.search(
            query=body.query,
            max_results=body.limit,
            search_depth="basic",
        )
        results = []
        for r in (response.get("results") or []):
            url = r.get("url", "")
            results.append(SearchSourceCandidate(
                title=r.get("title", "Untitled"),
                url=url,
                snippet=r.get("content", ""),
                publication=None,
                published_date=r.get("published_date"),
                source_quality=None,
            ))
        return SearchSourcesResponse(results=results, provider="tavily")
    except ImportError:
        return SearchSourcesResponse(
            results=[],
            fallback="The tavily-python package is not installed. Run: pip install tavily-python",
        )
    except Exception as exc:
        logger.warning("Tavily search failed: %s", exc)
        return SearchSourcesResponse(
            results=[],
            fallback=f"Search encountered an error. Try again or use URL mode.",
        )


# ── 3. Generate card draft (URL/paste/research_source) ────────────────────────

@router.post("/card-draft")
async def create_card_draft(body: CardDraftRequest) -> dict:
    """Generate a card draft from a URL, research_source_id, or pasted text.

    body_text is always extracted source text — never LLM-generated prose.
    """
    sb = get_supabase()

    research_source_id: Optional[str] = body.research_source_id
    source_quality = None
    credibility_notes = None

    if body.research_source_id:
        src = (
            sb.table("research_sources")
            .select("*")
            .eq("id", body.research_source_id)
            .eq("user_id", body.user_id)
            .limit(1)
            .execute()
        )
        if not src.data:
            raise HTTPException(status_code=404, detail="Research source not found.")
        row = src.data[0]
        from app.models.research import ArticleMetadata, ExtractedArticle
        meta = ArticleMetadata(
            title=row.get("title"),
            author=row.get("author"),
            publication=row.get("publication"),
            published_date=row.get("published_date"),
            url=row.get("url", ""),
        )
        article = ExtractedArticle(
            url=row.get("url", ""),
            metadata=meta,
            extracted_text=row.get("extracted_text", ""),
            extraction_method="loaded",
            extraction_confidence=(row.get("extraction_metadata_json") or {}).get("confidence", 0.7),
            status="ok" if row.get("extracted_text") else "failed",
        )
        source_quality = row.get("source_quality")

    elif body.url:
        try:
            article = extract_article(body.url)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        quality_result = rate_source_quality(body.url, article.metadata, article.extracted_text)
        source_quality = quality_result.source_quality
        credibility_notes = quality_result.credibility_notes

    elif body.pasted_text:
        article = extract_article_from_paste(body.pasted_text)
        source_quality = "unknown"

    else:
        raise HTTPException(
            status_code=422,
            detail="One of: url, research_source_id, or pasted_text is required.",
        )

    if article.status == "failed":
        raise HTTPException(
            status_code=422,
            detail=article.error or "Article extraction failed — cannot generate card.",
        )

    draft_dict = generate_card_draft(
        article=article,
        topic=body.topic,
        claim_goal=body.claim_goal,
        side=body.side,
        user_id=body.user_id,
        source_quality=source_quality,
        credibility_notes=credibility_notes,
    )
    draft_dict["research_source_id"] = research_source_id

    try:
        insert_result = sb.table("card_drafts").insert(draft_dict).execute()
        draft_row = insert_result.data[0]
        # Surface rich studio fields from draft_json so URL/Paste drafts populate
        # the Studio (evidence cut, citation, debate-prep) like Research Search.
        dj = draft_row.get("draft_json") or {}
        for _k in (
            "evidence_cut", "citation", "intelligence", "evidence_role",
            "short_cite", "mla_citation", "citation_quality",
            "cut_text_with_ellipses", "selected_spans", "best_supported_claim",
        ):
            if _k in dj:
                draft_row[_k] = dj[_k]
        if research_source_id:
            sb.table("research_sources").update({"status": "card_generated"}).eq(
                "id", research_source_id
            ).execute()
        return draft_row
    except Exception as exc:
        logger.error("Failed to save card_draft: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to save card draft.") from exc


# ── 4. Generate 0-4 candidate cards from web search ──────────────────────────

_MAX_SEARCH_URLS: int = settings.research_search_max_urls


def _build_providers_used(results: list[dict]) -> list[str]:
    """Return deduplicated list of provider names from search results."""
    providers: list[str] = []
    seen: set[str] = set()
    for r in results:
        p = r.get("_provider", "tavily")
        if p not in seen:
            seen.add(p)
            providers.append(p)
    if not providers and results:
        providers = ["tavily"]
    return providers


@router.post("/generate-cards", response_model=GenerateCardsResponse)
async def generate_cards(body: GenerateCardsRequest) -> GenerateCardsResponse:
    """Search the web and generate 0-4 candidate card drafts.

    Requires Tavily to be configured. Returns configured=False gracefully if not.
    Uses multiple query variants to maximise source coverage.
    Each card draft is stored in card_drafts with status='draft'.
    No card is saved to evidence_cards without the user's explicit confirmation.

    Safety:
    - body_text always comes from extracted source text
    - Weak/no-support passages never become cards
    - Fabricated metadata never inserted
    - At most 4 cards returned
    - SSRF protection applied to every fetched URL
    """
    if not body.claim_to_support or not body.claim_to_support.strip():
        raise HTTPException(status_code=422, detail="claim_to_support is required.")

    tavily_key = get_tavily_api_key()
    if not tavily_key:
        return GenerateCardsResponse(
            search_configured=False,
            cards=[],
            no_card_reason="Web research is not enabled.",
            suggestions=[
                "Add TAVILY_API_KEY to the backend environment and restart the backend.",
                "Use URL mode if you already have a source.",
                "Use Paste Text mode if you have source text.",
            ],
        )

    # Decompose the claim for normalization info (both paths)
    try:
        plan = decompose_claim(
            topic=body.topic or "",
            claim=body.claim_to_support,
            side=body.side or "",
        )
    except Exception as exc:
        logger.warning("claim decomposition failed (using fallback): %s", exc)
        plan = None

    # Shared search state
    all_results: list[dict] = []
    seen_urls: set[str] = set()
    tavily_errors: list[str] = []
    query_variants: list[str] = []

    try:
        from tavily import TavilyClient  # type: ignore
        client = TavilyClient(api_key=tavily_key)
    except ImportError:
        return GenerateCardsResponse(
            search_configured=False,
            no_card_reason="tavily-python package not installed.",
            suggestions=["Run: pip install tavily-python"],
        )

    # Per-slot search diagnostics
    _slot_queries_map: dict[str, list[str]] = {}
    _slot_errors: dict[str, list[str]] = {}
    gen_result = None

    # ── Per-slot search path (when slot planner is enabled) ───────────────────
    _use_per_slot = getattr(settings, "research_enable_slot_planner", True)
    _evidence_plan = None

    if _use_per_slot:
        try:
            from app.services.evidence_set_planner import plan_evidence_set, build_slot_queries
            _evidence_plan = plan_evidence_set(
                topic=body.topic or "",
                claim=body.claim_to_support,
                side=body.side or "",
                use_llm=False,
            )
        except Exception as exc:
            logger.warning("slot planning failed, using unified search: %s", exc)
            _use_per_slot = False

    if _use_per_slot and _evidence_plan:
        per_slot_results: dict[str, list[dict]] = {}

        for slot in _evidence_plan.slots:
            slot_id = getattr(slot, "slot_id", "")
            slot_queries = build_slot_queries(slot, body.topic or "", body.claim_to_support, n=3)
            _slot_queries_map[slot_id] = slot_queries
            # Extend query_variants with slot queries for diagnostics
            for q in slot_queries:
                if q not in query_variants:
                    query_variants.append(q)

            slot_pool: list[dict] = []
            slot_seen: set[str] = set()

            for q in slot_queries:
                try:
                    resp = client.search(query=q, max_results=4, search_depth="advanced")
                    for r in (resp.get("results") or []):
                        url = r.get("url", "")
                        c = canonicalize_url(url)
                        if url and c not in slot_seen:
                            slot_seen.add(c)
                            slot_pool.append(r)
                            # Track globally for diagnostics / no-result detection
                            if c not in seen_urls:
                                seen_urls.add(c)
                                all_results.append(r)
                except Exception as exc:
                    logger.warning("Per-slot Tavily failed for %s: %s", slot_id, exc)
                    tavily_errors.append(str(exc))
                    _slot_errors.setdefault(slot_id, []).append(str(exc))

            per_slot_results[slot_id] = slot_pool

        if any(per_slot_results.values()):
            from app.services.research_search import generate_cards_per_slot
            gen_result = generate_cards_per_slot(
                per_slot_results=per_slot_results,
                plan=_evidence_plan,
                topic=body.topic or "",
                claim_to_support=body.claim_to_support,
                side=body.side,
                user_id=body.user_id,
                max_cards=body.max_cards,
                source_quality_min=body.source_quality_min,
                use_llm=settings.research_enable_llm_role_classifier,
            )
            gen_result.slot_queries_run = _slot_queries_map
            gen_result.per_slot_provider_errors = _slot_errors

            # ── Second-pass: retry unfilled slots with backup queries ───────────
            if gen_result.unfilled_slots and len(gen_result.card_drafts) < body.max_cards:
                from app.services.evidence_set_planner import build_backup_slot_queries
                still_unfilled: list[str] = []
                for slot in _evidence_plan.slots:
                    slot_label = getattr(slot, "slot_label", "")
                    slot_id = getattr(slot, "slot_id", "")
                    if slot_label not in gen_result.unfilled_slots:
                        continue
                    if len(gen_result.card_drafts) >= body.max_cards:
                        break
                    backup_queries = build_backup_slot_queries(slot, body.topic or "", body.claim_to_support)
                    if not backup_queries:
                        still_unfilled.append(slot_label)
                        continue
                    backup_pool: list[dict] = []
                    backup_seen: set[str] = set()
                    for bq in backup_queries[:2]:  # limit to 2 backup queries
                        try:
                            resp = client.search(query=bq, max_results=3, search_depth="advanced")
                            for r in (resp.get("results") or []):
                                url = r.get("url", "")
                                c = canonicalize_url(url)
                                if url and c not in backup_seen:
                                    backup_seen.add(c)
                                    backup_pool.append(r)
                        except Exception as exc:
                            logger.debug("Second-pass Tavily failed for %s: %s", slot_id, exc)
                    if backup_pool:
                        backup_per_slot = {slot_id: backup_pool}
                        backup_plan_slots = [s for s in _evidence_plan.slots if getattr(s, "slot_id", "") == slot_id]
                        if backup_plan_slots:
                            from app.services.evidence_set_planner import EvidenceSetPlan as _ESP
                            mini_plan = _ESP(
                                topic=_evidence_plan.topic,
                                claim=_evidence_plan.claim,
                                side=_evidence_plan.side,
                                slots=backup_plan_slots,
                                planning_method=_evidence_plan.planning_method,
                            )
                            backup_result = generate_cards_per_slot(
                                per_slot_results=backup_per_slot,
                                plan=mini_plan,
                                topic=body.topic or "",
                                claim_to_support=body.claim_to_support,
                                side=body.side,
                                user_id=body.user_id,
                                max_cards=body.max_cards - len(gen_result.card_drafts),
                                source_quality_min="low",  # lower bar for second pass
                                use_llm=settings.research_enable_llm_role_classifier,
                            )
                            if backup_result.card_drafts:
                                # Mark backup cards so frontend can show "Needs verification"
                                for bc in backup_result.card_drafts:
                                    bc.setdefault("draft_json", {})
                                    bc["draft_json"]["is_backup_card"] = True
                                    bc["draft_json"]["backup_reason"] = f"Second-pass search for {slot_label}"
                                    # Ensure backup cards are always review_needed not ready
                                    bc["draft_json"]["search_pass"] = "backup"
                                gen_result.card_drafts.extend(backup_result.card_drafts)
                                gen_result.unfilled_slots = [
                                    s for s in gen_result.unfilled_slots if s != slot_label
                                ]
                                logger.info("Second-pass filled slot: %s", slot_label)
                            else:
                                still_unfilled.append(slot_label)
                                if backup_result.weak_leads:
                                    gen_result.weak_leads.extend(backup_result.weak_leads)
                    else:
                        still_unfilled.append(slot_label)
                gen_result.unfilled_slots = still_unfilled
        else:
            # Per-slot searches found no URLs → fall through to unified search
            _use_per_slot = False

    # ── Unified search fallback ───────────────────────────────────────────────
    if gen_result is None:
        if plan and plan.search_queries:
            query_variants = plan.search_queries
        else:
            query_variants = build_research_query_variants(
                topic=body.topic,
                claim_to_support=body.claim_to_support,
                side=body.side,
            )

        for variant in query_variants:
            if len(seen_urls) >= _MAX_SEARCH_URLS:
                break
            try:
                response = client.search(
                    query=variant,
                    max_results=5,
                    search_depth="advanced",
                )
                for r in (response.get("results") or []):
                    url = r.get("url", "")
                    _canonical = canonicalize_url(url)
                    if url and _canonical not in seen_urls:
                        seen_urls.add(_canonical)
                        all_results.append(r)
            except Exception as exc:
                logger.warning("Tavily search failed for variant '%s': %s", variant, exc)
                tavily_errors.append(str(exc))

        # Supplement with Exa if configured
        _exa_key = settings.exa_api_key
        if _exa_key and plan:
            _exa_queries = (plan.search_queries or query_variants)[:8]
            try:
                from app.services.research_search import _search_exa
                _exa_results = _search_exa(_exa_queries, _exa_key)
                _exa_added = 0
                for r in _exa_results:
                    if len(seen_urls) >= _MAX_SEARCH_URLS:
                        break
                    _c = canonicalize_url(r["url"])
                    if _c not in seen_urls:
                        seen_urls.add(_c)
                        all_results.append(r)
                        _exa_added += 1
                if _exa_added:
                    logger.info("Exa added %d unique URLs", _exa_added)
            except Exception as exc:
                logger.warning("Exa provider failed: %s", exc)

        if not all_results and tavily_errors:
            return GenerateCardsResponse(
                search_configured=True,
                query_used=query_variants[0] if query_variants else body.claim_to_support[:60],
                cards=[],
                no_card_reason=f"Search failed: {tavily_errors[0]}. Try again or use URL mode.",
                suggestions=["Use URL mode if you have a specific source.", "Try rephrasing the claim."],
                normalized_claim=plan.normalized_claim if plan else None,
                corrections_applied=plan.corrections_applied if plan else [],
            )

        if not all_results:
            return GenerateCardsResponse(
                search_configured=True,
                query_used=query_variants[0] if query_variants else body.claim_to_support[:60],
                cards=[],
                no_card_reason="No search results returned for this query.",
                suggestions=["Try a broader claim.", "Use a more specific topic.", "Try URL mode."],
                diagnostics=SearchDiagnostics(query_variants_used=query_variants),
                normalized_claim=plan.normalized_claim if plan else None,
                corrections_applied=plan.corrections_applied if plan else [],
            )

        gen_result = generate_candidate_cards(
            search_results=all_results,
            topic=body.topic or "",
            claim_to_support=body.claim_to_support,
            side=body.side,
            user_id=body.user_id,
            max_cards=body.max_cards,
            source_quality_min=body.source_quality_min,
            include_partial_support=body.include_partial_support,
            use_llm=settings.research_enable_llm_role_classifier,
            research_plan=plan,
        )

    # primary_query used in responses below
    primary_query = query_variants[0] if query_variants else build_research_search_query(
        topic=body.topic,
        claim_to_support=body.claim_to_support,
        side=body.side,
    )

    # ── Build extended diagnostics (Change 7) ────────────────────────────────
    # Count snippet-only vs full extraction from sources_considered
    _urls_full = sum(
        1 for s in gen_result.sources_considered
        if s.get("status") in ("card_generated", "no_support", "duplicate", "partial_skipped",
                               "rejected_quality", "rejected_no_best_claim")
    )
    _urls_snippet = sum(
        1 for s in gen_result.sources_considered if s.get("status") == "possible_lead"
    )
    _counter_evidence_count = len(gen_result.counter_evidence_drafts)

    diagnostics = SearchDiagnostics(
        sources_found=gen_result.sources_found,
        sources_attempted=gen_result.sources_attempted,
        sources_extracted=gen_result.sources_extracted,
        passages_considered=gen_result.passages_considered,
        candidates_generated=gen_result.candidates_generated,
        filtered_no_support=gen_result.filtered_no_support,
        filtered_low_quality=gen_result.filtered_low_quality,
        query_variants_used=query_variants,
        # Extended fields (Change 7)
        urls_extracted_full=_urls_full,
        urls_snippet_only=_urls_snippet,
        chunks_created=gen_result.passages_considered,
        chunks_after_quality_filter=gen_result.passages_considered - gen_result.filtered_no_support,
        chunks_classified=gen_result.passages_considered,
        rejected_by_low_source_quality=gen_result.rejected_by_source_quality,
        rejected_by_low_debate_usefulness=gen_result.filtered_no_support,
        rejected_by_overclaim=0,  # tracked at tag validation; not separately counted yet
        rejected_as_counter_evidence=_counter_evidence_count,
        providers_used=_build_providers_used(all_results),
        queries_run=query_variants[: len(query_variants)],
        possible_lead_urls=gen_result.possible_lead_urls,
        reranker_used=gen_result.reranker_used,
        firecrawl_attempted=gen_result.firecrawl_attempted,
        firecrawl_succeeded=gen_result.firecrawl_succeeded,
        firecrawl_failed=gen_result.firecrawl_failed,
        cohere_rerank_attempted=gen_result.cohere_rerank_attempted,
        cohere_rerank_succeeded=gen_result.cohere_rerank_succeeded,
        grobid_attempted=gen_result.grobid_attempted,
        grobid_succeeded=gen_result.grobid_succeeded,
        grobid_failed=gen_result.grobid_failed,
        # Per-slot diagnostics (populated when per-slot path was used)
        slot_diagnostics=gen_result.slot_diagnostics or None,
        slot_queries_run=gen_result.slot_queries_run or None,
        slot_cards_filled=gen_result.slot_cards_filled,
        slot_weak_leads=gen_result.slot_weak_leads_by_slot,
        slot_unfilled_reasons=gen_result.slot_unfilled_reasons or None,
    )

    # ── Compute claim ladder flags (Change 4) ─────────────────────────────────
    _direct_support_found = gen_result.candidates_by_role.get("direct_support", 0) > 0
    _indirect_roles = {"mechanism_support", "example_support", "impact_support",
                       "definition_support", "authority_support"}
    _usable_indirect = any(
        gen_result.candidates_by_role.get(r, 0) > 0 for r in _indirect_roles
    )
    _indirect_explanation: Optional[str] = None
    if not _direct_support_found and _usable_indirect:
        indirect_role_names = [
            r.replace("_", " ")
            for r in _indirect_roles
            if gen_result.candidates_by_role.get(r, 0) > 0
        ]
        _indirect_explanation = (
            f"We found {', '.join(indirect_role_names)} evidence — useful support, "
            "but you'll need to link it to the broader claim in your speech."
        )

    if not gen_result.card_drafts:
        # ── Differentiated no-card messages (Change 8) ────────────────────────
        # Case A: Tavily returned results, extraction failed on all of them
        if gen_result.sources_extracted == 0 and gen_result.sources_attempted > 0:
            reason = (
                f"Found {gen_result.sources_attempted} source(s) but couldn't extract text from any. "
                "Try URL mode with a direct link to a specific article."
            )
        # Case B: Low source quality rejections are the dominant failure
        elif gen_result.rejected_by_source_quality > 0 and gen_result.candidates_generated == 0:
            reason = (
                f"{gen_result.rejected_by_source_quality} source(s) were found but rejected for low credibility "
                "(below quality threshold). Try a broader claim or use URL mode with a government or academic source."
            )
        # Case C: Passages found but none had a classifiable best_supported_claim
        elif gen_result.rejected_by_missing_best_claim > 0 and gen_result.candidates_generated == 0:
            reason = (
                f"Sources were extracted but the classifier couldn't identify what specific claim each passage supports. "
                "Try rephrasing the claim to match how sources discuss this topic."
            )
        # Case D: Counter-evidence dominated the results
        elif _counter_evidence_count > 0 and gen_result.filtered_no_support == 0 and gen_result.candidates_generated == 0:
            reason = (
                f"The {_counter_evidence_count} relevant passage(s) found actually argued against your claim. "
                "Consider running these as pre-empts, or flip the claim direction."
            )
        # Case E: Low usefulness after extraction
        elif gen_result.filtered_no_support > 0:
            by_role = gen_result.candidates_by_role
            role_mentions = [
                f"{count} {role.replace('_', ' ')}"
                for role, count in by_role.items()
                if role not in ("not_useful",) and count > 0
            ]
            if role_mentions:
                reason = (
                    f"Searched {gen_result.sources_extracted} source(s) — found {', '.join(role_mentions)} passage(s) "
                    "but none met the usefulness threshold. Try a broader topic or different wording."
                )
            elif gen_result.possible_lead_urls:
                reason = (
                    f"No passages were strong enough to cut as cards, but {len(gen_result.possible_lead_urls)} "
                    "source(s) may be worth checking manually."
                )
            else:
                reason = (
                    f"Searched {gen_result.sources_extracted} source(s) but none clearly supported this claim. "
                    "The claim may be too broad, or the key mechanism needs different wording."
                )
        # Case F: Low quality filter (existing behavior)
        elif gen_result.filtered_low_quality > 0 and gen_result.filtered_no_support == 0:
            reason = (
                f"{gen_result.filtered_low_quality} source(s) found but filtered out for low credibility. "
                "Try a broader claim or use URL mode with a specific source."
            )
        else:
            reason = "No credible source text clearly supported this claim."

        return GenerateCardsResponse(
            search_configured=True,
            query_used=primary_query,
            cards=[],
            sources_considered=gen_result.sources_considered,
            no_card_reason=reason,
            suggestions=[
                "Try a narrower, mechanism-focused claim.",
                "Change the wording to match how sources discuss this topic.",
                "Try URL mode with a specific source you already know.",
                "Use a claim with clearer causal language (e.g. 'shields from liability' not 'lack of accountability').",
            ],
            warnings=gen_result.warnings + tavily_errors,
            diagnostics=diagnostics,
            suggested_revised_claims=gen_result.suggested_revised_claims,
            normalized_claim=gen_result.normalized_claim or (plan.normalized_claim if plan else None),
            corrections_applied=gen_result.corrections_applied or (plan.corrections_applied if plan else []),
            candidates_by_role=gen_result.candidates_by_role,
            # Claim ladder flags (Change 4)
            direct_support_found=_direct_support_found,
            usable_indirect_support_found=_usable_indirect,
            indirect_support_explanation=_indirect_explanation,
        )

    # Persist drafts to DB (status=draft, not saved to evidence_cards yet)
    sb = get_supabase()
    saved_drafts: list[dict] = []
    warnings = list(gen_result.warnings) + tavily_errors
    for draft in gen_result.card_drafts:
        try:
            row = _save_draft_to_db(draft, sb)
            # Merge draft_json fields back into the response row for frontend display
            draft_json = draft.get("draft_json") or {}
            row["support_level"]        = draft_json.get("support_level")
            row["support_rationale"]    = draft_json.get("support_rationale")
            row["card_purpose"]         = draft_json.get("card_purpose")
            row["claim_supported"]      = draft_json.get("claim_supported")
            row["best_supported_claim"] = draft_json.get("best_supported_claim")
            row["overclaim_warning"]    = draft_json.get("overclaim_warning")
            row["safe_tag_scope"]       = draft_json.get("safe_tag_scope")
            row["evidence_role"]        = draft_json.get("evidence_role")
            row["is_counter_evidence"]  = draft_json.get("is_counter_evidence", False)
            row["is_snippet_source"]    = draft_json.get("is_snippet_source", False)
            row["slot_id"]              = draft_json.get("slot_id") or draft.get("slot_id", "")
            row["slot_label"]           = draft_json.get("slot_label") or draft.get("slot_label", "")
            # Surface evidence-cut / citation / intelligence fields for the studio UI
            for _k in (
                "evidence_cut", "cut_text_with_ellipses", "selected_spans",
                "citation", "short_cite", "mla_citation", "citation_quality",
                "source_domain", "intelligence",
            ):
                if _k in draft:
                    row[_k] = draft[_k]
            saved_drafts.append(row)
        except Exception as exc:
            logger.error("Failed to persist candidate draft: %s", exc)
            warnings.append(f"One candidate card could not be saved: {exc}")

    return GenerateCardsResponse(
        search_configured=True,
        query_used=primary_query,
        cards=saved_drafts,
        sources_considered=gen_result.sources_considered,
        warnings=warnings,
        diagnostics=diagnostics,
        normalized_claim=gen_result.normalized_claim or (plan.normalized_claim if plan else None),
        corrections_applied=gen_result.corrections_applied or (plan.corrections_applied if plan else []),
        candidates_by_role=gen_result.candidates_by_role,
        # Claim ladder flags (Change 4)
        direct_support_found=_direct_support_found,
        usable_indirect_support_found=_usable_indirect,
        indirect_support_explanation=_indirect_explanation,
        # Evidence Set Builder (Parts 2 + 6)
        weak_leads=gen_result.weak_leads,
        unfilled_slots=gen_result.unfilled_slots,
        evidence_set_plan=gen_result.evidence_set_plan,
    )


# ── 5. Patch draft ─────────────────────────────────────────────────────────────

@router.patch("/card-drafts/{draft_id}")
async def patch_card_draft(draft_id: str, body: PatchCardDraftRequest) -> dict:
    """Edit user-facing fields of a card draft."""
    existing_draft = _get_draft_or_404(draft_id, body.user_id)

    updates: dict = {}
    for field in [
        "tag", "cite", "body_text",
        "highlighted_spans_json", "underline_spans_json",
        "author", "publication", "title", "published_date",
        "author_credentials", "warrant_summary", "impact_summary",
    ]:
        val = getattr(body, field, None)
        if val is not None:
            updates[field] = val

    # Persist full user markup (highlight/underline/bold/italic) into draft_json.
    # There are no DB columns for bold/italic, so they live in the JSON blob —
    # never silently dropped.
    if body.user_markup_json is not None:
        draft_json = dict(existing_draft.get("draft_json") or {})
        draft_json["user_markup"] = body.user_markup_json.model_dump()
        updates["draft_json"] = draft_json

    if not updates:
        result = get_supabase().table("card_drafts").select("*").eq("id", draft_id).limit(1).execute()
        return result.data[0]

    try:
        result = (
            get_supabase()
            .table("card_drafts")
            .update(updates)
            .eq("id", draft_id)
            .execute()
        )
        return result.data[0]
    except Exception as exc:
        logger.error("Failed to patch card_draft %s: %s", draft_id, exc)
        raise HTTPException(status_code=500, detail="Failed to update card draft.") from exc


# ── 6. Save draft → evidence_card ─────────────────────────────────────────────

@router.post("/card-drafts/{draft_id}/save", response_model=SaveDraftResponse)
async def save_card_draft(draft_id: str, body: SaveDraftRequest) -> SaveDraftResponse:
    """Confirm user review and save draft as an evidence_card.

    Requires confirmed=True. User must explicitly review before saving.
    """
    if not body.confirmed:
        raise HTTPException(
            status_code=422,
            detail="Save requires confirmed=True. Review the card before saving.",
        )

    draft = _get_draft_or_404(draft_id, body.user_id)
    if draft.get("status") == "saved":
        raise HTTPException(status_code=409, detail="Draft has already been saved.")

    body_text = draft.get("body_text", "").strip()
    if not body_text:
        raise HTTPException(status_code=422, detail="Card body is empty — cannot save.")

    sb = get_supabase()

    try:
        doc_id = _get_or_create_research_doc(body.user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to create Research Library document.") from exc

    chunk_text = f"{draft.get('tag', '')}\n\n{body_text}"
    try:
        chunk_result = (
            sb.table("document_chunks")
            .insert({
                "document_id": doc_id,
                "user_id": body.user_id,
                "chunk_text": chunk_text,
                "chunk_index": 0,
                "heading": draft.get("tag") or "Research card",
                "metadata_json": {
                    "source_type": draft.get("card_source_type"),
                    "url": draft.get("url"),
                    "draft_id": draft_id,
                },
            })
            .execute()
        )
        chunk_id = chunk_result.data[0]["id"]
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to create document chunk.") from exc

    embedding = _embed_text_safe(chunk_text)
    if embedding:
        try:
            sb.table("document_chunks").update({"embedding": embedding}).eq("id", chunk_id).execute()
        except Exception as exc:
            logger.warning("Failed to store embedding: %s", exc)

    try:
        card_row = {
            "document_id": doc_id,
            "chunk_id": chunk_id,
            "user_id": body.user_id,
            "tag": draft.get("tag", ""),
            "cite": draft.get("cite", ""),
            "body_text": body_text,
            "highlighted_spans_json": draft.get("highlighted_spans_json") or [],
            "underline_spans_json": draft.get("underline_spans_json") or [],
            "url": draft.get("url"),
            "title": draft.get("title"),
            "publication": draft.get("publication"),
            "author_credentials": draft.get("author_credentials"),
            "published_date": draft.get("published_date"),
            "source_quality": draft.get("source_quality"),
            "extraction_confidence": draft.get("extraction_confidence"),
            "generated_tag": draft.get("generated_tag", True),
            "user_reviewed": True,
            "card_source_type": draft.get("card_source_type", "url"),
            "card_cutting_metadata_json": _build_card_cutting_metadata(draft, draft_id),
        }
        card_result = sb.table("evidence_cards").insert(card_row).execute()
        card_id = card_result.data[0]["id"]
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to save evidence card.") from exc

    try:
        sb.table("card_drafts").update({"status": "saved", "saved_card_id": card_id}).eq("id", draft_id).execute()
        research_source_id = draft.get("research_source_id")
        if research_source_id:
            sb.table("research_sources").update({"status": "saved"}).eq("id", research_source_id).execute()
    except Exception as exc:
        logger.warning("Failed to update draft/source status: %s", exc)

    return SaveDraftResponse(
        card_id=card_id,
        draft_id=draft_id,
        message="Card saved to your Evidence Library. Review it anytime under the Library tab.",
    )


# ── 7. List drafts ─────────────────────────────────────────────────────────────

@router.get("/card-drafts")
async def list_card_drafts(
    user_id: str = Query(...),
    status: Optional[str] = Query(None),
) -> list[dict]:
    sb = get_supabase()
    query = (
        sb.table("card_drafts")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
    )
    if status:
        query = query.eq("status", status)
    try:
        result = query.execute()
        return result.data or []
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch card drafts.") from exc


# ── 8. Delete draft ────────────────────────────────────────────────────────────

@router.delete("/card-drafts/{draft_id}")
async def delete_card_draft(draft_id: str, user_id: str = Query(...)) -> dict:
    draft = _get_draft_or_404(draft_id, user_id)
    if draft.get("status") == "saved":
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a saved draft. Delete the evidence card instead.",
        )
    try:
        get_supabase().table("card_drafts").update({"status": "discarded"}).eq("id", draft_id).execute()
        return {"discarded": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to discard draft.") from exc
