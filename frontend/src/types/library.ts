/** Frontend types for Evidence Library (Pass 13). */

export type Side = "pro" | "con" | "neutral";
export type EventType = "pf" | "ld" | "policy" | "congress" | "other";
export type ArgumentType =
  | "contention" | "value" | "criterion" | "counterplan"
  | "kritik" | "position" | "framework" | "response" | "other";
export type CardStatus = "active" | "archived" | "flagged";
export type SectionType =
  | "constructive" | "definitions" | "framework" | "contention" | "uniqueness"
  | "link" | "internal_link" | "impact" | "responses" | "frontlines" | "turns"
  | "defense" | "weighing" | "extensions" | "crossfire" | "miscellaneous";
export type EntryType = "evidence_card" | "analytical_note" | "header";
export type RelationshipType =
  | "supports" | "contradicts" | "updates" | "qualifies" | "same_finding"
  | "stronger_source" | "primary_source_for" | "responds_to" | "turns"
  | "mitigates" | "outweighs";
export type RelationshipConfidence = "manual" | "suggested" | "auto";
export type ResponseType =
  | "no_link" | "link_defense" | "impact_defense" | "uniqueness_takeout"
  | "turn" | "counterplan" | "mitigation" | "non_unique" | "weighing"
  | "evidence_indictment" | "source_challenge";

// ── Resolution ────────────────────────────────────────────────────────────────

export interface Resolution {
  id: string;
  user_id: string;
  team_id?: string;
  title: string;
  normalized_title: string;
  season?: string;
  event_type: EventType;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ── Argument ──────────────────────────────────────────────────────────────────

export interface Argument {
  id: string;
  resolution_id?: string;
  user_id: string;
  team_id?: string;
  side: Side;
  title: string;
  summary?: string;
  argument_type: ArgumentType;
  parent_argument_id?: string;
  created_at: string;
  updated_at: string;
}

// ── EvidenceSource ────────────────────────────────────────────────────────────

export interface EvidenceSource {
  id: string;
  user_id: string;
  normalized_doi?: string;
  canonical_url?: string;
  content_hash?: string;
  title?: string;
  authors_json: Record<string, unknown>[];
  publisher?: string;
  container_title?: string;
  published_year?: number;
  source_type?: string;
  citation_record_json?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

// ── Library card metadata ─────────────────────────────────────────────────────

export interface LibraryCardMetadata {
  id: string;
  card_id: string;
  user_id: string;
  resolution_id?: string;
  argument_id?: string;
  source_id?: string;
  side?: Side;
  evidence_role?: string;
  card_status: CardStatus;
  support_verdict?: string;
  user_notes?: string;
  tags: string[];
  accessed_date?: string;
  created_at: string;
  updated_at: string;
}

// ── Blockfile ─────────────────────────────────────────────────────────────────

export interface Blockfile {
  id: string;
  user_id: string;
  team_id?: string;
  resolution_id?: string;
  title: string;
  side?: Side;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface BlockfileSection {
  id: string;
  blockfile_id: string;
  title: string;
  section_type: SectionType;
  position: number;
  parent_section_id?: string;
  created_at: string;
}

export interface BlockfileEntry {
  id: string;
  section_id: string;
  card_id?: string;
  position: number;
  entry_type: EntryType;
  custom_label?: string;
  notes?: string;
  created_at: string;
}

// ── CardRelationship ──────────────────────────────────────────────────────────

export interface CardRelationship {
  id: string;
  from_card_id: string;
  to_card_id: string;
  relationship_type: RelationshipType;
  confidence: RelationshipConfidence;
  explanation?: string;
  created_by: string;
  confirmed: boolean;
  created_at: string;
}

// ── CardVersion ───────────────────────────────────────────────────────────────

export interface CardVersion {
  id: string;
  card_id: string;
  user_id: string;
  version_number: number;
  changed_fields: Record<string, unknown>;
  previous_values: Record<string, unknown>;
  new_values: Record<string, unknown>;
  reason?: string;
  created_at: string;
}

// ── Frontline ─────────────────────────────────────────────────────────────────

export interface Frontline {
  id: string;
  user_id: string;
  team_id?: string;
  blockfile_id?: string;
  resolution_id?: string;
  argument_id?: string;
  side?: Side;
  title: string;
  opponent_claim?: string;
  opponent_warrant?: string;
  opponent_impact?: string;
  opponent_source?: string;
  created_at: string;
  updated_at: string;
}

export interface FrontlineResponse {
  id: string;
  frontline_id: string;
  response_type: ResponseType;
  response_claim: string;
  explanation?: string;
  wording_for_speech?: string;
  priority: number;
  speech_suitability: string[];
  is_analytical: boolean;
  position: number;
  created_at: string;
  updated_at: string;
}

export interface FrontlineResponseCard {
  id: string;
  response_id: string;
  card_id: string;
  card_role: "supporting" | "opposing";
  created_at: string;
}

// ── Search ────────────────────────────────────────────────────────────────────

export interface LibrarySearchResult {
  card_id: string;
  tag?: string;
  cite?: string;
  body_preview: string;
  resolution_id?: string;
  resolution_title?: string;
  argument_id?: string;
  argument_title?: string;
  side?: string;
  evidence_role?: string;
  support_verdict?: string;
  card_status: string;
  user_notes?: string;
  tags: string[];
  saved_at: string;
}

export interface LibrarySearchResponse {
  results: LibrarySearchResult[];
  total: number;
  offset: number;
  has_more: boolean;
}
