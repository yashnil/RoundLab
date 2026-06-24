-- Pass 16: Full-Round PF Simulation Schema
-- append-only flow events, immutable completed speech records, RLS policies

-- ── round_simulations ────────────────────────────────────────────────────────
create table if not exists round_simulations (
  id               uuid primary key default gen_random_uuid(),
  user_id          uuid not null references auth.users(id) on delete cascade,
  team_id          uuid references teams(id) on delete set null,
  config_json      jsonb not null default '{}',
  status           text not null default 'setup'
                   check (status in ('setup','active','paused','completed','abandoned')),
  current_phase    text not null default 'first_constructive',
  phase_history    jsonb not null default '[]',
  is_practice_mode boolean not null default false,
  started_at       timestamptz,
  completed_at     timestamptz,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

create index if not exists idx_round_simulations_user on round_simulations(user_id);
create index if not exists idx_round_simulations_team on round_simulations(team_id);
create index if not exists idx_round_simulations_status on round_simulations(status);

alter table round_simulations enable row level security;

create policy "Users own their round simulations"
  on round_simulations for all
  using (auth.uid() = user_id);

create policy "Service role can manage round simulations"
  on round_simulations for all
  to service_role using (true) with check (true);

-- ── round_participants ────────────────────────────────────────────────────────
create table if not exists round_participants (
  id            uuid primary key default gen_random_uuid(),
  round_id      uuid not null references round_simulations(id) on delete cascade,
  user_id       uuid references auth.users(id) on delete set null,
  is_ai         boolean not null default false,
  side          text not null check (side in ('pro','con')),
  speaker_role  text not null check (speaker_role in ('first','second')),
  display_name  text not null,
  created_at    timestamptz not null default now()
);

create index if not exists idx_round_participants_round on round_participants(round_id);

alter table round_participants enable row level security;

create policy "Users see participants in their rounds"
  on round_participants for select
  using (
    exists (
      select 1 from round_simulations rs
      where rs.id = round_participants.round_id and rs.user_id = auth.uid()
    )
  );

create policy "Service role can manage round participants"
  on round_participants for all
  to service_role using (true) with check (true);

-- ── round_speeches ────────────────────────────────────────────────────────────
-- is_immutable: once true, transcript and audio_url cannot be changed
create table if not exists round_speeches (
  id                      uuid primary key default gen_random_uuid(),
  round_id                uuid not null references round_simulations(id) on delete cascade,
  phase                   text not null,
  speaker_side            text not null check (speaker_side in ('pro','con')),
  is_ai                   boolean not null default false,
  transcript              text,
  audio_url               text,
  argument_labels         jsonb not null default '[]',
  responses_made          jsonb not null default '[]',
  arguments_extended      jsonb not null default '[]',
  arguments_dropped       jsonb not null default '[]',
  evidence_card_ids       jsonb not null default '[]',
  weighing_used           text,
  strategic_goal          text,
  estimated_speaking_time integer,
  legality_violations     jsonb not null default '[]',
  word_count              integer,
  is_immutable            boolean not null default false,
  created_at              timestamptz not null default now()
);

create index if not exists idx_round_speeches_round on round_speeches(round_id);
create index if not exists idx_round_speeches_phase on round_speeches(phase);
create index if not exists idx_round_speeches_speaker on round_speeches(speaker_side);

alter table round_speeches enable row level security;

create policy "Users see speeches in their rounds"
  on round_speeches for select
  using (
    exists (
      select 1 from round_simulations rs
      where rs.id = round_speeches.round_id and rs.user_id = auth.uid()
    )
  );

create policy "Service role can manage round speeches"
  on round_speeches for all
  to service_role using (true) with check (true);

-- ── round_crossfire_exchanges ─────────────────────────────────────────────────
create table if not exists round_crossfire_exchanges (
  id                     uuid primary key default gen_random_uuid(),
  round_id               uuid not null references round_simulations(id) on delete cascade,
  phase                  text not null,
  sequence               integer not null,
  questioner_side        text not null check (questioner_side in ('pro','con')),
  question               text not null,
  answer                 text,
  target_argument        text,
  exchange_type          text not null default 'question',
  concession_extracted   text,
  contradiction          text,
  evasion_detected       boolean not null default false,
  evidence_challenge     text,
  strategic_significance text not null default 'low',
  created_at             timestamptz not null default now()
);

create index if not exists idx_round_crossfire_round on round_crossfire_exchanges(round_id);
create index if not exists idx_round_crossfire_phase on round_crossfire_exchanges(phase);

alter table round_crossfire_exchanges enable row level security;

create policy "Users see crossfire in their rounds"
  on round_crossfire_exchanges for select
  using (
    exists (
      select 1 from round_simulations rs
      where rs.id = round_crossfire_exchanges.round_id and rs.user_id = auth.uid()
    )
  );

create policy "Service role can manage round crossfire"
  on round_crossfire_exchanges for all
  to service_role using (true) with check (true);

-- ── round_arguments ───────────────────────────────────────────────────────────
-- Status is deterministically updated via events; never freely overwritten
create table if not exists round_arguments (
  id                   uuid primary key default gen_random_uuid(),
  round_id             uuid not null references round_simulations(id) on delete cascade,
  label                text not null,
  side                 text not null check (side in ('pro','con')),
  claim                text not null default '',
  warrant              text,
  evidence_card_id     uuid references evidence_cards(id) on delete set null,
  impact               text,
  initial_phase        text not null,
  status               text not null default 'introduced',
  responses            jsonb not null default '[]',
  extensions           jsonb not null default '[]',
  concessions          jsonb not null default '[]',
  weighing             text,
  is_offense           boolean not null default true,
  is_turn              boolean not null default false,
  is_framework         boolean not null default false,
  parent_argument_id   uuid references round_arguments(id) on delete set null,
  last_updated_phase   text,
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  unique (round_id, label)
);

create index if not exists idx_round_arguments_round on round_arguments(round_id);
create index if not exists idx_round_arguments_side on round_arguments(side);
create index if not exists idx_round_arguments_status on round_arguments(status);

alter table round_arguments enable row level security;

create policy "Users see arguments in their rounds"
  on round_arguments for select
  using (
    exists (
      select 1 from round_simulations rs
      where rs.id = round_arguments.round_id and rs.user_id = auth.uid()
    )
  );

create policy "Service role can manage round arguments"
  on round_arguments for all
  to service_role using (true) with check (true);

-- ── round_flow_events ─────────────────────────────────────────────────────────
-- Append-only. Never updated after insert.
create table if not exists round_flow_events (
  id             uuid primary key default gen_random_uuid(),
  round_id       uuid not null references round_simulations(id) on delete cascade,
  phase          text not null,
  event_type     text not null,
  argument_id    uuid not null references round_arguments(id) on delete cascade,
  side           text not null check (side in ('pro','con')),
  description    text not null default '',
  new_status     text not null,
  evidence_card_id uuid references evidence_cards(id) on delete set null,
  created_at     timestamptz not null default now()
);

create index if not exists idx_round_flow_events_round on round_flow_events(round_id);
create index if not exists idx_round_flow_events_argument on round_flow_events(argument_id);
create index if not exists idx_round_flow_events_phase on round_flow_events(phase);

alter table round_flow_events enable row level security;

create policy "Users see flow events in their rounds"
  on round_flow_events for select
  using (
    exists (
      select 1 from round_simulations rs
      where rs.id = round_flow_events.round_id and rs.user_id = auth.uid()
    )
  );

create policy "Service role can manage round flow events"
  on round_flow_events for all
  to service_role using (true) with check (true);

-- ── round_evidence_uses ───────────────────────────────────────────────────────
create table if not exists round_evidence_uses (
  id                        uuid primary key default gen_random_uuid(),
  round_id                  uuid not null references round_simulations(id) on delete cascade,
  speech_id                 uuid not null references round_speeches(id) on delete cascade,
  card_id                   uuid not null references evidence_cards(id) on delete cascade,
  speaker_side              text not null check (speaker_side in ('pro','con')),
  phase                     text not null,
  citation_given            boolean not null default false,
  tag_matched_source        boolean not null default true,
  warrant_explained         boolean not null default false,
  extended_later            boolean not null default false,
  challenged_by_opponent    boolean not null default false,
  challenge_answered        boolean not null default false,
  relevant_to_final_decision boolean not null default false,
  violations                jsonb not null default '[]',
  support_verdict           text,
  source_classification     text,
  flagged                   boolean not null default false,
  created_at                timestamptz not null default now()
);

create index if not exists idx_round_evidence_uses_round on round_evidence_uses(round_id);
create index if not exists idx_round_evidence_uses_card on round_evidence_uses(card_id);
create index if not exists idx_round_evidence_uses_phase on round_evidence_uses(phase);

alter table round_evidence_uses enable row level security;

create policy "Users see evidence uses in their rounds"
  on round_evidence_uses for select
  using (
    exists (
      select 1 from round_simulations rs
      where rs.id = round_evidence_uses.round_id and rs.user_id = auth.uid()
    )
  );

create policy "Service role can manage round evidence uses"
  on round_evidence_uses for all
  to service_role using (true) with check (true);

-- ── round_decisions ───────────────────────────────────────────────────────────
create table if not exists round_decisions (
  id                   uuid primary key default gen_random_uuid(),
  round_id             uuid not null references round_simulations(id) on delete cascade,
  judge_type           text not null,
  engine_version       text not null default 'v1',
  winner               text not null check (winner in ('pro','con')),
  reason_for_decision  text not null default '',
  voting_issues        jsonb not null default '[]',
  speaker_points       jsonb not null default '{}',
  decisive_concessions jsonb not null default '[]',
  dropped_arguments    jsonb not null default '[]',
  evidence_issues      jsonb not null default '[]',
  weighing_comparison  text not null default '',
  legality_issues      jsonb not null default '[]',
  adaptation_successes jsonb not null default '[]',
  adaptation_failures  jsonb not null default '[]',
  decision_trace       jsonb not null default '{}',
  created_at           timestamptz not null default now()
);

create index if not exists idx_round_decisions_round on round_decisions(round_id);
create index if not exists idx_round_decisions_judge on round_decisions(judge_type);

alter table round_decisions enable row level security;

create policy "Users see decisions for their rounds"
  on round_decisions for select
  using (
    exists (
      select 1 from round_simulations rs
      where rs.id = round_decisions.round_id and rs.user_id = auth.uid()
    )
  );

create policy "Service role can manage round decisions"
  on round_decisions for all
  to service_role using (true) with check (true);

-- ── round_drills ──────────────────────────────────────────────────────────────
create table if not exists round_drills (
  id                  uuid primary key default gen_random_uuid(),
  round_id            uuid not null references round_simulations(id) on delete cascade,
  drill_id            uuid not null default gen_random_uuid(),
  source              jsonb not null default '{}',
  skill_target        text not null,
  title               text not null,
  prompt              text not null,
  success_criteria    jsonb not null default '[]',
  time_limit_seconds  integer not null default 90,
  created_at          timestamptz not null default now()
);

create index if not exists idx_round_drills_round on round_drills(round_id);

alter table round_drills enable row level security;

create policy "Users see drills for their rounds"
  on round_drills for select
  using (
    exists (
      select 1 from round_simulations rs
      where rs.id = round_drills.round_id and rs.user_id = auth.uid()
    )
  );

create policy "Service role can manage round drills"
  on round_drills for all
  to service_role using (true) with check (true);

-- ── opponent_round_plans ──────────────────────────────────────────────────────
create table if not exists opponent_round_plans (
  id                       uuid primary key default gen_random_uuid(),
  round_id                 uuid not null references round_simulations(id) on delete cascade,
  side                     text not null check (side in ('pro','con')),
  difficulty               text not null,
  judge_type               text not null,
  constructive_arguments   jsonb not null default '[]',
  expected_responses       jsonb not null default '[]',
  frontline_priorities     jsonb not null default '[]',
  preferred_collapse       text,
  weighing_strategy        text not null default '',
  speech_stage_goals       jsonb not null default '{}',
  approved_card_ids        jsonb not null default '[]',
  approved_frontline_ids   jsonb not null default '[]',
  created_at               timestamptz not null default now()
);

create index if not exists idx_opponent_plans_round on opponent_round_plans(round_id);

alter table opponent_round_plans enable row level security;

create policy "Users see opponent plans for their rounds"
  on opponent_round_plans for select
  using (
    exists (
      select 1 from round_simulations rs
      where rs.id = opponent_round_plans.round_id and rs.user_id = auth.uid()
    )
  );

create policy "Service role can manage opponent round plans"
  on opponent_round_plans for all
  to service_role using (true) with check (true);

-- ── round_adaptation_reviews ──────────────────────────────────────────────────
create table if not exists round_adaptation_reviews (
  id                    uuid primary key default gen_random_uuid(),
  round_id              uuid not null references round_simulations(id) on delete cascade,
  judge_type            text not null,
  adaptation_successes  jsonb not null default '[]',
  adaptation_failures   jsonb not null default '[]',
  how_other_judge_sees  text,
  alternate_judge_type  text,
  created_at            timestamptz not null default now()
);

create index if not exists idx_round_adaptation_reviews_round on round_adaptation_reviews(round_id);

alter table round_adaptation_reviews enable row level security;

create policy "Users see adaptation reviews for their rounds"
  on round_adaptation_reviews for select
  using (
    exists (
      select 1 from round_simulations rs
      where rs.id = round_adaptation_reviews.round_id and rs.user_id = auth.uid()
    )
  );

create policy "Service role can manage round adaptation reviews"
  on round_adaptation_reviews for all
  to service_role using (true) with check (true);

-- ── prep_gaps: add round_simulation_id column ─────────────────────────────────
-- Allow gaps to be linked back to the simulation that discovered them
alter table prep_gaps
  add column if not exists round_simulation_id uuid references round_simulations(id) on delete set null;

-- ── updated_at triggers ───────────────────────────────────────────────────────
create or replace function update_round_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_round_simulations_updated_at on round_simulations;
create trigger trg_round_simulations_updated_at
  before update on round_simulations
  for each row execute function update_round_updated_at();

drop trigger if exists trg_round_arguments_updated_at on round_arguments;
create trigger trg_round_arguments_updated_at
  before update on round_arguments
  for each row execute function update_round_updated_at();
