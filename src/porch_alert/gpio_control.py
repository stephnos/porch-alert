"""PIR motion sensor on GPIO."""

from __future__ import annotations


class GpioMotionSensor:
    def __init__(self, pin: int) -> None:
        from gpiozero import MotionSensor as PiMotionSensor

        self._sensor = PiMotionSensor(pin)

    def wait_for_motion(self, timeout: float | None = None) -> bool:
        if timeout is None:
            self._sensor.wait_for_motion()
            return True
        self._sensor.wait_for_motion(timeout=timeout)
        return self._sensor.motion_detected

    def close(self) -> None:
        self._sensor.close()
