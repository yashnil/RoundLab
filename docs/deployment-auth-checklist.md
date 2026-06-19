# Deployment & Auth Checklist

How to configure RoundLab so the authenticated team/assignment endpoints verify
real Supabase access tokens in production — for both modern (asymmetric JWKS) and
legacy (HS256) Supabase projects.

## Backend environment variables (server-only)

| Variable | Required | Purpose |
| --- | --- | --- |
| `SUPABASE_URL` | ✅ | Project URL. Also derives the token **issuer** (`<url>/auth/v1`) and the **JWKS URL** (`<url>/auth/v1/.well-known/jwks.json`). |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | Service-role DB access. **Never** expose to the browser. |
| `SUPABASE_JWKS_URL` | optional | Override the derived JWKS URL only if your setup differs. |
| `SUPABASE_JWT_ISSUER` | optional | Override the derived issuer only if your setup differs. |
| `SUPABASE_JWT_SECRET` | legacy only | HS256 shared secret (Supabase → Settings → API → JWT secret). |
| `AUTH_ALLOW_HS256_FALLBACK` | legacy only | `true` to accept HS256 tokens. Leave unset/`false` for modern projects. |
| `OPENAI_API_KEY` | optional | Enables the LLM pipeline; deterministic fallback runs without it. |
| `CORS_ORIGINS` | ✅ | Comma-separated allowed origins (your Vercel domain). |

### Modern Supabase project (default, recommended)
Asymmetric signing keys (RS256/ES256). Set `SUPABASE_URL` (+ `SUPABASE_SERVICE_ROLE_KEY`,
`CORS_ORIGINS`). JWKS URL and issuer derive automatically; keys are fetched, cached,
and rotated on an unknown `kid`. **Do not** enable HS256 fallback.

### Legacy Supabase project (HS256)
If your project still issues HS256 tokens, additionally set `SUPABASE_JWT_SECRET`
and `AUTH_ALLOW_HS256_FALLBACK=true`. The algorithm is still allowlisted — HS256 is
only accepted when both are present; it is never trusted implicitly.

## Frontend / Vercel environment variables

| Variable | Required | Notes |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | ✅ | Backend base URL. |
| `NEXT_PUBLIC_SUPABASE_URL` | ✅ | Public — safe in the browser. |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | ✅ | Public anon key — safe in the browser. |

The browser client signs users in and holds the session; `apiFetch` attaches the
**current** access token as `Authorization: Bearer <token>` and, on a `401`,
refreshes the Supabase session **once** and retries before surfacing the error.

## Secret-exposure verification

- ❌ Never prefix a secret with `NEXT_PUBLIC_`. Only `SUPABASE_URL` and the
  **anon** key are public; the **service-role key** and **JWT secret** are
  backend-only.
- Confirm `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET` appear **only** in the
  backend environment (Render/Fly/etc.), never in Vercel's client build.
- Quick check (should return nothing):
  ```bash
  grep -rEn "NEXT_PUBLIC_.*(SERVICE_ROLE|JWT_SECRET)" frontend/ .env.example
  ```
- The backend `get_supabase()` client uses the service-role key and is never sent
  to the client; tokens are verified locally (JWKS/HS256), so the service-role key
  is not needed for auth.

## Smoke test after deploy

1. Sign in on the deployed frontend.
2. As a coach, create an assignment → expect `201`.
3. Call an assignment endpoint with **no** `Authorization` header → expect `401`.
4. Call with a tampered/expired token → expect `401`.
5. Leave the tab open past the access-token lifetime, act again → the silent
   refresh-and-retry keeps it working (no spurious `401`).
