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
