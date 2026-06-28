"""
Pass 21.4 — Real RLS Enforcement + Security-Definer Hardening Tests.

Tests use authenticated Supabase clients (not mocks) to verify that
Row Level Security policies work as specified for each role, and that
security-definer helpers cannot be abused as membership oracles.

Requirements:
  - Local Supabase running (npx supabase start)
  - Test users seeded (bash scripts/setup_local_test_env.sh)
  - Env: SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY
    OR local defaults are used automatically

Test matrix:
  Actor               | Own data | Team student data | Unrelated | Writes
  ────────────────────────────────────────────────────────────────────────
  Student A           | allowed  | denied (own row)  | denied    | own only
  Coach A             | allowed  | allowed (Team A)  | denied    | via backend
  Student B           | allowed  | denied (own row)  | denied    | own only
  Coach B             | allowed  | allowed (Team B)  | denied    | via backend
  Anon                | denied   | denied            | denied    | denied
  Service role        | all      | all               | all       | all

Tables tested:
  mastery_scores, mastery_evidence, training_plans, training_sessions,
  curriculum_progress, diagnostic_results, coach_calibration,
  coach_mastery_audit, team_members

Security-definer functions tested:
  current_user_team_ids()
  current_user_is_coach_of(uuid)
  current_user_is_team_member(uuid)
  current_user_is_team_coach(uuid)

  Absent / removed:
  get_user_team_ids(uuid)      — arbitrary-UUID oracle, dropped
  is_coach_of(uuid, uuid)      — arbitrary-UUID oracle, dropped
  is_team_member_of(uuid, uuid)— arbitrary-UUID oracle, dropped
"""

from __future__ import annotations

import os
import re
import sys
import pytest
import requests
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

MIGRATIONS_DIR = ROOT.parent / "supabase" / "migrations"

# ── Local Supabase defaults (same values as in setup_local_test_env.sh) ──────

_LOCAL_URL = "http://127.0.0.1:54321"
_LOCAL_ANON = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9"
    ".CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0"
)
_LOCAL_SERVICE = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0"
    ".EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU"
)

SUPABASE_URL = os.environ.get("SUPABASE_URL", _LOCAL_URL)
ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", _LOCAL_ANON)
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", _LOCAL_SERVICE)

# Stable seeded UUIDs (from seed_test_users.sql)
STUDENT_A = "00000000-0000-0000-0001-000000000001"
COACH_A   = "00000000-0000-0000-0002-000000000001"
STUDENT_B = "00000000-0000-0000-0001-000000000002"
COACH_B   = "00000000-0000-0000-0002-000000000002"
TEAM_A    = "00000000-0000-0000-0003-000000000001"
TEAM_B    = "00000000-0000-0000-0003-000000000002"

PASSWORD = "Dissio_Test1!"


# ── Local-URL predicate (zero network calls) ──────────────────────────────────

def _is_local_url(url: str) -> bool:
    """Return True iff *url* targets the known-local Supabase stack.

    Only http://localhost:54321, http://127.0.0.1:54321, and the IPv6
    equivalent are considered local.  Remote Supabase cloud URLs
    (placeholder.supabase.co, *.supabase.co, etc.) always return False
    so no network request is ever attempted against them.
    """
    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        port = parsed.port
    except Exception:
        return False
    return hostname in {"localhost", "127.0.0.1", "::1"} and port == 54321


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _is_local_supabase_running() -> bool:
    """Diagnostic helper: check reachability of a known-local URL only."""
    if not _is_local_url(SUPABASE_URL):
        return False
    try:
        resp = requests.get(f"{SUPABASE_URL}/auth/v1/health", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


def _sign_in(email: str) -> str:
    resp = requests.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers={"apikey": ANON_KEY, "Content-Type": "application/json"},
        json={"email": email, "password": PASSWORD},
        timeout=5,
    )
    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise RuntimeError(f"Sign-in failed for {email}: {data.get('msg', data)}")
    return token


def _rest_get(token: str, table: str, params: dict | None = None) -> list[dict]:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": ANON_KEY,
        "Authorization": f"Bearer {token}",
    }
    resp = requests.get(url, headers=headers, params=params or {"select": "*", "limit": "5"}, timeout=5)
    if resp.status_code not in (200, 206):
        return []
    body = resp.json()
    return body if isinstance(body, list) else []


def _rest_post(token: str, table: str, data: dict) -> tuple[int, dict]:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": ANON_KEY,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    resp = requests.post(url, headers=headers, json=data, timeout=5)
    try:
        body = resp.json()
    except Exception:
        body = {}
    return resp.status_code, body


def _rest_rpc(token: str, fn_name: str, payload: dict) -> tuple[int, object]:
    """Call a Supabase RPC (REST function)."""
    url = f"{SUPABASE_URL}/rest/v1/rpc/{fn_name}"
    headers = {
        "apikey": ANON_KEY,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=5)
    try:
        body = resp.json()
    except Exception:
        body = {}
    return resp.status_code, body


def _service_get(table: str, params: dict | None = None) -> list[dict]:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
    }
    resp = requests.get(url, headers=headers, params=params or {"select": "*"}, timeout=5)
    if resp.status_code not in (200, 206):
        return []
    body = resp.json()
    return body if isinstance(body, list) else []


def _anon_rpc(fn_name: str, payload: dict) -> tuple[int, object]:
    """Call an RPC with the anon key and no user JWT."""
    url = f"{SUPABASE_URL}/rest/v1/rpc/{fn_name}"
    headers = {"apikey": ANON_KEY, "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json=payload, timeout=5)
    try:
        body = resp.json()
    except Exception:
        body = {}
    return resp.status_code, body


# ── Skip gate ─────────────────────────────────────────────────────────────────
#
# Live RLS tests run ONLY when SUPABASE_URL points to the local stack
# (hostname localhost/127.0.0.1/::1, port 54321).  Placeholder or remote
# cloud URLs are never contacted — the predicate is a pure URL parse.
#
# Requirement: when SUPABASE_URL IS local but the stack is down, live tests
# FAIL (rather than silently skipping) so the outage is visible.

_requires_local = pytest.mark.skipif(
    not _is_local_url(SUPABASE_URL),
    reason=(
        f"Live RLS integration tests require a local Supabase stack "
        f"(SUPABASE_URL must be http://127.0.0.1:54321 or http://localhost:54321). "
        f"Current SUPABASE_URL={SUPABASE_URL!r}. "
        "Run: bash scripts/setup_local_test_env.sh"
    ),
)


# ── Token cache (lazy, per-session) ──────────────────────────────────────────

@pytest.fixture(scope="session")
def student_a_token():
    return _sign_in("test_student_a@dissio.local")

@pytest.fixture(scope="session")
def coach_a_token():
    return _sign_in("test_coach_a@dissio.local")

@pytest.fixture(scope="session")
def student_b_token():
    return _sign_in("test_student_b@dissio.local")

@pytest.fixture(scope="session")
def coach_b_token():
    return _sign_in("test_coach_b@dissio.local")


# ═══════════════════════════════════════════════════════════════════════════
# 1. Infrastructure
# ═══════════════════════════════════════════════════════════════════════════

class TestLocalSupabaseAvailability:

    @_requires_local
    def test_supabase_health_endpoint(self):
        """Health check against the local stack.

        Skipped when SUPABASE_URL is not a local address — prevents any
        network contact with placeholder or remote Supabase projects.
        Fails (not skips) if the local stack is configured but down.
        """
        resp = requests.get(f"{SUPABASE_URL}/auth/v1/health", timeout=5)
        assert resp.status_code == 200, (
            f"Local Supabase is not running at {SUPABASE_URL}. "
            "Run: bash scripts/setup_local_test_env.sh"
        )

    @_requires_local
    def test_all_four_accounts_authenticate(self):
        for email in [
            "test_student_a@dissio.local",
            "test_coach_a@dissio.local",
            "test_student_b@dissio.local",
            "test_coach_b@dissio.local",
        ]:
            token = _sign_in(email)
            assert token and len(token) > 20, f"Sign-in failed for {email}"

    @_requires_local
    def test_seeded_mastery_data_present(self):
        rows = _service_get("mastery_scores", {"user_id": f"eq.{STUDENT_A}", "select": "skill_id,mastery_score"})
        assert len(rows) >= 1, "No mastery_scores seeded for Student A — re-run seed script"


# ═══════════════════════════════════════════════════════════════════════════
# 2. Static migration file checks (no DB required)
# ═══════════════════════════════════════════════════════════════════════════

class TestMigrationStaticAnalysis:
    """Verify the migration text satisfies security invariants without running it."""

    FIX_MIGRATION = "20260628000001_fix_team_members_rls.sql"

    def _migration_text(self) -> str:
        path = MIGRATIONS_DIR / self.FIX_MIGRATION
        assert path.exists(), f"{self.FIX_MIGRATION} not found in {MIGRATIONS_DIR}"
        return path.read_text()

    # ── Helper presence / absence ─────────────────────────────────────────

    def test_new_helpers_declared(self):
        text = self._migration_text()
        for fn in [
            "current_user_team_ids",
            "current_user_is_coach_of",
            "current_user_is_team_member",
            "current_user_is_team_coach",
        ]:
            assert fn in text, f"New helper {fn!r} missing from migration"

    def test_old_oracle_functions_dropped(self):
        text = self._migration_text()
        for fn in ["get_user_team_ids", "is_coach_of", "is_team_member_of"]:
            assert f"DROP FUNCTION IF EXISTS public.{fn}" in text or \
                   f"DROP FUNCTION IF EXISTS public.{fn}" in text.replace("\n", " "), (
                f"Old oracle function {fn!r} not explicitly dropped in migration"
            )

    def test_old_oracle_functions_not_recreated(self):
        """The old arbitrary-UUID helpers must not be created again."""
        text = self._migration_text()
        for fn in ["get_user_team_ids(uid", "is_coach_of(coach_uid", "is_team_member_of(uid"]:
            assert fn not in text, (
                f"Old arbitrary-UUID helper signature {fn!r} appears in migration — must be dropped, not recreated"
            )

    # ── search_path = '' ─────────────────────────────────────────────────

    def test_all_new_helpers_have_empty_search_path(self):
        text = self._migration_text()
        # Each function must declare SET search_path = ''
        # Count occurrences of the new function names paired with search_path
        new_fns = [
            "current_user_team_ids",
            "current_user_is_coach_of",
            "current_user_is_team_member",
            "current_user_is_team_coach",
        ]
        # The migration must contain at least N occurrences of "SET search_path = ''"
        # equal to the number of new helpers
        count = text.count("SET search_path = ''")
        assert count >= len(new_fns), (
            f"Expected at least {len(new_fns)} occurrences of \"SET search_path = ''\" "
            f"in migration (one per helper), found {count}"
        )

    def test_no_unsafe_search_path_public(self):
        """search_path = public is unsafe — must not appear in the new helpers section."""
        text = self._migration_text()
        # Allowed in comments; disallowed in actual SET statements for new functions
        # Use a regex to find SET search_path = public (without quotes = unsafe)
        unsafe = re.findall(r"SET\s+search_path\s*=\s*public\b", text, re.IGNORECASE)
        assert not unsafe, (
            "Found 'SET search_path = public' (without quotes) — use SET search_path = '' instead"
        )

    # ── REVOKE / GRANT ────────────────────────────────────────────────────

    def test_revoke_all_from_public_present(self):
        text = self._migration_text()
        count = text.count("REVOKE ALL ON FUNCTION")
        assert count >= 4, (
            f"Expected REVOKE ALL ON FUNCTION for 4 helpers, found {count}"
        )

    def test_grant_only_to_authenticated(self):
        text = self._migration_text()
        # Must GRANT to authenticated
        assert "TO authenticated" in text, "No GRANT ... TO authenticated in migration"
        # Must NOT grant to anon
        assert "TO anon" not in text, "GRANT ... TO anon must not appear — anon should not call helpers"

    def test_no_arbitrary_uid_params_in_new_helpers(self):
        """New helpers must not accept a caller-identity UUID parameter."""
        text = self._migration_text()
        # current_user_team_ids takes NO args
        assert "current_user_team_ids(uid" not in text and \
               "current_user_team_ids( uid" not in text, \
            "current_user_team_ids must not accept a uid parameter"
        # is_coach_of accepted two UUIDs; current_user_is_coach_of must accept only student_uid
        # Ensure it doesn't accept 'coach_uid' or similar
        assert "current_user_is_coach_of(coach_uid" not in text, \
            "current_user_is_coach_of must not accept a coach_uid parameter — caller is always auth.uid()"

    # ── SECURITY DEFINER ──────────────────────────────────────────────────

    def test_security_definer_on_all_new_helpers(self):
        text = self._migration_text()
        count = text.count("SECURITY DEFINER")
        assert count >= 4, f"Expected SECURITY DEFINER on 4 helpers, found {count}"

    # ── coach_calibration write policy dropped ────────────────────────────

    def test_coach_calibration_direct_write_policy_dropped(self):
        text = self._migration_text()
        assert "DROP POLICY IF EXISTS" in text
        assert "'coach_calibration_write'" in text or '"coach_calibration_write"' in text, (
            "Migration must explicitly drop the coach_calibration_write INSERT policy"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 3. mastery_scores RLS
# ═══════════════════════════════════════════════════════════════════════════

@_requires_local
class TestMasteryScoresRLS:

    def test_student_a_sees_own_mastery(self, student_a_token):
        rows = _rest_get(student_a_token, "mastery_scores", {"user_id": f"eq.{STUDENT_A}", "select": "user_id,skill_id"})
        assert len(rows) >= 1, "Student A cannot read own mastery_scores"
        assert all(r["user_id"] == STUDENT_A for r in rows)

    def test_student_a_cannot_see_student_b_mastery(self, student_a_token):
        rows = _rest_get(student_a_token, "mastery_scores", {"user_id": f"eq.{STUDENT_B}", "select": "user_id"})
        assert len(rows) == 0, "Student A can read Student B mastery_scores — RLS violation"

    def test_coach_a_sees_team_student_a_mastery(self, coach_a_token):
        rows = _rest_get(coach_a_token, "mastery_scores", {"user_id": f"eq.{STUDENT_A}", "select": "user_id,skill_id"})
        assert len(rows) >= 1, "Coach A cannot read Student A mastery_scores (should be allowed)"

    def test_coach_b_cannot_see_student_a_mastery(self, coach_b_token):
        rows = _rest_get(coach_b_token, "mastery_scores", {"user_id": f"eq.{STUDENT_A}", "select": "user_id"})
        assert len(rows) == 0, "Coach B can read Student A mastery_scores — cross-team RLS violation"

    def test_service_role_sees_all_mastery(self):
        rows_a = _service_get("mastery_scores", {"user_id": f"eq.{STUDENT_A}", "select": "user_id"})
        assert len(rows_a) >= 1

    def test_student_b_cannot_insert_for_student_a(self, student_b_token):
        status, body = _rest_post(student_b_token, "mastery_scores", {
            "user_id": STUDENT_A,
            "skill_id": "warranting",
            "mastery_score": 99.0,
            "confidence": 1.0,
            "evidence_count": 1,
            "mastery_state": "mastered",
        })
        assert status in (401, 403, 409) or (isinstance(body, list) and len(body) == 0), (
            f"Student B inserted mastery for Student A — RLS violation. status={status}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 4. mastery_evidence RLS
# ═══════════════════════════════════════════════════════════════════════════

@_requires_local
class TestMasteryEvidenceRLS:

    def test_student_a_sees_own_evidence(self, student_a_token):
        rows = _rest_get(student_a_token, "mastery_evidence", {"user_id": f"eq.{STUDENT_A}", "select": "user_id,skill_id"})
        assert len(rows) >= 1, "Student A cannot see own mastery_evidence"

    def test_student_a_cannot_see_student_b_evidence(self, student_a_token):
        rows = _rest_get(student_a_token, "mastery_evidence", {"user_id": f"eq.{STUDENT_B}", "select": "user_id"})
        assert len(rows) == 0, "Student A can read Student B evidence — RLS violation"

    def test_coach_a_can_see_student_a_evidence(self, coach_a_token):
        rows = _rest_get(coach_a_token, "mastery_evidence", {"user_id": f"eq.{STUDENT_A}", "select": "user_id"})
        assert len(rows) >= 1, "Coach A cannot read Student A mastery_evidence"

    def test_coach_b_cannot_see_student_a_evidence(self, coach_b_token):
        rows = _rest_get(coach_b_token, "mastery_evidence", {"user_id": f"eq.{STUDENT_A}", "select": "user_id"})
        assert len(rows) == 0, "Coach B can read Student A evidence — cross-team violation"

    def test_composite_source_index_enforces_uniqueness(self):
        url = f"{SUPABASE_URL}/rest/v1/mastery_evidence"
        headers = {
            "apikey": SERVICE_KEY,
            "Authorization": f"Bearer {SERVICE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        payload = {
            "user_id": STUDENT_A,
            "skill_id": "warranting",
            "raw_score": 5.0,
            "normalized_score": 25.0,
            "source_type": "speech_analysis",
            "source_id": "speech_analysis:seed-speech-001:warranting",
            "change_reason": "duplicate test",
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=5)
        assert resp.status_code in (409, 422, 400), (
            f"Duplicate composite insert did not fail: {resp.status_code}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 5. training_plans RLS
# ═══════════════════════════════════════════════════════════════════════════

@_requires_local
class TestTrainingPlansRLS:

    def test_student_a_sees_own_plan(self, student_a_token):
        rows = _rest_get(student_a_token, "training_plans", {"user_id": f"eq.{STUDENT_A}", "select": "id,user_id"})
        assert len(rows) >= 1, "Student A cannot read own training_plans"

    def test_student_a_cannot_see_student_b_plan(self, student_a_token):
        rows = _rest_get(student_a_token, "training_plans", {"user_id": f"eq.{STUDENT_B}", "select": "id"})
        assert len(rows) == 0, "Student A can read Student B training_plans — RLS violation"

    def test_coach_a_can_see_student_a_plan(self, coach_a_token):
        rows = _rest_get(coach_a_token, "training_plans", {"user_id": f"eq.{STUDENT_A}", "select": "id"})
        assert len(rows) >= 1, "Coach A cannot read Student A training_plans"

    def test_coach_b_cannot_see_student_a_plan(self, coach_b_token):
        rows = _rest_get(coach_b_token, "training_plans", {"user_id": f"eq.{STUDENT_A}", "select": "id"})
        assert len(rows) == 0, "Coach B can read Student A training_plans — cross-team violation"


# ═══════════════════════════════════════════════════════════════════════════
# 6. training_sessions RLS
# ═══════════════════════════════════════════════════════════════════════════

@_requires_local
class TestTrainingSessionsRLS:

    def test_student_a_sees_own_sessions(self, student_a_token):
        rows = _rest_get(student_a_token, "training_sessions", {"user_id": f"eq.{STUDENT_A}", "select": "id,user_id"})
        assert len(rows) >= 1, "Student A cannot read own training_sessions"

    def test_student_b_cannot_see_student_a_sessions(self, student_b_token):
        rows = _rest_get(student_b_token, "training_sessions", {"user_id": f"eq.{STUDENT_A}", "select": "id"})
        assert len(rows) == 0, "Student B can read Student A sessions — RLS violation"

    def test_coach_a_can_see_student_a_sessions(self, coach_a_token):
        rows = _rest_get(coach_a_token, "training_sessions", {"user_id": f"eq.{STUDENT_A}", "select": "id"})
        assert len(rows) >= 1, "Coach A cannot read Student A sessions"

    def test_coach_b_cannot_see_student_a_sessions(self, coach_b_token):
        rows = _rest_get(coach_b_token, "training_sessions", {"user_id": f"eq.{STUDENT_A}", "select": "id"})
        assert len(rows) == 0, "Coach B can read Student A sessions — cross-team violation"

    def test_session_version_column_present(self):
        rows = _service_get("training_sessions", {
            "id": f"eq.00000000-0000-0000-0008-000000000001",
            "select": "id,version",
        })
        if rows:
            assert "version" in rows[0], "version column missing from training_sessions"


# ═══════════════════════════════════════════════════════════════════════════
# 7. team_members RLS visibility
# ═══════════════════════════════════════════════════════════════════════════

@_requires_local
class TestTeamMembersRLS:

    def test_student_a_sees_own_membership_row(self, student_a_token):
        rows = _rest_get(student_a_token, "team_members", {
            "user_id": f"eq.{STUDENT_A}", "select": "user_id,team_id,role"
        })
        assert len(rows) >= 1, "Student A cannot see own team_members row"
        assert all(r["user_id"] == STUDENT_A for r in rows)

    def test_student_a_cannot_see_coach_a_row(self, student_a_token):
        """Students must not enumerate teammates — only own row is visible."""
        rows = _rest_get(student_a_token, "team_members", {
            "user_id": f"eq.{COACH_A}", "select": "user_id"
        })
        assert len(rows) == 0, (
            "Student A can read Coach A team_members row — roster enumeration is possible"
        )

    def test_student_a_cannot_see_student_b_row(self, student_a_token):
        rows = _rest_get(student_a_token, "team_members", {
            "user_id": f"eq.{STUDENT_B}", "select": "user_id"
        })
        assert len(rows) == 0, "Student A can read Student B team_members row — cross-team violation"

    def test_coach_a_can_see_all_team_a_members(self, coach_a_token):
        """Coaches see the full roster for teams they coach."""
        rows = _rest_get(coach_a_token, "team_members", {
            "team_id": f"eq.{TEAM_A}", "select": "user_id,role"
        })
        user_ids = {r["user_id"] for r in rows}
        assert STUDENT_A in user_ids, "Coach A cannot see Student A in their team roster"
        assert COACH_A in user_ids, "Coach A cannot see own row in team roster"

    def test_coach_a_cannot_see_team_b_roster(self, coach_a_token):
        rows = _rest_get(coach_a_token, "team_members", {
            "team_id": f"eq.{TEAM_B}", "select": "user_id"
        })
        assert len(rows) == 0, "Coach A can read Team B roster — cross-team violation"

    def test_anon_cannot_read_team_members(self):
        url = f"{SUPABASE_URL}/rest/v1/team_members"
        resp = requests.get(url, headers={"apikey": ANON_KEY}, timeout=5)
        body = resp.json() if isinstance(resp.json(), list) else []
        assert len(body) == 0, "Anon can read team_members rows"


# ═══════════════════════════════════════════════════════════════════════════
# 8. curriculum_progress and diagnostic_results RLS
# ═══════════════════════════════════════════════════════════════════════════

@_requires_local
class TestCurriculumProgressRLS:

    def test_student_a_sees_own_progress(self, student_a_token):
        rows = _rest_get(student_a_token, "curriculum_progress", {"user_id": f"eq.{STUDENT_A}", "select": "user_id,lesson_id"})
        assert len(rows) >= 1, "Student A cannot read own curriculum_progress"

    def test_student_b_cannot_see_student_a_progress(self, student_b_token):
        rows = _rest_get(student_b_token, "curriculum_progress", {"user_id": f"eq.{STUDENT_A}", "select": "user_id"})
        assert len(rows) == 0, "Student B can read Student A curriculum_progress — violation"

    def test_coach_b_cannot_see_student_a_progress(self, coach_b_token):
        rows = _rest_get(coach_b_token, "curriculum_progress", {"user_id": f"eq.{STUDENT_A}", "select": "user_id"})
        assert len(rows) == 0, "Coach B can read Student A curriculum_progress — cross-team violation"


@_requires_local
class TestDiagnosticResultsRLS:

    def test_student_a_sees_own_diagnostics(self, student_a_token):
        rows = _rest_get(student_a_token, "diagnostic_results", {"user_id": f"eq.{STUDENT_A}", "select": "user_id"})
        assert len(rows) >= 1, "Student A cannot read own diagnostic_results"

    def test_student_b_cannot_see_student_a_diagnostics(self, student_b_token):
        rows = _rest_get(student_b_token, "diagnostic_results", {"user_id": f"eq.{STUDENT_A}", "select": "user_id"})
        assert len(rows) == 0, "Student B can read Student A diagnostics — RLS violation"


# ═══════════════════════════════════════════════════════════════════════════
# 9. coach_calibration RLS
# ═══════════════════════════════════════════════════════════════════════════

@_requires_local
class TestCoachCalibrationRLS:

    def test_team_a_members_can_see_calibration(self, student_a_token):
        rows = _rest_get(student_a_token, "coach_calibration", {"team_id": f"eq.{TEAM_A}", "select": "team_id,standard"})
        assert len(rows) >= 1, "Team A member cannot read Team A calibration"

    def test_team_b_member_cannot_see_team_a_calibration(self, student_b_token):
        rows = _rest_get(student_b_token, "coach_calibration", {"team_id": f"eq.{TEAM_A}", "select": "team_id"})
        assert len(rows) == 0, "Team B student can read Team A calibration — RLS violation"

    def test_student_cannot_insert_calibration_directly(self, student_a_token):
        """Authenticated browser must not be able to write coach_calibration directly."""
        import uuid
        status, body = _rest_post(student_a_token, "coach_calibration", {
            "team_id": TEAM_A,
            "standard": "varsity",
            "judge_emphasis": "technical",
        })
        # No authenticated INSERT policy exists — must be rejected
        assert status in (401, 403, 409), (
            f"Student wrote coach_calibration directly — policy not enforced. status={status}"
        )

    def test_coach_a_cannot_insert_calibration_directly(self, coach_a_token):
        """Coaches must also write through the service-role backend, not directly."""
        status, body = _rest_post(coach_a_token, "coach_calibration", {
            "team_id": TEAM_A,
            "standard": "novice",
            "judge_emphasis": "lay",
        })
        # No authenticated INSERT policy — coach must use backend API
        assert status in (401, 403, 409), (
            f"Coach inserted coach_calibration directly — direct write surface open. status={status}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 10. coach_mastery_audit RLS
# ═══════════════════════════════════════════════════════════════════════════

@_requires_local
class TestCoachMasteryAuditRLS:

    def test_student_cannot_write_audit(self, student_a_token):
        status, body = _rest_post(student_a_token, "coach_mastery_audit", {
            "coach_id": COACH_A,
            "student_id": STUDENT_A,
            "skill_id": "warranting",
            "override_score": 99.0,
            "override_type": "mastery_override",
            "reason": "Forged by student",
        })
        assert status in (401, 403), (
            f"Student was able to write coach_mastery_audit — RLS violation. status={status}"
        )

    def test_anon_cannot_read_audit(self):
        url = f"{SUPABASE_URL}/rest/v1/coach_mastery_audit"
        resp = requests.get(url, headers={"apikey": ANON_KEY}, timeout=5)
        body = resp.json() if isinstance(resp.json(), list) else []
        assert len(body) == 0 or resp.status_code in (401, 403), (
            "Anon can read coach_mastery_audit — RLS violation"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 11. Security-definer helper function security
# ═══════════════════════════════════════════════════════════════════════════

@_requires_local
class TestHelperFunctionSecurity:
    """
    Verify that security-definer helpers cannot be abused as membership oracles
    by unauthenticated or arbitrary-UUID calls.
    """

    def test_anon_cannot_call_current_user_team_ids(self):
        """Anon must not be able to probe team membership via the helper."""
        status, body = _anon_rpc("current_user_team_ids", {})
        assert status in (401, 403, 404), (
            f"Anon was able to call current_user_team_ids — REVOKE FROM PUBLIC failed. status={status}"
        )

    def test_anon_cannot_call_current_user_is_coach_of(self):
        status, body = _anon_rpc("current_user_is_coach_of", {"student_uid": STUDENT_A})
        assert status in (401, 403, 404), (
            f"Anon called current_user_is_coach_of — status={status}"
        )

    def test_anon_cannot_call_current_user_is_team_member(self):
        status, body = _anon_rpc("current_user_is_team_member", {"tid": TEAM_A})
        assert status in (401, 403, 404), (
            f"Anon called current_user_is_team_member — status={status}"
        )

    def test_anon_cannot_call_current_user_is_team_coach(self):
        status, body = _anon_rpc("current_user_is_team_coach", {"tid": TEAM_A})
        assert status in (401, 403, 404), (
            f"Anon called current_user_is_team_coach — status={status}"
        )

    def test_old_oracle_function_get_user_team_ids_absent(self, coach_a_token):
        """
        get_user_team_ids(uid) was an arbitrary-UUID oracle and must be gone.
        Any authenticated user could call it to probe any user's team membership.
        """
        status, body = _rest_rpc(coach_a_token, "get_user_team_ids", {"uid": STUDENT_B})
        assert status in (404,), (
            f"get_user_team_ids still callable — old oracle function not dropped. status={status}, body={body}"
        )

    def test_old_oracle_function_is_coach_of_absent(self, student_a_token):
        """is_coach_of(coach_uid, student_uid) was an arbitrary-UUID oracle and must be gone."""
        status, body = _rest_rpc(student_a_token, "is_coach_of", {
            "coach_uid": COACH_A, "student_uid": STUDENT_A
        })
        assert status in (404,), (
            f"is_coach_of still callable — old oracle function not dropped. status={status}"
        )

    def test_old_oracle_function_is_team_member_of_absent(self, student_a_token):
        """is_team_member_of(uid, tid) was an arbitrary-UUID oracle and must be gone."""
        status, body = _rest_rpc(student_a_token, "is_team_member_of", {
            "uid": COACH_B, "tid": TEAM_A
        })
        assert status in (404,), (
            f"is_team_member_of still callable — old oracle function not dropped. status={status}"
        )

    def test_current_user_returns_own_teams_not_others(self, student_a_token):
        """current_user_team_ids() ignores any payload UUID — returns caller's teams only."""
        status, body = _rest_rpc(student_a_token, "current_user_team_ids", {})
        assert status == 200, f"current_user_team_ids call failed: {status}"
        # Student A is on Team A; must not see Team B
        if isinstance(body, list):
            assert TEAM_A in body or len(body) >= 1, "Student A sees no teams via current_user_team_ids"
            assert TEAM_B not in body, (
                "Student A sees Team B via current_user_team_ids — function returns wrong caller's data"
            )

    def test_student_a_is_not_coach_of_student_b(self, student_a_token):
        """Student A is not a coach — current_user_is_coach_of must return false."""
        status, body = _rest_rpc(student_a_token, "current_user_is_coach_of", {"student_uid": STUDENT_B})
        assert status == 200
        assert body is False or body == "false" or body is None, (
            f"Student A falsely reports as coach of Student B: {body}"
        )

    def test_coach_a_is_coach_of_student_a(self, coach_a_token):
        """Coach A must be recognized as coach of Student A via the helper."""
        status, body = _rest_rpc(coach_a_token, "current_user_is_coach_of", {"student_uid": STUDENT_A})
        assert status == 200
        assert body is True or body == "true", (
            f"Coach A not recognized as coach of Student A: {body}"
        )

    def test_coach_a_is_not_coach_of_student_b(self, coach_a_token):
        """Coach A must not be recognized as coach of Team B students."""
        status, body = _rest_rpc(coach_a_token, "current_user_is_coach_of", {"student_uid": STUDENT_B})
        assert status == 200
        assert body is False or body == "false" or body is None, (
            f"Coach A falsely reports as coach of Team B student: {body}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 12. Cross-team security
# ═══════════════════════════════════════════════════════════════════════════

@_requires_local
class TestCrossTeamSecurity:

    def test_coach_b_cannot_read_team_a_mastery(self, coach_b_token):
        rows = _rest_get(coach_b_token, "mastery_scores", {"user_id": f"eq.{STUDENT_A}"})
        assert len(rows) == 0, "Coach B reads Team A student mastery — cross-team RLS violation"

    def test_coach_b_cannot_modify_team_a_student(self, coach_b_token):
        status, _ = _rest_post(coach_b_token, "mastery_scores", {
            "user_id": STUDENT_A,
            "skill_id": "warranting",
            "mastery_score": 0.0,
            "confidence": 0.0,
            "evidence_count": 0,
            "mastery_state": "not_started",
        })
        assert status in (401, 403, 409), "Coach B modified Team A student data"

    def test_student_a_cannot_read_team_b_training(self, student_a_token):
        rows = _rest_get(student_a_token, "training_plans", {"user_id": f"eq.{STUDENT_B}"})
        assert len(rows) == 0, "Student A reads Student B training plans"

    def test_student_a_cannot_read_team_b_sessions(self, student_a_token):
        rows = _rest_get(student_a_token, "training_sessions", {"user_id": f"eq.{STUDENT_B}"})
        assert len(rows) == 0, "Student A reads Student B sessions"

    def test_forged_user_id_in_mastery_insert_rejected(self, student_a_token):
        status, _ = _rest_post(student_a_token, "mastery_scores", {
            "user_id": STUDENT_B,
            "skill_id": "warranting",
            "mastery_score": 100.0,
            "confidence": 1.0,
            "evidence_count": 99,
            "mastery_state": "mastered",
        })
        assert status in (401, 403, 409), "Forged user_id write was accepted"

    def test_service_role_bypasses_rls_intentionally(self):
        rows = _service_get("mastery_scores", {"limit": "10"})
        assert len(rows) >= 1, "Service role cannot read mastery_scores — unexpected"


# ═══════════════════════════════════════════════════════════════════════════
# 13. RLS matrix + static hardening documentation
# ═══════════════════════════════════════════════════════════════════════════

class TestRLSMatrixDocumentation:

    MATRIX = {
        ("student_own", "mastery_scores",   "SELECT"): "allowed",
        ("student_other","mastery_scores",  "SELECT"): "denied",
        ("student_own", "mastery_evidence", "SELECT"): "allowed",
        ("student_other","mastery_evidence","SELECT"): "denied",
        ("student_own", "training_plans",   "SELECT"): "allowed",
        ("student_other","training_plans",  "SELECT"): "denied",
        ("student_own", "training_sessions","SELECT"): "allowed",
        ("student_other","training_sessions","SELECT"): "denied",
        ("team_coach",   "mastery_scores",  "SELECT"): "allowed",
        ("team_coach",   "mastery_evidence","SELECT"): "allowed",
        ("cross_team_coach","mastery_scores","SELECT"): "denied",
        ("cross_team_coach","mastery_evidence","SELECT"): "denied",
        ("service_role", "mastery_scores",  "SELECT"): "allowed",
        ("service_role", "mastery_evidence","SELECT"): "allowed",
        ("student", "coach_mastery_audit",  "INSERT"): "denied",
        ("student_own", "team_members",     "SELECT"): "allowed",
        ("student_other","team_members",    "SELECT"): "denied",
        ("team_coach", "team_members",      "SELECT"): "allowed",
        ("cross_team_coach","team_members", "SELECT"): "denied",
    }

    def test_matrix_has_19_entries(self):
        assert len(self.MATRIX) == 19

    def test_student_own_data_always_allowed(self):
        own = {k: v for k, v in self.MATRIX.items() if k[0] == "student_own"}
        assert all(v == "allowed" for v in own.values())

    def test_cross_user_reads_always_denied(self):
        crossed = {k: v for k, v in self.MATRIX.items() if "other" in k[0] or "cross" in k[0]}
        assert all(v == "denied" for v in crossed.values())

    def test_service_role_always_allowed(self):
        svc = {k: v for k, v in self.MATRIX.items() if k[0] == "service_role"}
        assert all(v == "allowed" for v in svc.values())

    def test_helper_function_safety_invariants(self):
        """Document the security invariants of the hardened helpers."""
        invariants = {
            "no_caller_id_param": "Helpers accept no caller-UUID argument; auth.uid() used internally",
            "empty_search_path":  "SET search_path = '' prevents search_path hijacking",
            "security_definer":   "SECURITY DEFINER runs as postgres, bypasses RLS on team_members",
            "revoke_public":      "REVOKE ALL FROM PUBLIC prevents anon probing",
            "grant_authenticated":"Only authenticated role receives EXECUTE",
            "oracle_functions_removed": "get_user_team_ids/is_coach_of/is_team_member_of dropped",
        }
        assert len(invariants) == 6

    def test_oracle_function_signatures_absent_from_migration(self):
        """Confirm old signatures don't appear in the hardened migration file."""
        migration = MIGRATIONS_DIR / "20260628000001_fix_team_members_rls.sql"
        if migration.exists():
            text = migration.read_text()
            for bad_sig in [
                "get_user_team_ids(uid",
                "is_coach_of(coach_uid",
                "is_team_member_of(uid",
            ]:
                assert bad_sig not in text, (
                    f"Old oracle signature {bad_sig!r} found in hardened migration"
                )

    def test_no_team_members_direct_subquery_in_training_os_policies(self):
        """
        After hardening, Training OS policies must not query team_members directly.
        They must use current_user_* helpers instead.
        """
        migration = MIGRATIONS_DIR / "20260628000001_fix_team_members_rls.sql"
        if not migration.exists():
            pytest.skip("Migration file not found")
        text = migration.read_text()

        # In the POLICY sections (after functions are created), there must be no
        # raw "FROM team_members" or "FROM public.team_members" in USING/WITH CHECK clauses.
        # (The DROP FUNCTION section legitimately mentions team_members but not in a USING clause.)
        policy_section = text[text.find("── 3."):]
        direct_ref = re.search(
            r"USING\s*\(.*?FROM\s+(?:public\.)?team_members",
            policy_section, re.DOTALL | re.IGNORECASE
        )
        assert not direct_ref, (
            "Training OS policy contains a direct 'FROM team_members' subquery — "
            "this causes recursion. Use current_user_* helpers instead."
        )

    # ── Local-URL predicate regression ───────────────────────────────────────

    def test_placeholder_supabase_url_is_not_local(self):
        """Regression: CI placeholder and remote cloud URLs must never be treated as local.

        This prevents the test suite from attempting network contact with
        https://placeholder.supabase.co (or any *.supabase.co host) when
        running in CI with placeholder credentials.
        """
        # Remote / placeholder URLs must return False
        assert not _is_local_url("https://placeholder.supabase.co"), (
            "https://placeholder.supabase.co was wrongly classified as local"
        )
        assert not _is_local_url("https://xyzxyz.supabase.co"), (
            "Remote *.supabase.co URL was wrongly classified as local"
        )
        assert not _is_local_url("http://127.0.0.1:5432"), (
            "Port 5432 (postgres, not Supabase API) must not be classified as local"
        )
        assert not _is_local_url(""), (
            "Empty URL must not be classified as local"
        )

        # Known-local URLs must return True
        assert _is_local_url("http://127.0.0.1:54321"), (
            "http://127.0.0.1:54321 was not recognized as a local Supabase URL"
        )
        assert _is_local_url("http://localhost:54321"), (
            "http://localhost:54321 was not recognized as a local Supabase URL"
        )
