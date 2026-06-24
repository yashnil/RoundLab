from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    # ── Auth: Supabase access-token verification ────────────────────────────
    # Modern projects sign tokens with rotating asymmetric keys (RS256/ES256)
    # published at a JWKS endpoint; the issuer is "<supabase_url>/auth/v1".
    # Override the derived JWKS URL / issuer only if your setup differs.
    supabase_jwks_url: str = Field(default="", alias="SUPABASE_JWKS_URL")
    supabase_jwt_issuer: str = Field(default="", alias="SUPABASE_JWT_ISSUER")
    # Legacy projects sign with a shared HS256 secret. Only used when fallback is
    # explicitly enabled — never trusted implicitly.
    supabase_jwt_secret: str = Field(default="", alias="SUPABASE_JWT_SECRET")
    auth_allow_hs256_fallback: bool = Field(default=False, alias="AUTH_ALLOW_HS256_FALLBACK")
    cors_origins: str = "http://localhost:3000"
    environment: str = "development"
    tavily_api_key: str = ""

    # Optional provider keys — absence never breaks local dev
    exa_api_key: Optional[str] = Field(default=None, alias="EXA_API_KEY")
    firecrawl_api_key: Optional[str] = Field(default=None, alias="FIRECRAWL_API_KEY")
    cohere_api_key: Optional[str] = Field(default=None, alias="COHERE_API_KEY")
    jina_api_key: Optional[str] = Field(default=None, alias="JINA_API_KEY")

    # Research search tuning knobs
    research_search_max_queries: int = Field(default=12, alias="RESEARCH_SEARCH_MAX_QUERIES")
    research_search_max_urls: int = Field(default=20, alias="RESEARCH_SEARCH_MAX_URLS")
    research_search_max_extracted_pages: int = Field(default=12, alias="RESEARCH_SEARCH_MAX_EXTRACTED_PAGES")
    research_search_max_classified_chunks: int = Field(default=40, alias="RESEARCH_SEARCH_MAX_CLASSIFIED_CHUNKS")
    research_enable_llm_role_classifier: bool = Field(default=True, alias="RESEARCH_ENABLE_LLM_ROLE_CLASSIFIER")
    research_enable_strict_card_validation: bool = Field(default=True, alias="RESEARCH_ENABLE_STRICT_CARD_VALIDATION")

    # Optional LLM card refiner (tagline/warrant/impact/prep). Only used when an
    # OpenAI key is configured; otherwise the deterministic pipeline runs.
    research_enable_llm_refiner: bool = Field(default=True, alias="RESEARCH_ENABLE_LLM_REFINER")

    # Optional semantic reranker for candidate passages. Off by default so local
    # dev never pulls a model; enable explicitly when a provider is wired.
    use_semantic_reranker: bool = Field(default=False, alias="USE_SEMANTIC_RERANKER")

    # Evidence Set Builder — per-slot planning + search (Parts 1-2)
    research_enable_slot_planner: bool = Field(default=True, alias="RESEARCH_ENABLE_SLOT_PLANNER")
    research_max_evidence_slots: int = Field(default=5, alias="RESEARCH_MAX_EVIDENCE_SLOTS")

    # Optional Zotero Translation Server for citation metadata (Part 3)
    zotero_translation_server_url: Optional[str] = Field(
        default=None, alias="ZOTERO_TRANSLATION_SERVER_URL"
    )
    research_enable_zotero: bool = Field(default=False, alias="RESEARCH_ENABLE_ZOTERO")

    # Pass 9: academic and primary-source routing
    # Both providers are free without keys; keys only raise rate limits.
    semantic_scholar_api_key: Optional[str] = Field(
        default=None, alias="SEMANTIC_SCHOLAR_API_KEY"
    )
    openalex_contact_email: Optional[str] = Field(
        default=None, alias="OPENALEX_CONTACT_EMAIL"
    )
    # Set to False to prevent live HTTP calls in test / CI environments.
    research_enable_academic_search: bool = Field(
        default=True, alias="RESEARCH_ENABLE_ACADEMIC_SEARCH"
    )

    # Pass 11: card support verification
    research_enable_card_verification: bool = Field(
        default=True, alias="RESEARCH_ENABLE_CARD_VERIFICATION"
    )
    card_verifier_backend: str = Field(
        default="llm", alias="CARD_VERIFIER_BACKEND"
    )  # "llm" | "disabled"
    card_verifier_timeout_s: float = Field(
        default=10.0, alias="CARD_VERIFIER_TIMEOUT_S"
    )
    card_verifier_max_cards: int = Field(
        default=4, alias="CARD_VERIFIER_MAX_CARDS"
    )
    card_verifier_max_context_chars: int = Field(
        default=3000, alias="CARD_VERIFIER_MAX_CONTEXT_CHARS"
    )

    # ── Pass 18: Pilot mode + cost controls ────────────────────────────────
    # Enable to enforce per-user daily limits and surface cost tracking.
    pilot_mode: bool = Field(default=False, alias="PILOT_MODE")
    # Max USD per user per day across all LLM + provider calls.
    daily_llm_budget_usd: float = Field(default=1.0, alias="DAILY_LLM_BUDGET_USD")
    # Hard caps for specific operations per user per day.
    max_rounds_per_user_daily: int = Field(default=5, alias="MAX_ROUNDS_PER_USER_DAILY")
    max_evidence_searches_per_day: int = Field(default=20, alias="MAX_EVIDENCE_SEARCHES_PER_DAY")
    # Latency budget targets in seconds (for monitoring, not enforcement).
    latency_evidence_search_s: float = Field(default=30.0, alias="LATENCY_EVIDENCE_SEARCH_S")
    latency_card_cut_s: float = Field(default=15.0, alias="LATENCY_CARD_CUT_S")
    latency_opponent_speech_s: float = Field(default=20.0, alias="LATENCY_OPPONENT_SPEECH_S")
    latency_ballot_s: float = Field(default=25.0, alias="LATENCY_BALLOT_S")

    model_config = {"env_file": ".env", "extra": "ignore", "populate_by_name": True}


settings = Settings()


def get_tavily_api_key() -> Optional[str]:
    """Return the Tavily API key if configured, or None.

    Reads from the pydantic-settings object (which loads from .env in dev
    and from actual environment variables in production).
    Never logs or exposes the key value.
    """
    key = settings.tavily_api_key.strip()
    return key if key else None


def get_openai_api_key() -> Optional[str]:
    """Return the OpenAI API key if configured (settings or OS env), else None."""
    import os
    key = (settings.openai_api_key or os.getenv("OPENAI_API_KEY", "")).strip()
    return key if key else None
