#!/bin/bash
set -e
RPI_IP="${1:-192.168.1.101}"
RTP_PORT="${2:-4711}"

echo "=== PC -> RPi STREAM (192.168.1.108 -> $RPI_IP:$RTP_PORT) ==="
command -v ffmpeg >/dev/null || { echo "ffmpeg manquant"; exit 1; }

# Detect monitor source auto (PipeWire/Pulse)
MONITOR=$(pactl get-default-sink 2>/dev/null || echo "alsa_output.pci-0000_00_1f.3.analog-stereo")
MONITOR="${MONITOR}.monitor"
# verify exists, sinon fallback grep
if ! pactl list short sources 2>/dev/null | grep -q "$MONITOR"; then
  MONITOR=$(pactl list short sources 2>/dev/null | grep monitor | head -1 | awk '{print $2}')
  if [ -z "$MONITOR" ]; then
    MONITOR="alsa_output.pci-0000_00_1f.3.analog-stereo.monitor"
  fi
fi
echo "Source monitor: $MONITOR"
pactl list short sources

echo "Lancement ffmpeg pulse -> udp://$RPI_IP:$RTP_PORT (s16le 48k stereo, pkt 1024)"
# flush_packets pour faible latence
exec ffmpeg -hide_banner -loglevel info -f pulse -i "$MONITOR" -ac 2 -ar 48000 -acodec pcm_s16le -f s16le -flush_packets 1 "udp://$RPI_IP:$RTP_PORT?pkt_size=1024&buffer_size=65536"
