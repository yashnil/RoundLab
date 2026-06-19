"""Supabase access-token verification — asymmetric (JWKS) + legacy HS256."""

import json
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from fastapi import HTTPException
from jwt.algorithms import ECAlgorithm, RSAAlgorithm

from app.config import settings
from app.services import auth
from app.services.auth import get_current_user_id, verify_supabase_jwt

URL = "https://proj.supabase.co"
ISSUER = "https://proj.supabase.co/auth/v1"
HS_SECRET = "legacy-hs256-secret-at-least-32-bytes!!"


@pytest.fixture(autouse=True)
def _auth_env(monkeypatch):
    monkeypatch.setattr(settings, "supabase_url", URL, raising=False)
    monkeypatch.setattr(settings, "supabase_jwks_url", "", raising=False)
    monkeypatch.setattr(settings, "supabase_jwt_issuer", "", raising=False)
    monkeypatch.setattr(settings, "supabase_jwt_secret", "", raising=False)
    monkeypatch.setattr(settings, "auth_allow_hs256_fallback", False, raising=False)
    auth._reset_jwks_cache_for_tests()
    yield
    auth._reset_jwks_cache_for_tests()


# ── key + token helpers ─────────────────────────────────────────────────────────


def _rsa_key(kid: str):
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(RSAAlgorithm.to_jwk(priv.public_key()))
    jwk.update({"kid": kid, "alg": "RS256", "use": "sig"})
    return priv, jwk


def _ec_key(kid: str):
    priv = ec.generate_private_key(ec.SECP256R1())
    jwk = json.loads(ECAlgorithm.to_jwk(priv.public_key()))
    jwk.update({"kid": kid, "alg": "ES256", "use": "sig"})
    return priv, jwk


def _token(priv, kid, *, alg="RS256", sub="user-1", iss=ISSUER, aud="authenticated",
           exp_delta=timedelta(hours=1)):
    payload = {"sub": sub, "aud": aud, "iss": iss, "exp": datetime.now(timezone.utc) + exp_delta}
    return jwt.encode(payload, priv, algorithm=alg, headers={"kid": kid})


def _patch_jwks(monkeypatch, keys):
    monkeypatch.setattr(auth, "_load_jwks_keys", lambda: list(keys))


# ── asymmetric verification ─────────────────────────────────────────────────────


def test_valid_rs256_token(monkeypatch):
    priv, jwk = _rsa_key("k1")
    _patch_jwks(monkeypatch, [jwk])
    assert verify_supabase_jwt(_token(priv, "k1", sub="abc")) == "abc"


def test_valid_es256_token(monkeypatch):
    priv, jwk = _ec_key("e1")
    _patch_jwks(monkeypatch, [jwk])
    assert verify_supabase_jwt(_token(priv, "e1", alg="ES256", sub="ec-user")) == "ec-user"


def test_wrong_issuer_rejected(monkeypatch):
    priv, jwk = _rsa_key("k1")
    _patch_jwks(monkeypatch, [jwk])
    with pytest.raises(HTTPException) as exc:
        verify_supabase_jwt(_token(priv, "k1", iss="https://evil.example/auth/v1"))
    assert exc.value.status_code == 401


def test_unknown_kid_rejected(monkeypatch):
    priv, _ = _rsa_key("k1")
    _patch_jwks(monkeypatch, [])  # JWKS has no matching key
    with pytest.raises(HTTPException) as exc:
        verify_supabase_jwt(_token(priv, "missing-kid"))
    assert exc.value.status_code == 401


def test_rotated_key_triggers_refetch(monkeypatch):
    priv_a, jwk_a = _rsa_key("kA")
    priv_b, jwk_b = _rsa_key("kB")
    _patch_jwks(monkeypatch, [jwk_a])
    assert verify_supabase_jwt(_token(priv_a, "kA")) == "user-1"
    # Key rotates: JWKS now serves kB. A token with the new kid must verify.
    _patch_jwks(monkeypatch, [jwk_b])
    assert verify_supabase_jwt(_token(priv_b, "kB")) == "user-1"


def test_disallowed_algorithm_rejected(monkeypatch):
    # HS256 token while fallback is disabled → rejected without trusting the header.
    _patch_jwks(monkeypatch, [])
    token = jwt.encode(
        {"sub": "x", "aud": "authenticated", "iss": ISSUER,
         "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        HS_SECRET, algorithm="HS256", headers={"kid": "k1"},
    )
    with pytest.raises(HTTPException) as exc:
        verify_supabase_jwt(token)
    assert exc.value.status_code == 401


def test_expired_token_rejected(monkeypatch):
    priv, jwk = _rsa_key("k1")
    _patch_jwks(monkeypatch, [jwk])
    with pytest.raises(HTTPException) as exc:
        verify_supabase_jwt(_token(priv, "k1", exp_delta=timedelta(hours=-1)))
    assert exc.value.status_code == 401


def test_jwks_outage_uses_cached_key(monkeypatch):
    priv, jwk = _rsa_key("k1")
    _patch_jwks(monkeypatch, [jwk])
    assert verify_supabase_jwt(_token(priv, "k1")) == "user-1"  # primes the cache

    def _boom():
        raise RuntimeError("jwks endpoint down")

    monkeypatch.setattr(auth, "_load_jwks_keys", _boom)
    # Same kid is cached, so verification still succeeds during the outage.
    assert verify_supabase_jwt(_token(priv, "k1", sub="still-works")) == "still-works"


def test_jwks_outage_unknown_kid_is_503(monkeypatch):
    priv, _ = _rsa_key("k1")

    def _boom():
        raise RuntimeError("down")

    monkeypatch.setattr(auth, "_load_jwks_keys", _boom)
    with pytest.raises(HTTPException) as exc:
        verify_supabase_jwt(_token(priv, "k1"))
    assert exc.value.status_code == 503


# ── legacy HS256 fallback ────────────────────────────────────────────────────────


def _hs_token(**kw):
    payload = {"sub": kw.get("sub", "hs-user"), "aud": "authenticated", "iss": ISSUER,
               "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    return jwt.encode(payload, HS_SECRET, algorithm="HS256")


def test_legacy_fallback_enabled(monkeypatch):
    monkeypatch.setattr(settings, "supabase_jwt_secret", HS_SECRET, raising=False)
    monkeypatch.setattr(settings, "auth_allow_hs256_fallback", True, raising=False)
    assert verify_supabase_jwt(_hs_token(sub="legacy")) == "legacy"


def test_legacy_fallback_disabled(monkeypatch):
    monkeypatch.setattr(settings, "supabase_jwt_secret", HS_SECRET, raising=False)
    monkeypatch.setattr(settings, "auth_allow_hs256_fallback", False, raising=False)
    with pytest.raises(HTTPException) as exc:
        verify_supabase_jwt(_hs_token())
    assert exc.value.status_code == 401


# ── dependency ───────────────────────────────────────────────────────────────────


def test_dependency_requires_bearer():
    with pytest.raises(HTTPException) as exc:
        get_current_user_id(authorization=None)
    assert exc.value.status_code == 401
    with pytest.raises(HTTPException):
        get_current_user_id(authorization="Token xyz")


def test_dependency_extracts_user(monkeypatch):
    priv, jwk = _rsa_key("k1")
    _patch_jwks(monkeypatch, [jwk])
    assert get_current_user_id(authorization=f"Bearer {_token(priv, 'k1', sub='me')}") == "me"
