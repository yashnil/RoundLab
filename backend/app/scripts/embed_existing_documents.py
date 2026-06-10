"""Backfill embeddings for document chunks that have no embedding yet.

Usage:
    python -m app.scripts.embed_existing_documents
    python -m app.scripts.embed_existing_documents --user-id <uuid>
    python -m app.scripts.embed_existing_documents --document-id <uuid>
    python -m app.scripts.embed_existing_documents --dry-run

Options:
    --user-id       Only process chunks belonging to this user.
    --document-id   Only process chunks from this document.
    --batch-size    Chunks per API call (default: 50).
    --dry-run       Print what would be embedded without calling the API.

Safe to rerun — only processes chunks where embedding IS NULL.
Respects rate limits via per-batch delay configurable via --delay-ms.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path when run as a module from outside the package
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("embed_backfill")


def _fetch_missing(sb, user_id: str | None, document_id: str | None, batch_size: int) -> list[dict]:
    """Fetch all chunks with null embedding, optionally filtered."""
    q = (
        sb.table("document_chunks")
        .select("id, document_id, user_id, chunk_text, chunk_index")
        .is_("embedding", "null")
    )
    if user_id:
        q = q.eq("user_id", user_id)
    if document_id:
        q = q.eq("document_id", document_id)
    result = q.order("document_id").order("chunk_index").execute()
    return result.data or []


def run(
    user_id: str | None = None,
    document_id: str | None = None,
    batch_size: int = 50,
    delay_ms: int = 200,
    dry_run: bool = False,
) -> None:
    from app.services.embeddings import EMBEDDING_MODEL, embed_texts, vector_to_pg_str
    from app.services.supabase_client import get_supabase

    sb = get_supabase()
    missing = _fetch_missing(sb, user_id, document_id, batch_size)

    if not missing:
        logger.info("No un-embedded chunks found — nothing to do.")
        return

    logger.info(
        "Found %d chunk(s) to embed (user_id=%s, document_id=%s, dry_run=%s)",
        len(missing),
        user_id or "all",
        document_id or "all",
        dry_run,
    )

    if dry_run:
        for row in missing:
            logger.info("  would embed chunk %s (doc %s, idx %d)", row["id"], row["document_id"], row["chunk_index"])
        return

    now = datetime.now(timezone.utc).isoformat()
    embedded_total = 0
    failed_total = 0

    for batch_start in range(0, len(missing), batch_size):
        batch = missing[batch_start : batch_start + batch_size]
        texts = [r["chunk_text"] for r in batch]

        try:
            embeddings = embed_texts(texts)
        except Exception as exc:
            logger.error("  batch starting at %d: embed_texts failed | %s", batch_start, exc)
            failed_total += len(batch)
            continue

        for row, emb in zip(batch, embeddings):
            try:
                sb.table("document_chunks").update({
                    "embedding": vector_to_pg_str(emb),
                    "embedding_model": EMBEDDING_MODEL,
                    "embedded_at": now,
                }).eq("id", row["id"]).execute()
                embedded_total += 1
            except Exception as exc:
                logger.warning("  chunk %s: update failed | %s", row["id"], exc)
                failed_total += 1

        logger.info(
            "  embedded %d/%d (this batch: %d ok, running totals: ok=%d fail=%d)",
            min(batch_start + batch_size, len(missing)),
            len(missing),
            len(batch),
            embedded_total,
            failed_total,
        )

        if delay_ms > 0 and batch_start + batch_size < len(missing):
            time.sleep(delay_ms / 1000.0)

    logger.info(
        "Done. embedded=%d failed=%d model=%s",
        embedded_total,
        failed_total,
        EMBEDDING_MODEL,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill embeddings for document chunks.")
    parser.add_argument("--user-id", default=None, help="Restrict to one user.")
    parser.add_argument("--document-id", default=None, help="Restrict to one document.")
    parser.add_argument("--batch-size", type=int, default=50, help="Chunks per API call.")
    parser.add_argument("--delay-ms", type=int, default=200, help="Delay between batches (ms).")
    parser.add_argument("--dry-run", action="store_true", help="Print without embedding.")
    args = parser.parse_args()

    run(
        user_id=args.user_id,
        document_id=args.document_id,
        batch_size=args.batch_size,
        delay_ms=args.delay_ms,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
