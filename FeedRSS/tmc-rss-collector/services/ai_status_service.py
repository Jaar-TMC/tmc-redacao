"""
AI Status Service - Runtime control for AI operations.
Provides a database-backed kill switch with TTL cache for pausing all AI operations.
"""
import datetime
import logging
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 30


class AiStatusService:
    """Thread-safe service for checking/setting AI pause state with TTL cache."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._cache = {"paused": False, "paused_by": None, "paused_at": None}
        self._cache_expires_at = 0.0
        self._cache_lock = threading.Lock()
        self._initialized = True
        logger.info("AiStatusService initialized")

    def _is_cache_valid(self) -> bool:
        return time.time() < self._cache_expires_at

    def _refresh_cache(self) -> None:
        """Load AI status from database, fail-open to active."""
        try:
            from services.database import get_db
            db = get_db()
            setting = db.get_system_setting("ai_paused")
            if setting:
                self._cache = {
                    "paused": setting["value"].lower() == "true",
                    "paused_by": setting.get("updated_by"),
                    "paused_at": setting.get("updated_at"),
                }
            else:
                self._cache = {"paused": False, "paused_by": None, "paused_at": None}
            self._cache_expires_at = time.time() + CACHE_TTL_SECONDS
        except Exception as e:
            logger.warning(f"Failed to refresh AI status cache, defaulting to active: {e}")
            self._cache = {"paused": False, "paused_by": None, "paused_at": None}
            self._cache_expires_at = time.time() + CACHE_TTL_SECONDS

    def is_ai_paused(self) -> bool:
        """Check if AI operations are paused. Thread-safe, cached with 30s TTL. Fail-open."""
        with self._cache_lock:
            if not self._is_cache_valid():
                self._refresh_cache()
            return self._cache["paused"]

    def get_ai_status(self) -> dict:
        """Get full AI status including pause state, who paused, and cost data."""
        with self._cache_lock:
            if not self._is_cache_valid():
                self._refresh_cache()
            status = dict(self._cache)

        # Add cost savings estimate if paused
        if status["paused"] and status.get("paused_at"):
            try:
                from services.database import get_db
                db = get_db()
                # Calculate hours paused
                paused_at = status["paused_at"]
                if isinstance(paused_at, str):
                    paused_at = datetime.datetime.fromisoformat(paused_at)
                hours_paused = (datetime.datetime.utcnow() - paused_at).total_seconds() / 3600

                # Get average hourly cost from last 7 days
                cost_summary = db.get_ai_cost_summary(hours=168)  # 7 days
                if cost_summary and cost_summary["total_cost_usd"] > 0:
                    avg_hourly_cost = cost_summary["total_cost_usd"] / cost_summary["hours"]
                    status["estimated_savings_usd"] = round(avg_hourly_cost * hours_paused, 2)
                    status["avg_hourly_cost_usd"] = round(avg_hourly_cost, 4)
                else:
                    status["estimated_savings_usd"] = 0.0
                    status["avg_hourly_cost_usd"] = 0.0

                status["hours_paused"] = round(hours_paused, 1)
            except Exception as e:
                logger.warning(f"Failed to calculate cost savings: {e}")
                status["estimated_savings_usd"] = 0.0
                status["hours_paused"] = 0.0

        return status

    def set_ai_paused(self, paused: bool, user_email: str) -> bool:
        """Set AI pause state. Invalidates cache immediately."""
        try:
            from services.database import get_db
            db = get_db()
            db.set_system_setting("ai_paused", str(paused).lower(), updated_by=user_email)

            # Invalidate cache immediately
            with self._cache_lock:
                self._cache_expires_at = 0.0

            action = "paused" if paused else "resumed"
            logger.info(f"AI operations {action} by {user_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to set AI pause state: {e}")
            return False


# Module-level convenience functions (match project patterns)
_service: Optional[AiStatusService] = None


def get_ai_status_service() -> AiStatusService:
    """Get or create the AiStatusService singleton."""
    global _service
    if _service is None:
        _service = AiStatusService()
    return _service


def is_ai_paused() -> bool:
    """Convenience function: check if AI is paused. Safe to call from any context."""
    return get_ai_status_service().is_ai_paused()
