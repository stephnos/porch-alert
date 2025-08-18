# Porch Alert

Raspberry Pi porch monitor: PIR on GPIO 4 wakes the Pi Camera, TensorFlow Lite checks for a person across several frames, then emails a snapshot.

Default recipient: `stephanos@papatsaras.com` (override with `PORCH_ALERT_EMAIL_TO`).

## Wiring

| Part | Pin |
|------|-----|
| PIR | GPIO 4 (BCM) |
| Pi Camera | camera port |
| Optional LED/buzzer | GPIO 26 (BCM) — not wired in this version |

## Install (Raspberry Pi OS)

```bash
bash scripts/install_pi.sh ~/porch-alert
cd ~/porch-alert
source .venv/bin/activate
```

1. Download the model — see [models/README.md](models/README.md).
2. `cp config.example.yaml config.yaml` and set `email.from`.
3. Export SMTP (see below). Use `dry_run: true` in `config.yaml` first if you want to test without sending mail.
4. `python scripts/check_setup.py` — one capture + detection test
5. Run in the foreground: `porch-alert`
6. Enable the service: `sudo systemctl enable --now porch-alert`

## SMTP

Do not commit passwords. Set:

| Variable | Purpose |
|----------|---------|
| `PORCH_ALERT_SMTP_HOST` | SMTP server |
| `PORCH_ALERT_SMTP_PORT` | Default `587` (STARTTLS); use `465` with `smtp_use_ssl: true` in config |
| `PORCH_ALERT_SMTP_USER` | Login user |
| `PORCH_ALERT_SMTP_PASSWORD` | Password or app password |
| `PORCH_ALERT_EMAIL_TO` | Override recipient |

Or `PORCH_ALERT_SMTP_PASSWORD_FILE` pointing at a root-only file.

Example systemd override (`/etc/systemd/system/porch-alert.service.d/smtp.conf`):

```ini
[Service]
Environment=PORCH_ALERT_SMTP_HOST=smtp.gmail.com
Environment=PORCH_ALERT_SMTP_USER=you@gmail.com
Environment=PORCH_ALERT_SMTP_PASSWORD=your-app-password
```

## Notes

Requires `models/detect.tflite`, Pi camera (`picamera2` recommended), and PIR on BCM 4. `safety.py` needs a person on every confirmation frame (default 3). Cooldown is 15 minutes after a sent alert. Check `logs/porch_alert.log` if alerts look wrong.
