# Evidence Snapshot Policy

## Purpose

A source snapshot is a lightweight audit record created for each URL that
enters the extraction pipeline. It allows evidence cards to be traced back
to a specific version of a source document retrieved at a specific time.

## What Is Stored

| Field | Stored | Rationale |
|-------|--------|-----------|
| Canonical URL | ✅ | Needed for traceability |
| Retrieval timestamp | ✅ | When content was fetched |
| HTTP status | ✅ | Confirms source was accessible |
| Content-Type | ✅ | Documents parser routing decision |
| SHA-256 of raw response | ✅ | Fingerprint without storing full body |
| SHA-256 of extracted text | ✅ | Fingerprint without storing full text |
| Parser name + version | ✅ | Reproducibility |
| Bounded excerpt (≤500 chars) | ✅ | Supports audit; avoids reproduction |
| Page count (PDF) | ✅ | Structural metadata |
| Failure reason | ✅ | Debugging |
| **Full source body** | ❌ | Copyright; not stored |
| Request headers, cookies | ❌ | Credentials; never stored |
| Authorization tokens | ❌ | Credentials; never stored |

## Copyright Compliance

Full copyrighted source bodies are **not stored**. Only hashes, bounded
excerpts (≤500 chars), and structural metadata are retained. This is
sufficient for:
- Detecting if a source has changed since card cutting
- Auditing which parser was used
- Fingerprint-based deduplication

## Persistence Configuration

Snapshot persistence is **disabled by default**:

```python
# config.py
research_enable_snapshots: bool = False
```

When disabled, `NoOpSnapshotStore` is used — all snapshots are computed
in-memory but not written to any persistent storage.

When enabled, snapshots are intended to be stored in Supabase Storage
(implementation pending). The store is abstracted behind `InMemorySnapshotStore`
so the backend can be swapped without changing calling code.

## Failure Behavior

**Snapshot creation never fails evidence generation.** The snapshot is
computed after extraction succeeds. A failure in snapshot creation is logged
as a warning and counted in `snapshot_failure_count` in the trace, but
evidence generation continues normally.

## Deduplication

Within a single request, identical canonical URLs are not re-snapshotted.
The `InMemorySnapshotStore.add()` method returns `False` when a URL is
already in the session's seen set, and the caller should discard the
duplicate rather than writing it.

## Testing

Tests use `InMemorySnapshotStore` or `NoOpSnapshotStore`. No live Supabase
calls are required. Tests verify:
- `SourceSnapshot.stored_excerpt` is ≤500 chars
- `SourceSnapshot` never contains credentials or headers
- Duplicate URLs are not re-snapshotted
- Snapshot failure does not propagate as an extraction error
