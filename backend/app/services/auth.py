"""Supabase access-token verification.

The frontend sends the user's Supabase access token as `Authorization: Bearer
<jwt>`. We verify it locally and derive the acting user from the verified `sub`
claim — never from a client-supplied user_id. The service-role key stays
server-side and is never exposed.

Verification is production-safe for both modern and legacy Supabase projects:

* Modern: asymmetric signatures (RS256/ES256) using keys from the project's JWKS
  endpoint, with issuer + audience + expiry checks, cached keys, and rotation
  (an unknown `kid` triggers a refetch; on a JWKS outage a cached key is reused).
* Legacy: HS256 with the shared project secret — only when explicitly enabled
  via AUTH_ALLOW_HS256_FALLBACK, never trusted implicitly.

The algorithm is always restricted to a supported allowlist; the value declared
in the token header is never trusted on its own.
"""

import json
import logging
import threading
import time
import urllib.request
from typing import Annotated

import jwt
from fastapi import Header, HTTPException

from app.config import settings

logger = logging.getLogger(__name__)

_ASYMMETRIC_ALGS = ("RS256", "ES256")
_AUDIENCE = "authenticated"
_JWKS_TTL_SECONDS = 600

# Module-level signing-key cache: kid -> PyJWK. Retained across requests so a
# brief JWKS outage can still verify recently-seen tokens.
_jwk_cache: dict[str, "jwt.PyJWK"] = {}
_jwk_last_fetch: float = 0.0
_jwk_lock = threading.Lock()


# ── Configuration helpers ──────────────────────────────────────────────────────


def _issuer() -> str:
    if settings.supabase_jwt_issuer:
        return settings.supabase_jwt_issuer.rstrip("/")
    if settings.supabase_url:
        return f"{settings.supabase_url.rstrip('/')}/auth/v1"
    return ""


def _jwks_url() -> str:
    if settings.supabase_jwks_url:
        return settings.supabase_jwks_url
    if settings.supabase_url:
        return f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    return ""


# ── JWKS retrieval (network call isolated for testing) ──────────────────────────


def _load_jwks_keys() -> list[dict]:
    """Fetch the raw JWK list from the project's JWKS endpoint.

    Isolated so tests can patch it. Raises on network/HTTP failure.
    """
    url = _jwks_url()
    if not url:
        raise RuntimeError("No JWKS URL configured")
    with urllib.request.urlopen(url, timeout=5) as resp:  # noqa: S310 (trusted, configured URL)
        payload = json.loads(resp.read().decode("utf-8"))
    return payload.get("keys", [])


def _refresh_jwks() -> None:
    """Fetch the JWKS and merge into the cache (new/rotated keys are added)."""
    global _jwk_last_fetch
    keys = _load_jwks_keys()
    for raw in keys:
        kid = raw.get("kid")
        if not kid:
            continue
        try:
            _jwk_cache[kid] = jwt.PyJWK.from_dict(raw)
        except Exception:  # malformed key — skip it
            logger.warning("jwks: skipped malformed key | kid=%s", kid)
    _jwk_last_fetch = time.monotonic()


def _signing_key(kid: str) -> "jwt.PyJWK":
    """Return the signing key for `kid`, refetching for unknown/rotated keys.

    A cached key is preferred (and reused during a JWKS outage). An unknown kid
    triggers a refetch; if that fails but the kid is already cached, the cached
    key is served (outage tolerance).
    """
    with _jwk_lock:
        cached = _jwk_cache.get(kid)
        if cached is not None:
            return cached
        try:
            _refresh_jwks()
        except Exception as exc:  # outage and kid not cached → cannot verify
            logger.error("jwks: refresh failed | %s", type(exc).__name__)
            raise HTTPException(status_code=503, detail="Auth keys temporarily unavailable") from exc
        key = _jwk_cache.get(kid)
        if key is None:
            raise HTTPException(status_code=401, detail="Unknown signing key")
        return key


# ── Verification ────────────────────────────────────────────────────────────────


def _allowed_algorithms() -> list[str]:
    algs = list(_ASYMMETRIC_ALGS)
    if settings.auth_allow_hs256_fallback and settings.supabase_jwt_secret:
        algs.append("HS256")
    return algs


def verify_supabase_jwt(token: str) -> str:
    """Verify a Supabase access token and return its user id (`sub`).

    Raises HTTPException(401) for missing/expired/invalid/disallowed tokens,
    HTTPException(503) when verification keys can't be obtained.
    """
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid session") from exc

    alg = header.get("alg")
    allowed = _allowed_algorithms()
    # Never trust the token's declared algorithm beyond our allowlist.
    if alg not in allowed:
        raise HTTPException(status_code=401, detail="Unsupported token algorithm")

    if alg == "HS256":
        if not (settings.auth_allow_hs256_fallback and settings.supabase_jwt_secret):
            raise HTTPException(status_code=401, detail="Unsupported token algorithm")
        key: object = settings.supabase_jwt_secret
    else:
        kid = header.get("kid")
        if not kid:
            raise HTTPException(status_code=401, detail="Invalid session")
        key = _signing_key(kid).key

    decode_kwargs: dict = {
        "algorithms": allowed,
        "audience": _AUDIENCE,
        "options": {"require": ["exp", "sub"]},
    }
    issuer = _issuer()
    if issuer:
        decode_kwargs["issuer"] = issuer

    try:
        payload = jwt.decode(token, key, **decode_kwargs)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Your session has expired") from exc
    except jwt.InvalidIssuerError as exc:
        raise HTTPException(status_code=401, detail="Untrusted token issuer") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid or tampered session") from exc

    sub = payload.get("sub")
    if not sub or not isinstance(sub, str):
        raise HTTPException(status_code=401, detail="Invalid session")
    return sub


def get_current_user_id(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """FastAPI dependency: the verified acting user's id from the Bearer token."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Sign in to continue")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Sign in to continue")
    return verify_supabase_jwt(token)


def _reset_jwks_cache_for_tests() -> None:
    """Clear the in-memory key cache (test helper)."""
    with _jwk_lock:
        _jwk_cache.clear()
        global _jwk_last_fetch
        _jwk_last_fetch = 0.0
