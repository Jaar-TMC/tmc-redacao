"""
Centralized configuration loaded from environment variables.

Validates required vars at startup (fail fast).
Thread-safe frozen dataclass singleton.
"""

import os
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
    llm_model: str = "claude-sonnet-4-5-20250929"

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

    # Safety thresholds
    min_source_chars: int = 100
    nota_only_threshold: int = 150
    max_regeneration_attempts: int = 1
    regen_fabrication_threshold: int = 2

    # CORS
    cors_allowed_origins: str = ""

    # Rate limits
    rate_limit_generate: float = 0.5
    rate_limit_burst_generate: int = 3

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
        llm_model=os.environ.get("LLM_MODEL", "claude-sonnet-4-5-20250929"),
        # Exa
        exa_api_key=os.environ.get("EXA_API_KEY", ""),
        exa_max_results=_int_env("EXA_MAX_RESULTS", 5),
        exa_search_days=_int_env("EXA_SEARCH_DAYS", 7),
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
        min_source_chars=_int_env("MIN_SOURCE_CHARS", 100),
        nota_only_threshold=_int_env("NOTA_ONLY_THRESHOLD", 150),
        max_regeneration_attempts=_int_env("MAX_REGENERATION_ATTEMPTS", 1),
        regen_fabrication_threshold=_int_env("REGEN_FABRICATION_THRESHOLD", 2),
        # CORS
        cors_allowed_origins=os.environ.get("CORS_ALLOWED_ORIGINS", ""),
        # Rate limits
        rate_limit_generate=_float_env("RATE_LIMIT_GENERATE", 0.5),
        rate_limit_burst_generate=_int_env("RATE_LIMIT_BURST_GENERATE", 3),
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
