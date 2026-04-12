#!/usr/bin/env bash
# Run on Raspberry Pi OS as user pi (or your service user).
set -euo pipefail

REPO_DIR="${1:-$HOME/porch-alert}"
cd "$REPO_DIR"

echo "==> System packages"
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip libcamera-dev

echo "==> Python venv"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .

if [[ ! -f config.yaml ]]; then
  cp config.example.yaml config.yaml
  echo "Created config.yaml — set email.from and SMTP env vars."
fi

mkdir -p logs models

echo "==> systemd unit (porch-alert.service)"
sudo tee /etc/systemd/system/porch-alert.service > /dev/null <<EOF
[Unit]
Description=Porch Alert
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$REPO_DIR
Environment=PORCH_ALERT_CONFIG=$REPO_DIR/config.yaml
ExecStart=$REPO_DIR/.venv/bin/porch-alert
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "Done. Next steps:"
echo "  1. curl -L -o models/detect.tflite (see models/README.md)"
echo "  2. Export PORCH_ALERT_SMTP_* or use dry_run: true for a dry test"
echo "  3. source .venv/bin/activate && python scripts/check_setup.py"
echo "  4. porch-alert   # foreground"
echo "  5. sudo systemctl enable --now porch-alert"
