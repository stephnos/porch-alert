from pathlib import Path

import pytest

from porch_alert.config import Config, EmailConfig, load_config, resolve_path, validate_config


def test_load_config_example():
    root = Path(__file__).resolve().parents[1]
    cfg = load_config(root / "config.example.yaml")
    assert cfg.dry_run is False
    assert cfg.camera_backend == "picamera2"
    assert cfg.motion_pin == 4
    assert cfg.email.to == "stephanos@papatsaras.com"


def test_resolve_path_relative():
    base = Path("/tmp/project")
    assert resolve_path(base, "models/x.tflite") == (base / "models/x.tflite").resolve()


def test_env_override_dry_run(monkeypatch):
    monkeypatch.setenv("PORCH_ALERT_DRY_RUN", "true")
    cfg = Config(dry_run=False)
    cfg.apply_env_overrides()
    assert cfg.dry_run is True


def test_env_smtp_overrides(monkeypatch):
    monkeypatch.setenv("PORCH_ALERT_SMTP_HOST", "smtp.test")
    monkeypatch.setenv("PORCH_ALERT_SMTP_PORT", "465")
    email = EmailConfig()
    email.apply_env_overrides()
    assert email.smtp_host == "smtp.test"
    assert email.smtp_port == 465


def test_validate_config_requires_model(tmp_path):
    cfg = Config(model_path="missing.tflite", labels_path="missing.txt")
    with pytest.raises(FileNotFoundError, match="TFLite"):
        validate_config(cfg, tmp_path)


def test_validate_config_requires_smtp_when_live(tmp_path):
    root = Path(__file__).resolve().parents[1]
    labels = root / "models" / "coco_labels.txt"
    model = tmp_path / "detect.tflite"
    model.write_bytes(b"\x00")
    cfg = Config(
        dry_run=False,
        model_path=str(model),
        labels_path=str(labels),
    )
    with pytest.raises(RuntimeError, match="SMTP"):
        validate_config(cfg, tmp_path)
