#!/bin/bash
exec >> /tmp/krk_gui_debug.log 2>&1
echo "=== Launched at $(date) ==="
export PATH="$HOME/.local/bin:$PATH"
python3 /home/timo/dev/fedora-wifi-sound-link/src/gui/modern_app.py
