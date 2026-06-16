"""Tests that user card markup (highlight/underline/bold/italic) is persisted.

Covers:
- _build_card_cutting_metadata pure helper carries user_markup through save.
- PatchCardDraftRequest accepts a full UserMarkup payload.
- PATCH /research/card-drafts/{id} merges user_markup into draft_json.
- POST /research/card-drafts/{id}/save copies user_markup into the saved
  evidence_card's card_cutting_metadata_json (so bold/italic survive).
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.research import _build_card_cutting_metadata
from app.main import app
from app.models.research import PatchCardDraftRequest, UserMarkup

client = TestClient(app)

USER_ID = "user-123"
DRAFT_ID = "draft-abc"

MARKUP = {
    "highlight": [{"start": 0, "end": 9, "type": "highlight", "reason": "user"}],
    "underline": [{"start": 10, "end": 20, "type": "underline", "reason": "user"}],
    "bold": [{"start": 0, "end": 4, "type": "bold", "reason": "user"}],
    "italic": [{"start": 5, "end": 9, "type": "italic", "reason": "user"}],
}


# ── Fake Supabase ──────────────────────────────────────────────────────────────

class _FakeQuery:
    def __init__(self, table, store):
        self.table = table
        self.store = store
        self._op = None
        self._payload = None
        self._filters = {}

    def select(self, *a, **k):
        self._op = "select"
        return self

    def insert(self, row):
        self._op = "insert"
        self._payload = row
        self.store["inserts"].setdefault(self.table, []).append(row)
        return self

    def update(self, row):
        self._op = "update"
        self._payload = row
        self.store["updates"].setdefault(self.table, []).append(row)
        return self

    def eq(self, k, v):
        self._filters[k] = v
        return self

    def limit(self, n):
        return self

    def order(self, *a, **k):
        return self

    def execute(self):
        if self._op == "select":
            return type("R", (), {"data": self.store["rows"].get(self.table, [])})()
        if self._op == "insert":
            return type("R", (), {"data": [{"id": f"{self.table}-new", **self._payload}]})()
        return type("R", (), {"data": [{"id": self._filters.get("id", "x"), **(self._payload or {})}]})()


class _FakeSupabase:
    def __init__(self, rows):
        self.store = {"rows": rows, "inserts": {}, "updates": {}}

    def table(self, name):
        return _FakeQuery(name, self.store)


def _draft_row(**over):
    row = {
        "id": DRAFT_ID,
        "user_id": USER_ID,
        "status": "draft",
        "tag": "Section 230 shields platforms",
        "cite": "Smith 2024",
        "body_text": "Section 230 grants broad immunity to platforms today.",
        "draft_json": {},
        "highlighted_spans_json": [],
        "underline_spans_json": [],
        "card_source_type": "url",
    }
    row.update(over)
    return row


# ── _build_card_cutting_metadata ───────────────────────────────────────────────

class TestBuildCardCuttingMetadata:
    def test_includes_user_markup_when_present(self):
        draft = _draft_row(draft_json={"user_markup": MARKUP})
        meta = _build_card_cutting_metadata(draft, DRAFT_ID)
        assert meta["user_markup"] == MARKUP
        assert meta["draft_id"] == DRAFT_ID

    def test_omits_user_markup_when_absent(self):
        meta = _build_card_cutting_metadata(_draft_row(), DRAFT_ID)
        assert "user_markup" not in meta

    def test_carries_summaries(self):
        draft = _draft_row(warrant_summary="W", impact_summary="I")
        meta = _build_card_cutting_metadata(draft, DRAFT_ID)
        assert meta["warrant_summary"] == "W"
        assert meta["impact_summary"] == "I"


# ── Model ──────────────────────────────────────────────────────────────────────

class TestUserMarkupModel:
    def test_patch_request_accepts_full_markup(self):
        req = PatchCardDraftRequest(user_id=USER_ID, user_markup_json=UserMarkup(**MARKUP))
        assert req.user_markup_json.bold == MARKUP["bold"]
        assert req.user_markup_json.italic == MARKUP["italic"]

    def test_markup_defaults_empty(self):
        m = UserMarkup()
        assert m.highlight == [] and m.bold == [] and m.italic == [] and m.underline == []


# ── PATCH endpoint ─────────────────────────────────────────────────────────────

class TestPatchPersistsMarkup:
    def test_patch_merges_markup_into_draft_json(self):
        fake = _FakeSupabase({"card_drafts": [_draft_row()]})
        with patch("app.api.research.get_supabase", return_value=fake):
            resp = client.patch(
                f"/research/card-drafts/{DRAFT_ID}",
                json={"user_id": USER_ID, "user_markup_json": MARKUP},
            )
        assert resp.status_code == 200
        updates = fake.store["updates"]["card_drafts"]
        assert any("draft_json" in u and u["draft_json"].get("user_markup") == MARKUP for u in updates)

    def test_patch_preserves_existing_draft_json_keys(self):
        fake = _FakeSupabase({"card_drafts": [_draft_row(draft_json={"evidence_role": "mechanism_support"})]})
        with patch("app.api.research.get_supabase", return_value=fake):
            client.patch(
                f"/research/card-drafts/{DRAFT_ID}",
                json={"user_id": USER_ID, "user_markup_json": MARKUP},
            )
        merged = fake.store["updates"]["card_drafts"][0]["draft_json"]
        assert merged["evidence_role"] == "mechanism_support"
        assert merged["user_markup"] == MARKUP


# ── SAVE endpoint ──────────────────────────────────────────────────────────────

class TestSavePersistsMarkup:
    def _rows(self, markup):
        return {
            "card_drafts": [_draft_row(draft_json={"user_markup": markup} if markup else {})],
            "profiles": [{"id": USER_ID}],
            "documents": [{"id": "doc-1"}],
        }

    def test_save_writes_markup_into_card_metadata(self):
        fake = _FakeSupabase(self._rows(MARKUP))
        with patch("app.api.research.get_supabase", return_value=fake), \
             patch("app.api.research._embed_text_safe", return_value=None):
            resp = client.post(
                f"/research/card-drafts/{DRAFT_ID}/save",
                json={"user_id": USER_ID, "confirmed": True},
            )
        assert resp.status_code == 200, resp.text
        card_inserts = fake.store["inserts"]["evidence_cards"]
        assert len(card_inserts) == 1
        meta = card_inserts[0]["card_cutting_metadata_json"]
        assert meta["user_markup"] == MARKUP
        # bold + italic survived (no dedicated DB columns exist for them)
        assert meta["user_markup"]["bold"] == MARKUP["bold"]
        assert meta["user_markup"]["italic"] == MARKUP["italic"]

    def test_save_without_markup_still_succeeds(self):
        fake = _FakeSupabase(self._rows(None))
        with patch("app.api.research.get_supabase", return_value=fake), \
             patch("app.api.research._embed_text_safe", return_value=None):
            resp = client.post(
                f"/research/card-drafts/{DRAFT_ID}/save",
                json={"user_id": USER_ID, "confirmed": True},
            )
        assert resp.status_code == 200, resp.text
        meta = fake.store["inserts"]["evidence_cards"][0]["card_cutting_metadata_json"]
        assert "user_markup" not in meta
