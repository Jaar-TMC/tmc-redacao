"""
Centralized configuration loaded from environment variables.

Validates required vars at startup (fail fast).
Thread-safe frozen dataclass singleton.
"""

import os
import secrets
import threading
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class AppConfig:
    """Application configuration loaded from environment variables."""

    # Database (required)
    sql_server: str = ""
    sql_database: str = ""
    sql_username: str = ""
    sql_password: str = ""
    sql_query_timeout: int = 30

    # LLM
    anthropic_api_key: str = ""
    azure_ai_api_key: str = ""
    azure_ai_endpoint: str = ""
    # Gemini (Vertex AI) - used for classification, scoring, theme naming
    gemini_sa_path: str = ""      # Path to service account JSON key
    gemini_project_id: str = ""   # GCP project ID
    gemini_region: str = "us-central1"

    # Per-task model routing (optimize cost vs quality)
    # Default: Anthropic API direct — Haiku for cheap tasks, Sonnet for heavy tasks
    # Gemini fields below are dormant (for future GCP production use)
    classification_model: str = "claude-haiku-4-5"
    scoring_model: str = "claude-haiku-4-5"
    theme_naming_model: str = "claude-haiku-4-5"
    # Heavy tasks: Sonnet 4.5 (generation, fact-check, editing, merging, extraction)
    event_verification_model: str = "claude-sonnet-4-5"
    event_extraction_model: str = "claude-sonnet-4-5"
    enrichment_extraction_model: str = "claude-sonnet-4-5"
    generation_model: str = "claude-sonnet-4-5"
    fact_check_model: str = "claude-sonnet-4-5"
    edit_model: str = "claude-sonnet-4-5"
    merge_model: str = "claude-sonnet-4-5"

    # Exa enrichment
    exa_api_key: str = ""
    exa_max_results: int = 5
    exa_search_days: int = 7

    # Feature flags
    fact_check_enabled: bool = True
    fact_check_enrichment_enabled: bool = True
    fact_check_verification_enabled: bool = True
    event_extraction_enabled: bool = True
    event_matching_enabled: bool = True
    cove_enabled: bool = True
    decontamination_enabled: bool = True
    production_safety_mode: bool = True

    # Prompt caching (Anthropic only - reduces cost on repeated system prompts)
    prompt_caching_enabled: bool = True

    # Safety thresholds
    min_source_chars: int = 300
    nota_only_threshold: int = 500
    short_source_threshold: int = 800
    # Publication-readiness floors (absolute minimums for any published article)
    publish_confidence_floor: float = 0.65
    publish_grounded_floor: float = 0.70
    publish_max_expansion: float = 8.0
    # CORS
    cors_allowed_origins: str = ""

    # Rate limits
    rate_limit_generate: float = 0.5
    rate_limit_burst_generate: int = 3

    # JWT Authentication
    jwt_secret_key: str = ""
    jwt_access_token_minutes: int = 60
    jwt_refresh_token_days: int = 7

    @property
    def has_llm_key(self) -> bool:
        return bool(self.anthropic_api_key or self.azure_ai_api_key)

    @property
    def has_exa_key(self) -> bool:
        return bool(self.exa_api_key)


def _bool_env(key: str, default: bool = True) -> bool:
    return os.environ.get(key, str(default).lower()).lower() == "true"


def _int_env(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except (ValueError, TypeError):
        return default


def _float_env(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, str(default)))
    except (ValueError, TypeError):
        return default


def load_config() -> AppConfig:
    """Load configuration from environment variables. Validates required vars."""
    config = AppConfig(
        # Database
        sql_server=os.environ.get("SQL_SERVER", ""),
        sql_database=os.environ.get("SQL_DATABASE", ""),
        sql_username=os.environ.get("SQL_USERNAME", ""),
        sql_password=os.environ.get("SQL_PASSWORD", ""),
        sql_query_timeout=_int_env("SQL_QUERY_TIMEOUT", 30),
        # LLM
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        azure_ai_api_key=os.environ.get("AZURE_AI_API_KEY", ""),
        azure_ai_endpoint=os.environ.get("AZURE_AI_ENDPOINT", ""),
        # Per-task model routing
        # Gemini (Vertex AI)
        gemini_sa_path=os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", ""),
        gemini_project_id=os.environ.get("GCP_PROJECT_ID", ""),
        gemini_region=os.environ.get("GCP_REGION", "us-central1"),
        # Per-task model routing
        classification_model=os.environ.get("CLASSIFICATION_MODEL", "claude-haiku-4-5"),
        scoring_model=os.environ.get("SCORING_MODEL", "claude-haiku-4-5"),
        theme_naming_model=os.environ.get("THEME_NAMING_MODEL", "claude-haiku-4-5"),
        event_verification_model=os.environ.get("EVENT_VERIFICATION_MODEL", "claude-sonnet-4-5"),
        event_extraction_model=os.environ.get("EVENT_EXTRACTION_MODEL", "claude-sonnet-4-5"),
        enrichment_extraction_model=os.environ.get("ENRICHMENT_EXTRACTION_MODEL", "claude-sonnet-4-5"),
        generation_model=os.environ.get("GENERATION_MODEL", "claude-sonnet-4-5"),
        fact_check_model=os.environ.get("FACT_CHECK_MODEL", "claude-sonnet-4-5"),
        edit_model=os.environ.get("EDIT_MODEL", "claude-sonnet-4-5"),
        merge_model=os.environ.get("MERGE_MODEL", "claude-sonnet-4-5"),
        # Exa
        exa_api_key=os.environ.get("EXA_API_KEY", ""),
        exa_max_results=_int_env("EXA_MAX_RESULTS", 5),
        exa_search_days=_int_env("EXA_SEARCH_DAYS", 7),
        # Prompt caching
        prompt_caching_enabled=_bool_env("PROMPT_CACHING_ENABLED", True),
        # Feature flags
        fact_check_enabled=_bool_env("FACT_CHECK_ENABLED", True),
        fact_check_enrichment_enabled=_bool_env("FACT_CHECK_ENRICHMENT_ENABLED", True),
        fact_check_verification_enabled=_bool_env("FACT_CHECK_VERIFICATION_ENABLED", True),
        event_extraction_enabled=_bool_env("EVENT_EXTRACTION_ENABLED", True),
        event_matching_enabled=_bool_env("EVENT_MATCHING_ENABLED", True),
        cove_enabled=_bool_env("COVE_ENABLED", True),
        decontamination_enabled=_bool_env("DECONTAMINATION_ENABLED", True),
        production_safety_mode=_bool_env("PRODUCTION_SAFETY_MODE", True),
        # Safety
        min_source_chars=_int_env("MIN_SOURCE_CHARS", 300),
        nota_only_threshold=_int_env("NOTA_ONLY_THRESHOLD", 500),
        short_source_threshold=_int_env("SHORT_SOURCE_THRESHOLD", 800),
        publish_confidence_floor=_float_env("PUBLISH_CONFIDENCE_FLOOR", 0.65),
        publish_grounded_floor=_float_env("PUBLISH_GROUNDED_FLOOR", 0.70),
        publish_max_expansion=_float_env("PUBLISH_MAX_EXPANSION", 8.0),
        # CORS
        cors_allowed_origins=os.environ.get("CORS_ALLOWED_ORIGINS", ""),
        # Rate limits
        rate_limit_generate=_float_env("RATE_LIMIT_GENERATE", 0.5),
        rate_limit_burst_generate=_int_env("RATE_LIMIT_BURST_GENERATE", 3),
        # JWT
        jwt_secret_key=os.environ.get("JWT_SECRET_KEY", ""),
        jwt_access_token_minutes=_int_env("JWT_ACCESS_TOKEN_MINUTES", 60),
        jwt_refresh_token_days=_int_env("JWT_REFRESH_TOKEN_DAYS", 7),
    )

    import logging
    log = logging.getLogger(__name__)

    # Validate: warn if database not configured (allow startup for local dev)
    missing_db = []
    if not config.sql_server:
        missing_db.append("SQL_SERVER")
    if not config.sql_database:
        missing_db.append("SQL_DATABASE")
    if missing_db:
        log.warning(
            f"Missing required DB env vars: {', '.join(missing_db)}. "
            "Database operations will fail."
        )

    # Validate LLM key (required for article generation)
    if not config.has_llm_key:
        log.warning(
            "Missing LLM API key: set ANTHROPIC_API_KEY or AZURE_AI_API_KEY. "
            "Article generation will fail."
        )

    # Validate Exa key (required for enrichment - degrades silently without)
    if not config.has_exa_key:
        log.warning(
            "Missing EXA_API_KEY: enrichment will be disabled. "
            "Anti-hallucination pipeline operates in degraded mode."
        )

    # Validate CORS in production
    if config.production_safety_mode and not config.cors_allowed_origins:
        log.warning(
            "PRODUCTION_SAFETY_MODE=true but CORS_ALLOWED_ORIGINS not set. "
            "Set to specific origins (e.g. https://app.tmc.com.br) for production."
        )

    # Validate JWT secret in production (mandatory - prevents forged tokens)
    if config.production_safety_mode:
        if not config.jwt_secret_key:
            raise RuntimeError(
                "JWT_SECRET_KEY is required in production mode. "
                "Set it as an environment variable."
            )
        if len(config.jwt_secret_key) < 32:
            raise RuntimeError(
                "JWT_SECRET_KEY must be at least 32 characters in production mode."
            )
    else:
        # Dev mode: generate a random secret so an empty string can never be
        # used as a valid signing key (prevents trivially forged JWTs).
        if not config.jwt_secret_key:
            fallback = secrets.token_hex(32)
            object.__setattr__(config, 'jwt_secret_key', fallback)
            log.warning(
                "JWT_SECRET_KEY not set — generated random dev secret. "
                "JWTs will be invalidated on restart."
            )

    # Force fact-checking in production mode - never allow it to be disabled
    if config.production_safety_mode and not config.fact_check_enabled:
        log.warning(
            "FACT_CHECK_ENABLED was False but PRODUCTION_SAFETY_MODE is True. "
            "Forcing fact_check_enabled=True."
        )
        object.__setattr__(config, 'fact_check_enabled', True)

    return config


_config: Optional[AppConfig] = None
_config_lock = threading.Lock()


def get_config() -> AppConfig:
    """Get or create the application config singleton."""
    global _config
    if _config is None:
        with _config_lock:
            if _config is None:
                _config = load_config()
    return _config
