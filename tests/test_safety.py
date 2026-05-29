from porch_alert.detection import Detection
from porch_alert.safety import SafetyEvaluator


def _person(score: float = 0.8):
    return [Detection(class_id=0, label="person", score=score)]


def test_requires_min_frames():
    ev = SafetyEvaluator(min_frames=3)
    ev.add_frame(True, _person())
    ok, reason = ev.should_alert()
    assert not ok
    assert "need 3 frames" in reason


def test_alerts_when_consistent():
    ev = SafetyEvaluator(min_frames=3)
    for _ in range(3):
        ev.add_frame(True, _person())
    ok, reason = ev.should_alert()
    assert ok
    assert reason == "ok"


def test_rejects_without_person():
    ev = SafetyEvaluator(min_frames=2)
    ev.add_frame(True, _person())
    ev.add_frame(False, [])
    ok, reason = ev.should_alert()
    assert not ok
    assert "person" in reason


def test_rejects_single_frame_spike():
    ev = SafetyEvaluator(min_frames=3)
    ev.add_frame(False, [])
    ev.add_frame(False, [])
    ev.add_frame(True, _person())
    ev.add_frame(True, _person())
    ev.add_frame(True, _person())
    ok, reason = ev.should_alert()
    assert not ok
    assert "last frames only" in reason
