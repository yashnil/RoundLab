-- Pass 13 — Evidence Library Graph, Blockfiles, and Frontline Workflows
-- Apply via Supabase SQL editor or psql.
-- All tables use UUID primary keys. Row-Level Security (RLS) policies follow
-- the same ownership model as existing RoundLab tables.
--
-- Rollback: see DROP TABLE statements at the bottom (commented out by default).

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. resolutions
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS resolutions (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid REFERENCES auth.users(id) ON DELETE CASCADE,
    team_id         uuid,               -- references teams(id); nullable for personal
    title           text NOT NULL,
    normalized_title text NOT NULL,     -- lowercase, trimmed for dedup checks
    season          text,               -- "2024-2025"
    event_type      text NOT NULL DEFAULT 'pf'  -- pf|ld|policy|congress
        CHECK (event_type IN ('pf', 'ld', 'policy', 'congress', 'other')),
    is_active       boolean NOT NULL DEFAULT true,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS resolutions_user_idx         ON resolutions (user_id);
CREATE INDEX IF NOT EXISTS resolutions_team_idx         ON resolutions (team_id) WHERE team_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS resolutions_active_idx       ON resolutions (user_id, is_active);
CREATE INDEX IF NOT EXISTS resolutions_norm_title_idx   ON resolutions (normalized_title);

ALTER TABLE resolutions ENABLE ROW LEVEL SECURITY;

CREATE POLICY resolutions_owner_all ON resolutions
    FOR ALL USING (auth.uid() = user_id);
CREATE POLICY resolutions_team_read ON resolutions
    FOR SELECT USING (team_id IS NOT NULL AND team_id IN (
        SELECT team_id FROM team_members WHERE user_id = auth.uid()
    ));

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. arguments
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS arguments (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    resolution_id       uuid REFERENCES resolutions(id) ON DELETE CASCADE,
    user_id             uuid REFERENCES auth.users(id) ON DELETE CASCADE,
    team_id             uuid,
    side                text NOT NULL DEFAULT 'neutral'
        CHECK (side IN ('pro', 'con', 'neutral')),
    title               text NOT NULL,
    summary             text,
    argument_type       text NOT NULL DEFAULT 'contention'
        CHECK (argument_type IN ('contention', 'value', 'criterion', 'counterplan',
                                  'kritik', 'position', 'framework', 'response', 'other')),
    parent_argument_id  uuid REFERENCES arguments(id) ON DELETE SET NULL,
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS arguments_resolution_idx ON arguments (resolution_id);
CREATE INDEX IF NOT EXISTS arguments_user_idx       ON arguments (user_id);
CREATE INDEX IF NOT EXISTS arguments_side_idx       ON arguments (resolution_id, side);

ALTER TABLE arguments ENABLE ROW LEVEL SECURITY;

CREATE POLICY arguments_owner_all ON arguments
    FOR ALL USING (auth.uid() = user_id);
CREATE POLICY arguments_team_read ON arguments
    FOR SELECT USING (team_id IS NOT NULL AND team_id IN (
        SELECT team_id FROM team_members WHERE user_id = auth.uid()
    ));

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. evidence_sources (normalized source identity)
-- ─────────────────────────────────────────────────────────────────────────────
-- Multiple cards may point to the same source while retaining different cuts,
-- tags, highlights, and debate uses.

CREATE TABLE IF NOT EXISTS evidence_sources (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             uuid REFERENCES auth.users(id) ON DELETE CASCADE,
    -- Deduplication keys (sparse unique indexes below)
    normalized_doi      text,           -- stripped of https://doi.org/ etc.
    canonical_url       text,           -- tracking params stripped
    content_hash        text,           -- SHA-256 of normalized body text
    provider_record_id  text,           -- external provider ID when available
    -- Bibliographic fields
    title               text,
    authors_json        jsonb DEFAULT '[]'::jsonb,   -- list of CitationPerson dicts
    publisher           text,
    container_title     text,
    published_year      integer,
    source_type         text,           -- CSL type string (article-journal|report|etc.)
    -- Structured citation (CitationRecord serialized to JSON)
    citation_record_json jsonb,
    provenance_summary  text,
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now()
);

-- Sparse unique indexes: NULLs are excluded so multiple NULL DOIs coexist.
CREATE UNIQUE INDEX IF NOT EXISTS evidence_sources_doi_idx
    ON evidence_sources (normalized_doi)
    WHERE normalized_doi IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS evidence_sources_url_hash_idx
    ON evidence_sources (canonical_url, content_hash)
    WHERE canonical_url IS NOT NULL AND content_hash IS NOT NULL;

CREATE INDEX IF NOT EXISTS evidence_sources_user_idx  ON evidence_sources (user_id);

ALTER TABLE evidence_sources ENABLE ROW LEVEL SECURITY;

CREATE POLICY evidence_sources_owner ON evidence_sources
    FOR ALL USING (auth.uid() = user_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. library_card_metadata
-- Extends existing evidence_cards with library organisation fields.
-- One row per saved card; card_id references evidence_cards.id (text/uuid).
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS library_card_metadata (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    card_id         text NOT NULL UNIQUE, -- evidence_cards.id
    user_id         uuid REFERENCES auth.users(id) ON DELETE CASCADE,
    resolution_id   uuid REFERENCES resolutions(id) ON DELETE SET NULL,
    argument_id     uuid REFERENCES arguments(id) ON DELETE SET NULL,
    source_id       uuid REFERENCES evidence_sources(id) ON DELETE SET NULL,
    side            text CHECK (side IN ('pro', 'con', 'neutral', null)),
    evidence_role   text,   -- EvidenceRole literal from research.py
    card_status     text NOT NULL DEFAULT 'active'
        CHECK (card_status IN ('active', 'archived', 'flagged')),
    support_verdict text,   -- from evidence verification (supported|partially_supported|unsupported|contradicted)
    user_notes      text,
    tags            jsonb NOT NULL DEFAULT '[]'::jsonb,
    accessed_date   text,   -- ISO date string (set when citation_record is first created)
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS lcm_user_idx        ON library_card_metadata (user_id);
CREATE INDEX IF NOT EXISTS lcm_resolution_idx  ON library_card_metadata (resolution_id) WHERE resolution_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS lcm_argument_idx    ON library_card_metadata (argument_id)   WHERE argument_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS lcm_source_idx      ON library_card_metadata (source_id)     WHERE source_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS lcm_status_idx      ON library_card_metadata (user_id, card_status);
CREATE INDEX IF NOT EXISTS lcm_verdict_idx     ON library_card_metadata (user_id, support_verdict);

ALTER TABLE library_card_metadata ENABLE ROW LEVEL SECURITY;

CREATE POLICY lcm_owner_all ON library_card_metadata
    FOR ALL USING (auth.uid() = user_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. blockfiles
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS blockfiles (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid REFERENCES auth.users(id) ON DELETE CASCADE,
    team_id         uuid,
    resolution_id   uuid REFERENCES resolutions(id) ON DELETE SET NULL,
    title           text NOT NULL,
    side            text CHECK (side IN ('pro', 'con', 'neutral', null)),
    description     text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS blockfiles_user_idx        ON blockfiles (user_id);
CREATE INDEX IF NOT EXISTS blockfiles_resolution_idx  ON blockfiles (resolution_id) WHERE resolution_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS blockfiles_team_idx        ON blockfiles (team_id) WHERE team_id IS NOT NULL;

ALTER TABLE blockfiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY blockfiles_owner_all ON blockfiles
    FOR ALL USING (auth.uid() = user_id);
CREATE POLICY blockfiles_team_read ON blockfiles
    FOR SELECT USING (team_id IS NOT NULL AND team_id IN (
        SELECT team_id FROM team_members WHERE user_id = auth.uid()
    ));

-- ─────────────────────────────────────────────────────────────────────────────
-- 6. blockfile_sections
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS blockfile_sections (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    blockfile_id        uuid NOT NULL REFERENCES blockfiles(id) ON DELETE CASCADE,
    title               text NOT NULL,
    section_type        text NOT NULL DEFAULT 'miscellaneous'
        CHECK (section_type IN (
            'constructive', 'definitions', 'framework', 'contention', 'uniqueness',
            'link', 'internal_link', 'impact', 'responses', 'frontlines', 'turns',
            'defense', 'weighing', 'extensions', 'crossfire', 'miscellaneous'
        )),
    position            integer NOT NULL DEFAULT 0,
    parent_section_id   uuid REFERENCES blockfile_sections(id) ON DELETE SET NULL,
    created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS bfs_blockfile_idx  ON blockfile_sections (blockfile_id);
CREATE INDEX IF NOT EXISTS bfs_position_idx   ON blockfile_sections (blockfile_id, position);

ALTER TABLE blockfile_sections ENABLE ROW LEVEL SECURITY;

-- Sections inherit blockfile ownership
CREATE POLICY bfs_via_blockfile ON blockfile_sections
    FOR ALL USING (
        blockfile_id IN (SELECT id FROM blockfiles WHERE user_id = auth.uid())
    );

-- ─────────────────────────────────────────────────────────────────────────────
-- 7. blockfile_entries
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS blockfile_entries (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    section_id      uuid NOT NULL REFERENCES blockfile_sections(id) ON DELETE CASCADE,
    card_id         text,               -- evidence_cards.id (text); null for analytical notes
    position        integer NOT NULL DEFAULT 0,
    entry_type      text NOT NULL DEFAULT 'evidence_card'
        CHECK (entry_type IN ('evidence_card', 'analytical_note', 'header')),
    custom_label    text,               -- overrides card tag in blockfile context
    notes           text,               -- analytical/coaching note for this card in this blockfile
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS bfe_section_idx  ON blockfile_entries (section_id);
CREATE INDEX IF NOT EXISTS bfe_card_idx     ON blockfile_entries (card_id) WHERE card_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS bfe_position_idx ON blockfile_entries (section_id, position);

ALTER TABLE blockfile_entries ENABLE ROW LEVEL SECURITY;

CREATE POLICY bfe_via_section ON blockfile_entries
    FOR ALL USING (
        section_id IN (
            SELECT id FROM blockfile_sections WHERE blockfile_id IN (
                SELECT id FROM blockfiles WHERE user_id = auth.uid()
            )
        )
    );

-- ─────────────────────────────────────────────────────────────────────────────
-- 8. card_relationships
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS card_relationships (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    from_card_id        text NOT NULL,  -- evidence_cards.id
    to_card_id          text NOT NULL,  -- evidence_cards.id
    relationship_type   text NOT NULL
        CHECK (relationship_type IN (
            'supports', 'contradicts', 'updates', 'qualifies', 'same_finding',
            'stronger_source', 'primary_source_for', 'responds_to', 'turns',
            'mitigates', 'outweighs'
        )),
    confidence          text NOT NULL DEFAULT 'manual'
        CHECK (confidence IN ('manual', 'suggested', 'auto')),
    explanation         text,           -- why this relationship exists
    created_by          uuid REFERENCES auth.users(id) ON DELETE CASCADE,
    confirmed           boolean NOT NULL DEFAULT false,  -- suggested→confirmed by user
    created_at          timestamptz NOT NULL DEFAULT now(),
    UNIQUE (from_card_id, to_card_id, relationship_type)
);

CREATE INDEX IF NOT EXISTS cr_from_card_idx ON card_relationships (from_card_id);
CREATE INDEX IF NOT EXISTS cr_to_card_idx   ON card_relationships (to_card_id);
CREATE INDEX IF NOT EXISTS cr_creator_idx   ON card_relationships (created_by);
CREATE INDEX IF NOT EXISTS cr_type_idx      ON card_relationships (relationship_type);

ALTER TABLE card_relationships ENABLE ROW LEVEL SECURITY;

CREATE POLICY cr_creator_all ON card_relationships
    FOR ALL USING (auth.uid() = created_by);

-- ─────────────────────────────────────────────────────────────────────────────
-- 9. card_versions
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS card_versions (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    card_id         text NOT NULL,              -- evidence_cards.id
    user_id         uuid REFERENCES auth.users(id) ON DELETE CASCADE,
    version_number  integer NOT NULL,
    changed_fields  jsonb NOT NULL DEFAULT '{}'::jsonb,   -- list of field names changed
    previous_values jsonb NOT NULL DEFAULT '{}'::jsonb,   -- {field: old_value}
    new_values      jsonb NOT NULL DEFAULT '{}'::jsonb,   -- {field: new_value}
    reason          text,                       -- user-supplied reason or "citation_edit"
    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (card_id, version_number)
);

CREATE INDEX IF NOT EXISTS cv_card_idx    ON card_versions (card_id);
CREATE INDEX IF NOT EXISTS cv_user_idx    ON card_versions (user_id);
CREATE INDEX IF NOT EXISTS cv_created_idx ON card_versions (card_id, created_at DESC);

ALTER TABLE card_versions ENABLE ROW LEVEL SECURITY;

CREATE POLICY cv_owner_all ON card_versions
    FOR ALL USING (auth.uid() = user_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 10. frontlines
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS frontlines (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid REFERENCES auth.users(id) ON DELETE CASCADE,
    team_id         uuid,
    blockfile_id    uuid REFERENCES blockfiles(id) ON DELETE SET NULL,
    resolution_id   uuid REFERENCES resolutions(id) ON DELETE SET NULL,
    argument_id     uuid REFERENCES arguments(id) ON DELETE SET NULL,
    side            text CHECK (side IN ('pro', 'con', 'neutral', null)),
    title           text NOT NULL,
    opponent_claim  text,
    opponent_warrant text,
    opponent_impact  text,
    opponent_source  text,               -- case reference or known source
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS frontlines_user_idx        ON frontlines (user_id);
CREATE INDEX IF NOT EXISTS frontlines_argument_idx    ON frontlines (argument_id) WHERE argument_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS frontlines_blockfile_idx   ON frontlines (blockfile_id) WHERE blockfile_id IS NOT NULL;

ALTER TABLE frontlines ENABLE ROW LEVEL SECURITY;

CREATE POLICY frontlines_owner_all ON frontlines
    FOR ALL USING (auth.uid() = user_id);
CREATE POLICY frontlines_team_read ON frontlines
    FOR SELECT USING (team_id IS NOT NULL AND team_id IN (
        SELECT team_id FROM team_members WHERE user_id = auth.uid()
    ));

-- ─────────────────────────────────────────────────────────────────────────────
-- 11. frontline_responses
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS frontline_responses (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    frontline_id        uuid NOT NULL REFERENCES frontlines(id) ON DELETE CASCADE,
    response_type       text NOT NULL
        CHECK (response_type IN (
            'no_link', 'link_defense', 'impact_defense', 'uniqueness_takeout',
            'turn', 'counterplan', 'mitigation', 'non_unique', 'weighing',
            'evidence_indictment', 'source_challenge'
        )),
    response_claim      text NOT NULL,
    explanation         text,
    wording_for_speech  text,           -- concise read-aloud wording
    priority            integer NOT NULL DEFAULT 1,  -- 1=best first
    speech_suitability  jsonb NOT NULL DEFAULT '["rebuttal","summary","final_focus"]'::jsonb,
    is_analytical       boolean NOT NULL DEFAULT false,  -- true=no evidence card needed
    position            integer NOT NULL DEFAULT 0,
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS fr_frontline_idx   ON frontline_responses (frontline_id);
CREATE INDEX IF NOT EXISTS fr_priority_idx    ON frontline_responses (frontline_id, priority);
CREATE INDEX IF NOT EXISTS fr_position_idx    ON frontline_responses (frontline_id, position);

ALTER TABLE frontline_responses ENABLE ROW LEVEL SECURITY;

CREATE POLICY fr_via_frontline ON frontline_responses
    FOR ALL USING (
        frontline_id IN (SELECT id FROM frontlines WHERE user_id = auth.uid())
    );

-- ─────────────────────────────────────────────────────────────────────────────
-- 12. frontline_response_cards
-- Junction: one response → many supporting/opposing cards
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS frontline_response_cards (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    response_id uuid NOT NULL REFERENCES frontline_responses(id) ON DELETE CASCADE,
    card_id     text NOT NULL,
    card_role   text NOT NULL DEFAULT 'supporting'
        CHECK (card_role IN ('supporting', 'opposing')),
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (response_id, card_id)
);

CREATE INDEX IF NOT EXISTS frc_response_idx ON frontline_response_cards (response_id);
CREATE INDEX IF NOT EXISTS frc_card_idx     ON frontline_response_cards (card_id);

ALTER TABLE frontline_response_cards ENABLE ROW LEVEL SECURITY;

CREATE POLICY frc_via_response ON frontline_response_cards
    FOR ALL USING (
        response_id IN (
            SELECT id FROM frontline_responses WHERE frontline_id IN (
                SELECT id FROM frontlines WHERE user_id = auth.uid()
            )
        )
    );

-- ─────────────────────────────────────────────────────────────────────────────
-- Updated-at triggers (shared helper function)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DO $$
DECLARE
    tbl text;
BEGIN
    FOREACH tbl IN ARRAY ARRAY['resolutions','arguments','blockfiles','frontlines','frontline_responses','library_card_metadata']
    LOOP
        EXECUTE format(
            'CREATE TRIGGER set_updated_at_%I BEFORE UPDATE ON %I
             FOR EACH ROW EXECUTE FUNCTION set_updated_at()',
            tbl, tbl
        );
    END LOOP;
END;
$$;

-- ─────────────────────────────────────────────────────────────────────────────
-- Rollback (run manually to revert — order matters for FK constraints)
-- ─────────────────────────────────────────────────────────────────────────────
/*
DROP TABLE IF EXISTS frontline_response_cards CASCADE;
DROP TABLE IF EXISTS frontline_responses CASCADE;
DROP TABLE IF EXISTS frontlines CASCADE;
DROP TABLE IF EXISTS card_versions CASCADE;
DROP TABLE IF EXISTS card_relationships CASCADE;
DROP TABLE IF EXISTS blockfile_entries CASCADE;
DROP TABLE IF EXISTS blockfile_sections CASCADE;
DROP TABLE IF EXISTS blockfiles CASCADE;
DROP TABLE IF EXISTS library_card_metadata CASCADE;
DROP TABLE IF EXISTS evidence_sources CASCADE;
DROP TABLE IF EXISTS arguments CASCADE;
DROP TABLE IF EXISTS resolutions CASCADE;
DROP FUNCTION IF EXISTS set_updated_at();
*/
