"""Pydantic models for Research-to-Card Evidence Builder."""

from typing import Literal, Optional
from pydantic import BaseModel, Field

SourceQuality = Literal["high", "medium", "low", "unknown"]
CardDraftStatus = Literal["draft", "saved", "discarded"]
CardSourceType = Literal["url", "manual_paste", "research_search"]
ResearchSourceStatus = Literal["fetched", "failed", "card_generated", "saved"]
SupportLevel = Literal["strong_support", "partial_support", "weak_support", "no_support"]
CardPurpose = Literal[
    "uniqueness", "link", "internal_link", "impact", "answer",
    "frontline", "weighing", "background", "solvency", "harm", "unknown",
]
EvidenceRole = Literal[
    "direct_support", "mechanism_support", "example_support",
    "impact_support", "definition_support", "authority_support",
    "counter_evidence", "not_useful",
]


# ── Span types ────────────────────────────────────────────────────────────────

class HighlightSpan(BaseModel):
    start: int
    end: int
    type: Literal["highlight", "underline"] = "highlight"
    reason: str = ""


# ── Evidence cut models ────────────────────────────────────────────────────────

class SelectedSpan(BaseModel):
    start: int            # char offset in original_passage
    end: int              # char offset in original_passage
    text: str             # exact text of span (must match original_passage[start:end])
    sentence_index: int = 0
    rationale: str = ""


class AnnotatedSpan(BaseModel):
    """A selected span with prefix/suffix anchoring for robust re-location."""
    id: str = ""          # uuid
    start: int
    end: int
    text: str
    sentence_index: int = 0
    rationale: str = ""
    selected_by: Literal["ai", "user"] = "ai"
    confidence: float = 0.8
    prefix: str = ""      # up to 20 chars before span in original text
    suffix: str = ""      # up to 20 chars after span in original text


class EvidenceCutResult(BaseModel):
    original_passage: str
    selected_spans: list[SelectedSpan] = []
    cut_text: str = ""                    # joined selected spans, no ellipses
    cut_text_with_ellipses: str = ""      # joined with " [...] " between non-adjacent spans
    compression_ratio: float = 1.0        # len(cut_text) / len(original_passage)
    confidence: float = 0.5
    cut_style: Literal["full", "light_cut", "medium_cut", "aggressive_cut"] = "medium_cut"
    validation_passed: bool = True
    validation_notes: str = ""
    # Part 4 — cut quality signals
    cut_confidence: float = 0.5           # 0-1 confidence in the cut quality
    cut_warnings: list[str] = []          # e.g. "Aggressive cut may lose context"
    bold_spans: list[SelectedSpan] = []   # most important phrases (subset of selected_spans)
    annotated_spans: list[AnnotatedSpan] = []  # selected_spans with prefix/suffix anchoring
    # Part 4b — spans remapped to cut_text_with_ellipses offsets (for card-body highlighting)
    cut_body_spans: list[SelectedSpan] = []
    cut_body_bold_spans: list[SelectedSpan] = []


class CitationMetadata(BaseModel):
    author_display: str = ""          # "Smith" or "Smith et al." or "No author"
    authors: list[str] = []
    year: str = ""
    title: str = ""
    container_title: str = ""         # journal/publication name
    publication_name: str = ""        # site/publication/source label
    url: str = ""
    doi: str = ""
    accessed_date: str = ""
    citation_quality: Literal["complete", "partial", "weak"] = "partial"
    mla_citation: str = ""
    short_cite: str = ""              # "Smith 2024" or "Cornell LII"
    # Part 3 — citation provenance (where each field came from)
    author_source: str = ""           # meta_tags|schema_org|search_provider|organization_heuristic|grobid|zotero|crossref|missing
    date_source: str = ""
    title_source: str = ""
    publication_source: str = ""


# ── Card intelligence (debate-use annotations) ─────────────────────────────────

class CardIntelligence(BaseModel):
    """Deterministic debate-intelligence annotations derived from card metadata."""
    why_this_card: str = ""
    supports_claim_because: list[str] = []
    best_use: Literal[
        "contention", "rebuttal", "frontline", "weighing",
        "impact", "definition", "crossfire",
    ] = "contention"
    debate_use_notes: list[str] = []
    limitations: list[str] = []
    suggested_block_label: str = ""
    save_readiness: Literal["ready", "review_needed", "weak"] = "review_needed"
    save_readiness_reasons: list[str] = []
    # Part 9 — slot-aware debate intelligence
    opponent_response: str = ""   # likely counterargument from opponent
    crossfire_question: str = ""  # useful crossfire question based on card


# ── Article extraction ────────────────────────────────────────────────────────

class ArticleMetadata(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    publication: Optional[str] = None
    published_date: Optional[str] = None
    url: str
    canonical_url: Optional[str] = None
    language: Optional[str] = None
    excerpt: Optional[str] = None
    warnings: list[str] = []


class ExtractedArticle(BaseModel):
    url: str
    metadata: ArticleMetadata
    extracted_text: str
    extraction_method: str = "unknown"
    extraction_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    status: Literal["ok", "partial", "failed"] = "ok"
    error: Optional[str] = None


# ── Source quality ─────────────────────────────────────────────────────────────

class SourceQualityResult(BaseModel):
    source_quality: SourceQuality = "unknown"
    credibility_notes: str = ""
    warnings: list[str] = []


# ── Card draft ────────────────────────────────────────────────────────────────

class CardDraftRow(BaseModel):
    id: str
    user_id: str
    research_source_id: Optional[str] = None
    url: Optional[str] = None
    topic: Optional[str] = None
    claim_goal: Optional[str] = None
    side: Optional[str] = None
    tag: str = ""
    cite: str = ""
    body_text: str = ""
    highlighted_spans_json: list[dict] = []
    underline_spans_json: list[dict] = []
    author: Optional[str] = None
    publication: Optional[str] = None
    title: Optional[str] = None
    published_date: Optional[str] = None
    author_credentials: Optional[str] = None
    warrant_summary: Optional[str] = None
    impact_summary: Optional[str] = None
    source_quality: Optional[SourceQuality] = None
    credibility_notes: Optional[str] = None
    extraction_confidence: Optional[float] = None
    generated_tag: bool = True
    missing_metadata_json: dict = {}
    draft_json: dict = {}
    card_source_type: Optional[CardSourceType] = None
    status: CardDraftStatus = "draft"
    saved_card_id: Optional[str] = None
    # Research search extra fields (optional — not in table, stored in draft_json)
    support_level: Optional[SupportLevel] = None
    support_rationale: Optional[str] = None
    card_purpose: Optional[CardPurpose] = None
    claim_supported: Optional[bool] = None
    best_supported_claim: Optional[str] = None
    overclaim_warning: Optional[str] = None
    safe_tag_scope: Optional[str] = None
    evidence_role: Optional[EvidenceRole] = None
    # New evidence cut fields (optional for backward compat)
    evidence_cut: Optional[EvidenceCutResult] = None
    citation: Optional[CitationMetadata] = None
    intelligence: Optional[CardIntelligence] = None
    source_domain: Optional[str] = None
    source_title: Optional[str] = None
    created_at: str
    updated_at: str


# ── API request/response models ────────────────────────────────────────────────

class ExtractUrlRequest(BaseModel):
    user_id: str
    url: str
    topic: Optional[str] = None
    claim_goal: Optional[str] = None


class ExtractUrlResponse(BaseModel):
    research_source_id: str
    article: ExtractedArticle
    quality: SourceQualityResult


class SearchSourcesRequest(BaseModel):
    user_id: str
    query: str
    side: Optional[str] = None
    limit: int = Field(default=8, ge=1, le=20)


class SearchSourceCandidate(BaseModel):
    title: str
    url: str
    snippet: str
    publication: Optional[str] = None
    published_date: Optional[str] = None
    source_quality: Optional[SourceQuality] = None


class SearchSourcesResponse(BaseModel):
    results: list[SearchSourceCandidate] = []
    provider: Optional[str] = None
    fallback: Optional[str] = None


class CardDraftRequest(BaseModel):
    user_id: str
    url: Optional[str] = None
    research_source_id: Optional[str] = None
    pasted_text: Optional[str] = None
    topic: str
    claim_goal: str
    side: Optional[str] = None
    card_type: Optional[str] = None


class PatchCardDraftRequest(BaseModel):
    user_id: str
    tag: Optional[str] = None
    cite: Optional[str] = None
    body_text: Optional[str] = None
    highlighted_spans_json: Optional[list[dict]] = None
    underline_spans_json: Optional[list[dict]] = None
    author: Optional[str] = None
    publication: Optional[str] = None
    title: Optional[str] = None
    published_date: Optional[str] = None
    author_credentials: Optional[str] = None
    warrant_summary: Optional[str] = None
    impact_summary: Optional[str] = None


class SaveDraftRequest(BaseModel):
    user_id: str
    confirmed: bool = False


class SaveDraftResponse(BaseModel):
    card_id: str
    draft_id: str
    message: str


# ── Generate-cards request/response ──────────────────────────────────────────

class GenerateCardsRequest(BaseModel):
    user_id: str
    topic: Optional[str] = None
    claim_to_support: str
    side: Optional[str] = None
    max_cards: int = Field(default=5, ge=1, le=5)
    source_quality_min: SourceQuality = "medium"
    include_partial_support: bool = True


class SearchDiagnostics(BaseModel):
    sources_found: int = 0
    sources_attempted: int = 0
    sources_extracted: int = 0
    passages_considered: int = 0
    candidates_generated: int = 0
    filtered_no_support: int = 0
    filtered_low_quality: int = 0
    query_variants_used: list[str] = []
    # Extended diagnostics (Change 7)
    urls_extracted_full: int = 0
    urls_snippet_only: int = 0
    chunks_created: int = 0
    chunks_after_quality_filter: int = 0
    chunks_classified: int = 0
    rejected_by_low_source_quality: int = 0
    rejected_by_low_debate_usefulness: int = 0
    rejected_by_overclaim: int = 0
    rejected_as_counter_evidence: int = 0
    providers_used: list[str] = []
    queries_run: list[str] = []
    possible_lead_urls: list[str] = []
    reranker_used: str = "none"
    # Firecrawl / Cohere instrumentation
    firecrawl_attempted: int = 0
    firecrawl_succeeded: int = 0
    firecrawl_failed: int = 0
    cohere_rerank_attempted: int = 0
    cohere_rerank_succeeded: int = 0
    # GROBID instrumentation (optional scholarly PDF extraction)
    grobid_attempted: int = 0
    grobid_succeeded: int = 0
    grobid_failed: int = 0
    # Per-slot search diagnostics (populated when slot planner is active)
    slot_diagnostics: Optional[dict] = None
    slot_queries_run: Optional[dict] = None
    slot_cards_filled: list[str] = []
    slot_weak_leads: list[str] = []
    slot_unfilled_reasons: Optional[dict] = None


class GenerateCardsResponse(BaseModel):
    search_configured: bool
    query_used: Optional[str] = None
    cards: list[dict] = []
    sources_considered: list[dict] = []
    no_card_reason: Optional[str] = None
    suggestions: list[str] = []
    warnings: list[str] = []
    diagnostics: Optional[SearchDiagnostics] = None
    suggested_revised_claims: list[str] = []
    normalized_claim: Optional[str] = None
    corrections_applied: list[str] = []
    candidates_by_role: dict[str, int] = {}
    providers_used: list[str] = []
    # Claim ladder support indicators (Change 4)
    direct_support_found: bool = False
    usable_indirect_support_found: bool = False
    indirect_support_explanation: Optional[str] = None
    # Evidence Set Builder (Parts 2 + 6)
    weak_leads: list[dict] = []
    unfilled_slots: list[str] = []
    evidence_set_plan: Optional[dict] = None


# ── Config response ───────────────────────────────────────────────────────────

class ResearchConfigResponse(BaseModel):
    search_provider: str = "tavily"
    search_configured: bool
    url_extraction_available: bool = True
    card_builder_available: bool = True
