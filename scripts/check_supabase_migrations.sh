#!/usr/bin/env bash
# Dissio — Supabase migration validation script.
#
# Validates migration filenames, checks for ordering/duplicate issues, runs
# the static schema tests, and optionally replays the full migration chain on
# a clean local Supabase database or shows pending migrations via a dry-run.
#
# NEVER connects to the production database by default.
#
# Compatible with bash 3+ (macOS) and bash 5+ (Linux/CI).
#
# Usage:
#   ./scripts/check_supabase_migrations.sh              # filename + static tests
#   ./scripts/check_supabase_migrations.sh --local      # + full local DB replay (Docker required)
#   ./scripts/check_supabase_migrations.sh --dry-run    # + dry-run against linked project
#
# Exit codes:
#   0  all checks passed
#   1  any validation error (duplicates, bad names, ordering, replay failure)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
MIGRATIONS_DIR="$PROJECT_DIR/supabase/migrations"
BACKEND_DIR="$PROJECT_DIR/backend"

MODE="${1:-}"

# ── CLI helper ────────────────────────────────────────────────────────────────
# Prefer the supabase binary already on PATH (e.g. installed by setup-cli@v1
# in CI, or by the user locally); fall back to a pinned npx invocation so the
# script always uses a known-good CLI version.
_SUPABASE_VERSION="2.107.0"
_supabase() {
  if command -v supabase &>/dev/null; then
    supabase "$@"
  else
    npx --yes "supabase@${_SUPABASE_VERSION}" "$@"
  fi
}

echo "==> Dissio migration validator"
echo "    migrations : $MIGRATIONS_DIR"
echo "    mode       : ${MODE:-filename+tests}"
echo ""

# ── 1. Enumerate migration files ──────────────────────────────────────────────
if [[ ! -d "$MIGRATIONS_DIR" ]]; then
  echo "ERROR: migrations directory not found: $MIGRATIONS_DIR" >&2
  exit 1
fi

# Collect basenames in sorted order (bash 3 compatible: no mapfile/readarray).
MIGRATION_FILES=()
while IFS= read -r f; do
  [[ -n "$f" ]] && MIGRATION_FILES+=("$f")
done < <(find "$MIGRATIONS_DIR" -maxdepth 1 -name "*.sql" -exec basename {} \; | sort)

if [[ ${#MIGRATION_FILES[@]} -eq 0 ]]; then
  echo "ERROR: No .sql files found in $MIGRATIONS_DIR" >&2
  exit 1
fi

echo "==> Found ${#MIGRATION_FILES[@]} migration file(s)"

# ── 2. Validate filenames and detect duplicate versions ───────────────────────
# Use a temp file to track seen versions (bash 3 compatible — no declare -A).
SEEN_VERSIONS_FILE="$(mktemp)"
trap 'rm -f "$SEEN_VERSIONS_FILE"' EXIT

ERRORS=0

for base in "${MIGRATION_FILES[@]}"; do
  # Timestamp prefix must be exactly 14 digits followed by an underscore.
  if ! echo "$base" | grep -qE '^[0-9]{14}_'; then
    echo "ERROR: Invalid filename (no 14-digit timestamp prefix): $base" >&2
    ERRORS=$((ERRORS + 1))
    continue
  fi

  version="${base:0:14}"

  if grep -qF "$version" "$SEEN_VERSIONS_FILE" 2>/dev/null; then
    existing="$(grep -F "$version" "$SEEN_VERSIONS_FILE" | head -1)"
    echo "ERROR: Duplicate migration version $version" >&2
    echo "       first : $existing" >&2
    echo "       second: $base" >&2
    ERRORS=$((ERRORS + 1))
  else
    echo "$version $base" >> "$SEEN_VERSIONS_FILE"
  fi
done

if [[ $ERRORS -gt 0 ]]; then
  echo "" >&2
  echo "ERROR: $ERRORS filename/version problem(s) — fix them before proceeding." >&2
  exit 1
fi

echo "==> All migration filenames are valid and versions are unique"

# ── 3. Verify strict ascending timestamp order ────────────────────────────────
PREV_VERSION=""
for base in "${MIGRATION_FILES[@]}"; do
  version="${base:0:14}"
  if [[ -n "$PREV_VERSION" ]] && [[ "$version" < "$PREV_VERSION" ]]; then
    echo "ERROR: Migrations are not in strict ascending order:" >&2
    echo "       $PREV_VERSION → $version" >&2
    exit 1
  fi
  PREV_VERSION="$version"
done

echo "==> Migration timestamps are in strict ascending order"

# ── 4. Static schema / model tests ───────────────────────────────────────────
if [[ -f "$BACKEND_DIR/tests/test_schema_validation.py" ]]; then
  echo ""
  echo "==> Running static schema validation tests..."
  (
    cd "$BACKEND_DIR"
    SUPABASE_URL="https://placeholder.supabase.co" \
    SUPABASE_KEY="placeholder" \
    OPENAI_API_KEY="test-openai-key" \
    CORS_ORIGINS="http://localhost:3000" \
    python -m pytest tests/test_schema_validation.py -q --no-header
  )
  echo "==> Static tests passed"
else
  echo "==> No test_schema_validation.py found; skipping static tests"
fi

# ── 5. Replay all migrations on a clean local database (requires Docker) ──────
if [[ "$MODE" == "--local" ]]; then
  echo ""
  echo "==> Checking Docker availability..."
  if ! command -v docker &>/dev/null; then
    echo "ERROR: docker is not installed — cannot start local Supabase." >&2
    exit 1
  fi
  if ! docker info &>/dev/null 2>&1; then
    echo "ERROR: Docker daemon is not running — cannot start local Supabase." >&2
    exit 1
  fi

  cd "$PROJECT_DIR"

  echo "==> Starting local Postgres (DB container only)..."
  _supabase db start --workdir "$PROJECT_DIR"

  echo ""
  echo "==> Resetting local database and replaying ALL migrations from scratch..."
  _supabase db reset --local --no-seed --workdir "$PROJECT_DIR"

  echo ""
  echo "==> Listing applied migrations on local DB..."
  _supabase migration list --local --workdir "$PROJECT_DIR"

  echo ""
  echo "==> Local migration replay succeeded"
fi

# ── 6. Dry-run against the linked project (read-only, no changes applied) ─────
if [[ "$MODE" == "--dry-run" ]]; then
  echo ""
  echo "==> Dry-run: identifying pending migrations on linked project..."
  echo "    (This is READ-ONLY — no changes will be applied.)"
  cd "$PROJECT_DIR"
  _supabase db push --dry-run --linked --workdir "$PROJECT_DIR"
fi

echo ""
echo "==> All checks passed."
