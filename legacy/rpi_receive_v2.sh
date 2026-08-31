#!/bin/bash
# rpi_receive_v2.sh - RPi reception avec jitter buffer
# Usage: ./rpi_receive_v2.sh <PC_IP> [pcm|opus] [stable|fast] [port]
set -e
PC_IP="${1:-192.168.1.108}"
CODEC="${2:-opus}"
MODE="${3:-stable}"
PORT="${4:-4711}"

echo "=== RPi RECEIVE V2: $CODEC / $MODE on 0.0.0.0:$PORT -> AudioBox KRK ==="
echo "Sink:"
pactl info 2>&1 | grep -E "Default Sink|Server Name" || true
wpctl status 2>&1 | grep -A3 Sinks | head -10 || true

UDP_IN="udp://0.0.0.0:$PORT?buffer_size=262144&fifo_size=8192&overrun_nonfatal=1&timeout=10000000"

if [ "$MODE" = "stable" ]; then
  JITTER="-thread_queue_size 2048 -analyzeduration 0 -probesize 32"
  PULSE_BUF="-buffer_size 4096"
  FILTER="-af aresample=async=1:min_hard_comp=0.100000:first_pts=0"
else
  JITTER="-fflags nobuffer -flags low_delay -probesize 32 -thread_queue_size 512"
  PULSE_BUF="-buffer_size 1024"
  FILTER=""
fi

if [ "$CODEC" = "opus" ]; then
  echo "Codec OPUS 192k (Ogg) -> pulse default"
  exec ffmpeg -hide_banner -loglevel info \
    -thread_queue_size 1024 -fflags nobuffer -analyzeduration 0 -probesize 32 \
    -f ogg -i "$UDP_IN" \
    -af aresample=async=1:min_hard_comp=0.100000:first_pts=0 -f pulse -buffer_size 4096 default
else
  echo "Codec PCM S16LE -> pulse default"
  exec ffmpeg -hide_banner -loglevel info $JITTER \
    -f s16le -ar 48000 -ac 2 -i "$UDP_IN" \
    $FILTER -f pulse $PULSE_BUF default
fi
