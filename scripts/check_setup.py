#!/usr/bin/env python3
"""One-shot check: config, model, camera capture, person detection. Run on the Pi."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from porch_alert.config import load_config, resolve_path, validate_config  # noqa: E402
from porch_alert.detection import create_detector  # noqa: E402
from porch_alert.camera import create_camera  # noqa: E402
from porch_alert.email_alert import apply_porch_roi  # noqa: E402


def main() -> int:
    import os

    os.chdir(ROOT)
    cfg_path = os.environ.get("PORCH_ALERT_CONFIG", str(ROOT / "config.yaml"))
    if not Path(cfg_path).is_file():
        cfg_path = str(ROOT / "config.example.yaml")
        print(f"using {cfg_path} (copy to config.yaml for production)")

    cfg = load_config(cfg_path)
    validate_config(cfg, ROOT)

    print(f"camera: {cfg.camera_backend} {cfg.camera_resolution}")
    print(f"model: {cfg.model_path}")
    print(f"email to: {cfg.email.to} dry_run={cfg.dry_run}")

    detector = create_detector(
        resolve_path(ROOT, cfg.model_path),
        resolve_path(ROOT, cfg.labels_path),
        cfg.detection_threshold,
        cfg.detection_classes,
    )

    camera = create_camera(cfg.camera_backend, cfg.camera_resolution)
    try:
        frame = camera.capture_frame()
        cropped = apply_porch_roi(frame, cfg.porch_roi)
        found, persons = detector.has_target(cropped)
        print(f"capture: {frame.size[0]}x{frame.size[1]} person={found}")
        for p in persons:
            print(f"  {p.label} {p.score:.2f}")
    finally:
        camera.close()

    return 0 if found else 1


if __name__ == "__main__":
    raise SystemExit(main())
