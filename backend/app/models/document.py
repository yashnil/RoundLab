"""Pydantic models for Evidence-Aware Coach document pipeline."""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel


# ── Enums / literals ──────────────────────────────────────────────────────────

class DocumentStatus:
    UPLOADED = "uploaded"
    PARSED = "parsed"
    FAILED = "failed"


class DocumentType:
    CASE = "case"
    EVIDENCE = "evidence"
    BRIEF = "brief"
    OTHER = "other"


class EvidenceSupportLevel:
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNSUPPORTED = "unsupported"
    UNVERIFIABLE = "unverifiable"


class RetrievalMode:
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    NONE = "none"


# ── Request models ─────────────────────────────────────────────────────────────

class DocumentCreateRequest(BaseModel):
    user_id: str
    filename: str
    storage_path: str
    doc_type: str = "case"
    file_size_bytes: Optional[int] = None
    team_id: Optional[str] = None


class DocumentSearchRequest(BaseModel):
    user_id: str
    query: str
    limit: int = 10
    # keyword | semantic | hybrid
    mode: str = "keyword"
    document_id: Optional[str] = None
    similarity_threshold: float = 0.30


class EvidenceCheckRequest(BaseModel):
    user_id: str
    argument_label: Optional[str] = None
    claim_text: str
    evidence_text_from_speech: Optional[str] = None


# ── Row models (database records) ─────────────────────────────────────────────

class DocumentRow(BaseModel):
    id: str
    user_id: str
    team_id: Optional[str] = None
    filename: str
    storage_path: str
    doc_type: str
    status: str
    file_size_bytes: Optional[int] = None
    page_count: Optional[int] = None
    error_message: Optional[str] = None
    created_at: str


class DocumentChunkRow(BaseModel):
    id: str
    document_id: str
    user_id: str
    chunk_text: str
    chunk_index: int
    heading: Optional[str] = None
    page_number: Optional[int] = None
    metadata_json: dict = {}
    created_at: str
    # embedding fields are NOT returned in standard API responses (too large)
    # they are present here only for internal use
    embedding_model: Optional[str] = None
    embedded_at: Optional[str] = None


class EvidenceCardRow(BaseModel):
    id: str
    document_id: str
    user_id: str
    chunk_id: Optional[str] = None
    tag: Optional[str] = None
    author: Optional[str] = None
    source: Optional[str] = None
    year: Optional[int] = None
    card_text: str
    claim_summary: Optional[str] = None
    attribution_complete: bool
    metadata_json: dict = {}
    created_at: str


class ClaimEvidenceCheckRow(BaseModel):
    id: str
    speech_id: str
    user_id: str
    argument_label: Optional[str] = None
    claim_text: str
    evidence_text_from_speech: Optional[str] = None
    matched_card_id: Optional[str] = None
    support_level: Optional[str] = None
    explanation: Optional[str] = None
    created_at: str
    # RAG audit fields (added in migration 20260609600000)
    matched_chunk_ids: list[str] = []
    top_similarity: Optional[float] = None
    retrieved_snippets_json: list[dict[str, Any]] = []
    support_rationale: Optional[str] = None
    missing_link: Optional[str] = None
    retrieval_mode: Optional[str] = None


# ── Semantic retrieval helper types ───────────────────────────────────────────

class SemanticChunkResult(BaseModel):
    """One row returned by match_document_chunks RPC."""
    id: str
    document_id: str
    user_id: str
    chunk_text: str
    chunk_index: int
    heading: Optional[str] = None
    page_number: Optional[int] = None
    metadata_json: dict = {}
    created_at: str
    similarity: float


class EmbedDocumentResponse(BaseModel):
    document_id: str
    chunks_embedded: int
    chunks_failed: int
    message: str


# ── Composite response models ──────────────────────────────────────────────────

class DocumentWithCards(BaseModel):
    document: DocumentRow
    chunks: list[DocumentChunkRow] = []
    cards: list[EvidenceCardRow] = []


class SearchResultItem(BaseModel):
    chunk: DocumentChunkRow
    document_filename: str
    cards: list[EvidenceCardRow] = []
    similarity: Optional[float] = None
    retrieval_mode: Optional[str] = None


class EvidenceCheckResult(BaseModel):
    argument_label: Optional[str]
    claim_text: str
    evidence_text_from_speech: Optional[str]
    matched_card: Optional[EvidenceCardRow]
    support_level: str
    explanation: str
    # RAG fields
    matched_chunk_ids: list[str] = []
    top_similarity: Optional[float] = None
    retrieved_snippets: list[dict[str, Any]] = []
    support_rationale: Optional[str] = None
    missing_link: Optional[str] = None
    retrieval_mode: Optional[str] = None
