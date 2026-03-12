"""
Gemini API client for Vertex AI.

Provides the same interface as LLMService._call_api() so callers
(classification, scoring, theme naming) work unchanged.
"""

import asyncio
import json
import logging
import os
import re
import threading
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Gemini cost per token (Gemini 2.5 Flash on Vertex AI)
GEMINI_COST_MAP = {
    "gemini-2.5-flash": (0.15 / 1_000_000, 0.60 / 1_000_000),   # $0.15/M in, $0.60/M out
    "gemini-2.5-pro":   (1.25 / 1_000_000, 10.00 / 1_000_000),
    "gemini-2.0-flash": (0.10 / 1_000_000, 0.40 / 1_000_000),
}


class GeminiService:
    """Vertex AI Gemini client with OAuth2 token auto-refresh."""

    def __init__(
        self,
        service_account_path: str = "",
        project_id: str = "",
        region: str = "us-central1",
    ):
        self._sa_path = service_account_path or os.environ.get(
            "GOOGLE_APPLICATION_CREDENTIALS", ""
        )
        self._project_id = project_id or os.environ.get(
            "GCP_PROJECT_ID", ""
        )
        self._region = region or os.environ.get("GCP_REGION", "us-central1")

        # Token cache
        self._token: Optional[str] = None
        self._token_expiry: float = 0
        self._token_lock = threading.Lock()

        # HTTP client (lazy init for async context)
        self._http_client: Optional[httpx.AsyncClient] = None

        # Circuit breaker
        self._failures = 0
        self._circuit_open = False
        self._circuit_open_until = 0.0

        if not self._sa_path:
            logger.warning(
                "GeminiService: No service account path configured. "
                "Set GOOGLE_APPLICATION_CREDENTIALS env var."
            )
        else:
            logger.info(
                f"GeminiService: project={self._project_id} "
                f"region={self._region} sa={self._sa_path}"
            )

    @property
    def is_configured(self) -> bool:
        """Return True if Gemini is properly configured."""
        return bool(self._sa_path and self._project_id)

    def _refresh_token(self) -> str:
        """Get or refresh the OAuth2 access token (thread-safe)."""
        now = time.time()
        if self._token and now < self._token_expiry - 60:
            return self._token

        with self._token_lock:
            # Double-check after acquiring lock
            if self._token and now < self._token_expiry - 60:
                return self._token

            from google.auth.transport.requests import Request
            from google.oauth2 import service_account

            creds = service_account.Credentials.from_service_account_file(
                self._sa_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            creds.refresh(Request())
            self._token = creds.token
            # Google tokens expire in ~3600s; refresh at 3540s
            self._token_expiry = now + 3540
            logger.info("GeminiService: OAuth2 token refreshed")
            return self._token

    def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=120.0)
        return self._http_client

    async def close(self):
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    async def call_api(
        self,
        system: str,
        user_content: str,
        max_tokens: int = 4096,
        correlation_id: str = "",
        model: str = "gemini-2.5-flash",
        task_type: str = "",
    ) -> str:
        """
        Call Gemini API via Vertex AI. Returns response text.

        Same interface as LLMService._call_api() for drop-in compatibility.
        """
        _cid = f"[{correlation_id}] " if correlation_id else ""

        # Circuit breaker
        if self._circuit_open:
            if time.time() < self._circuit_open_until:
                raise RuntimeError("Gemini API circuit breaker is open")
            self._circuit_open = False
            logger.info(f"{_cid}Gemini circuit breaker half-open")

        if not self.is_configured:
            raise ValueError(
                "GeminiService not configured. "
                "Set GOOGLE_APPLICATION_CREDENTIALS and GCP_PROJECT_ID."
            )

        token = self._refresh_token()

        endpoint = (
            f"https://{self._region}-aiplatform.googleapis.com/v1/"
            f"projects/{self._project_id}/locations/{self._region}/"
            f"publishers/google/models/{model}:generateContent"
        )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

        # Build Gemini payload
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_content}],
                }
            ],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0.0,
            },
        }

        # Add system instruction if provided
        if system:
            payload["systemInstruction"] = {
                "parts": [{"text": system}]
            }

        logger.info(
            f"{_cid}Gemini API call: model={model} task={task_type} "
            f"region={self._region}"
        )

        client = self._get_client()

        # Retry loop for 429 rate limits (up to 3 attempts)
        max_retries = 3
        for attempt in range(max_retries):
            t0 = time.time()
            resp = await client.post(endpoint, json=payload, headers=headers)
            elapsed = time.time() - t0

            if resp.status_code == 429 and attempt < max_retries - 1:
                wait = 5 * (attempt + 1)  # 5s, 10s
                logger.warning(
                    f"{_cid}Gemini 429 rate limited ({elapsed:.1f}s), "
                    f"retry {attempt+1}/{max_retries} in {wait}s"
                )
                await asyncio.sleep(wait)
                continue

            if resp.status_code != 200:
                error_text = resp.text[:500]
                logger.error(
                    f"{_cid}Gemini API error: {resp.status_code} "
                    f"({elapsed:.1f}s) {error_text}"
                )
                self._failures += 1
                if self._failures >= 5:
                    self._circuit_open = True
                    self._circuit_open_until = time.time() + 120
                    logger.warning(f"{_cid}Gemini circuit breaker OPENED")
                raise RuntimeError(
                    f"Gemini API error {resp.status_code}: {error_text}"
                )
            break  # Success — proceed to parse response

        data = resp.json()

        # Extract text from Gemini response
        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError("Gemini returned no candidates")

        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts)

        # Gemini wraps JSON in ```json ... ``` — strip for compatibility
        # with callers that expect raw JSON (classification, scoring, etc.)
        if text.strip().startswith("```"):
            text = re.sub(r'^```(?:json)?\s*', '', text.strip())
            text = re.sub(r'\s*```\s*$', '', text)

        # Extract usage
        usage = data.get("usageMetadata", {})
        input_tokens = usage.get("promptTokenCount", 0)
        output_tokens = usage.get("candidatesTokenCount", 0)

        logger.info(
            f"{_cid}Gemini OK: {model} in={input_tokens} "
            f"out={output_tokens} ({elapsed:.1f}s)"
        )

        # Reset circuit breaker on success
        self._failures = 0

        # Log usage asynchronously (non-blocking)
        self._log_usage_async(
            model=model,
            task_type=task_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            elapsed=elapsed,
            correlation_id=correlation_id,
        )

        return text

    def _log_usage_async(
        self,
        model: str,
        task_type: str,
        input_tokens: int,
        output_tokens: int,
        elapsed: float,
        correlation_id: str,
    ):
        """Log usage to llm_usage_log table (non-blocking)."""
        try:
            from concurrent.futures import ThreadPoolExecutor

            cost_in, cost_out = GEMINI_COST_MAP.get(
                model, (0.15 / 1_000_000, 0.60 / 1_000_000)
            )
            total_cost = input_tokens * cost_in + output_tokens * cost_out

            def _do_log():
                try:
                    from services.database import get_db

                    db = get_db()
                    db.log_llm_usage(
                        model=model,
                        task_type=task_type or "gemini_call",
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cost_usd=total_cost,
                        duration_ms=int(elapsed * 1000),
                        correlation_id=correlation_id or None,
                    )
                except Exception as e:
                    logger.debug(f"Gemini usage log failed: {e}")

            _executor = ThreadPoolExecutor(max_workers=1)
            _executor.submit(_do_log)
        except Exception:
            pass  # Never fail on logging


# Singleton
_gemini_service: Optional[GeminiService] = None
_gemini_lock = threading.Lock()


def get_gemini_service() -> GeminiService:
    """Get or create the GeminiService singleton."""
    global _gemini_service
    if _gemini_service is None:
        with _gemini_lock:
            if _gemini_service is None:
                from services.config import get_config

                cfg = get_config()
                _gemini_service = GeminiService(
                    service_account_path=cfg.gemini_sa_path,
                    project_id=cfg.gemini_project_id,
                    region=cfg.gemini_region,
                )
    return _gemini_service
