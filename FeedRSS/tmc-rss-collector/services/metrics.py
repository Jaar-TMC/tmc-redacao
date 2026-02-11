"""
In-process metrics collection for TMC pipeline observability.

Thread-safe counters and histograms with rolling window.
No external dependencies (no Prometheus, no Redis).

Exposed via GET /api/metrics endpoint.
"""

import threading
import time
from collections import deque
from typing import Dict, Optional


class Metrics:
    """Thread-safe in-process metrics singleton."""

    _instance: Optional["Metrics"] = None
    _lock = threading.Lock()

    ROLLING_WINDOW = 1000  # Keep last N observations per histogram

    def __init__(self):
        self._counters: Dict[str, int] = {}
        self._histograms: Dict[str, deque] = {}
        self._counter_lock = threading.Lock()
        self._histogram_lock = threading.Lock()
        self._start_time = time.time()

    @classmethod
    def get(cls) -> "Metrics":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = Metrics()
        return cls._instance

    def increment(self, name: str, value: int = 1) -> None:
        with self._counter_lock:
            self._counters[name] = self._counters.get(name, 0) + value

    def observe(self, name: str, value: float) -> None:
        with self._histogram_lock:
            if name not in self._histograms:
                self._histograms[name] = deque(maxlen=self.ROLLING_WINDOW)
            self._histograms[name].append(value)

    def get_counter(self, name: str) -> int:
        with self._counter_lock:
            return self._counters.get(name, 0)

    def get_histogram_stats(self, name: str) -> Optional[dict]:
        with self._histogram_lock:
            if name not in self._histograms or len(self._histograms[name]) == 0:
                return None
            values = sorted(self._histograms[name])
            n = len(values)
            return {
                "count": n,
                "min": values[0],
                "max": values[-1],
                "avg": sum(values) / n,
                "p50": values[n // 2],
                "p95": values[int(n * 0.95)] if n >= 20 else values[-1],
                "p99": values[int(n * 0.99)] if n >= 100 else values[-1],
            }

    def snapshot(self) -> dict:
        with self._counter_lock:
            counters = dict(self._counters)
        histograms = {}
        with self._histogram_lock:
            for name in self._histograms:
                stats = self.get_histogram_stats(name)
                if stats:
                    histograms[name] = stats
        return {
            "uptime_seconds": int(time.time() - self._start_time),
            "counters": counters,
            "histograms": histograms,
        }

    def reset(self) -> None:
        with self._counter_lock:
            self._counters.clear()
        with self._histogram_lock:
            self._histograms.clear()
