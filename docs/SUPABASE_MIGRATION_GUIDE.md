# Supabase Migration Guide

How RoundLab manages its database schema safely across local development, CI, and production.

---

## Verification tools — what each one does

| Tool | What it verifies | Modifies DB? |
|---|---|---|
| `migration list` | Ledger alignment (which migrations are recorded in the remote history table) | No |
| `db push --dry-run` | Pending migrations (what *would* be applied next) | No |
| `db reset --local` | Full replay from zero (every migration in strict order on the local DB) | Local only |
| `scripts/audit_remote_schema.sql` | Actual tables, policies, indexes, functions, triggers, constraints, RLS | No |
| `scripts/check_supabase_migrations.sh` | Filename validity, duplicate versions, ordering, static tests | No |

### `migration list` vs `db push --dry-run`

- **`migration list`** shows which migration versions are recorded in the `supabase_migrations.schema_migrations` ledger. A migration can be in the ledger but its DDL could still be missing (e.g., if the migration was manually marked applied without executing it).
- **`db push --dry-run`** shows which local migration files are *not yet in the ledger* — i.e., what would be applied on the next real push.
- **`scripts/audit_remote_schema.sql`** goes deeper: it checks whether the *actual database objects* (tables, columns, indexes, triggers, RLS policies) that each migration was supposed to create actually exist. Use this after any manual intervention.

---

## Running checks locally

### 1. Filename and static validation (no Docker needed)

```bash
bash scripts/check_supabase_migrations.sh
```

Checks: 14-digit timestamps, no duplicate versions, ascending order, Python Pydantic model tests.

### 2. Full local replay (requires Docker)

Replays every migration from scratch on a clean Supabase local database:

```bash
bash scripts/check_supabase_migrations.sh --local
```

This is the gold standard: if it passes, the migration chain is coherent and every migration can be applied to a fresh database without errors.

### 3. Check pending migrations on production (read-only)

Requires the project to be linked (`supabase link --project-ref <ref>`):

```bash
bash scripts/check_supabase_migrations.sh --dry-run
```

Or directly:

```bash
npx supabase db push --dry-run --linked
```

**This is read-only** — it prints what would be applied but makes no changes.

### 4. Object-level drift check

Run `scripts/audit_remote_schema.sql` in the Supabase SQL Editor (Dashboard → SQL Editor). It is a pure `SELECT` query that inspects `pg_class`, `pg_policy`, `pg_indexes`, etc. without touching any data.

For checking linked-project drift from the CLI (read-only, no changes):

```bash
npx supabase migration list --linked
```

---

## CI automation (`.github/workflows/supabase-schema.yml`)

Triggers automatically on pull requests and main-branch pushes that touch migrations or the workflow file.

| Job | Trigger | What it does |
|---|---|---|
| `validate` | PRs, relevant main pushes, manual dispatch | Filename checks + static tests + full local DB replay from scratch using `supabase db start` + `supabase db reset --local`. No production secrets required. |
| `production` | `workflow_dispatch` only | Links to production, shows the ledger, dry-runs pending migrations, and optionally applies them. Requires one approval from the `production` GitHub environment gate. |

### `production` job behaviour by input

| `deploy_to_production` input | What happens |
|---|---|
| `false` (default) | Ledger check + `db push --dry-run` — **read-only, nothing applied** |
| `true` | Dry-run first, then `db push --linked` applies pending migrations |

`--include-all` is never automated regardless of input.

### Why production deployment is manual-only

Database migrations are irreversible DDL. A silent automatic push on every `main` merge would apply schema changes with no human review. The single `production` job requires:

1. A human explicitly triggers `workflow_dispatch`.
2. GitHub environment protection rules (configure under Settings → Environments → `production`) require approval from a designated reviewer.
3. Even with `deploy_to_production=true`, a dry-run runs immediately before the real push as a final safety check.

Combining the ledger check, dry-run, and optional apply into **one job** means only one environment approval gate is needed.

---

## Required GitHub repository secrets

Configure these under **Settings → Secrets and variables → Actions** and assign them to the **`production` environment**:

| Secret | Description |
|---|---|
| `SUPABASE_ACCESS_TOKEN` | Personal access token from `supabase.com/dashboard/account/tokens` — authenticates the CLI against the Supabase Management API |
| `SUPABASE_PROJECT_ID` | Project reference (the short alphanumeric string in your project URL, e.g. `abcdefghijklmnop`) |
| `SUPABASE_DB_PASSWORD` | Database password set when the project was created (Dashboard → Project Settings → Database) |

Also configure the **`production` environment** under Settings → Environments:
- Add required reviewers for deployment approval.
- Optionally restrict deployment branches to `main` only.

---

## Rules for creating new migrations

1. **Always use a new forward migration file.** Never edit an already-applied migration.
2. **Timestamp must be 14 digits** (`YYYYMMDDHHmmss`) and strictly greater than all existing timestamps.
3. **Write idempotent SQL where possible** (`CREATE TABLE IF NOT EXISTS`, `ALTER TABLE … ADD COLUMN IF NOT EXISTS`, etc.) so a repeated apply does not error.
4. **Test locally first**: `bash scripts/check_supabase_migrations.sh --local`
5. **Emergency repair**: if a schema fix was applied directly via the Supabase Dashboard (bypassing migrations), create a new migration that documents what was done. Then run `scripts/audit_remote_schema.sql` to confirm the actual state matches the migration chain.

---

## Prohibited operations

- **Never run `supabase db push --include-all` automatically.** This flag forces all local migrations into the ledger without checking what's already applied and is reserved for explicit manual reconciliation after a ledger discrepancy.
- **Never edit the production schema through the Supabase UI** except in an emergency. If you do, immediately follow up with a new migration that makes the local chain match production.
- **Never hardcode project IDs, database URLs, access tokens, or service-role keys** in workflow files or scripts.
