"""
In-process rate limiter using token bucket algorithm.

Thread-safe, no external dependencies.
Returns 429 with Retry-After header when exceeded.
"""

import threading
import time
from functools import wraps
from typing import Dict, Optional

import azure.functions as func
import json


class TokenBucket:
    """Thread-safe token bucket rate limiter."""

    def __init__(self, rate: float, burst: int):
        self.rate = rate  # tokens per second
        self.burst = burst  # max tokens
        self.tokens = float(burst)
        self.last_refill = time.monotonic()
        self._lock = threading.Lock()

    def consume(self) -> Optional[float]:
        """Try to consume one token. Returns None if allowed, or seconds to wait."""
        with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_refill = now

            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return None
            else:
                return (1.0 - self.tokens) / self.rate


class RateLimiter:
    """Manages multiple named rate limiters."""

    _instance: Optional["RateLimiter"] = None
    _lock = threading.Lock()

    # Default limits per endpoint
    DEFAULT_LIMITS = {
        "generate": {"rate": 0.5, "burst": 3},
        "extract-topics": {"rate": 2.0, "burst": 10},
        "generate-tags": {"rate": 2.0, "burst": 10},
        "merge-topics": {"rate": 1.0, "burst": 5},
        "edit-article": {"rate": 1.0, "burst": 5},
        "auth-login": {"rate": 0.2, "burst": 5},
        "auth-forgot-password": {"rate": 0.1, "burst": 3},
    }

    def __init__(self):
        self._buckets: Dict[str, TokenBucket] = {}
        self._bucket_lock = threading.Lock()

    @classmethod
    def get(cls) -> "RateLimiter":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = RateLimiter()
        return cls._instance

    def _get_bucket(self, name: str) -> TokenBucket:
        if name not in self._buckets:
            with self._bucket_lock:
                if name not in self._buckets:
                    config = self.DEFAULT_LIMITS.get(name, {"rate": 5.0, "burst": 20})
                    self._buckets[name] = TokenBucket(config["rate"], config["burst"])
        return self._buckets[name]

    def check(self, name: str) -> Optional[float]:
        """Check rate limit. Returns None if allowed, or seconds to wait."""
        bucket = self._get_bucket(name)
        return bucket.consume()


def with_rate_limit(endpoint_name: str):
    """Decorator to add rate limiting to Azure Function handlers."""
    def decorator(handler):
        @wraps(handler)
        async def wrapper(req: func.HttpRequest) -> func.HttpResponse:
            limiter = RateLimiter.get()
            retry_after = limiter.check(endpoint_name)
            if retry_after is not None:
                return func.HttpResponse(
                    json.dumps({
                        "error": "Rate limit exceeded",
                        "retry_after_seconds": round(retry_after, 1),
                    }),
                    status_code=429,
                    headers={"Retry-After": str(int(retry_after) + 1)},
                    mimetype="application/json",
                )
            return await handler(req)
        return wrapper
    return decorator
