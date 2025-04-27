#!/bin/bash

set -e

# === CONFIG ===
REPO_URL="https://github.com/YOUR_USERNAME/concierge.git"
PROJECT_DIR="/home/dietpi/concierge"
SERVICE_NAME="concierge"
BRANCH_NAME="$1"

# === CHECKS ===
if [ -z "$BRANCH_NAME" ]; then
  echo "Usage: ./install.sh branch-name"
  exit 1
fi

echo "Installing Concierge from branch '$BRANCH_NAME'..."

# === INSTALL PYTHON DEPENDENCIES ===
sudo apt update
sudo apt install -y python3 python3-pip python3.11-venv
# === CREATE VENV ===
python3 -m venv /home/dietpi/concierge/venv

# === ACTIVATE VENV ===
source /home/dietpi/concierge/venv/bin/activate

# === INSTALL PYTHON DEPENDENCIES ===
pip install --upgrade pip
pip install -r requirements.txt

# After install, venv stays isolated.

# === CLONE OR UPDATE REPO ===
if [ ! -d "$PROJECT_DIR" ]; then
  git clone "$REPO_URL" "$PROJECT_DIR"
fi

cd "$PROJECT_DIR"
git fetch
git checkout "$BRANCH_NAME"
git pull origin "$BRANCH_NAME"

# === CREATE DEFAULT CONFIG IF NOT EXISTS ===
if [ ! -f /etc/concierge/config.yaml ]; then
  echo "Creating default /etc/concierge/config.yaml..."
  sudo mkdir -p /etc/concierge
  sudo tee /etc/concierge/config.yaml > /dev/null <<EOF
snapshot_url: "http://192.168.100.191:6688/snapshot.jpg"
telegram_bot_token: "PUT_YOUR_TOKEN_HERE"
notify_user_ids:
  - 123456789
model_path: "/home/dietpi/concierge/yolov8n_person.onnx"
confidence_threshold: 0.5
check_interval_seconds: 60
DEBUG: false
model_path: "/home/dietpi/concierge/yolov8n_person.onnx"
model_url: "https://huggingface.co/.../yolov8n_person.onnx"
EOF
fi

# === INSTALL SYSTEMD SERVICE ===
echo "Installing systemd service..."

sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=Concierge Camera Watcher
After=network.target

[Service]
ExecStart=/usr/bin/python3 $PROJECT_DIR/concierge.py
WorkingDirectory=$PROJECT_DIR
Restart=always
User=dietpi
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}.service
sudo systemctl restart ${SERVICE_NAME}.service

echo "Concierge installed and running."
