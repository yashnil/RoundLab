"""Source snapshot model and creation utilities.

A SourceSnapshot is a lightweight audit record created for each URL that
enters the extraction pipeline.  It records:
- canonical URL and retrieval time
- HTTP status and content type
- Hashes of the raw response and extracted text
- Parser used and parser version
- A bounded excerpt (never the full copyrighted body)

POLICY (see docs/EVIDENCE_SNAPSHOT_POLICY.md)
- Full source bodies are NOT stored (copyright).
- Only hashes, metadata, and a short excerpt (≤500 chars) are persisted.
- Secrets, credentials, and cookies are never stored.
- Duplicate canonical URLs within the same request are not re-snapshotted.
- Snapshot creation failure NEVER fails evidence generation.
- Snapshot persistence is configurable (default: disabled).

Tests use the in-memory store; no live Supabase calls are required.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class SourceSnapshot:
    """Audit record for one fetched source.

    snapshot_id: UUID-4 string, unique per snapshot.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    canonical_url: str = ""
    retrieval_timestamp: str = ""

    # ── HTTP metadata ─────────────────────────────────────────────────────────
    http_status: int = 0
    content_type: str = ""

    # ── Content fingerprints ──────────────────────────────────────────────────
    response_hash: str = ""        # SHA-256 of raw HTTP response body
    extracted_text_hash: str = ""  # SHA-256 of extracted text

    # ── Parser ────────────────────────────────────────────────────────────────
    parser: str = ""
    parser_version: str = ""

    # ── Storage ───────────────────────────────────────────────────────────────
    snapshot_storage_path: str = ""   # path in Supabase Storage (if stored)
    full_source_retained: bool = False

    # ── Excerpt (bounded, non-copyright-violating) ────────────────────────────
    stored_excerpt: str = ""          # first 500 chars of extracted text

    # ── Document structure ────────────────────────────────────────────────────
    page_count: Optional[int] = None
    source_text_type: str = ""

    # ── Failure ───────────────────────────────────────────────────────────────
    failure_reason: str = ""


def _hash(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8", errors="replace")
    return hashlib.sha256(data).hexdigest()


def create_snapshot(
    document: "ExtractedDocument",
    *,
    http_status: int = 200,
    raw_response_bytes: bytes | None = None,
) -> SourceSnapshot:
    """Create a SourceSnapshot from an ExtractedDocument.

    Never raises; if the document has no text, the snapshot still records
    the failure.  Credentials and full source bodies are never stored.
    """
    ts = document.retrieval_timestamp or datetime.now(timezone.utc).isoformat()

    response_hash = ""
    if raw_response_bytes:
        response_hash = _hash(raw_response_bytes)

    extracted_text_hash = _hash(document.raw_text) if document.raw_text else ""

    # Bounded excerpt — never the full copyrighted body
    excerpt = (document.raw_text or "")[:500]
    if len(document.raw_text or "") > 500:
        excerpt += "…"

    return SourceSnapshot(
        canonical_url=document.canonical_url or document.source_url,
        retrieval_timestamp=ts,
        http_status=http_status,
        content_type=document.http_content_type,
        response_hash=response_hash,
        extracted_text_hash=extracted_text_hash,
        parser=document.extraction_method,
        parser_version=document.extraction_version,
        stored_excerpt=excerpt,
        full_source_retained=False,
        page_count=document.page_count,
        source_text_type=document.source_text_type,
        failure_reason=(
            "; ".join(document.extraction_warnings) if document.is_metadata_only else ""
        ),
    )


class InMemorySnapshotStore:
    """Simple non-persistent snapshot store for tests and dev use.

    Deduplicates by canonical_url; never persists to disk or network.
    """

    def __init__(self) -> None:
        self._seen: set[str] = set()
        self._snapshots: list[SourceSnapshot] = []

    def add(self, snapshot: SourceSnapshot) -> bool:
        """Add snapshot. Returns False if canonical_url already seen (dedup)."""
        key = snapshot.canonical_url or snapshot.snapshot_id
        if key in self._seen:
            return False
        self._seen.add(key)
        self._snapshots.append(snapshot)
        return True

    def all(self) -> list[SourceSnapshot]:
        return list(self._snapshots)

    def __len__(self) -> int:
        return len(self._snapshots)


class NoOpSnapshotStore:
    """Drop-all store used when snapshots are disabled."""

    def add(self, snapshot: SourceSnapshot) -> bool:
        return False

    def all(self) -> list[SourceSnapshot]:
        return []

    def __len__(self) -> int:
        return 0
