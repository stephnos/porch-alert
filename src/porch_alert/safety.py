"""Require person detection across several frames before alerting."""

from __future__ import annotations

from dataclasses import dataclass, field

from porch_alert.detection import Detection


@dataclass
class FrameEvidence:
    person_detected: bool
    person_score: float


@dataclass
class SafetyEvaluator:
    min_frames: int = 3
    min_avg_score: float = 0.35
    _history: list[FrameEvidence] = field(default_factory=list)

    def reset(self) -> None:
        self._history.clear()

    def add_frame(self, person_detected: bool, persons: list[Detection]) -> None:
        score = max((p.score for p in persons), default=0.0) if persons else 0.0
        self._history.append(
            FrameEvidence(person_detected=person_detected, person_score=score)
        )

    def should_alert(self) -> tuple[bool, str]:
        if len(self._history) < self.min_frames:
            return False, f"need {self.min_frames} frames, have {len(self._history)}"

        recent = self._history[-self.min_frames :]

        if not all(f.person_detected for f in recent):
            return False, "person not present in all confirmation frames"

        avg_score = sum(f.person_score for f in recent) / len(recent)
        if avg_score < self.min_avg_score:
            return False, "person detection confidence too low"

        prior = self._history[: -self.min_frames]
        if prior and all(not p.person_detected for p in prior[-2:]):
            return False, "person showed up on the last frames only"

        return True, "ok"
