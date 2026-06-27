#!/usr/bin/env bash
# RoundLab — Local test environment setup.
#
# Starts local Supabase when needed, applies all migrations, creates
# deterministic authentication users, seeds Training OS fixtures, and writes
# local test environment files.
#
# Usage:
#   bash scripts/setup_local_test_env.sh
#   bash scripts/setup_local_test_env.sh --skip-start
#   bash scripts/setup_local_test_env.sh --reseed
#   bash scripts/setup_local_test_env.sh --skip-start --reseed
#
# Prerequisites:
#   - Docker
#   - Node/npm
#   - Supabase CLI through `npx supabase`
#   - curl
#
# After this script completes:
#   cd backend
#   python -m pytest tests/test_pass21p4_rls_enforcement.py -v
#
#   cd ../frontend
#   npx playwright test e2e/trainingOS.spec.ts

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

SKIP_START=false
RESEED=false

# ── Output helpers ────────────────────────────────────────────────────────────

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok() {
  printf '%b✔%b  %s\n' "$GREEN" "$NC" "$1"
}

warn() {
  printf '%b⚠%b  %s\n' "$YELLOW" "$NC" "$1"
}

err() {
  printf '%b✖%b  %s\n' "$RED" "$NC" "$1" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage:
  bash scripts/setup_local_test_env.sh [options]

Options:
  --skip-start   Do not run `supabase start`; require an existing local stack
  --reseed       Refresh deterministic test users and database fixtures
  --help         Show this help message
EOF
}

# ── Arguments ─────────────────────────────────────────────────────────────────

for arg in "$@"; do
  case "$arg" in
    --skip-start)
      SKIP_START=true
      ;;
    --reseed)
      RESEED=true
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      err "Unknown argument: $arg"
      ;;
  esac
done

# ── Prerequisite checks ───────────────────────────────────────────────────────

for command_name in docker npx curl awk grep sed mktemp; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    err "Required command is unavailable: $command_name"
  fi
done

if ! docker info >/dev/null 2>&1; then
  err "Docker is not running. Start Docker Desktop and retry."
fi

ok "Docker is running"

cd "$PROJECT_DIR"

# ── 1. Start Supabase ─────────────────────────────────────────────────────────

if [ "$SKIP_START" = true ]; then
  warn "Skipping Supabase start (--skip-start)"
else
  printf 'Starting local Supabase...\n'

  if npx supabase status -o env >/dev/null 2>&1; then
    ok "Supabase is already running"
  else
    if ! npx supabase start; then
      err "Failed to start local Supabase"
    fi

    ok "Supabase start command completed"
  fi
fi

# ── 2. Read local connection details ─────────────────────────────────────────

env_value() {
  local key="$1"

  awk -v key="$key" '
    index($0, key "=") == 1 {
      value = substr($0, length(key) + 2)
      gsub(/^"|"$/, "", value)
      print value
      exit
    }
  '
}

SUPABASE_STATUS=""
SUPABASE_URL=""
ANON_KEY=""
SERVICE_KEY=""
DB_URL=""

for _ in $(seq 1 30); do
  if SUPABASE_STATUS="$(
    cd "$PROJECT_DIR"
    npx supabase status -o env 2>/dev/null
  )"; then
    SUPABASE_URL="$(
      printf '%s\n' "$SUPABASE_STATUS" | env_value API_URL
    )"

    ANON_KEY="$(
      printf '%s\n' "$SUPABASE_STATUS" | env_value ANON_KEY
    )"

    SERVICE_KEY="$(
      printf '%s\n' "$SUPABASE_STATUS" | env_value SERVICE_ROLE_KEY
    )"

    DB_URL="$(
      printf '%s\n' "$SUPABASE_STATUS" | env_value DB_URL
    )"

    # Support newer CLI naming if legacy names are not present.
    if [ -z "$ANON_KEY" ]; then
      ANON_KEY="$(
        printf '%s\n' "$SUPABASE_STATUS" | env_value PUBLISHABLE_KEY
      )"
    fi

    if [ -z "$SERVICE_KEY" ]; then
      SERVICE_KEY="$(
        printf '%s\n' "$SUPABASE_STATUS" | env_value SECRET_KEY
      )"
    fi

    if [ -n "$SUPABASE_URL" ] &&
       [ -n "$ANON_KEY" ] &&
       [ -n "$SERVICE_KEY" ]; then
      break
    fi
  fi

  sleep 1
done

if [ -z "$SUPABASE_URL" ]; then
  err "API_URL was missing from Supabase status output"
fi

if [ -z "$ANON_KEY" ]; then
  err "ANON_KEY or PUBLISHABLE_KEY was missing from Supabase status output"
fi

if [ -z "$SERVICE_KEY" ]; then
  err "SERVICE_ROLE_KEY or SECRET_KEY was missing from Supabase status output"
fi

if [ -z "$DB_URL" ]; then
  DB_URL="postgresql://postgres:postgres@127.0.0.1:54322/postgres"
fi

ok "Supabase URL: $SUPABASE_URL"

# Wait until the authentication service is actually reachable.
AUTH_READY=false

for _ in $(seq 1 30); do
  if curl -fsS "$SUPABASE_URL/auth/v1/health" >/dev/null 2>&1; then
    AUTH_READY=true
    break
  fi

  sleep 1
done

if [ "$AUTH_READY" != true ]; then
  err "Supabase Auth did not become healthy within 30 seconds"
fi

ok "Supabase Auth is healthy"

# ── 3. Apply migrations ───────────────────────────────────────────────────────

printf 'Applying local migrations...\n'

if ! printf 'Y\n' | npx supabase db push --local >/dev/null 2>&1; then
  err "Failed to apply local migrations"
fi

ok "Migrations applied or already up to date"

# ── 4. Resolve the local database container ──────────────────────────────────

SUPABASE_CONFIG="$PROJECT_DIR/supabase/config.toml"

if [ ! -f "$SUPABASE_CONFIG" ]; then
  err "Supabase configuration was not found: $SUPABASE_CONFIG"
fi

SUPABASE_PROJECT_ID="$(
  awk -F '=' '
    /^[[:space:]]*project_id[[:space:]]*=/ {
      value = $2
      gsub(/[[:space:]"]/, "", value)
      print value
      exit
    }
  ' "$SUPABASE_CONFIG"
)"

if [ -z "$SUPABASE_PROJECT_ID" ]; then
  err "Could not determine project_id from supabase/config.toml"
fi

DB_CONTAINER="supabase_db_${SUPABASE_PROJECT_ID}"

if ! docker inspect "$DB_CONTAINER" >/dev/null 2>&1; then
  err "Local Supabase database container was not found: $DB_CONTAINER"
fi

if [ "$(docker inspect -f '{{.State.Running}}' "$DB_CONTAINER")" != "true" ]; then
  err "Local Supabase database container is not running: $DB_CONTAINER"
fi

ok "Database container is running: $DB_CONTAINER"

# ── 5. Seed deterministic Auth users ─────────────────────────────────────────

STUDENT_A_ID="00000000-0000-0000-0001-000000000001"
COACH_A_ID="00000000-0000-0000-0002-000000000001"
STUDENT_B_ID="00000000-0000-0000-0001-000000000002"
COACH_B_ID="00000000-0000-0000-0002-000000000002"

TEAM_A_ID="00000000-0000-0000-0003-000000000001"
TEAM_B_ID="00000000-0000-0000-0003-000000000002"

TEST_PASSWORD="RoundLab_Test1!"

delete_test_user() {
  local user_id="$1"
  local response_file
  local http_code

  response_file="$(mktemp)"

  http_code="$(
    curl -sS \
      -o "$response_file" \
      -w '%{http_code}' \
      -X DELETE "$SUPABASE_URL/auth/v1/admin/users/$user_id" \
      -H "apikey: $SERVICE_KEY" \
      -H "Authorization: Bearer $SERVICE_KEY"
  )"

  case "$http_code" in
    200|204|404)
      ;;
    *)
      cat "$response_file" >&2
      rm -f "$response_file"
      err "Failed to delete test user $user_id; HTTP $http_code"
      ;;
  esac

  rm -f "$response_file"
}

create_or_update_user() {
  local email="$1"
  local user_id="$2"
  local response_file
  local http_code

  response_file="$(mktemp)"

  http_code="$(
    curl -sS \
      -o "$response_file" \
      -w '%{http_code}' \
      -X POST "$SUPABASE_URL/auth/v1/admin/users" \
      -H "apikey: $SERVICE_KEY" \
      -H "Authorization: Bearer $SERVICE_KEY" \
      -H "Content-Type: application/json" \
      -d "{
        \"email\":\"$email\",
        \"password\":\"$TEST_PASSWORD\",
        \"id\":\"$user_id\",
        \"email_confirm\":true
      }"
  )"

  case "$http_code" in
    200|201)
      rm -f "$response_file"
      return 0
      ;;
    400|409|422)
      if ! grep -Eqi \
        'email_exists|user_already_exists|already been registered|already exists' \
        "$response_file"; then
        cat "$response_file" >&2
        rm -f "$response_file"
        err "Failed to create test user $email; HTTP $http_code"
      fi
      ;;
    *)
      cat "$response_file" >&2
      rm -f "$response_file"
      err "Failed to create test user $email; HTTP $http_code"
      ;;
  esac

  rm -f "$response_file"
  response_file="$(mktemp)"

  http_code="$(
    curl -sS \
      -o "$response_file" \
      -w '%{http_code}' \
      -X PUT "$SUPABASE_URL/auth/v1/admin/users/$user_id" \
      -H "apikey: $SERVICE_KEY" \
      -H "Authorization: Bearer $SERVICE_KEY" \
      -H "Content-Type: application/json" \
      -d "{
        \"password\":\"$TEST_PASSWORD\",
        \"email_confirm\":true
      }"
  )"

  case "$http_code" in
    200)
      ;;
    *)
      cat "$response_file" >&2
      rm -f "$response_file"
      err "Failed to update existing test user $email; HTTP $http_code"
      ;;
  esac

  rm -f "$response_file"
}

if [ "$RESEED" = true ]; then
  warn "Refreshing deterministic test users and fixtures without deleting Auth users"
fi

printf 'Seeding authentication users through the Admin API...\n'

create_or_update_user \
  "test_student_a@roundlab.local" \
  "$STUDENT_A_ID"

create_or_update_user \
  "test_coach_a@roundlab.local" \
  "$COACH_A_ID"

create_or_update_user \
  "test_student_b@roundlab.local" \
  "$STUDENT_B_ID"

create_or_update_user \
  "test_coach_b@roundlab.local" \
  "$COACH_B_ID"

ok "Authentication users created or updated"

# ── 6. Seed profiles, teams, memberships, and Training OS fixtures ───────────

SEED_FILE="$SCRIPT_DIR/seed_test_users.sql"

if [ ! -f "$SEED_FILE" ]; then
  err "Seed SQL file was not found: $SEED_FILE"
fi

printf 'Seeding profiles, teams, memberships, and Training OS data...\n'

SEED_LOG="$(mktemp)"

if ! docker exec -i "$DB_CONTAINER" \
  psql \
    -U postgres \
    -d postgres \
    -v ON_ERROR_STOP=1 \
    < "$SEED_FILE" \
    > "$SEED_LOG" 2>&1; then
  cat "$SEED_LOG" >&2
  rm -f "$SEED_LOG"
  err "Failed to seed local test data"
fi

grep -E 'NOTICE|WARNING' "$SEED_LOG" || true
rm -f "$SEED_LOG"

ok "Database test fixtures seeded"

# ── 7. Verify seeded identities and memberships ───────────────────────────────

USER_COUNT="$(
  docker exec "$DB_CONTAINER" \
    psql -U postgres -d postgres -t -A -c "
      SELECT COUNT(*)
      FROM auth.users
      WHERE
        (id = '$STUDENT_A_ID'::uuid AND email = 'test_student_a@roundlab.local')
        OR
        (id = '$COACH_A_ID'::uuid AND email = 'test_coach_a@roundlab.local')
        OR
        (id = '$STUDENT_B_ID'::uuid AND email = 'test_student_b@roundlab.local')
        OR
        (id = '$COACH_B_ID'::uuid AND email = 'test_coach_b@roundlab.local');
    "
)"

if [ "$USER_COUNT" != "4" ]; then
  err "Expected exactly 4 deterministic authentication users; found $USER_COUNT"
fi

ok "4 deterministic authentication users verified"

PROFILE_COUNT="$(
  docker exec "$DB_CONTAINER" \
    psql -U postgres -d postgres -t -A -c "
      SELECT COUNT(*)
      FROM public.profiles
      WHERE id IN (
        '$STUDENT_A_ID'::uuid,
        '$COACH_A_ID'::uuid,
        '$STUDENT_B_ID'::uuid,
        '$COACH_B_ID'::uuid
      );
    "
)"

if [ "$PROFILE_COUNT" != "4" ]; then
  err "Expected exactly 4 deterministic profiles; found $PROFILE_COUNT"
fi

ok "4 deterministic profiles verified"

TEAM_COUNT="$(
  docker exec "$DB_CONTAINER" \
    psql -U postgres -d postgres -t -A -c "
      SELECT COUNT(*)
      FROM public.teams
      WHERE id IN (
        '$TEAM_A_ID'::uuid,
        '$TEAM_B_ID'::uuid
      );
    "
)"

if [ "$TEAM_COUNT" != "2" ]; then
  err "Expected exactly 2 deterministic teams; found $TEAM_COUNT"
fi

ok "2 deterministic teams verified"

MEMBERSHIP_COUNT="$(
  docker exec "$DB_CONTAINER" \
    psql -U postgres -d postgres -t -A -c "
      SELECT COUNT(*)
      FROM public.team_members
      WHERE
        (
          team_id = '$TEAM_A_ID'::uuid
          AND user_id = '$STUDENT_A_ID'::uuid
          AND role = 'student'
        )
        OR
        (
          team_id = '$TEAM_A_ID'::uuid
          AND user_id = '$COACH_A_ID'::uuid
          AND role = 'coach'
        )
        OR
        (
          team_id = '$TEAM_B_ID'::uuid
          AND user_id = '$STUDENT_B_ID'::uuid
          AND role = 'student'
        )
        OR
        (
          team_id = '$TEAM_B_ID'::uuid
          AND user_id = '$COACH_B_ID'::uuid
          AND role = 'coach'
        );
    "
)"

if [ "$MEMBERSHIP_COUNT" != "4" ]; then
  err "Expected exactly 4 deterministic team memberships; found $MEMBERSHIP_COUNT"
fi

ok "4 deterministic team memberships verified"

# ── 8. Write root .env.test ──────────────────────────────────────────────────

ENV_TEST="$PROJECT_DIR/.env.test"

cat > "$ENV_TEST" <<EOF
# Auto-generated by setup_local_test_env.sh — do not commit

SUPABASE_URL=$SUPABASE_URL
SUPABASE_ANON_KEY=$ANON_KEY
SUPABASE_SERVICE_ROLE_KEY=$SERVICE_KEY
SUPABASE_DB_URL=$DB_URL

# Stable test identities
TEST_STUDENT_A_ID=$STUDENT_A_ID
TEST_COACH_A_ID=$COACH_A_ID
TEST_STUDENT_B_ID=$STUDENT_B_ID
TEST_COACH_B_ID=$COACH_B_ID
TEST_TEAM_A_ID=$TEAM_A_ID
TEST_TEAM_B_ID=$TEAM_B_ID

# Playwright test credentials
TEST_USER_EMAIL=test_student_a@roundlab.local
TEST_USER_PASSWORD=$TEST_PASSWORD
TEST_COACH_EMAIL=test_coach_a@roundlab.local
TEST_COACH_PASSWORD=$TEST_PASSWORD

BASE_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
EOF

chmod 600 "$ENV_TEST"
ok "Written: $ENV_TEST"

# ── 9. Validate or create frontend/.env.local ────────────────────────────────

FRONTEND_ENV="$PROJECT_DIR/frontend/.env.local"

file_env_value() {
  local key="$1"
  local file="$2"

  awk -F '=' -v key="$key" '
    $1 == key {
      value = substr($0, length(key) + 2)
      gsub(/^"|"$/, "", value)
      print value
      exit
    }
  ' "$file"
}

if [ ! -f "$FRONTEND_ENV" ]; then
  cat > "$FRONTEND_ENV" <<EOF
# Auto-generated by setup_local_test_env.sh
NEXT_PUBLIC_SUPABASE_URL=$SUPABASE_URL
NEXT_PUBLIC_SUPABASE_ANON_KEY=$ANON_KEY
EOF

  chmod 600 "$FRONTEND_ENV"
  ok "Written: $FRONTEND_ENV"
else
  EXISTING_URL="$(
    file_env_value NEXT_PUBLIC_SUPABASE_URL "$FRONTEND_ENV"
  )"

  EXISTING_ANON_KEY="$(
    file_env_value NEXT_PUBLIC_SUPABASE_ANON_KEY "$FRONTEND_ENV"
  )"

  if [ "$EXISTING_URL" != "$SUPABASE_URL" ]; then
    err "$FRONTEND_ENV points to '$EXISTING_URL', not local Supabase '$SUPABASE_URL'"
  fi

  if [ "$EXISTING_ANON_KEY" != "$ANON_KEY" ]; then
    err "$FRONTEND_ENV contains a different Supabase anonymous key"
  fi

  ok "$FRONTEND_ENV already points to local Supabase"
fi

# ── 10. Summary ───────────────────────────────────────────────────────────────

printf '\n%b=== Local test environment ready ===%b\n' "$GREEN" "$NC"
printf '  Database:   %s\n' "$DB_URL"
printf '  API:        %s\n' "$SUPABASE_URL"
printf '  Studio:     http://127.0.0.1:54323\n'

printf '\n  Accounts (password: %s):\n' "$TEST_PASSWORD"
printf '    test_student_a@roundlab.local  — student, Team A\n'
printf '    test_coach_a@roundlab.local    — coach, Team A\n'
printf '    test_student_b@roundlab.local  — student, Team B\n'
printf '    test_coach_b@roundlab.local    — coach, Team B\n'

printf '\n  Next steps:\n'
printf '    cd backend\n'
printf '    python -m pytest tests/test_pass21p4_rls_enforcement.py -v\n'
printf '\n'
printf '    cd ../frontend\n'
printf '    npx playwright test e2e/trainingOS.spec.ts --reporter=line\n'

printf '\n  Blank-database migration replay:\n'
printf '    bash scripts/check_supabase_migrations.sh --local\n'
printf '    bash scripts/setup_local_test_env.sh --skip-start --reseed\n'

printf '\n  Stop local Supabase when finished:\n'
printf '    npx supabase stop --workdir %s\n' "$PROJECT_DIR"
