#!/bin/bash
# pc_stream_v2.sh - PC -> RPi avec modes resilient pour wifi pourri
# Usage: ./pc_stream_v2.sh <RPI_IP> [pcm|opus] [stable|fast] [port]
set -e
RPI_IP="${1:-192.168.1.101}"
CODEC="${2:-opus}"      # pcm = lossless 1536kbps, opus = 192kbps resilient
MODE="${3:-stable}"     # stable = gros buffer ~500ms, fast = low latency ~50ms
PORT="${4:-4711}"

echo "=== PC STREAM V2: $CODEC / $MODE -> $RPI_IP:$PORT ==="
command -v ffmpeg >/dev/null || { echo "ffmpeg manquant"; exit 1; }

MONITOR=$(pactl get-default-sink 2>/dev/null || echo "alsa_output.pci-0000_00_1f.3.analog-stereo")
MONITOR="${MONITOR}.monitor"
if ! pactl list short sources 2>/dev/null | grep -q "$MONITOR"; then
  MONITOR=$(pactl list short sources 2>/dev/null | grep monitor | head -1 | awk '{print $2}')
fi
echo "Monitor: $MONITOR"

# params selon mode
if [ "$MODE" = "stable" ]; then
  UDP_OPTS="pkt_size=512&buffer_size=262144"
  THREAD_Q=1024
else
  UDP_OPTS="pkt_size=1024&buffer_size=65536"
  THREAD_Q=512
fi

if [ "$CODEC" = "opus" ]; then
  # Opus 192k VBR + FEC : ultra resilient, 8x moins de bande que PCM, qualité transparente
  echo "Codec: OPUS 192k VBR FEC (recommandé wifi pourri, qualité ~ transparente)"
  echo "Bande: 192 kbps vs 1536 kbps PCM => 8x moins de saccades"
  exec ffmpeg -hide_banner -loglevel info -thread_queue_size $THREAD_Q \
    -f pulse -i "$MONITOR" \
    -ac 2 -ar 48000 \
    -c:a libopus -b:a 192k -vbr on -compression_level 10 -application audio \
    -frame_duration 20 -fec 1 -packet_loss 15 \
    -f ogg "udp://$RPI_IP:$PORT?$UDP_OPTS"
else
  echo "Codec: PCM S16LE 1536k lossless (qualité max, plus sensible wifi)"
  if [ "$MODE" = "stable" ]; then
    echo "Buffer 262KB ~1.3s latence mais stable"
  fi
  exec ffmpeg -hide_banner -loglevel info -thread_queue_size $THREAD_Q \
    -f pulse -i "$MONITOR" \
    -ac 2 -ar 48000 -acodec pcm_s16le -f s16le -flush_packets 0 \
    "udp://$RPI_IP:$PORT?$UDP_OPTS"
fi
