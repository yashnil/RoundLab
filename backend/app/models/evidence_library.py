"""Pydantic models for the Evidence Library (Pass 13).

Tables: resolutions · arguments · evidence_sources · library_card_metadata ·
        blockfiles · blockfile_sections · blockfile_entries ·
        card_relationships · card_versions ·
        frontlines · frontline_responses · frontline_response_cards
"""

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

# ── Literals ─────────────────────────────────────────────────────────────────

EventType = Literal["pf", "ld", "policy", "congress", "other"]
Side = Literal["pro", "con", "neutral"]
ArgumentType = Literal[
    "contention", "value", "criterion", "counterplan",
    "kritik", "position", "framework", "response", "other",
]
CardStatus = Literal["active", "archived", "flagged"]
SectionType = Literal[
    "constructive", "definitions", "framework", "contention", "uniqueness",
    "link", "internal_link", "impact", "responses", "frontlines", "turns",
    "defense", "weighing", "extensions", "crossfire", "miscellaneous",
]
EntryType = Literal["evidence_card", "analytical_note", "header"]
RelationshipType = Literal[
    "supports", "contradicts", "updates", "qualifies", "same_finding",
    "stronger_source", "primary_source_for", "responds_to", "turns",
    "mitigates", "outweighs",
]
RelationshipConfidence = Literal["manual", "suggested", "auto"]
ResponseType = Literal[
    "no_link", "link_defense", "impact_defense", "uniqueness_takeout",
    "turn", "counterplan", "mitigation", "non_unique", "weighing",
    "evidence_indictment", "source_challenge",
]
CardRole = Literal["supporting", "opposing"]
SupportVerdict = Literal[
    "supported", "partially_supported", "unsupported", "contradicted",
]

# ── Resolution ────────────────────────────────────────────────────────────────

class ResolutionCreate(BaseModel):
    user_id: str
    title: str
    season: Optional[str] = None
    event_type: EventType = "pf"
    team_id: Optional[str] = None
    is_active: bool = True


class ResolutionUpdate(BaseModel):
    user_id: str
    title: Optional[str] = None
    season: Optional[str] = None
    event_type: Optional[EventType] = None
    is_active: Optional[bool] = None


class ResolutionRow(BaseModel):
    id: str
    user_id: str
    team_id: Optional[str] = None
    title: str
    normalized_title: str
    season: Optional[str] = None
    event_type: EventType = "pf"
    is_active: bool = True
    created_at: str
    updated_at: str


# ── Argument ──────────────────────────────────────────────────────────────────

class ArgumentCreate(BaseModel):
    user_id: str
    resolution_id: Optional[str] = None
    side: Side = "neutral"
    title: str
    summary: Optional[str] = None
    argument_type: ArgumentType = "contention"
    parent_argument_id: Optional[str] = None
    team_id: Optional[str] = None


class ArgumentUpdate(BaseModel):
    user_id: str
    title: Optional[str] = None
    summary: Optional[str] = None
    argument_type: Optional[ArgumentType] = None
    side: Optional[Side] = None
    parent_argument_id: Optional[str] = None


class ArgumentRow(BaseModel):
    id: str
    resolution_id: Optional[str] = None
    user_id: str
    team_id: Optional[str] = None
    side: Side = "neutral"
    title: str
    summary: Optional[str] = None
    argument_type: ArgumentType = "contention"
    parent_argument_id: Optional[str] = None
    created_at: str
    updated_at: str


# ── EvidenceSource (normalized source identity) ───────────────────────────────

class EvidenceSourceCreate(BaseModel):
    user_id: str
    normalized_doi: Optional[str] = None
    canonical_url: Optional[str] = None
    content_hash: Optional[str] = None
    provider_record_id: Optional[str] = None
    title: Optional[str] = None
    authors_json: list[dict] = []      # list of CitationPerson dicts
    publisher: Optional[str] = None
    container_title: Optional[str] = None
    published_year: Optional[int] = None
    source_type: Optional[str] = None
    citation_record_json: Optional[dict] = None
    provenance_summary: Optional[str] = None


class EvidenceSourceRow(BaseModel):
    id: str
    user_id: str
    normalized_doi: Optional[str] = None
    canonical_url: Optional[str] = None
    content_hash: Optional[str] = None
    provider_record_id: Optional[str] = None
    title: Optional[str] = None
    authors_json: list[dict] = []
    publisher: Optional[str] = None
    container_title: Optional[str] = None
    published_year: Optional[int] = None
    source_type: Optional[str] = None
    citation_record_json: Optional[dict] = None
    provenance_summary: Optional[str] = None
    created_at: str
    updated_at: str


# ── Library card metadata ─────────────────────────────────────────────────────

class LibraryCardSaveRequest(BaseModel):
    """Request to save a generated card into the library.

    Always preserves the original card_id (evidence_cards.id). Only the
    library-organisation fields are set here — evidence body, source text,
    and support verdict remain as-is on the card row.
    """
    user_id: str
    card_id: str
    resolution_id: Optional[str] = None
    argument_id: Optional[str] = None
    side: Optional[Side] = None
    evidence_role: Optional[str] = None
    card_status: CardStatus = "active"
    support_verdict: Optional[SupportVerdict] = None
    user_notes: Optional[str] = None
    tags: list[str] = []
    accessed_date: Optional[str] = None  # ISO date string; set to today if omitted
    team_id: Optional[str] = None
    # If both DOI and URL are known, the library can find/create a shared EvidenceSource
    source_doi: Optional[str] = None
    source_url: Optional[str] = None
    source_content_hash: Optional[str] = None
    # Override for unsupported/contradicted cards (requires explicit true)
    unsupported_save_override: bool = False


class LibraryCardUpdate(BaseModel):
    user_id: str
    resolution_id: Optional[str] = None
    argument_id: Optional[str] = None
    side: Optional[Side] = None
    evidence_role: Optional[str] = None
    card_status: Optional[CardStatus] = None
    user_notes: Optional[str] = None
    tags: Optional[list[str]] = None


class LibraryCardMetadataRow(BaseModel):
    id: str
    card_id: str
    user_id: str
    resolution_id: Optional[str] = None
    argument_id: Optional[str] = None
    source_id: Optional[str] = None
    side: Optional[Side] = None
    evidence_role: Optional[str] = None
    card_status: CardStatus = "active"
    support_verdict: Optional[str] = None
    user_notes: Optional[str] = None
    tags: list[str] = []
    accessed_date: Optional[str] = None
    created_at: str
    updated_at: str


# ── Blockfile ─────────────────────────────────────────────────────────────────

class BlockfileCreate(BaseModel):
    user_id: str
    title: str
    resolution_id: Optional[str] = None
    side: Optional[Side] = None
    description: Optional[str] = None
    team_id: Optional[str] = None


class BlockfileUpdate(BaseModel):
    user_id: str
    title: Optional[str] = None
    resolution_id: Optional[str] = None
    side: Optional[Side] = None
    description: Optional[str] = None


class BlockfileRow(BaseModel):
    id: str
    user_id: str
    team_id: Optional[str] = None
    resolution_id: Optional[str] = None
    title: str
    side: Optional[Side] = None
    description: Optional[str] = None
    created_at: str
    updated_at: str


# ── BlockfileSection ──────────────────────────────────────────────────────────

class BlockfileSectionCreate(BaseModel):
    blockfile_id: str
    user_id: str          # used for auth checks
    title: str
    section_type: SectionType = "miscellaneous"
    position: int = 0
    parent_section_id: Optional[str] = None


class BlockfileSectionUpdate(BaseModel):
    user_id: str
    title: Optional[str] = None
    section_type: Optional[SectionType] = None
    position: Optional[int] = None


class BlockfileSectionRow(BaseModel):
    id: str
    blockfile_id: str
    title: str
    section_type: SectionType
    position: int
    parent_section_id: Optional[str] = None
    created_at: str


# ── BlockfileEntry ────────────────────────────────────────────────────────────

class BlockfileEntryCreate(BaseModel):
    section_id: str
    user_id: str          # auth check
    card_id: Optional[str] = None
    position: int = 0
    entry_type: EntryType = "evidence_card"
    custom_label: Optional[str] = None
    notes: Optional[str] = None


class BlockfileEntryUpdate(BaseModel):
    user_id: str
    position: Optional[int] = None
    custom_label: Optional[str] = None
    notes: Optional[str] = None


class BlockfileEntryRow(BaseModel):
    id: str
    section_id: str
    card_id: Optional[str] = None
    position: int
    entry_type: EntryType
    custom_label: Optional[str] = None
    notes: Optional[str] = None
    created_at: str


class ReorderEntriesRequest(BaseModel):
    user_id: str
    entry_ids: list[str]   # ordered list → position = index


class ReorderSectionsRequest(BaseModel):
    user_id: str
    section_ids: list[str]


class DuplicateSectionRequest(BaseModel):
    user_id: str
    section_id: str


# ── CardRelationship ──────────────────────────────────────────────────────────

class CardRelationshipCreate(BaseModel):
    user_id: str
    from_card_id: str
    to_card_id: str
    relationship_type: RelationshipType
    confidence: RelationshipConfidence = "manual"
    explanation: Optional[str] = None
    confirmed: bool = True              # manual=confirmed; suggested=awaiting user


class CardRelationshipConfirm(BaseModel):
    user_id: str
    confirmed: bool


class CardRelationshipRow(BaseModel):
    id: str
    from_card_id: str
    to_card_id: str
    relationship_type: RelationshipType
    confidence: RelationshipConfidence
    explanation: Optional[str] = None
    created_by: str
    confirmed: bool
    created_at: str


# ── CardVersion ───────────────────────────────────────────────────────────────

class CardVersionRow(BaseModel):
    id: str
    card_id: str
    user_id: str
    version_number: int
    changed_fields: dict[str, Any]
    previous_values: dict[str, Any]
    new_values: dict[str, Any]
    reason: Optional[str] = None
    created_at: str


class RestoreVersionRequest(BaseModel):
    user_id: str
    reason: Optional[str] = "version_restore"


# ── Frontline ─────────────────────────────────────────────────────────────────

class FrontlineCreate(BaseModel):
    user_id: str
    title: str
    resolution_id: Optional[str] = None
    argument_id: Optional[str] = None
    blockfile_id: Optional[str] = None
    side: Optional[Side] = None
    opponent_claim: Optional[str] = None
    opponent_warrant: Optional[str] = None
    opponent_impact: Optional[str] = None
    opponent_source: Optional[str] = None
    team_id: Optional[str] = None


class FrontlineUpdate(BaseModel):
    user_id: str
    title: Optional[str] = None
    opponent_claim: Optional[str] = None
    opponent_warrant: Optional[str] = None
    opponent_impact: Optional[str] = None
    opponent_source: Optional[str] = None
    argument_id: Optional[str] = None
    blockfile_id: Optional[str] = None


class FrontlineRow(BaseModel):
    id: str
    user_id: str
    team_id: Optional[str] = None
    blockfile_id: Optional[str] = None
    resolution_id: Optional[str] = None
    argument_id: Optional[str] = None
    side: Optional[Side] = None
    title: str
    opponent_claim: Optional[str] = None
    opponent_warrant: Optional[str] = None
    opponent_impact: Optional[str] = None
    opponent_source: Optional[str] = None
    created_at: str
    updated_at: str


# ── FrontlineResponse ─────────────────────────────────────────────────────────

class FrontlineResponseCreate(BaseModel):
    frontline_id: str
    user_id: str
    response_type: ResponseType
    response_claim: str
    explanation: Optional[str] = None
    wording_for_speech: Optional[str] = None
    priority: int = Field(default=1, ge=1)
    speech_suitability: list[str] = ["rebuttal", "summary", "final_focus"]
    is_analytical: bool = False
    position: int = 0


class FrontlineResponseUpdate(BaseModel):
    user_id: str
    response_type: Optional[ResponseType] = None
    response_claim: Optional[str] = None
    explanation: Optional[str] = None
    wording_for_speech: Optional[str] = None
    priority: Optional[int] = None
    speech_suitability: Optional[list[str]] = None
    is_analytical: Optional[bool] = None
    position: Optional[int] = None


class FrontlineResponseRow(BaseModel):
    id: str
    frontline_id: str
    response_type: ResponseType
    response_claim: str
    explanation: Optional[str] = None
    wording_for_speech: Optional[str] = None
    priority: int
    speech_suitability: list[str]
    is_analytical: bool
    position: int
    created_at: str
    updated_at: str


# ── FrontlineResponseCard ─────────────────────────────────────────────────────

class FrontlineResponseCardCreate(BaseModel):
    response_id: str
    user_id: str
    card_id: str
    card_role: CardRole = "supporting"


class FrontlineResponseCardRow(BaseModel):
    id: str
    response_id: str
    card_id: str
    card_role: CardRole
    created_at: str


# ── Library search / filter ───────────────────────────────────────────────────

class LibrarySearchRequest(BaseModel):
    user_id: str
    query: Optional[str] = None
    resolution_id: Optional[str] = None
    argument_id: Optional[str] = None
    side: Optional[Side] = None
    evidence_role: Optional[str] = None
    support_verdict: Optional[SupportVerdict] = None
    card_status: CardStatus = "active"
    tags: list[str] = []
    team_id: Optional[str] = None
    include_team: bool = False
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = 0


class LibrarySearchResult(BaseModel):
    card_id: str
    tag: Optional[str] = None
    cite: Optional[str] = None
    body_preview: str = ""
    resolution_id: Optional[str] = None
    resolution_title: Optional[str] = None
    argument_id: Optional[str] = None
    argument_title: Optional[str] = None
    side: Optional[str] = None
    evidence_role: Optional[str] = None
    support_verdict: Optional[str] = None
    card_status: str = "active"
    user_notes: Optional[str] = None
    tags: list[str] = []
    saved_at: str


class LibrarySearchResponse(BaseModel):
    results: list[LibrarySearchResult]
    total: int
    offset: int
    has_more: bool


# ── Export ────────────────────────────────────────────────────────────────────

class BlockfileExportRequest(BaseModel):
    user_id: str
    blockfile_id: str
    format: Literal["json", "markdown", "docx"] = "json"


class FrontlineExportRequest(BaseModel):
    user_id: str
    frontline_id: str
    format: Literal["json", "markdown"] = "json"


# ── Related-evidence search ───────────────────────────────────────────────────

class RelatedEvidenceSearchRequest(BaseModel):
    user_id: str
    card_id: str
    action: Literal[
        "find_stronger_source",
        "find_newer_evidence",
        "find_primary_source",
        "find_supporting",
        "find_counterevidence",
        "find_impact",
        "find_warrant",
        "find_responses",
    ]


# ── Observability event ───────────────────────────────────────────────────────

class LibraryEvent(BaseModel):
    """Product event payload (never include source text or private notes)."""
    event_type: str
    user_id: str
    metadata: dict[str, Any] = {}
