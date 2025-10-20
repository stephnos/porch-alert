"""Camera capture for Raspberry Pi."""

from __future__ import annotations

import io

from PIL import Image


class Picamera2Camera:
    def __init__(self, resolution: tuple[int, int]) -> None:
        from picamera2 import Picamera2

        self._picam = Picamera2()
        config = self._picam.create_still_configuration(
            main={"size": resolution, "format": "RGB888"}
        )
        self._picam.configure(config)
        self._picam.start()

    def capture_frame(self) -> Image.Image:
        import numpy as np

        array = self._picam.capture_array()
        return Image.fromarray(array.astype("uint8"), "RGB")

    def close(self) -> None:
        self._picam.stop()
        self._picam.close()


class PicameraLegacyCamera:
    def __init__(self, resolution: tuple[int, int]) -> None:
        import picamera

        self._camera = picamera.PiCamera(resolution=resolution)

    def capture_frame(self) -> Image.Image:
        stream = io.BytesIO()
        self._camera.capture(stream, format="jpeg", use_video_port=True)
        stream.seek(0)
        return Image.open(stream).convert("RGB")

    def close(self) -> None:
        self._camera.close()


def create_camera(backend: str, resolution: tuple[int, int]) -> Picamera2Camera | PicameraLegacyCamera:
    if backend == "picamera2":
        return Picamera2Camera(resolution)
    if backend == "picamera":
        return PicameraLegacyCamera(resolution)
    raise ValueError(f"Unknown camera backend: {backend!r} (use picamera2 or picamera)")
