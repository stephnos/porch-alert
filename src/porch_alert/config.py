"""Load configuration from YAML file and environment overrides."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


def _env_bool(key: str, default: bool) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    return int(raw) if raw is not None else default


def _env_float(key: str, default: float) -> float:
    raw = os.environ.get(key)
    return float(raw) if raw is not None else default


@dataclass
class EmailConfig:
    to: str = "stephanos@papatsaras.com"
    from_addr: str = "porch-alert@yourdomain.com"
    subject_prefix: str = "Porch alert"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_ssl: bool = False

    def apply_env_overrides(self) -> None:
        if to := os.environ.get("PORCH_ALERT_EMAIL_TO"):
            self.to = to
        if host := os.environ.get("PORCH_ALERT_SMTP_HOST"):
            self.smtp_host = host
        self.smtp_port = _env_int("PORCH_ALERT_SMTP_PORT", self.smtp_port)
        if user := os.environ.get("PORCH_ALERT_SMTP_USER"):
            self.smtp_user = user
        if password := os.environ.get("PORCH_ALERT_SMTP_PASSWORD"):
            self.smtp_password = password
        elif path := os.environ.get("PORCH_ALERT_SMTP_PASSWORD_FILE"):
            self.smtp_password = Path(path).read_text(encoding="utf-8").strip()


@dataclass
class Config:
    dry_run: bool = False
    log_level: str = "INFO"
    log_file: str | None = "logs/porch_alert.log"

    motion_pin: int = 4

    camera_resolution: tuple[int, int] = (640, 480)
    camera_backend: str = "picamera2"

    model_path: str = "models/detect.tflite"
    labels_path: str = "models/coco_labels.txt"
    detection_threshold: float = 0.4
    detection_classes: tuple[str, ...] = ("person",)
    porch_roi: tuple[float, float, float, float] | None = None

    min_confirm_frames: int = 3
    frame_interval_seconds: float = 0.5
    cooldown_minutes: int = 15
    poll_interval_seconds: float = 10.0

    email: EmailConfig = field(default_factory=EmailConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        cam = data.get("camera", {})
        res = cam.get("resolution", [640, 480])
        roi = data.get("porch_roi")
        classes = data.get("detection_classes", ["person"])
        email_data = data.get("email", {})
        email = EmailConfig(
            to=email_data.get("to", "stephanos@papatsaras.com"),
            from_addr=email_data.get("from", "porch-alert@yourdomain.com"),
            subject_prefix=email_data.get("subject_prefix", "Porch alert"),
            smtp_host=email_data.get("smtp_host", ""),
            smtp_port=int(email_data.get("smtp_port", 587)),
            smtp_user=email_data.get("smtp_user", ""),
            smtp_password=email_data.get("smtp_password", ""),
            smtp_use_ssl=bool(email_data.get("smtp_use_ssl", False)),
        )
        return cls(
            dry_run=data.get("dry_run", False),
            log_level=data.get("log_level", "INFO"),
            log_file=data.get("log_file"),
            motion_pin=data.get("motion_pin", 4),
            camera_resolution=(int(res[0]), int(res[1])),
            camera_backend=cam.get("backend", "picamera2"),
            model_path=data.get("model_path", "models/detect.tflite"),
            labels_path=data.get("labels_path", "models/coco_labels.txt"),
            detection_threshold=float(data.get("detection_threshold", 0.4)),
            detection_classes=tuple(classes),
            porch_roi=tuple(roi) if roi else None,
            min_confirm_frames=int(data.get("min_confirm_frames", 3)),
            frame_interval_seconds=float(data.get("frame_interval_seconds", 0.5)),
            cooldown_minutes=int(data.get("cooldown_minutes", 15)),
            poll_interval_seconds=float(data.get("poll_interval_seconds", 10.0)),
            email=email,
        )

    def apply_env_overrides(self) -> None:
        self.dry_run = _env_bool("PORCH_ALERT_DRY_RUN", self.dry_run)
        self.motion_pin = _env_int("PORCH_ALERT_MOTION_PIN", self.motion_pin)
        self.detection_threshold = _env_float(
            "PORCH_ALERT_DETECTION_THRESHOLD", self.detection_threshold
        )
        if model := os.environ.get("PORCH_ALERT_MODEL"):
            self.model_path = model
        self.email.apply_env_overrides()


def load_config(path: str | Path | None = None) -> Config:
    path = Path(path or os.environ.get("PORCH_ALERT_CONFIG", "config.yaml"))
    data: dict[str, Any] = {}
    if path.is_file():
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    cfg = Config.from_dict(data)
    cfg.apply_env_overrides()
    return cfg


def resolve_path(base: Path, relative: str) -> Path:
    p = Path(relative)
    return p if p.is_absolute() else (base / p).resolve()


def validate_config(cfg: Config, base: Path) -> None:
    if cfg.camera_backend not in ("picamera2", "picamera"):
        raise ValueError(
            f"camera.backend must be picamera2 or picamera, got {cfg.camera_backend!r}"
        )
    model = resolve_path(base, cfg.model_path)
    labels = resolve_path(base, cfg.labels_path)
    if not model.is_file():
        raise FileNotFoundError(f"TFLite model not found: {model}")
    if not labels.is_file():
        raise FileNotFoundError(f"Labels file not found: {labels}")
    if not cfg.dry_run and not cfg.email.smtp_host:
        raise RuntimeError(
            "SMTP host required when dry_run is false (set PORCH_ALERT_SMTP_HOST)"
        )
