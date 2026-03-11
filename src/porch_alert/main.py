"""Main entry point: motion → capture → detect → safety → email."""

from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from porch_alert.camera import create_camera
from porch_alert.config import Config, load_config, resolve_path, validate_config
from porch_alert.cooldown import CooldownTracker
from porch_alert.detection import Detection, TfliteDetector, create_detector
from porch_alert.email_alert import (
    SmtpEmailSender,
    apply_porch_roi,
    build_body,
    build_subject,
    format_detection_summary,
    frame_to_jpeg,
)
from porch_alert.gpio_control import GpioMotionSensor
from porch_alert.safety import SafetyEvaluator


def setup_logging(cfg: Config) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if cfg.log_file:
        log_path = Path(cfg.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path))
    logging.basicConfig(
        level=getattr(logging, cfg.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def _base_dir() -> Path:
    return Path.cwd()


@dataclass
class CapturedFrame:
    image: Image.Image
    has_person: bool
    persons: list[Detection]


def build_components(cfg: Config, base: Path | None = None):
    base = base or _base_dir()
    logger = logging.getLogger(__name__)

    motion = GpioMotionSensor(cfg.motion_pin)
    camera = create_camera(cfg.camera_backend, cfg.camera_resolution)
    model_path = resolve_path(base, cfg.model_path)
    labels_path = resolve_path(base, cfg.labels_path)
    detector = create_detector(
        model_path,
        labels_path,
        cfg.detection_threshold,
        cfg.detection_classes,
    )
    email_sender = SmtpEmailSender(cfg.email, dry_run=cfg.dry_run)
    safety = SafetyEvaluator(
        min_frames=cfg.min_confirm_frames,
        min_avg_score=min(0.35, cfg.detection_threshold),
    )
    cooldown = CooldownTracker.from_minutes(cfg.cooldown_minutes)

    logger.info(
        "ready backend=%s dry_run=%s to=%s model=%s",
        cfg.camera_backend,
        cfg.dry_run,
        cfg.email.to,
        model_path,
    )
    return motion, camera, detector, email_sender, safety, cooldown


def _best_frame(frames: list[CapturedFrame]) -> CapturedFrame:
    return max(
        frames,
        key=lambda f: max((p.score for p in f.persons), default=0.0),
    )


def process_motion_event(
    cfg: Config,
    camera,
    detector: TfliteDetector,
    email_sender: SmtpEmailSender,
    safety: SafetyEvaluator,
    cooldown: CooldownTracker,
) -> bool:
    logger = logging.getLogger(__name__)

    if not cooldown.can_alert():
        remaining = int(cooldown.seconds_remaining())
        logger.info("cooldown active (%ss remaining); skipping alert", remaining)
        return False

    safety.reset()
    captured: list[CapturedFrame] = []

    try:
        for i in range(cfg.min_confirm_frames):
            frame = camera.capture_frame()
            cropped = apply_porch_roi(frame, cfg.porch_roi)
            has_person, persons = detector.has_target(cropped)

            logger.info(
                "frame=%s person=%s detections=%s",
                i + 1,
                has_person,
                [(p.label, round(p.score, 2)) for p in persons],
            )

            safety.add_frame(has_person, persons)
            captured.append(
                CapturedFrame(image=frame, has_person=has_person, persons=persons)
            )

            if i < cfg.min_confirm_frames - 1:
                time.sleep(cfg.frame_interval_seconds)

        ok, reason = safety.should_alert()
        logger.info("safety decision: alert=%s reason=%s", ok, reason)

        if not ok:
            return False

        recent = captured[-cfg.min_confirm_frames :]
        best = _best_frame(recent)
        detected_at = datetime.now(timezone.utc).astimezone()
        subject = build_subject(cfg.email.subject_prefix, detected_at)
        summary = format_detection_summary(best.persons)
        body = build_body(summary, detected_at)
        jpeg = frame_to_jpeg(best.image)

        if not jpeg:
            raise RuntimeError("failed to encode alert JPEG")

        email_sender.send_alert(subject, body, jpeg)
        cooldown.record_alert()
        return True

    except Exception:
        logger.exception("motion event failed; no alert sent")
        return False


def run_loop(cfg: Config | None = None) -> None:
    cfg = cfg or load_config()
    base = _base_dir()
    validate_config(cfg, base)
    setup_logging(cfg)
    logger = logging.getLogger(__name__)
    logger.info(
        "starting porch alert dry_run=%s backend=%s to=%s",
        cfg.dry_run,
        cfg.camera_backend,
        cfg.email.to,
    )

    motion, camera, detector, email_sender, safety, cooldown = build_components(cfg, base)

    try:
        while True:
            logger.debug("waiting for motion...")
            motion.wait_for_motion()
            try:
                process_motion_event(
                    cfg, camera, detector, email_sender, safety, cooldown
                )
            except Exception:
                logger.exception("processing failed")
            time.sleep(cfg.poll_interval_seconds)
    except KeyboardInterrupt:
        logger.info("shutting down")
    finally:
        camera.close()
        motion.close()


def run() -> None:
    run_loop()


if __name__ == "__main__":
    run()
