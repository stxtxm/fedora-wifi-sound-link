#!/bin/bash
set -e
PC_IP="${1:-192.168.1.108}"
PORT="${2:-4711}"
echo "=== RPi RECEIVER ($PC_IP -> 0.0.0.0:$PORT -> KRK AudioBox) ==="
echo "Sink par défaut:"
wpctl status 2>&1 | grep -A5 Sinks || true
pactl info 2>&1 | grep -E "Default Sink|Server Name" || true
echo "Lancement ffmpeg udp s16le -> pulse default (AudioBox USB 96)"
# buffer_size petit pour latence faible, nobuffer
exec ffmpeg -hide_banner -loglevel info -fflags nobuffer -flags low_delay -probesize 32 -f s16le -ar 48000 -ac 2 -i "udp://0.0.0.0:$PORT?buffer_size=65536&fifo_size=1024&overrun_nonfatal=1" -f pulse -buffer_size 1024 default
