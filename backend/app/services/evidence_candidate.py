"""Typed EvidenceCandidate model shared across retrieval stages.

A single EvidenceCandidate flows from passage construction through
deduplication, hybrid ranking, and into the card-cutting pipeline.

SAFETY INVARIANTS (preserved throughout):
- `text` is always exact, immutable extracted source text.
- No LLM or external call modifies `text` after construction.
- `start`/`end` are character offsets into the original extracted_text.
- `rejection_reason` records why a candidate was removed, never how to
  fabricate a replacement.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EvidenceCandidate:
    """One passage candidate extracted from a source document.

    Fields are populated progressively as the candidate moves through stages:
      1. passage_builder: text, start, end, url, domain, title, section_heading
      2. hybrid_retriever: lexical_score, semantic_score, final_score
      3. deduplicator:     duplicate_penalty, rejection_reason
      4. classify stage:   evidence_role, credibility_score

    `text` must never be modified after construction.
    """

    # ── Source text (immutable after construction) ────────────────────────────
    text: str               # IMMUTABLE: exact passage text from source

    # ── Document position (stable char offsets) ───────────────────────────────
    start: int = 0          # char offset in the parent extracted_text
    end: int = 0            # char offset in the parent extracted_text

    # ── Source provenance ─────────────────────────────────────────────────────
    url: str = ""
    canonical_url: str = ""
    domain: str = ""
    title: str = ""         # page/article title
    author: str = ""        # author when known from provider metadata
    published_date: str = ""
    provider: str = ""      # "tavily" | "exa" | "snippet" | "firecrawl" | ...
    query: str = ""         # originating search query
    section_heading: str = ""  # heading above this passage, if any

    # ── P10 extraction provenance (optional; populated from ExtractedDocument) ─
    page_number: int | None = None        # PDF page (1-based); None for HTML/DOCX
    paragraph_index: int = 0
    section_index: int = 0
    extraction_method: str = ""           # "trafilatura" | "pymupdf" | …
    content_hash: str = ""                # SHA-256 of parent document raw_text
    retrieval_timestamp: str = ""         # ISO-8601 UTC
    source_text_type: str = "full_text"   # "full_text" | "abstract_only" | …
    document_type: str = "html"           # "html" | "pdf" | "docx" | "text"

    # ── Evidence classification (set after role classification) ───────────────
    evidence_role: str = ""

    # ── Retrieval scores (set by evidence_hybrid_retriever) ───────────────────
    lexical_score: float = 0.0    # normalized BM25 score
    semantic_score: float = 0.0   # normalized semantic similarity
    reranker_score: float = 0.0   # cross-encoder score when available
    credibility_score: float = 0.0  # domain-quality score (0-10 → normalized)
    duplicate_penalty: float = 0.0
    final_score: float = 0.0      # RRF-fused composite score

    # ── Rejection tracking ────────────────────────────────────────────────────
    rejection_reason: str = ""  # "" = kept; otherwise explains why removed


@dataclass
class DeduplicationStats:
    """Counts from one deduplication pass (for trace reporting)."""
    candidates_in: int = 0
    candidates_out: int = 0
    exact_hash_removed: int = 0
    url_removed: int = 0        # removed because canonical URL was already seen
    near_dup_removed: int = 0   # word-set overlap >= threshold
    domain_capped: int = 0      # per-domain diversity limit reached
    title_dup_removed: int = 0  # normalized title matched an existing candidate


@dataclass
class RetrievalStats:
    """Stats from one hybrid-ranking call (for trace reporting)."""
    backend: str = "bm25"            # "bm25" | "bm25+semantic"
    total_in: int = 0
    total_out: int = 0
    rrf_k: int = 60
    semantic_available: bool = False
    reranker_timed_out: bool = False
    notes: list[str] = field(default_factory=list)
