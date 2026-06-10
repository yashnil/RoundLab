"""OpenAI embedding service for Evidence RAG.

Wraps text-embedding-3-small (1536 dimensions) with:
- whitespace normalization
- safe truncation to avoid token limit
- batch support
- basic retry on transient API failures
"""

from __future__ import annotations

import logging
import re
import time
from typing import Optional

import openai

from app.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

# text-embedding-3-small supports 8192 tokens; ~4 chars/token → ~30k chars
# We use a conservative 24000-char ceiling (~6000 tokens) to stay well under.
_MAX_CHARS = 24_000

# Number of texts per batch API call
_BATCH_SIZE = 50

# Retry config for transient failures
_MAX_RETRIES = 3
_RETRY_DELAY_S = 1.0


def _normalize(text: str) -> str:
    """Collapse whitespace and truncate to _MAX_CHARS."""
    text = re.sub(r"\s+", " ", text.strip())
    return text[:_MAX_CHARS]


def embed_text(text: str) -> list[float]:
    """Embed a single text string. Returns a list of 1536 floats.

    Raises ValueError for empty input.
    Raises openai.APIError on persistent failure.
    """
    if not text or not text.strip():
        raise ValueError("embed_text: input text must not be empty")

    normalized = _normalize(text)
    client = openai.OpenAI(api_key=settings.openai_api_key)

    last_exc: Optional[Exception] = None
    for attempt in range(_MAX_RETRIES):
        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=[normalized],
            )
            return response.data[0].embedding
        except (openai.APITimeoutError, openai.InternalServerError) as exc:
            last_exc = exc
            logger.warning(
                "embeddings: transient error attempt %d/%d | %s",
                attempt + 1,
                _MAX_RETRIES,
                exc,
            )
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_DELAY_S * (attempt + 1))
        except openai.APIError:
            raise

    raise last_exc or RuntimeError("embed_text: all retries exhausted")


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts in batches. Returns list[list[float]] in input order.

    Empty-string inputs in the list are replaced with a single space so the API
    does not reject them; the caller is responsible for filtering obvious empty inputs.

    Raises ValueError if texts is empty.
    """
    if not texts:
        return []

    normalized = [_normalize(t) if t.strip() else " " for t in texts]
    client = openai.OpenAI(api_key=settings.openai_api_key)

    all_embeddings: list[list[float]] = []

    for batch_start in range(0, len(normalized), _BATCH_SIZE):
        batch = normalized[batch_start : batch_start + _BATCH_SIZE]

        last_exc: Optional[Exception] = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=batch,
                )
                # Sort by index to guarantee order matches input order
                sorted_data = sorted(response.data, key=lambda x: x.index)
                all_embeddings.extend(item.embedding for item in sorted_data)
                break
            except (openai.APITimeoutError, openai.InternalServerError) as exc:
                last_exc = exc
                logger.warning(
                    "embeddings: batch transient error attempt %d/%d batch_start=%d | %s",
                    attempt + 1,
                    _MAX_RETRIES,
                    batch_start,
                    exc,
                )
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_RETRY_DELAY_S * (attempt + 1))
            except openai.APIError:
                raise
        else:
            raise last_exc or RuntimeError(
                f"embed_texts: all retries exhausted for batch starting at {batch_start}"
            )

    return all_embeddings


def vector_to_pg_str(embedding: list[float]) -> str:
    """Convert a float list to the PostgreSQL vector literal string '[f1,f2,...]'.

    Use this when storing embeddings via supabase-py .update() calls so that
    PostgREST correctly casts the value to vector(1536).
    """
    return "[" + ",".join(f"{v:.8f}" for v in embedding) + "]"
