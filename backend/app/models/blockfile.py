from __future__ import annotations
from typing import Any, Optional
from datetime import datetime
from pydantic import BaseModel


# ── Block entry ───────────────────────────────────────────────────────────────

ENTRY_TYPES = frozenset({"block", "frontline", "answer", "turn", "defense", "weighing", "overview", "unknown"})
SIDE_VALUES  = frozenset({"pro", "con", "aff", "neg", "both"})
COVERAGE_STATUSES = frozenset({"covered", "partially_covered", "missing", "no_available_block"})


class BlockEntryRow(BaseModel):
    id: str
    user_id: str
    document_id: Optional[str] = None
    source_chunk_id: Optional[str] = None
    entry_type: str = "unknown"
    side: Optional[str] = None
    tag: Optional[str] = None
    opponent_claim: Optional[str] = None
    response_text: str
    warrant_text: Optional[str] = None
    evidence_text: Optional[str] = None
    impact_text: Optional[str] = None
    weighing_text: Optional[str] = None
    author: Optional[str] = None
    source: Optional[str] = None
    date: Optional[str] = None
    topic: Optional[str] = None
    metadata_json: dict[str, Any] = {}
    embedding_model: Optional[str] = None
    embedded_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class BlockEntryCreate(BaseModel):
    """Internal shape used when inserting entries (before DB assigns id/timestamps)."""
    user_id: str
    document_id: Optional[str] = None
    source_chunk_id: Optional[str] = None
    entry_type: str = "unknown"
    side: Optional[str] = None
    tag: Optional[str] = None
    opponent_claim: Optional[str] = None
    response_text: str
    warrant_text: Optional[str] = None
    evidence_text: Optional[str] = None
    impact_text: Optional[str] = None
    weighing_text: Optional[str] = None
    author: Optional[str] = None
    source: Optional[str] = None
    date: Optional[str] = None
    topic: Optional[str] = None
    metadata_json: dict[str, Any] = {}


class BlockSearchResult(BaseModel):
    id: str
    document_id: Optional[str] = None
    entry_type: str
    side: Optional[str] = None
    tag: Optional[str] = None
    opponent_claim: Optional[str] = None
    response_text: str
    warrant_text: Optional[str] = None
    evidence_text: Optional[str] = None
    impact_text: Optional[str] = None
    weighing_text: Optional[str] = None
    source: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None
    similarity: Optional[float] = None


# ── Block coverage ─────────────────────────────────────────────────────────────

class BlockCoverageCheck(BaseModel):
    id: str
    user_id: str
    speech_id: str
    argument_id: Optional[str] = None
    claim_text: str
    check_type: str  # "block" | "frontline"
    status: str      # covered | partially_covered | missing | no_available_block
    matched_block_entry_ids: list[str] = []
    top_similarity: Optional[float] = None
    rationale: Optional[str] = None
    missing_piece: Optional[str] = None
    suggested_drill_json: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class BlockCoverageResult(BaseModel):
    """Un-persisted result from classification, used before insert."""
    argument_id: Optional[str] = None
    claim_text: str
    check_type: str
    status: str
    matched_entries: list[BlockSearchResult] = []
    top_similarity: Optional[float] = None
    rationale: str
    missing_piece: Optional[str] = None
    suggested_drill_json: Optional[dict[str, Any]] = None


# ── API request/response shapes ───────────────────────────────────────────────

class ExtractBlocksRequest(BaseModel):
    user_id: str
    document_role: Optional[str] = None
    topic: Optional[str] = None
    side: Optional[str] = None
    force_regenerate: bool = False


class ExtractBlocksResponse(BaseModel):
    document_id: str
    entries_extracted: int
    entries_embedded: int
    entries: list[BlockEntryRow]


class BlockCoverageRequest(BaseModel):
    user_id: str
    force_rerun: bool = False


class BlockCoverageResponse(BaseModel):
    speech_id: str
    checks: list[BlockCoverageCheck]
    covered_count: int
    partially_covered_count: int
    missing_count: int
    no_available_block_count: int
    total_block_entries: int


class PatchBlockEntryRequest(BaseModel):
    user_id: str
    entry_type: Optional[str] = None
    side: Optional[str] = None
    tag: Optional[str] = None
    opponent_claim: Optional[str] = None
    response_text: Optional[str] = None
    warrant_text: Optional[str] = None
    evidence_text: Optional[str] = None
    impact_text: Optional[str] = None
    weighing_text: Optional[str] = None
    topic: Optional[str] = None
