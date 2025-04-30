#!/bin/bash

set -e

# === CONFIG ===
REPO_URL="https://github.com/YOUR_USERNAME/concierge.git"
PROJECT_DIR="/root/concierge"
SERVICE_NAME="concierge"

# === INSTALL PYTHON DEPENDENCIES ===
sudo apt install -y python3 python3-pip python3.11-venv libgl1
# === CREATE VENV ===
python3 -m venv /root/concierge/venv

# === ACTIVATE VENV ===
source /root/concierge/venv/bin/activate

# === INSTALL PYTHON DEPENDENCIES ===
pip install --upgrade pip
pip install -r requirements.txt
deactivate

# After install, venv stays isolated.


# === CREATE DEFAULT CONFIG IF NOT EXISTS ===
if [ ! -f /etc/concierge/config.yaml ]; then
  echo "Creating default /etc/concierge/config.yaml..."
  sudo mkdir -p /etc/concierge
  sudo tee /etc/concierge/config.yaml > /dev/null <<EOF
snapshot_url: "http://192.168.100.191:6688/snapshot.jpg"
telegram_bot_token: "PUT_YOUR_TOKEN_HERE"
notify_user_ids:
  - 123456789
confidence_threshold: 0.5
check_interval_seconds: 5
DEBUG: false
EOF
fi

# === INSTALL SYSTEMD SERVICE ===
echo "Installing systemd service..."

sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=Concierge Camera Watcher
After=network.target

[Service]
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/concierge.py
WorkingDirectory=$PROJECT_DIR
Restart=always
User=root
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}.service
sudo systemctl restart ${SERVICE_NAME}.service

echo "Concierge installed and running."
