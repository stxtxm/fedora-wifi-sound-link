#!/bin/bash
# Fedora Wifi Sound Link - PC Sender v3 (Roc + fallback ffmpeg stable)
# Usage: ./pc_sender.sh <RPI_IP> [pcm|opus|roc] [stable|fast] [port]
set -e
RPI_IP="${1:-192.168.1.101}"
CODEC="${2:-pcm}"
MODE="${3:-stable}"
PORT="${4:-4711}"

# Roc ports (si roc) - rtp+rs8m consolidé + rtcp
ROC_SRC="$PORT"
ROC_CTRL=$((PORT+1))

MONITOR=$(pactl get-default-sink 2>/dev/null || echo "alsa_output.pci-0000_00_1f.3.analog-stereo")
MONITOR="${MONITOR}.monitor"
if ! pactl list short sources 2>/dev/null | grep -q "$MONITOR"; then
  MONITOR=$(pactl list short sources 2>/dev/null | grep monitor | head -1 | awk '{print $2}')
fi
echo "Monitor: $MONITOR -> $RPI_IP:$PORT ($CODEC/$MODE)"

if [ "$CODEC" = "roc" ]; then
  if command -v roc-send >/dev/null 2>&1; then
    echo "Mode ROC (real-time streaming, FEC, jitter buffer adaptatif) - QUALITÉ MAX"
    LAT="300ms"
    if [ "$MODE" = "fast" ]; then LAT="80ms"; fi
    echo "ROC latency $LAT -> rtp+rs8m://$RPI_IP:$ROC_SRC + rtcp://$RPI_IP:$ROC_CTRL"
    exec roc-send -v -i pulse://"$MONITOR" -s rtp+rs8m://$RPI_IP:$ROC_SRC -c rtcp://$RPI_IP:$ROC_CTRL --rate 48000 --target-latency=$LAT --resampler-profile=high
  else
    echo "roc-send manquant, fallback PCM stable"
    CODEC="pcm"; MODE="stable"
  fi
fi

if [ "$CODEC" = "opus" ]; then
  UDP_OPTS="pkt_size=512&buffer_size=262144"
  exec ffmpeg -hide_banner -loglevel info -thread_queue_size 1024 -f pulse -i "$MONITOR" -ac 2 -ar 48000 -c:a libopus -b:a 192k -vbr on -application audio -frame_duration 20 -fec 1 -packet_loss 15 -f ogg "udp://$RPI_IP:$PORT?$UDP_OPTS"
else
  # PCM - envoi S32LE natif hardware pour éviter conversion (AudioBox natif S32LE)
  # Mais bande double, on offre S16LE par défaut + S32LE haute qualité option via env
  FMT="s16le"; CODEC_PCM="pcm_s16le"; BITS=16
  if [ "$PCM_FMT" = "s32" ]; then FMT="s32le"; CODEC_PCM="pcm_s32le"; BITS=32; fi
  if [ "$MODE" = "stable" ]; then
    echo "PCM $BITS-bit stable 262KB buffer ~600ms latence"
    exec ffmpeg -hide_banner -loglevel info -thread_queue_size 2048 -f pulse -i "$MONITOR" -ac 2 -ar 48000 -acodec $CODEC_PCM -f $FMT -flush_packets 0 "udp://$RPI_IP:$PORT?pkt_size=512&buffer_size=262144"
  else
    echo "PCM $BITS-bit fast 64KB low latency ~80ms"
    exec ffmpeg -hide_banner -loglevel info -thread_queue_size 512 -f pulse -i "$MONITOR" -ac 2 -ar 48000 -acodec $CODEC_PCM -f $FMT -flush_packets 1 "udp://$RPI_IP:$PORT?pkt_size=1024&buffer_size=65536"
  fi
fi
