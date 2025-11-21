from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class CooldownTracker:
    cooldown_seconds: float
    _last_alert_at: float | None = field(default=None, repr=False)

    @classmethod
    def from_minutes(cls, minutes: int) -> CooldownTracker:
        return cls(cooldown_seconds=float(minutes) * 60.0)

    def can_alert(self, now: float | None = None) -> bool:
        if self._last_alert_at is None:
            return True
        now = now if now is not None else time.monotonic()
        return (now - self._last_alert_at) >= self.cooldown_seconds

    def seconds_remaining(self, now: float | None = None) -> float:
        if self._last_alert_at is None:
            return 0.0
        now = now if now is not None else time.monotonic()
        elapsed = now - self._last_alert_at
        return max(0.0, self.cooldown_seconds - elapsed)

    def record_alert(self, now: float | None = None) -> None:
        self._last_alert_at = now if now is not None else time.monotonic()
