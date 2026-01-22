"""
Tracks fallback usage and offline transitions for Gemini integration.
Provides simple counters and last-reason snapshots for UI/telemetry.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass
class FallbackMonitor:
    event_fallbacks: int = 0
    resolution_fallbacks: int = 0
    offline_notified: bool = False
    last_reason: str | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def record_event(self, source: str, reason: str | None = None):
        if source != "fallback":
            return
        with self._lock:
            self.event_fallbacks += 1
            self.last_reason = reason or self.last_reason

    def record_resolution(self, source: str, reason: str | None = None):
        if source != "fallback":
            return
        with self._lock:
            self.resolution_fallbacks += 1
            self.last_reason = reason or self.last_reason

    def mark_offline_notified(self):
        with self._lock:
            self.offline_notified = True

    def should_notify_offline(self) -> bool:
        with self._lock:
            return not self.offline_notified
