"""Lightweight in-process metrics for voice endpoints.

Tracks per-backend call counts, latency histogram, failure reasons, and
cache hits. Exposed via /voice/metrics for quick health checks without
pulling in prometheus.
"""
from __future__ import annotations

import threading
import time
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Deque, Dict


@dataclass
class _BackendStats:
    calls: int = 0
    errors: int = 0
    total_latency: float = 0.0
    recent_latencies: Deque[float] = field(default_factory=lambda: deque(maxlen=100))
    error_reasons: Counter = field(default_factory=Counter)
    last_error: str = ""

    def record(self, latency: float, error: str | None) -> None:
        self.calls += 1
        self.total_latency += latency
        self.recent_latencies.append(latency)
        if error:
            self.errors += 1
            # Clip reason to avoid unbounded growth from unique messages.
            reason = error.split(":")[0][:80]
            self.error_reasons[reason] += 1
            self.last_error = error[:200]

    def snapshot(self) -> Dict:
        avg = self.total_latency / self.calls if self.calls else 0.0
        recent = list(self.recent_latencies)
        recent_sorted = sorted(recent)
        p50 = recent_sorted[len(recent_sorted) // 2] if recent_sorted else 0.0
        p95_idx = max(0, int(len(recent_sorted) * 0.95) - 1)
        p95 = recent_sorted[p95_idx] if recent_sorted else 0.0
        return {
            "calls": self.calls,
            "errors": self.errors,
            "error_rate": round(self.errors / self.calls, 4) if self.calls else 0.0,
            "avg_latency_s": round(avg, 3),
            "p50_latency_s": round(p50, 3),
            "p95_latency_s": round(p95, 3),
            "top_errors": self.error_reasons.most_common(3),
            "last_error": self.last_error,
        }


class VoiceMetrics:
    """Thread-safe metrics aggregator."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._backends: Dict[str, _BackendStats] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        self._started_at = time.time()

    def record(self, backend: str, latency: float, error: str | None = None) -> None:
        with self._lock:
            stats = self._backends.setdefault(backend, _BackendStats())
            stats.record(latency, error)

    def record_cache(self, hit: bool) -> None:
        with self._lock:
            if hit:
                self._cache_hits += 1
            else:
                self._cache_misses += 1

    def snapshot(self) -> Dict:
        with self._lock:
            total_cache = self._cache_hits + self._cache_misses
            return {
                "uptime_s": round(time.time() - self._started_at, 1),
                "backends": {k: v.snapshot() for k, v in self._backends.items()},
                "cache": {
                    "hits": self._cache_hits,
                    "misses": self._cache_misses,
                    "hit_rate": round(self._cache_hits / total_cache, 4) if total_cache else 0.0,
                },
            }


metrics = VoiceMetrics()
