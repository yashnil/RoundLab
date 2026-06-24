-- Pass 13: Evidence Library — resolutions, arguments, blockfiles, frontlines,
--          relationships, versions, metadata.
-- All tables depend only on auth.users, teams, and evidence_cards (pre-existing).

-- ── resolutions ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS resolutions (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    team_id          uuid REFERENCES teams(id) ON DELETE SET NULL,
    title            text NOT NULL,
    normalized_title text NOT NULL,
    season           text,
    event_type       text NOT NULL DEFAULT 'pf'
                     CHECK (event_type IN ('pf','ld','policy','congress','other')),
    is_active        boolean NOT NULL DEFAULT true,
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_resolutions_user ON resolutions (user_id);
CREATE INDEX IF NOT EXISTS idx_resolutions_team ON resolutions (team_id);
CREATE INDEX IF NOT EXISTS idx_resolutions_active ON resolutions (user_id, is_active);

ALTER TABLE resolutions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "resolutions_owner" ON resolutions
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "resolutions_team_read" ON resolutions
    FOR SELECT USING (
        team_id IS NOT NULL AND
        EXISTS (SELECT 1 FROM team_members tm
                WHERE tm.team_id = resolutions.team_id AND tm.user_id = auth.uid())
    );

CREATE POLICY "resolutions_service_role" ON resolutions
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ── arguments ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS arguments (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    team_id            uuid REFERENCES teams(id) ON DELETE SET NULL,
    resolution_id      uuid REFERENCES resolutions(id) ON DELETE SET NULL,
    parent_argument_id uuid REFERENCES arguments(id) ON DELETE SET NULL,
    title              text NOT NULL,
    argument_type      text NOT NULL DEFAULT 'contention'
                       CHECK (argument_type IN (
                           'contention','value','criterion','counterplan',
                           'kritik','position','framework','response','other'
                       )),
    side               text NOT NULL DEFAULT 'neutral'
                       CHECK (side IN ('pro','con','neutral')),
    summary            text,
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_arguments_user ON arguments (user_id);
CREATE INDEX IF NOT EXISTS idx_arguments_resolution ON arguments (resolution_id);
CREATE INDEX IF NOT EXISTS idx_arguments_type ON arguments (argument_type);

ALTER TABLE arguments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "arguments_owner" ON arguments
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "arguments_service_role" ON arguments
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ── evidence_sources ──────────────────────────────────────────────────────────
-- Normalized, deduplicated source records for citation enrichment.
-- Separate from research_sources (which tracks raw provider results).
CREATE TABLE IF NOT EXISTS evidence_sources (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    normalized_doi       text,
    canonical_url        text,
    content_hash         text,       -- SHA-256 of article body, for dedup
    provider_record_id   text,
    title                text,
    authors_json         jsonb,      -- list of CitationPerson dicts
    publisher            text,
    container_title      text,
    published_year       int,
    source_type          text,
    citation_record_json jsonb,
    provenance_summary   text,
    created_at           timestamptz NOT NULL DEFAULT now(),
    updated_at           timestamptz NOT NULL DEFAULT now(),
    -- Dedup per user: same DOI → same source record
    CONSTRAINT evidence_sources_user_doi_unique UNIQUE (user_id, normalized_doi)
);

CREATE INDEX IF NOT EXISTS idx_evidence_sources_user ON evidence_sources (user_id);
CREATE INDEX IF NOT EXISTS idx_evidence_sources_doi ON evidence_sources (normalized_doi);
CREATE INDEX IF NOT EXISTS idx_evidence_sources_url_hash
    ON evidence_sources (canonical_url, content_hash);

ALTER TABLE evidence_sources ENABLE ROW LEVEL SECURITY;

CREATE POLICY "evidence_sources_owner" ON evidence_sources
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "evidence_sources_service_role" ON evidence_sources
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ── library_card_metadata ─────────────────────────────────────────────────────
-- User-curated metadata for saved evidence cards: status, tags, argument links.
CREATE TABLE IF NOT EXISTS library_card_metadata (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    card_id        uuid NOT NULL REFERENCES evidence_cards(id) ON DELETE CASCADE,
    user_id        uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    source_id      uuid REFERENCES evidence_sources(id) ON DELETE SET NULL,
    resolution_id  uuid REFERENCES resolutions(id) ON DELETE SET NULL,
    argument_id    uuid REFERENCES arguments(id) ON DELETE SET NULL,
    card_status    text NOT NULL DEFAULT 'active'
                   CHECK (card_status IN ('active','archived','flagged')),
    tags           text[] NOT NULL DEFAULT '{}',
    side           text CHECK (side IN ('pro','con','neutral')),
    evidence_role  text,
    support_verdict text CHECK (support_verdict IN (
                        'supported','partially_supported','unsupported','contradicted')),
    user_notes     text,
    accessed_date  text,   -- ISO date string, e.g. "2026-06-22"
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT library_card_metadata_card_user_unique UNIQUE (card_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_library_card_metadata_user ON library_card_metadata (user_id);
CREATE INDEX IF NOT EXISTS idx_library_card_metadata_card ON library_card_metadata (card_id);
CREATE INDEX IF NOT EXISTS idx_library_card_metadata_resolution
    ON library_card_metadata (user_id, resolution_id);

ALTER TABLE library_card_metadata ENABLE ROW LEVEL SECURITY;

CREATE POLICY "library_card_metadata_owner" ON library_card_metadata
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "library_card_metadata_service_role" ON library_card_metadata
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ── blockfiles ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS blockfiles (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    team_id       uuid REFERENCES teams(id) ON DELETE SET NULL,
    resolution_id uuid REFERENCES resolutions(id) ON DELETE SET NULL,
    title         text NOT NULL,
    description   text,
    side          text CHECK (side IN ('pro','con','neutral')),
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_blockfiles_user ON blockfiles (user_id);
CREATE INDEX IF NOT EXISTS idx_blockfiles_resolution ON blockfiles (resolution_id);

ALTER TABLE blockfiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "blockfiles_owner" ON blockfiles
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "blockfiles_team_read" ON blockfiles
    FOR SELECT USING (
        team_id IS NOT NULL AND
        EXISTS (SELECT 1 FROM team_members tm
                WHERE tm.team_id = blockfiles.team_id AND tm.user_id = auth.uid())
    );

CREATE POLICY "blockfiles_service_role" ON blockfiles
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ── blockfile_sections ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS blockfile_sections (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    blockfile_id      uuid NOT NULL REFERENCES blockfiles(id) ON DELETE CASCADE,
    parent_section_id uuid REFERENCES blockfile_sections(id) ON DELETE SET NULL,
    title             text NOT NULL,
    section_type      text NOT NULL DEFAULT 'miscellaneous'
                      CHECK (section_type IN (
                          'constructive','definitions','framework','contention',
                          'uniqueness','link','internal_link','impact','responses',
                          'frontlines','turns','defense','weighing','extensions',
                          'crossfire','miscellaneous'
                      )),
    position          int NOT NULL DEFAULT 0,
    created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_blockfile_sections_blockfile
    ON blockfile_sections (blockfile_id);
CREATE INDEX IF NOT EXISTS idx_blockfile_sections_position
    ON blockfile_sections (blockfile_id, position);

ALTER TABLE blockfile_sections ENABLE ROW LEVEL SECURITY;

CREATE POLICY "blockfile_sections_owner" ON blockfile_sections
    FOR ALL USING (
        EXISTS (SELECT 1 FROM blockfiles b
                WHERE b.id = blockfile_sections.blockfile_id AND b.user_id = auth.uid())
    );

CREATE POLICY "blockfile_sections_service_role" ON blockfile_sections
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ── blockfile_entries ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS blockfile_entries (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    section_id   uuid NOT NULL REFERENCES blockfile_sections(id) ON DELETE CASCADE,
    card_id      uuid REFERENCES evidence_cards(id) ON DELETE SET NULL,
    entry_type   text NOT NULL DEFAULT 'evidence_card'
                 CHECK (entry_type IN ('evidence_card','analytical_note','header')),
    custom_label text,
    notes        text,
    position     int NOT NULL DEFAULT 0,
    created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_blockfile_entries_section ON blockfile_entries (section_id);
CREATE INDEX IF NOT EXISTS idx_blockfile_entries_card ON blockfile_entries (card_id);

ALTER TABLE blockfile_entries ENABLE ROW LEVEL SECURITY;

CREATE POLICY "blockfile_entries_owner" ON blockfile_entries
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM blockfile_sections bs
            JOIN blockfiles b ON b.id = bs.blockfile_id
            WHERE bs.id = blockfile_entries.section_id AND b.user_id = auth.uid()
        )
    );

CREATE POLICY "blockfile_entries_service_role" ON blockfile_entries
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ── frontlines ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS frontlines (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    team_id          uuid REFERENCES teams(id) ON DELETE SET NULL,
    resolution_id    uuid REFERENCES resolutions(id) ON DELETE SET NULL,
    argument_id      uuid REFERENCES arguments(id) ON DELETE SET NULL,
    blockfile_id     uuid REFERENCES blockfiles(id) ON DELETE SET NULL,
    title            text NOT NULL,
    side             text CHECK (side IN ('pro','con','neutral')),
    opponent_claim   text,
    opponent_warrant text,
    opponent_impact  text,
    opponent_source  text,
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_frontlines_user ON frontlines (user_id);
CREATE INDEX IF NOT EXISTS idx_frontlines_argument ON frontlines (argument_id);
CREATE INDEX IF NOT EXISTS idx_frontlines_blockfile ON frontlines (blockfile_id);

ALTER TABLE frontlines ENABLE ROW LEVEL SECURITY;

CREATE POLICY "frontlines_owner" ON frontlines
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "frontlines_service_role" ON frontlines
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ── frontline_responses ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS frontline_responses (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    frontline_id       uuid NOT NULL REFERENCES frontlines(id) ON DELETE CASCADE,
    response_type      text NOT NULL
                       CHECK (response_type IN (
                           'no_link','link_defense','impact_defense','uniqueness_takeout',
                           'turn','counterplan','mitigation','non_unique','weighing',
                           'evidence_indictment','source_challenge'
                       )),
    response_claim     text NOT NULL,
    explanation        text,
    wording_for_speech text,
    priority           int NOT NULL DEFAULT 1 CHECK (priority >= 1),
    speech_suitability text[] NOT NULL DEFAULT '{"rebuttal","summary","final_focus"}',
    is_analytical      boolean NOT NULL DEFAULT false,
    position           int NOT NULL DEFAULT 0,
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_frontline_responses_frontline
    ON frontline_responses (frontline_id);
CREATE INDEX IF NOT EXISTS idx_frontline_responses_type
    ON frontline_responses (frontline_id, response_type);

ALTER TABLE frontline_responses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "frontline_responses_owner" ON frontline_responses
    FOR ALL USING (
        EXISTS (SELECT 1 FROM frontlines f
                WHERE f.id = frontline_responses.frontline_id AND f.user_id = auth.uid())
    );

CREATE POLICY "frontline_responses_service_role" ON frontline_responses
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ── frontline_response_cards ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS frontline_response_cards (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    response_id uuid NOT NULL REFERENCES frontline_responses(id) ON DELETE CASCADE,
    card_id     uuid NOT NULL REFERENCES evidence_cards(id) ON DELETE CASCADE,
    card_role   text NOT NULL DEFAULT 'supporting'
                CHECK (card_role IN ('supporting','opposing')),
    created_at  timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT frontline_response_cards_unique UNIQUE (response_id, card_id)
);

CREATE INDEX IF NOT EXISTS idx_frontline_response_cards_response
    ON frontline_response_cards (response_id);
CREATE INDEX IF NOT EXISTS idx_frontline_response_cards_card
    ON frontline_response_cards (card_id);

ALTER TABLE frontline_response_cards ENABLE ROW LEVEL SECURITY;

CREATE POLICY "frontline_response_cards_owner" ON frontline_response_cards
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM frontline_responses fr
            JOIN frontlines f ON f.id = fr.frontline_id
            WHERE fr.id = frontline_response_cards.response_id AND f.user_id = auth.uid()
        )
    );

CREATE POLICY "frontline_response_cards_service_role" ON frontline_response_cards
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ── card_relationships ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS card_relationships (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    from_card_id      uuid NOT NULL REFERENCES evidence_cards(id) ON DELETE CASCADE,
    to_card_id        uuid NOT NULL REFERENCES evidence_cards(id) ON DELETE CASCADE,
    relationship_type text NOT NULL
                      CHECK (relationship_type IN (
                          'supports','contradicts','updates','qualifies','same_finding',
                          'stronger_source','primary_source_for','responds_to',
                          'turns','mitigates','outweighs'
                      )),
    confidence        text NOT NULL DEFAULT 'manual'
                      CHECK (confidence IN ('manual','suggested','auto')),
    created_by        uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    confirmed         boolean NOT NULL DEFAULT true,
    explanation       text,
    created_at        timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT card_relationships_unique
        UNIQUE (from_card_id, to_card_id, relationship_type)
);

CREATE INDEX IF NOT EXISTS idx_card_relationships_from ON card_relationships (from_card_id);
CREATE INDEX IF NOT EXISTS idx_card_relationships_to ON card_relationships (to_card_id);
CREATE INDEX IF NOT EXISTS idx_card_relationships_creator ON card_relationships (created_by);

ALTER TABLE card_relationships ENABLE ROW LEVEL SECURITY;

CREATE POLICY "card_relationships_creator" ON card_relationships
    FOR ALL USING (auth.uid() = created_by);

CREATE POLICY "card_relationships_service_role" ON card_relationships
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ── card_versions ─────────────────────────────────────────────────────────────
-- Append-only audit log of evidence card mutations.
CREATE TABLE IF NOT EXISTS card_versions (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    card_id         uuid NOT NULL REFERENCES evidence_cards(id) ON DELETE CASCADE,
    user_id         uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    version_number  int NOT NULL,
    changed_fields  jsonb NOT NULL DEFAULT '{}',
    previous_values jsonb NOT NULL DEFAULT '{}',
    new_values      jsonb NOT NULL DEFAULT '{}',
    reason          text,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_card_versions_card ON card_versions (card_id);
CREATE INDEX IF NOT EXISTS idx_card_versions_user ON card_versions (user_id);
CREATE INDEX IF NOT EXISTS idx_card_versions_number
    ON card_versions (card_id, version_number);

ALTER TABLE card_versions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "card_versions_owner" ON card_versions
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "card_versions_service_role" ON card_versions
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ── frontline_performance_log ─────────────────────────────────────────────────
-- Tracks how frontline responses performed in practice rounds.
CREATE TABLE IF NOT EXISTS frontline_performance_log (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    frontline_id         uuid NOT NULL REFERENCES frontlines(id) ON DELETE CASCADE,
    user_id              uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    response_id          uuid REFERENCES frontline_responses(id) ON DELETE SET NULL,
    -- round_simulation_id added in Pass 16 migration once that table exists
    was_used             boolean NOT NULL DEFAULT false,
    outcome              text CHECK (outcome IN ('won','lost','neutral','not_evaluated')),
    opponent_recovered   boolean,
    notes                text,
    created_at           timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_frontline_perf_frontline
    ON frontline_performance_log (frontline_id);
CREATE INDEX IF NOT EXISTS idx_frontline_perf_user
    ON frontline_performance_log (user_id);

ALTER TABLE frontline_performance_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "frontline_performance_log_owner" ON frontline_performance_log
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "frontline_performance_log_service_role" ON frontline_performance_log
    FOR ALL TO service_role USING (true) WITH CHECK (true);

NOTIFY pgrst, 'reload schema';
