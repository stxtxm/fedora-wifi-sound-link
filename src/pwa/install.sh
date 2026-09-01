#!/bin/bash
# Install PWA server on Pi
set -e
DIR="$(cd "$(dirname "$0")/../.." && pwd)"
echo "Install PWA server sur Pi..."
sudo apt update && sudo apt install -y python3-flask 2>&1 | tail -5 || pip3 install flask --quiet
# Service systemd user
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/krk-pwa.service <<EOF
[Unit]
Description=KRK Link PWA Server
After=network.target pipewire.service

[Service]
ExecStart=/usr/bin/python3 $DIR/src/pwa/server.py --host 0.0.0.0 --port 8080
Restart=always
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user enable --now krk-pwa.service 2>&1 | tail -5
echo "PWA lancée sur http://$(hostname -I | awk '{print $1}'):8080"
systemctl --user status krk-pwa.service 2>&1 | head -20
