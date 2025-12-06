from porch_alert.cooldown import CooldownTracker


def test_allows_first_alert():
    cd = CooldownTracker(cooldown_seconds=60)
    assert cd.can_alert(now=0.0)


def test_blocks_within_cooldown():
    cd = CooldownTracker(cooldown_seconds=900)
    cd.record_alert(now=100.0)
    assert not cd.can_alert(now=500.0)
    assert cd.seconds_remaining(now=500.0) == 500.0
